# Self-Healing Customer Support Agent

A production-style multi-agent support system. It reads a customer ticket, finds the answer in the company docs, proposes a fix, and sends it to a **human reviewer**. The human can approve it, or reject it with feedback so the agent tries again. After 3 rejections, or when the docs have no answer, the ticket is **escalated** and a human writes the solution.

Built with LangGraph, FastAPI, Groq, a hybrid RAG pipeline, Supabase, LangSmith and Grafana Cloud.

---

## How it works

```
Customer ticket
      |
   TRIAGE          classifies the issue (Groq LLM)
      |
   RESEARCH        hybrid RAG: vector + BM25 -> RRF merge -> cross-encoder rerank -> confidence gate
      |
      |-- confidence < 0.5 (no answer in docs) ------------------+
      |                                                          |
   ANALYZER        finds root cause and solution type            |
      |                                                          |
   FIXER           writes the step-by-step fix                   |
      |            (retries automatically if the model returns   |
      |             invalid structured output)                   |
   SANDBOX         runs customer code in E2B when code exists    |
      |                                                          |
  HUMAN_REVIEW     pauses here and waits for a human             |
      |                                                          |
  approve --> done                                               |
  reject + feedback --> back to RESEARCH (max 3 rejections) -----+
                                                                 |
                                                       MANUAL_ESCALATION
                                                                 |
                                                human writes the fix (/submit-manual-fix)
```

Key design choices:
- **No guessing.** If the docs do not contain the answer, the agent does not invent one. The ticket goes straight to a human.
- **Human in the loop.** The graph pauses at `Wait_for_human` (LangGraph checkpoint stored in Postgres) and resumes after `/review`.
- **Resilient LLM calls.** Retries on rate limits, server errors, and on `tool_use_failed` (when the model skips required fields).

---

## Tech stack

| Layer | Technology |
|---|---|
| Orchestration | LangGraph (StateGraph, Postgres checkpointer) |
| LLM | Groq, `openai/gpt-oss-20b` |
| RAG | ChromaDB, all-MiniLM-L6-v2, BM25, cross-encoder reranker |
| Code sandbox | E2B Code Interpreter |
| Database | Supabase (PostgreSQL) |
| Tracing | LangSmith (each trace carries the `ticket_id`) |
| Metrics | Grafana Cloud via OTLP (`tickets_total`, label `status`) |
| API | FastAPI, API-key auth, rate limiting (slowapi) |

---

## API

All endpoints need the header `x-api-key: <APP_API_KEY>`. Interactive docs: `http://localhost:8000/docs`.

| Endpoint | Method | What it does |
|---|---|---|
| `/ticket/stream` | POST | Submit a ticket. Returns `pending_review` (proposed fix) or `escalated` (no answer in docs). |
| `/review` | POST | Human decision: `human_approved` true/false + `human_feedback`. Returns `approved`, `pending_review` (new attempt) or `escalated`. |
| `/pending-escalations` | GET | Tickets waiting for a human-written solution. |
| `/submit-manual-fix` | POST | Human writes the final solution. Status becomes `resolved`. |

Ticket statuses: `pending_review`, `approved`, `escalated`, `resolved`, `failed`.

Example:
```bash
curl -X POST http://localhost:8000/ticket/stream \
  -H "x-api-key: $APP_API_KEY" -H "Content-Type: application/json" \
  -d '{"customer_message": "api keeps giving me 401, im sending my key in X-API-Key header"}'
```

---

## Run locally

Python 3.11 is recommended (Linux or WSL).

```bash
python -m venv .venv && source .venv/bin/activate
pip install torch --index-url https://download.pytorch.org/whl/cpu   # small CPU build
pip install -r requirement.txt
cp .env.example .env      # then fill in your keys
python -m uvicorn main:app --port 8000
```

On startup the app opens the database pool, builds the RAG index from `docs/`, and builds the graph.

---

## Environment variables

| Variable | Description |
|---|---|
| `DATABASE_URL` | Supabase PostgreSQL connection string (pooler, port 6543) |
| `GROQ_API_KEY` | Groq API key |
| `APP_API_KEY` | Secret you choose. Clients send it in `x-api-key` |
| `E2B_API_KEY` | E2B sandbox key |
| `LANGCHAIN_TRACING_V2` | `true` to enable LangSmith tracing |
| `LANGCHAIN_API_KEY` | LangSmith API key |
| `LANGCHAIN_PROJECT` | LangSmith project name |
| `GRAFANA_URL` | Grafana OTLP metrics endpoint |
| `GRAFANA_USER` | Grafana instance ID |
| `GRAFANA_TOKEN` | Grafana token |

---

## Observability

- **LangSmith:** one trace per run. Filter by metadata `ticket_id` to find every run of a ticket (first attempt and review attempts).
- **Grafana:** `tickets_total` with label `status` (`created`, `pending_review`, `approved`, `escalated`, `resolved`, `failed`). Sent in a background thread with a 5 second timeout, so a slow Grafana never blocks the API.
- **Supabase:** `tickets` and `ticket_draft` tables keep every attempt, the human feedback and the final result.

---

## Project structure

```
main.py          FastAPI app, endpoints, human-review flow, metrics
agent.py         LangGraph nodes, routing, retry logic
rag.py           Production RAG (hybrid retrieval, rerank, confidence gate)
database.py      Async Postgres manager (psycopg pool)
monitoring.py    Grafana OTLP metric sender
config.py        Environment loader
docs/            Knowledge base (markdown)
golden.py, eval_rag.py   RAG evaluation set and script
Dockerfile       Container image
deploy/          Kubernetes manifests (not yet re-tested for this version)
requirement.txt  Python dependencies
```

---

## Known limits

- The E2B sandbox only runs when the proposed fix contains code. Tickets without code show `test_result: skipped`.
- Kubernetes manifests in `deploy/` come from an earlier version and need review before use.
