from config import DATABASE_URL, APP_API_KEY
import json
import datetime
import os
import time
import uvicorn
from pydantic import BaseModel
from fastapi import FastAPI, Header, HTTPException, Request, Depends
from fastapi.responses import JSONResponse
from langchain_core.messages import HumanMessage, SystemMessage
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from database import DatabaseManager
from braintrust import init_logger, traced, current_span
import agent

init_logger(project="Customer_support_system")

db = DatabaseManager(DATABASE_URL)


class TicketRequest(BaseModel):
    customer_message: str
    customer_code: str | None = None


class ReviewRequest(BaseModel):
    ticket_id: str
    human_approved: bool
    human_feedback: str = ""


class ManualReviewRequest(BaseModel):
    ticket_id: str
    proposed_fix: str
    fix_explanation: str


app_graph = None

app = FastAPI(title="AI-Support-System")

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Guarantees every error response is valid JSON, even for an unexpected
    failure (e.g. the upstream LLM provider's rate limit being exhausted after
    our own retries). Without this, FastAPI's default error page is plain
    text, which breaks any client expecting a JSON API."""
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal error occurred while processing the request.", "error_type": type(exc).__name__},
    )


def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != APP_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")


@app.on_event("startup")
async def startup_app():
    global app_graph
    await db.open_pool()
    app_graph = await agent.build_graph()


@app.on_event("shutdown")
async def shutdown_app():
    await db.close_pool()


@app.post("/ticket/stream")
@limiter.limit("5/minute")
@traced
async def analyze_ticket(request: Request, ticket_request: TicketRequest, _: None = Depends(verify_api_key)):
    ticket_id = await db.create_ticket(ticket_request.customer_message, ticket_request.customer_code)
    thread = {"configurable": {"thread_id": ticket_id}}
    formatted_doc = {
        "ticket_id": ticket_id,
        "customer_message": ticket_request.customer_message,
        "customer_code": ticket_request.customer_code,
        "attempt_count": 0,
        "max_attempts": 3,
    }

    try:
        async for event in app_graph.astream(formatted_doc, thread, stream_mode="values"):
            final_event = event
    except Exception:
        await db.update_ticket(ticket_id, status="failed")
        raise

    final_state = await app_graph.aget_state(thread)

    if "Wait_for_human" in final_state.next:
        proposed_fix = json.dumps(final_event.get("proposed_fix", ""))

        await db.update_ticket(
            ticket_id,
            status="pending_review",
            root_cause=final_event.get("root_cause", ""),
            error_diagnosis=final_event.get("error_diagnosis", ""),
            proposed_fix=proposed_fix,
            test_result=final_event.get("test_result", ""),
        )

        await db.save_draft(
            ticket_id=ticket_id,
            attempt_number=1,
            proposed_fix=proposed_fix,
            fix_explanation=final_event.get("fix_explanation", ""),
            test_result=final_event.get("test_result", ""),
            human_approved=None,
            human_feedback="",
        )

        return {
            "ticket_id": ticket_id,
            "status": "pending_review",
            "proposed_fix": final_event.get("proposed_fix", ""),
            "fix_explanation": final_event.get("fix_explanation", ""),
            "test_result": final_event.get("test_result", ""),
        }

    await db.update_ticket(ticket_id, status="failed")
    raise HTTPException(status_code=500, detail="Graph did not stop at human review")


@app.post("/review")
@limiter.limit("5/minute")
@traced
async def review(request: Request, review_request: ReviewRequest, _: None = Depends(verify_api_key)):
    thread = {"configurable": {"thread_id": review_request.ticket_id}}

    await app_graph.aupdate_state(
        thread,
        {
            "human_approved": review_request.human_approved,
            "human_feedback": review_request.human_feedback,
        },
        as_node="Wait_for_human",
    )

    try:
        async for event in app_graph.astream(None, thread, stream_mode="values"):
            final_event = event
    except Exception:
        await db.update_ticket(review_request.ticket_id, status="failed")
        raise

    final_state = await app_graph.aget_state(thread)

    if final_event.get("escalation_summary"):
        await db.update_ticket(
            review_request.ticket_id,
            status="escalated",
            escalation_summary=json.dumps(final_event.get("escalation_summary", "")),
        )
        return {
            "ticket_id": review_request.ticket_id,
            "status": "escalated",
            "escalation_summary": final_event.get("escalation_summary", ""),
        }

    elif final_state.next == ():
        await db.update_ticket(
            review_request.ticket_id,
            status="approved",
            human_approved=final_event.get("human_approved", None),
        )
        return {
            "ticket_id": review_request.ticket_id,
            "status": "approved",
            "human_approved": final_event.get("human_approved", None),
        }

    else:
        proposed_fix = json.dumps(final_event.get("proposed_fix", ""))

        await db.update_ticket(
            review_request.ticket_id,
            status="pending_review",
            human_feedback=review_request.human_feedback,
            proposed_fix=proposed_fix,
            fix_explanation=final_event.get("fix_explanation", ""),
            test_result=final_event.get("test_result", ""),
        )

        await db.save_draft(
            ticket_id=review_request.ticket_id,
            attempt_number=final_event.get("attempt_count", 0) + 1,
            proposed_fix=proposed_fix,
            fix_explanation=final_event.get("fix_explanation", ""),
            test_result=final_event.get("test_result", ""),
            human_approved=False,
            human_feedback=review_request.human_feedback,
        )

        return {
            "ticket_id": review_request.ticket_id,
            "status": "pending_review",
            "proposed_fix": final_event.get("proposed_fix", ""),
            "fix_explanation": final_event.get("fix_explanation", ""),
            "test_result": final_event.get("test_result", ""),
        }


@app.get("/pending-escalations")
@limiter.limit("20/minute")
async def pending_escalations(request: Request, _: None = Depends(verify_api_key)):
    return await db.get_pending_escalations()


@app.post("/submit-manual-fix")
@limiter.limit("5/minute")
async def submit_manual_fix(request: Request, manual_request: ManualReviewRequest, _: None = Depends(verify_api_key)):
    await db.update_ticket(
        manual_request.ticket_id,
        status="resolved",
        proposed_fix=manual_request.proposed_fix,
        fix_explanation=manual_request.fix_explanation,
        human_approved=True,
    )

    return {
        "ticket_id": manual_request.ticket_id,
        "status": "resolved",
        "proposed_fix": manual_request.proposed_fix,
        "fix_explanation": manual_request.fix_explanation,
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)