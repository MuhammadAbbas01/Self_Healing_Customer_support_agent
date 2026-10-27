import ast
import json
import asyncio
from typing import Optional, TypedDict, Literal

import config
import rag
from e2b_code_interpreter import AsyncSandbox
from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg_pool import AsyncConnectionPool
from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq


llm = ChatGroq(
    model= "openai/gpt-oss-20b",
    api_key=config.GROQ_API_KEY
)

#Handling the API...
async def invoke_with_retry(structured_llm, message, max_retries=5):
    last_error = None
    delay = 1
    for attempt in range(max_retries):
        try:
            return await structured_llm.ainvoke(message)
        except Exception as e:
            last_error = e
            status = getattr(e, "status_code", None)
            bad_tool_output = status == 400 and "tool_use_failed" in str(e)
            if (status in (429, 500, 502, 503, 504) or bad_tool_output) and attempt < max_retries - 1:
                print(f"Model call failed (attempt {attempt + 1}/{max_retries}): {e}")
                await asyncio.sleep(delay)
                delay *= 2
            else:
                print(f"Model call failed: {e}")
                break
    raise last_error      

class Triageinfo(BaseModel):
    issue_type: str = Field(..., description="short label for the kind of issue, in your own words based on the message")
    severity: Literal["critical", "high", "medium", "low"] = Field(..., description="""critical = system down or data loss,
    high = some feature is defect and system not working, medium = partial problem, low = low problem not produce any affection """)
    category: str = Field(..., description="area of the system this issue belongs to, in your own words")
    requires_code_fix: bool = Field(..., description="true if the customer's code must change")

class Analyzerinfo(BaseModel):
    root_cause: str = Field(..., description="root cause of the issue")
    error_diagnosis: str = Field(..., description=" the diagnosis of the error")
    expected_solution_type: str = Field(..., description="kind of solution expected, in a few words")


class Fixerinfo(BaseModel):
    estimated_risk: Literal["high", "medium", "safe"] = Field(..., description="""high = the system can stop working,
    medium = part of the system can be affected, safe = the system stays reliable and working""")
    why_this_works: str = Field(..., description="why this solution fixes the problem")
    step_by_step_solution: list[str] = Field(..., description="clear steps of the proposed solution")
    exact_commands: list[str] = Field(default_factory=list, description="commands to run, step by step, if any")
    exact_code_to_use: Optional[str] = Field(None, description="the corrected code, only if the fix needs code")
    exact_config_changes: Optional[str] = Field(None, description="the settings to change, only if the fix needs config")
    before_code: Optional[str] = Field(None, description="the old code or setting, only if relevant")
    after_code: Optional[str] = Field(None, description="the new code or setting, only if relevant")


#___________________________________________AgentState____________________________________________#
class AgentState(TypedDict):
    customer_message: str
    customer_code: Optional[str]
    ticket_id: str
    issue_type: str
    severity: str
    category: str
    requires_code_fix: bool
    relevant_docs: list[str]
    similar_tickets: list[str]
    confidence_score: float
    root_cause: str
    error_diagnosis: str
    expected_solution_type: str
    proposed_fix: dict
    fix_explanation: str
    estimated_risk: str
    test_result: str
    error_logs: str
    attempt_count: int      # sandbox tries
    review_count: int       # human rejections
    max_attempts: int
    verified_solution: str
    human_approved: Optional[bool]
    customer_response: str
    human_feedback: str
    escalation_summary: dict




async def TRIAGE(state: AgentState):
    customer_message = state["customer_message"]
    customer_code = state.get("customer_code")

    system = SystemMessage(content="""You are a technical support triage agent.
Classify the customer's issue using the Triageinfo fields. Be clear, concise and correct.""")

    human = HumanMessage(content=f"""Customer message: {customer_message}
Customer code: {customer_code or "No code provided"}""")

    structured_llm = llm.with_structured_output(Triageinfo)
    result = await invoke_with_retry(structured_llm, [system, human])

    return {
        "issue_type": result.issue_type,
        "severity": result.severity,
        "category": result.category,
        "requires_code_fix": result.requires_code_fix
    }

