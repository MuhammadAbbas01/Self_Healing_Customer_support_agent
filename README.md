# Self-Healing AI Customer Support Agent

A support-ticket agent built with LangGraph: it triages a ticket, retrieves evidence with a production-style hybrid RAG pipeline, proposes a fix with an LLM, **runs the fix in an isolated E2B sandbox**, and feeds any execution error back to the model for a revised attempt. A **human reviews every draft** (approve or reject with feedback) before it is accepted, and tickets the knowledge base cannot answer are escalated to a person with a structured case summary.

![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-async%20API-009688?logo=fastapi&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-agent%20orchestration-1C3C3C)
![Groq](https://img.shields.io/badge/LLM-Groq-black)
![ChromaDB](https://img.shields.io/badge/Vector%20DB-ChromaDB-orange)
![E2B](https://img.shields.io/badge/Sandbox-E2B-ff8800)
![LangSmith](https://img.shields.io/badge/Tracing-LangSmith-1C3C3C)
![Supabase](https://img.shields.io/badge/DB-Supabase%20Postgres-3ECF8E?logo=supabase&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-containerized-2496ED?logo=docker&logoColor=white)
![Kubernetes](https://img.shields.io/badge/Kubernetes-manifests%20%2B%20HPA-326CE5?logo=kubernetes&logoColor=white)
![CI](https://github.com/MuhammadAbbas01/Self_Healing_Customer_support_agent/actions/workflows/ci.yml/badge.svg)

> **Version note.** This is **v2**. The original version is preserved on the `v1` branch and the `v1.0` tag (single `/ticket` endpoint, basic structure check instead of sandbox execution, automatic review). See [Versions](#versions).

---

## Overview

Traditional support bots answer from a static script and stop when they're wrong. This agent loops: after generating a candidate fix it runs the fix's code in an E2B sandbox, and if that fails it returns the execution error to the Fixer for a revised attempt, up to a retry limit. Then a human approves or rejects the draft; a rejection with feedback sends the ticket back through research for a better answer, and after three rejections it is escalated to a human agent with a case summary.

Context for each ticket comes from a RAG pipeline over three markdown sources: a company technical handbook, a wiki, and a searchable archive of past tickets. If the retrieved evidence is too weak, a **confidence gate** refuses to pass it to the model and escalates the ticket instead of letting the LLM guess.

---

## How It Works

```mermaid
graph TD
    START((Ticket)) --> TRIAGE[Triage Node]
    TRIAGE --> RESEARCH["Research Node<br/>hybrid RAG + confidence gate"]
    RESEARCH -- "weak evidence (gate)" --> ESCALATE
    RESEARCH --> ANALYZER[Analyzer Node]
    ANALYZER --> FIXER[Fixer Node]
    FIXER --> SANDBOX["Validation Node<br/>runs the fix in an E2B sandbox"]
    SANDBOX -- "Test failed, retries left" --> FIXER
    SANDBOX -- "Passed, skipped, or retries exhausted" --> WAIT["Human review<br/>graph paused, state saved in Postgres"]
    WAIT -- "Approve" --> DONE((Approved))
    WAIT -- "Reject + feedback (up to 3)" --> RESEARCH
    WAIT -- "3 rejections" --> ESCALATE["Manual escalation<br/>structured case summary"]
    ESCALATE --> HUMAN["Human agent<br/>POST /submit-manual-fix"]

    subgraph "Knowledge base"
        DOCS[(Company docs)]
        TICKETS[(Ticket archive)]
        WIKI[(Engineering wiki)]
    end

    RESEARCH -.-> DOCS
    RESEARCH -.-> TICKETS
    RESEARCH -.-> WIKI

    subgraph "Observability"
        LANGSMITH[LangSmith traces]
        GRAFANA[Grafana Cloud]
        SUPA[(Supabase audit trail)]
    end

    DONE -.-> GRAFANA
    FIXER -.-> LANGSMITH
    WAIT -.-> SUPA
```

1. **Triage** — an LLM classifies the incoming ticket by type, severity and technical domain.
2. **Research (RAG)** — hybrid retrieval (vector + BM25, merged with RRF, reranked by a cross-encoder) pulls the most relevant docs, wiki entries and similar past tickets. A confidence gate stops weak evidence from reaching the model.
3. **Analyzer** — combines the triage result and retrieved context to identify the likely root cause and the type of fix needed (code fix, config change, or a system-level bug).
4. **Fixer** — generates a concrete proposed solution, including corrected code when the fix needs it.
5. **Validation (E2B sandbox)** — runs the proposed Python in an isolated E2B sandbox. Results are `passed`, `failed`, `skipped` (nothing to run, or not valid Python) or `error` (the sandbox itself broke). Only a real code failure counts as an attempt.
6. **Adaptive routing** — a failed run loops back to the Fixer with the execution error (up to 3 attempts); a passing, skipped or exhausted run goes to human review.
7. **Human review** — the graph pauses (`interrupt_before`) with its state checkpointed in Postgres, so it survives restarts. `POST /review` resumes it: approve finishes the ticket, reject (with feedback) re-runs research with that feedback, and after 3 rejections the ticket is escalated with a structured case summary.
8. **Escalation** — tickets with weak evidence, or 3 rejections, land in a human queue (`GET /pending-escalations`) and are closed with `POST /submit-manual-fix`.

---

## Production RAG

The retrieval layer was built and evaluated on its own before being wired into the agent.

| Stage | What it does |
|---|---|
| Chunking | Heading-aware splitting of the three markdown sources in `data/` (174 chunks) |
| Vector search | Dense retrieval from a persistent ChromaDB index, top 30 candidates |
| BM25 | Keyword retrieval over the same chunks, top 30 candidates |
| RRF fusion | Reciprocal Rank Fusion merges the two ranked lists |
| Cross-encoder rerank | A cross-encoder rescores the merged candidates and keeps the best 5 |
| Confidence gate | If the best rerank score is below the calibrated threshold (−5.0), no context is passed to the LLM and the ticket is escalated |

### Retrieval quality

Measured on a hand-labelled golden set of 30 questions, 10 of them held out (never used for tuning), across two tagged releases of the retrieval pipeline:

| Held-out metric | Release 1 | Release 2 |
|---|---|---|
| hit@1 | 60% | **80%** |
| hit@5 | 90% | **100%** |
| MRR | 0.73 | **0.90** |

### Confidence gate

The gate threshold was calibrated on the development questions plus a small set of out-of-scope questions. It was then checked offline (retrieval layer only, no LLM) on questions it had never seen:

| Question group | Result |
|---|---|
| 10 held-out in-scope questions | **0 wrongly refused** |
| 12 unseen out-of-scope questions (about half off-topic, half near the product's domain) | **12/12 refused** |
| 5 out-of-scope calibration questions | 5/5 refused (used to set the threshold, so in-sample) |

The margin is real but not huge: the weakest out-of-scope best-score was −6.4 and the lowest in-scope best-score was −3.9, against a threshold of −5.0. The 12 unseen questions were written by the author, not an independent labeller, so treat this as a sanity check rather than a benchmark.

---

## Human-in-the-Loop and Escalation

- **Durable state.** The LangGraph checkpointer (`AsyncPostgresSaver`) stores graph state in Supabase Postgres, so a paused ticket can be resumed after a restart.
- **Approve.** `POST /review` with `human_approved: true` finishes the ticket and records the approved solution.
- **Reject with feedback.** `human_approved: false` plus `human_feedback` sends the ticket back to research; the new draft takes the feedback into account.
- **Escalate.** After 3 rejections, or when the confidence gate refuses weak evidence, the ticket is marked `escalated` with a structured summary and waits in `GET /pending-escalations` for a person.
- **Close manually.** `POST /submit-manual-fix` lets a human agent write the final fix and resolve the ticket.

---

## Database and Audit Trail

Supabase (PostgreSQL) holds a five-table audit trail:

| Table | Purpose |
|---|---|
| `tickets` | One row per ticket: message, status, classification, root cause, proposed fix, test result, human decision and feedback, escalation summary |
| `ticket_draft` | Each draft shown to the human reviewer, with the review decision and feedback |
| `solution` | The accepted solution: fix, explanation, test result, risk estimate, attempt number, approval |
| `agent_step` | Node-level log: input, output, attempt count and error text for every step of the graph |
| `metrics` | Daily aggregate counts |

LangGraph also creates its own checkpoint tables in the same database. For tickets that are waiting on a human (for example escalated ones), `human_approved` stays empty until a person acts; `human_feedback` shows "Awaiting human agent" in the meantime.

---

## Measured Results

A 20-ticket live test run through the real API against Supabase, Groq and E2B, run twice: once before and once after a reliability fix (see below). Metrics come from LangSmith traces, Supabase rows and the server logs. The mix: 10 held-out in-scope questions, 5 out-of-scope questions, 3 code tickets and 2 reject-then-retry tickets.

### Behaviour

| Check | Result (after fix) |
|---|---|
| In-scope held-out questions that produced a draft | 10/10 |
| Out-of-scope questions escalated by the gate | 5/5 (calibration set, in-sample) |
| Code tickets passing the E2B sandbox | 2/3 (the third had no related docs and was escalated by the gate) |
| Reject → revised draft → approve | 2/2 produced a revised draft |
| Errors on ticket submission | 0/20 (before the fix: 1/20) |

### Performance and cost

| Metric | Value |
|---|---|
| Time from ticket to proposed fix (AI-drafted tickets) | **median 17.5 s, p95 27 s** |
| Escalation (gate) | about 11 s |
| Approval resume (`/review`) | median 7.6 s (a reject re-runs research and takes about 20 s) |
| LLM cost per ticket (LangSmith, Groq list pricing) | **median about $0.0005** (about $0.010 for 20 tickets) |
| Tokens per ticket | about 4k |
| Audit-trail steps logged | 129 for 20 tickets (about 6.5 per ticket) |

### Reliability fix found by the test

The first run exposed that the Fixer's structured output sometimes returned `null` for optional list fields, which the schema rejected, and one ticket exhausted its retries and returned an HTTP 500. The fix (in `backend/agent.py`) lets the schema accept `null` and converts it to an empty list, and makes the retry wrapper also retry output-parser errors.

| | Before | After |
|---|---|---|
| Failed LLM calls (LangSmith) | 12 over 19 tickets (0.63 per ticket) | 8 over 20 tickets (0.40 per ticket) |
| Tickets needing at least one retry | 6 of 19 | 4 of 20 |
| `null`-array schema failures | recurring | 0 |

### Read these results with care

- **Small sample.** 20 tickets, run twice, by one person. This is a behaviour check, not a production benchmark.
- **Scripted approvals.** The human approvals in the test were automated, so the numbers show how the system behaves, not how good the answers are. Answer quality is covered by the retrieval evaluation above.
- **Provider limits.** The Groq free tier has a daily token cap. It was reached at the end of the second run, and one `/review` call returned a 500 because of it. Handling that gracefully is on the roadmap.
- **Failure counts are noisy.** Going from 12 to 8 failed calls is a small change in a random process; the clear result is that the specific `null` failure disappeared.

---

## Project Structure

```text
Self_Healing_Customer_support_agent/
|-- backend/
|   |-- main.py                  FastAPI app: ticket, review, escalation endpoints
|   |-- agent.py                 LangGraph state machine (triage, research, fix, sandbox, human review)
|   |-- config.py                Environment variable loading (no hardcoded secrets)
|   |-- database/                Supabase (Postgres) read/write
|   `-- rag/                     Hybrid retrieval: chunking, vector + BM25, RRF, rerank, confidence gate
|-- monitoring/                  Pushes metrics to Grafana Cloud
|-- evaluation/                  Retrieval + gate evaluation, live ticket runner, run analysis, saved results
|-- data/                        Knowledge base (handbook, wiki, ticket archive)
|-- docs/                        Architecture diagrams (.mmd + rendered .png)
|-- deploy/                      Kubernetes manifests (deployment, service, HPA)
|-- .github/workflows/ci.yml     GitHub Actions: syntax check + Docker build
|-- .env.example                 Environment variable template (names only)
|-- Dockerfile
|-- railway.json
`-- requirements.txt
```

---

## Tech Stack

| Category | Technology | Role |
|---|---|---|
| Agent orchestration | LangGraph | State machine for the triage → research → fix → sandbox → human review workflow, with Postgres checkpointing |
| Vector database | ChromaDB | Dense retrieval over docs, wiki and ticket archive |
| Keyword retrieval | BM25 | Lexical candidates merged with vector results via RRF |
| Reranking | Cross-encoder (sentence-transformers) | Rescores merged candidates, keeps the best 5 |
| Relational database | Supabase (Postgres) | Five-table audit trail (tickets, drafts, solutions, agent steps, metrics) plus LangGraph checkpoints |
| Secure execution | E2B | Runs generated code in an isolated sandbox; errors are fed back to the Fixer |
| Observability | LangSmith, Grafana Cloud | Per-ticket traces, token/cost tracking, ticket volume and success/failure counts |
| LLM | Groq | Classification, analysis and fix generation across agent nodes |
| Embeddings | Sentence Transformers | Vector embeddings for RAG retrieval |
| API | FastAPI | Async HTTP API with API-key authentication and rate limiting |
| CI | GitHub Actions (`.github/workflows/ci.yml`) | Syntax check + Docker build on every push/PR to `main` |
| Deployment | Docker, Kubernetes manifests (`deploy/`), Railway | Containerized run; K8s deployment with readiness/liveness probes and HPA (2–50 replicas) |

---

## Getting Started

### Prerequisites
- Python 3.11
- Docker (for containerized deployment)
- Kubernetes (optional, for cluster deployment)

### 1. Clone and install

```bash
git clone https://github.com/MuhammadAbbas01/Self_Healing_Customer_support_agent.git
cd Self_Healing_Customer_support_agent
pip install -r requirements.txt
```

### 2. Configure environment

Copy `.env.example` to `.env` and fill it in (names only are committed; never commit real keys):

```env
GROQ_API_KEY="your_groq_api_key_here"
DATABASE_URL="postgresql://user:password@host:port/database_name"
E2B_API_KEY="your_e2b_api_key_here"
APP_API_KEY="a_long_random_string_clients_send_in_the_x-api-key_header"
GRAFANA_URL="your_grafana_otlp_metrics_endpoint_here"
GRAFANA_USER="your_grafana_username_here"
GRAFANA_TOKEN="your_grafana_api_token_here"
LANGCHAIN_API_KEY="your_langsmith_api_key_here"
LANGCHAIN_TRACING_V2="true"
LANGCHAIN_PROJECT="AI-Support-Agent"
```

- `GROQ_API_KEY` — from the [Groq Console](https://console.groq.com/)
- `DATABASE_URL` — a Postgres connection string, e.g. from [Supabase](https://supabase.com/)
- `E2B_API_KEY` — used to run generated code in a sandbox ([E2B.dev](https://e2b.dev/))
- `APP_API_KEY` — the shared secret the API checks in the `x-api-key` header
- `GRAFANA_URL` / `GRAFANA_USER` / `GRAFANA_TOKEN` — from your Grafana Cloud instance
- `LANGCHAIN_*` — LangSmith tracing ([smith.langchain.com](https://smith.langchain.com/))

### 3. Run locally

Run from the project root (not from inside `backend/`) so the app finds `data/`, `monitoring/` and the other folders:

```bash
python backend/main.py
```

On first run, `backend/rag/loader.py` loads, chunks and embeds the three files in `data/` (`Company_Technical_Handbook.md`, `support_tickets_archive.md`, `engineering_wiki.md`) into ChromaDB. The first start also downloads the embedding and reranker models, so allow a couple of minutes.

The API is available at `http://0.0.0.0:8000` (set `PORT` to change it), with interactive docs at `http://0.0.0.0:8000/docs`.

---

## API Reference

All endpoints require the `x-api-key` header and are rate limited (5 requests per minute per client).

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/ticket/stream` | Submit a ticket. Returns `pending_review` with a proposed fix, or `escalated` if the knowledge base cannot answer |
| `POST` | `/review` | Human decision on a draft: approve, or reject with feedback (re-runs research; escalates after 3 rejections) |
| `GET` | `/pending-escalations` | The queue of tickets waiting for a human agent |
| `POST` | `/submit-manual-fix` | A human agent writes the final fix and resolves an escalated ticket |

Submit a ticket:

```bash
curl -X POST http://localhost:8000/ticket/stream \
  -H "Content-Type: application/json" \
  -H "x-api-key: $APP_API_KEY" \
  -d '{
    "customer_message": "My API key is returning a 401 Unauthorized error after the recent deployment. I am using the old format.",
    "customer_code": "import requests\nr = requests.get(\"https://api.example.com/v2/data\", headers={\"X-API-Key\": \"sk-old-format-key\"})\nprint(r.status_code)"
  }'
```

`customer_code` is optional. A ticket that is not escalated returns `"status": "pending_review"` with `ticket_id`, `proposed_fix`, `fix_explanation` and `test_result`.

Approve it, or reject it with feedback:

```bash
curl -X POST http://localhost:8000/review \
  -H "Content-Type: application/json" -H "x-api-key: $APP_API_KEY" \
  -d '{"ticket_id": "TICKET-XXXXXXXX", "human_approved": false,
       "human_feedback": "Show a full curl example and explain key rotation."}'
```

Close an escalated ticket by hand:

```bash
curl -X POST http://localhost:8000/submit-manual-fix \
  -H "Content-Type: application/json" -H "x-api-key: $APP_API_KEY" \
  -d '{"ticket_id": "TICKET-XXXXXXXX",
       "proposed_fix": "We do not support PayPal yet. Cards and bank transfer only.",
       "fix_explanation": "Checked the docs: no PayPal integration exists."}'
```

### Security

- API-key authentication on every endpoint (`x-api-key`, checked against `APP_API_KEY`).
- Rate limiting (5 requests per minute per client).
- No secrets in the repository: `backend/config.py` reads everything from the environment, and `.env` files are git-ignored.
- Generated code only ever runs inside an isolated E2B sandbox, never on the API server.

---

## Evaluation

Run these from the project root with the `.env` filled in (see each script's header for options):

```bash
python evaluation/rag_eval.py            # retrieval metrics (hit@k, MRR) on the golden set
python evaluation/gate_eval.py           # confidence-gate check, offline, no LLM calls
python evaluation/run_scenarios.py       # sends live tickets to a running server (--quick for a short run)
python evaluation/analyze_run.py         # pulls LangSmith + Supabase numbers for a run
```

`evaluation/golden.py` holds the hand-labelled questions (30 in-scope with a development/held-out split, plus out-of-scope questions for the gate), and `evaluation/results/` keeps the saved outputs of the before/after live test described above.

---

## CI/CD

Every push and pull request to `main` runs through GitHub Actions (`.github/workflows/ci.yml`):

```mermaid
flowchart LR
    A["git push"] --> B["Checkout code"]
    B --> C["Set up Python 3.11"]
    C --> D["pip install -r requirements.txt"]
    D --> E["compileall backend, monitoring, evaluation"]
    E --> F["docker build<br/>self-healing-ai-agent:ci"]
    F --> G{"All steps green?"}
    G -- "yes" --> H(["CI passed"])
    G -- "no" --> I(["CI failed"])
```

What it checks:
1. **Syntax/import check** on every Python module via `compileall` — catches broken code before it reaches `main`.
2. **Docker build** — confirms the `Dockerfile` actually produces a working image, not just that the Python is valid.

What it deliberately does **not** do yet: push the built image to a registry (Docker Hub / GHCR) or auto-deploy. That's a manual step for now — see [Roadmap](#roadmap).

---

## Deployment

### Docker

```bash
docker build -t self-healing-ai-agent:latest .
docker run -p 8000:8000 --env-file ./.env self-healing-ai-agent:latest
```

### Kubernetes

The `deploy/` directory has manifests for a deployment (3 replicas, readiness + liveness probes, CPU/memory requests and limits), a `LoadBalancer` service, and a `HorizontalPodAutoscaler` (2–50 replicas, scales on 70% CPU):

```bash
kubectl create secret generic agent-secrets --from-env-file=.env
kubectl apply -f deploy/
```

```mermaid
flowchart TB
    subgraph Cluster["Kubernetes cluster"]
        SVC["Service: langgraph-svc<br/>type: LoadBalancer · port 80 → 8000"]
        HPA["HPA: langgraph-hpa<br/>2–50 replicas · scale at 70% CPU"]
        subgraph Pods["Deployment: langgraph-agent"]
            P1["Pod<br/>agent container"]
            P2["Pod<br/>agent container"]
            P3["Pod<br/>agent container"]
        end
        HPA -.->|watches CPU, adjusts replica count| Pods
        SVC --> P1
        SVC --> P2
        SVC --> P3
    end
    LB(["External traffic"]) --> SVC
    P1 & P2 & P3 --> EXT["Supabase, Groq, E2B, LangSmith, Grafana Cloud"]
```

Before applying to a real cluster: build and push the image to a registry, then update the placeholder `image:` field in `deploy/deployment.yaml` (currently `langgraph-agent:latest` — the file has a comment showing the expected format).

### Railway

`railway.json` configures a Dockerfile-based build with an on-failure restart policy, for a single-command deploy on [Railway](https://railway.app/) without touching Kubernetes.

---

## About the Benchmarks

v1 shipped a comparison chart (manual support vs. a standard AI bot vs. this agent) that used illustrative, assumed figures to show the *shape* of the intended improvement; it was a design goal, not measured data. In v2 that placeholder is replaced by the real measurements in [Retrieval quality](#retrieval-quality), [Confidence gate](#confidence-gate) and [Measured Results](#measured-results). There is still no comparison against manual support or other bots, because no production traffic has been benchmarked.

---

## Versions

| Version | Where | What it is |
|---|---|---|
| **v2** | `main`, tag `v2.0` | Real E2B sandbox execution, human-in-the-loop review with Postgres checkpointing, hybrid RAG with a confidence gate, 5-table audit trail, LangSmith tracing, API-key auth and rate limiting |
| **v1** | `v1` branch, tag `v1.0` | Original version: single `/ticket` endpoint, basic structure check in the validation stage, automatic review |

---

## Known Limitations

- The measured results come from a small live test (20 tickets, run twice) with scripted approvals; there is no production traffic and no measurement of answer quality beyond the retrieval evaluation.
- The confidence gate threshold was calibrated on a small set; the margin to the weakest in-scope and out-of-scope scores is about 1 point on each side.
- The sandbox only runs valid Python; configuration text, shell commands and other languages are skipped, so a `skipped` result does not prove the fix works.
- The sandbox retry loop has a fixed maximum attempt count; there is no adaptive back-off or cost cap on repeated LLM calls per ticket.
- When the LLM provider's rate limit or daily token cap is hit, the API returns a 500 instead of a clear "try again later" response.
- The table schema is not included as a SQL file in the repo yet.
- No automated unit-test suite yet; CI runs a syntax check and a Docker build, and the evaluation scripts are run by hand.
- CI builds the Docker image but does not push it to a registry or auto-deploy; deploying still means building, pushing and applying the manifests by hand.
- The Kubernetes manifests are written and were not deployed to a live cluster; `deploy/deployment.yaml` still has a placeholder image name to replace once an image is pushed somewhere.

---

## Roadmap

- [x] Integrate real E2B sandbox execution in the validation stage
- [x] Add a real human approval step (approve / reject with feedback / escalate)
- [x] Wire up agent-step, solution and draft logging in the database
- [x] Replace illustrative benchmark chart with real measurements from test traffic
- [x] Add API-key authentication and rate limiting
- [x] Add LangSmith tracing
- [ ] Add the SQL schema for the Supabase tables to the repo
- [ ] Return a clear "try again later" response when the LLM provider rate-limits
- [ ] Expand automated test coverage and run the real test suite in CI (not just a syntax check)
- [ ] Add a registry-push job to CI (Docker Hub or GHCR) and wire it to the K8s manifests
- [ ] Cost caps on the sandbox retry loop
- [ ] Larger, independently labelled evaluation sets for the confidence gate
- [ ] CONTRIBUTING guide for outside contributors

---

Independent project, built to learn and demonstrate agentic AI system design (LangGraph, production RAG, sandboxed self-correction, human-in-the-loop). Not connected to a live production support system.

## Author

**Muhammad Abbas** — AI/ML Engineer
GitHub: [@MuhammadAbbas01](https://github.com/MuhammadAbbas01)

---

<sub>Built with LangGraph, FastAPI and ChromaDB.</sub>