def RESEARCH(state: AgentState):
    customer_message = state["customer_message"]
    issue_type = state["issue_type"]
    category = state["category"]

    # Retry data (empty on the first run)
    review_count = state.get("review_count", 0)
    human_feedback = state.get("human_feedback", "")

    search_query = f"{customer_message} {issue_type} {category}"

    # After a human rejection, the reviewer's feedback steers the search
    if review_count > 0 and human_feedback:
        print(f"Retry after human rejection {review_count}. Feedback: {human_feedback}")
        search_query += f" {human_feedback}"
    else:
        print("First attempt.")

    relevant_docs, similar_tickets, confidence_score = rag.search_docs(search_query)

    print(f"\nRAG Search: found {len(relevant_docs)} chunks for query: {search_query[:60]}...")

    return {
        "relevant_docs": relevant_docs,
        "similar_tickets": similar_tickets,
        "confidence_score": confidence_score
    }


async def ANALYZER(state: AgentState):
    customer_message = state["customer_message"]
    customer_code = state.get("customer_code")
    relevant_docs = state["relevant_docs"]
    similar_tickets = state["similar_tickets"]
    issue_type = state["issue_type"]
    category = state["category"]

    # NEW: retry data (empty on the first run)
    human_feedback = state.get("human_feedback", "")
    review_count = state.get("review_count", 0)
    previous_root_cause = state.get("root_cause", "")

    system = SystemMessage(content="""You are a technical support analyzer agent.
Analyze and diagnose the customer's issue using the Analyzerinfo fields. Be clear, concise and correct.
Use the provided documents and similar tickets only if they are relevant to this issue.""")

    docs_text = "\n---\n".join(relevant_docs) or "None found"
    tickets_text = "\n---\n".join(similar_tickets) or "None found"

    # NEW: only filled after a human rejection
    retry_text = (
        f"\n\nA human reviewer rejected the previous solution.\n"
        f"Previous root cause: {previous_root_cause}\n"
        f"Reviewer feedback: {human_feedback}\n"
        f"Re-check the diagnosis. Do not repeat the same root cause if the feedback says it is wrong."
        if review_count > 0 and human_feedback else ""
    )

    human = HumanMessage(content=f"""Customer message: {customer_message}
Customer code: {customer_code or "No code provided"}
Issue type: {issue_type}
Category: {category}

Relevant documents:
{docs_text}

Similar past tickets:
{tickets_text}{retry_text}""")

    structured_llm = llm.with_structured_output(Analyzerinfo)
    result = await invoke_with_retry(structured_llm, [system, human])

    return {
        "root_cause": result.root_cause,
        "error_diagnosis": result.error_diagnosis,
        "expected_solution_type": result.expected_solution_type
    }


async def FIXER(state: AgentState):
    root_cause = state["root_cause"]
    error_diagnosis = state["error_diagnosis"]
    customer_message = state["customer_message"]
    customer_code = state.get("customer_code")
    relevant_docs = state["relevant_docs"]
    similar_tickets = state["similar_tickets"]
    issue_type = state["issue_type"]
    category = state["category"]
    attempt_count = state["attempt_count"]
    error_logs = state.get("error_logs", "")
    expected_solution_type = state["expected_solution_type"]

    # Human rejection data and the previous fix (empty on the first run)
    review_count = state.get("review_count", 0)
    human_feedback = state.get("human_feedback", "")
    previous_fix = state.get("proposed_fix")
    previous_fix_text = (
        json.dumps(previous_fix, default=str)[:2000] if previous_fix else ""
    )

    if attempt_count == 0 and review_count == 0:
        print("First attempt")
    else:
        print(f"Retry: sandbox attempt {attempt_count}, human rejections {review_count}")

    system = SystemMessage(content="""You are a technical support fixer agent.
Propose a correct and clear fix for the customer's issue using the Fixerinfo fields.
Base the fix on the provided documents when they are relevant.
Fill the code, config and command fields only if this fix needs them.""")

    docs_text = "\n---\n".join(relevant_docs) or "None found"
    tickets_text = "\n---\n".join(similar_tickets) or "None found"

    # Sandbox retry: the previous fix failed when it was run
    sandbox_retry_text = (
        f"\n\nThe previous fix failed in the sandbox.\n"
        f"Previous fix: {previous_fix_text}\n"
        f"Error: {error_logs}\n"
        f"Do not repeat it."
        if attempt_count > 0 and error_logs else ""
    )

    # Human retry: a human reviewer rejected the previous fix
    human_retry_text = (
        f"\n\nA human reviewer rejected a previous fix.\n"
        f"Rejected fix: {previous_fix_text}\n"
        f"Reviewer feedback: {human_feedback}\n"
        f"Follow the feedback. Do not repeat the rejected fix."
        if review_count > 0 and human_feedback else ""
    )

    human = HumanMessage(content=f"""Customer message: {customer_message}
Customer code: {customer_code or "No code provided"}
Issue type: {issue_type}
Category: {category}
Root cause: {root_cause}
Error diagnosis: {error_diagnosis}
Expected solution type: {expected_solution_type}
Attempt: {attempt_count + 1}

Relevant documents:
{docs_text}

Similar past tickets:
{tickets_text}{human_retry_text}{sandbox_retry_text}""")

    structured_llm = llm.with_structured_output(Fixerinfo)
    result = await invoke_with_retry(structured_llm, [system, human])

    return {
        "proposed_fix": result.model_dump(exclude_none=True),
        "fix_explanation": result.why_this_works,
        "estimated_risk": result.estimated_risk,
    }


async def SANDBOX(state: AgentState):
    """Runs the fix ONCE and reports honestly. The 3-try loop is
    FIXER -> SANDBOX -> route_after_sandbox -> FIXER, not a loop in here.

    test_result values:
      passed  = the code ran with no error
      failed  = the code crashed (this one counts as an attempt)
      skipped = nothing to run (no code, or not valid Python)
      error   = the sandbox itself broke (says nothing about the code)
    """
    proposed_fix = state["proposed_fix"]
    attempt_count = state["attempt_count"]

    code_to_test = proposed_fix.get("exact_code_to_use") if isinstance(proposed_fix, dict) else None
    code_to_test = (code_to_test or "").strip()

    if not code_to_test:
        print("No code to execute - sandbox skipped")
        return {"test_result": "skipped"}

    # Only valid Python is run. Config text, bash and other languages are skipped.
    try:
        ast.parse(code_to_test)
    except SyntaxError:
        print("Not valid Python - sandbox skipped")
        return {"test_result": "skipped"}

    print(f"Running code in E2B sandbox (attempt {attempt_count + 1})...")

    sbx = None
    try:
        sbx = await AsyncSandbox.create()
        execution = await sbx.run_code(code_to_test, timeout=30)
    except Exception as e:
        print(f"Sandbox infrastructure error: {e}")
        return {"test_result": "error", "error_logs": f"Sandbox error: {e}"[:500]}
    finally:
        if sbx:
            await sbx.kill()

    if execution.error:
        detail = f"{execution.error.name}: {execution.error.value}"[:500]
        print(f"Sandbox failed: {detail[:150]}")
        return {
            "test_result": "failed",
            "error_logs": detail,
            "attempt_count": attempt_count + 1,
        }

    print("Sandbox execution passed")
    return {"test_result": "passed"}


def Wait_for_human(state: AgentState):
    """No-op node. The graph is interrupted BEFORE this node (interrupt_before).
    /review writes the human decision with as_node="Wait_for_human"."""
    pass


def HUMAN_REVIEW(state: AgentState):
    """Prepares the draft the human will review. It decides nothing:
    only the human sets human_approved (through /review)."""
    customer_message = state["customer_message"]
    root_cause = state["root_cause"]
    proposed_fix = state["proposed_fix"]
    test_result = state["test_result"]
    attempt_count = state["attempt_count"]
    relevant_docs = state.get("relevant_docs", [])
    similar_tickets = state.get("similar_tickets", [])
    confidence_score = state.get("confidence_score", 0)

    status = {
        "passed": "Sandbox test PASSED",
        "failed": f"Sandbox test FAILED after {attempt_count} attempt(s) - NOT verified",
        "skipped": "NOT TESTED - this fix has no runnable Python code",
        "error": "NOT TESTED - the sandbox had an error",
    }.get(test_result, "Test status unknown")

    verified_solution = (
        json.dumps(proposed_fix, default=str) if test_result == "passed"
        else "Not verified by sandbox"
    )

    step_by_step = proposed_fix.get("step_by_step_solution", [])
    exact_code = proposed_fix.get("exact_code_to_use", "")
    config_changes = proposed_fix.get("exact_config_changes", "")
    commands = proposed_fix.get("exact_commands", [])
    before_code = proposed_fix.get("before_code", "")
    after_code = proposed_fix.get("after_code", "")
    why_works = proposed_fix.get("why_this_works", "")
    risk = proposed_fix.get("estimated_risk", "medium")

    print(f"""
==========================================
TICKET SUMMARY:
==========================================
Customer Issue: {customer_message}
Root Cause: {root_cause}
Test Status: {status}
==========================================
""")

    customer_response = f"""==========================================
PROPOSED SOLUTION (waiting for human review)
==========================================

ISSUE IDENTIFIED:
{root_cause}

STEP-BY-STEP SOLUTION:
"""

    if step_by_step:
        for i, step in enumerate(step_by_step, 1):
            customer_response += f"  Step {i}: {step}\n"
    else:
        customer_response += "  See implementation details below\n"

    customer_response += f"""
IMPLEMENTATION DETAILS:

Code to Use:
  {exact_code if exact_code else 'No specific code changes required'}

Configuration Changes:
  {config_changes if config_changes else 'No configuration changes required'}

Commands to Run:
"""
    if commands:
        for cmd in commands:
            customer_response += f"  $ {cmd}\n"
    else:
        customer_response += "  No specific commands required\n"

    if before_code and after_code:
        customer_response += f"""
BEFORE:
{before_code}

AFTER:
{after_code}
"""

    customer_response += f"""
WHY THIS WORKS:
{why_works}

RISK LEVEL: {risk.upper()}

KNOWLEDGE BASE REFERENCES:
  - Found {len(relevant_docs)} relevant documentation sections
  - Similar resolved tickets: {len(similar_tickets)}
  - Confidence Score: {confidence_score:.0%}

TEST STATUS: {status}

==========================================
For additional support, contact: support@acme.tech
=========================================="""

    return {
        "verified_solution": verified_solution,
        "customer_response": customer_response,
        "human_approved": None,   # reset: a new draft waits for a new decision
    }


def REVIEW_DECISION(state: AgentState):
    """Runs right after the human decision arrives (/review).
    Rejected -> count the rejection and give the sandbox 3 fresh tries."""
    if state.get("human_approved") is True:
        return {}

    return {
        "review_count": state.get("review_count", 0) + 1,
        "attempt_count": 0,
        "error_logs": "",
    }


def route_after_research(state):
    # Low confidence = the docs have no answer. Do not let the fixer guess, send to a human.
    if state.get("confidence_score", 0) < 0.5:
        return "MANUAL_ESCALATION"
    return "ANALYZER"


def route_after_sandbox(state):
    test_result = state["test_result"]
    attempt_count = state["attempt_count"]
    max_attempts = state["max_attempts"]

    # Retry only when the code really failed. skipped / error / passed go to the human.
    if test_result == "failed" and attempt_count < max_attempts:
        return "FIXER"
    return "HUMAN_REVIEW"


def route_after_review(state: AgentState):
    if state.get("human_approved") is True:
        return END
    if state.get("review_count", 0) < state["max_attempts"]:
        return "RESEARCH"
    return "MANUAL_ESCALATION"


def MANUAL_ESCALATION(state: AgentState):
    """Builds the summary a human needs to write the fix by hand.
    Attempt history is already in the ticket_draft table."""
    escalation_summary = {
        "customer_message": state["customer_message"],
        "customer_code": state.get("customer_code"),
        "issue_type": state.get("issue_type", ""),
        "root_cause": state.get("root_cause", ""),
        "error_diagnosis": state.get("error_diagnosis", ""),
        "expected_solution_type": state.get("expected_solution_type", ""),
        "proposed_fix": state.get("proposed_fix", {}),
        "test_result": state.get("test_result", ""),
        "error_logs": state.get("error_logs", ""),
        "human_feedback": state.get("human_feedback", ""),
        "review_count": state.get("review_count", 0),
        "confidence_score": state.get("confidence_score", 0),
        "similar_tickets": state.get("similar_tickets", []),
        "relevant_docs_count": len(state.get("relevant_docs", [])),
    }

    print("Max review attempts reached. Sending ticket to human escalation queue.")

    return {"escalation_summary": escalation_summary}


async def build_graph():
    graph_builder = StateGraph(AgentState)

    graph_builder.add_node("TRIAGE", TRIAGE)
    graph_builder.add_node("RESEARCH", RESEARCH)
    graph_builder.add_node("ANALYZER", ANALYZER)
    graph_builder.add_node("FIXER", FIXER)
    graph_builder.add_node("SANDBOX", SANDBOX)
    graph_builder.add_node("HUMAN_REVIEW", HUMAN_REVIEW)
    graph_builder.add_node("Wait_for_human", Wait_for_human)
    graph_builder.add_node("REVIEW_DECISION", REVIEW_DECISION)
    graph_builder.add_node("MANUAL_ESCALATION", MANUAL_ESCALATION)

    graph_builder.add_edge(START, "TRIAGE")
    graph_builder.add_edge("TRIAGE", "RESEARCH")
    graph_builder.add_conditional_edges(
        "RESEARCH",
        route_after_research,
        {"ANALYZER": "ANALYZER", "MANUAL_ESCALATION": "MANUAL_ESCALATION"},
    )
    graph_builder.add_edge("ANALYZER", "FIXER")
    graph_builder.add_edge("FIXER", "SANDBOX")
    graph_builder.add_edge("HUMAN_REVIEW", "Wait_for_human")
    graph_builder.add_edge("Wait_for_human", "REVIEW_DECISION")
    graph_builder.add_edge("MANUAL_ESCALATION", END)

    graph_builder.add_conditional_edges(
        "SANDBOX",
        route_after_sandbox,
        {
            "HUMAN_REVIEW": "HUMAN_REVIEW",
            "FIXER": "FIXER",
        },
    )

    graph_builder.add_conditional_edges(
        "REVIEW_DECISION",
        route_after_review,
        {
            "RESEARCH": "RESEARCH",
            "MANUAL_ESCALATION": "MANUAL_ESCALATION",
            END: END,
        },
    )

    # The checkpointer needs a long-lived Postgres connection, so it uses the Session pooler
    # (port 5432) instead of the Transaction pooler (6543). A pool with check_connection
    # replaces dead connections automatically (same idea as database.py).
    checkpointer_db_url = config.DATABASE_URL.replace(":6543/", ":5432/")
    pool = AsyncConnectionPool(
        conninfo=checkpointer_db_url,
        max_size=10,
        kwargs={"autocommit": True, "prepare_threshold": 0},
        check=AsyncConnectionPool.check_connection,
        open=False,
    )
    await pool.open()
    memory = AsyncPostgresSaver(pool)
    await memory.setup()

    return graph_builder.compile(interrupt_before=["Wait_for_human"], checkpointer=memory)
