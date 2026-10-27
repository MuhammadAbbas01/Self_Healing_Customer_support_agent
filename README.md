# Self-Healing AI Customer Support Agent

A support-ticket agent built with LangGraph: it triages a ticket, retrieves relevant context with RAG, proposes a fix with an LLM, validates it, and retries automatically with a revised fix before generating a reviewed customer reply. The validation stage is built so a real E2B sandbox run can be plugged in (see Roadmap).

![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-async%20API-009688?logo=fastapi&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-agent%20orchestration-1C3C3C)
![Groq](https://img.shields.io/badge/LLM-Groq-black)
![ChromaDB](https://img.shields.io/badge/Vector%20DB-ChromaDB-orange)
![Supabase](https://img.shields.io/badge/DB-Supabase%20Postgres-3ECF8E?logo=supabase&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-containerized-2496ED?logo=docker&logoColor=white)
![Kubernetes](https://img.shields.io/badge/Kubernetes-manifests%20%2B%20HPA-326CE5?logo=kubernetes&logoColor=white)
![CI](https://github.com/MuhammadAbbas01/Self_Healing_Customer_support_agent/actions/workflows/ci.yml/badge.svg)

---

## Overview

Traditional support bots answer from a static script and stop when they're wrong. This agent loops: after generating a candidate fix it goes through a validation stage, and if that fails it returns to the Fixer for a revised attempt, up to a retry limit. The validation stage currently runs a basic structure check; executing fixes in an E2B sandbox is the next planned step.

Context for each ticket comes from a small RAG pipeline over three markdown sources: a company technical handbook, a wiki, and a searchable archive of past tickets.

---

## How It Works

```mermaid
graph TD
    START((Start)) --> TRIAGE[Triage Node]
    TRIAGE --> RESEARCH[Research Node - RAG]
    RESEARCH --> ANALYZER[Analyzer Node]
    ANALYZER --> FIXER[Fixer Node]
    FIXER --> SANDBOX[Validation Node - E2B sandbox planned]
    SANDBOX -- "Test passed" --> HUMAN_REVIEW[Review Node]
    SANDBOX -- "Test failed, retries left" --> FIXER
    SANDBOX -- "Test failed, retries exhausted" --> HUMAN_REVIEW
    HUMAN_REVIEW --> FINISH((Done))

    subgraph "Knowledge base"
        DOCS[(Company docs)]
        TICKETS[(Ticket archive)]
        WIKI[(Engineering wiki)]
    end

    RESEARCH -.-> DOCS
    RESEARCH -.-> TICKETS
    RESEARCH -.-> WIKI

    subgraph "Observability"
        GRAFANA[Grafana Cloud]
    end

    HUMAN_REVIEW -.-> GRAFANA
```

1. **Triage** — an LLM classifies the incoming ticket by type, severity and technical domain.
2. **Research (RAG)** — semantic search over the vectorized knowledge base (ChromaDB) pulls the most relevant docs, wiki entries and similar past tickets.
3. **Analyzer** — combines the triage result and retrieved context to identify the likely root cause and the type of fix needed (code fix, config change, or a system-level bug).
4. **Fixer** — generates a concrete proposed solution.
5. **Validation (sandbox stage)** - checks the proposed fix before it moves on. It currently runs a basic structure check; real execution in an E2B sandbox is planned.
6. **Adaptive routing** - a passing check goes to the review step; a failing one loops back to the Fixer (up to a retry limit) and then goes to review with the failure noted.
7. **Review** - builds the ticket summary and the customer reply and marks it approved automatically for now; a manual approval step is on the roadmap. Ticket and success counts are pushed to Grafana Cloud.

---

## Project Structure

```text
Self_Healing_Customer_support_agent/
|-- backend/
|   |-- main.py                  FastAPI app + ticket endpoint
|   |-- agent.py                 LangGraph state machine (triage, fix, test, review)
|   |-- config.py                Environment variable loading
|   |-- database/                Supabase (Postgres) read/write
|   `-- rag/                     Loads data/ into ChromaDB for retrieval
|-- monitoring/                  Pushes metrics to Grafana Cloud
|-- evaluation/                  Sample-ticket runner and benchmark chart script
|-- data/                        Knowledge base (handbook, wiki, ticket archive)
|-- docs/                        Architecture diagrams (.mmd + rendered .png)
|-- deploy/                      Kubernetes manifests (deployment, service, HPA)
|-- .github/workflows/ci.yml     GitHub Actions: syntax check + Docker build
|-- Dockerfile
|-- railway.json
`-- requirements.txt
```

---

## Tech Stack

| Category | Technology | Role |
|---|---|---|
| Agent orchestration | LangGraph | State machine for the triage → research → fix → test → review workflow |
| Vector database | ChromaDB | Semantic search over docs, wiki and ticket archive |
| Relational database | Supabase (Postgres) | Stores new tickets (`backend/database/manager.py`); helpers for agent steps, solutions and daily metrics are written and ready to wire in |
| Secure execution | E2B | Planned integration for the validation stage |
| Observability | Grafana Cloud | Metrics on ticket volume and success/failure counts |
| LLM | Groq | Classification, analysis and fix generation across agent nodes |
| Embeddings | Sentence Transformers | Vector embeddings for RAG retrieval |
| API | FastAPI | Async HTTP API for submitting and processing tickets |
| CI | GitHub Actions (`.github/workflows/ci.yml`) | Syntax check + Docker build on every push/PR to `main` |
| Deployment | Docker, Kubernetes manifests (`deploy/`), Railway | Containerized run; K8s deployment with readiness/liveness probes and HPA (2–50 replicas) |

---

## Getting Started

### Prerequisites
- Python 3.9+
- Docker (for containerized deployment)
- Kubernetes (optional, for cluster deployment)

### 1. Clone and install

```bash
git clone https://github.com/MuhammadAbbas01/Self_Healing_Customer_support_agent.git
cd Self_Healing_Customer_support_agent
pip install -r requirements.txt
```

### 2. Configure environment

Create a `.env` file in the project root:

```env
GROQ_API_KEY="your_groq_api_key_here"
DATABASE_URL="postgresql://user:password@host:port/database_name"
E2B_API_KEY="your_e2b_api_key_here"
GRAFANA_URL="your_grafana_otlp_metrics_endpoint_here"
GRAFANA_USER="your_grafana_username_here"
GRAFANA_TOKEN="your_grafana_api_token_here"
```

- `GROQ_API_KEY` — from the [Groq Console](https://console.groq.com/)
- `DATABASE_URL` — a Postgres connection string, e.g. from [Supabase](https://supabase.com/)
- `E2B_API_KEY` - reserved for the planned sandbox integration ([E2B.dev](https://e2b.dev/)); not used yet
- `GRAFANA_URL` / `GRAFANA_USER` / `GRAFANA_TOKEN` — from your Grafana Cloud instance

### 3. Run locally

Run from the project root (not from inside `backend/`) so the app finds `data/`, `monitoring/` and the other folders:

```bash
python backend/main.py
```

On first run, `backend/rag/loader.py` loads, chunks and embeds the three files in `data/` (`Company_Technical_Handbook.md`, `support_tickets_archive.md`, `engineering_wiki.md`) into ChromaDB.

The API is available at `http://0.0.0.0:8000`, with interactive docs at `http://0.0.0.0:8000/docs`.

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Health check and endpoint overview |
| `POST` | `/ticket` | Submit a support ticket for processing |

Example request:

```bash
curl -X POST http://localhost:8000/ticket \
  -H "Content-Type: application/json" \
  -d '{
    "message": "My API key is returning a 401 Unauthorized error after the recent deployment. I am using the old format.",
    "code": "const apiKey = \"sk-old-format-key\";\nfetch(\"/api/data\", { headers: { \"X-API-Key\": apiKey } });"
  }'
```

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
    P1 & P2 & P3 --> EXT["Supabase, Groq, Grafana Cloud"]
```

Before applying to a real cluster: build and push the image to a registry, then update the placeholder `image:` field in `deploy/deployment.yaml` (currently `langgraph-agent:latest` — the file has a comment showing the expected format).

### Railway

`railway.json` configures a Dockerfile-based build with an on-failure restart policy, for a single-command deploy on [Railway](https://railway.app/) without touching Kubernetes.

---

## About the Benchmark Chart

The chart generated by `evaluation/generate_benchmarks.py` (comparing manual support, a standard AI bot, and this agent on resolution time and accuracy) uses illustrative, assumed figures to show the *shape* of the intended improvement — it is not measured production data from a real deployment. Treat it as a design goal, not a claim.

---

## Known Limitations

- The comparison chart in `evaluation/generate_benchmarks.py` uses illustrative numbers, not measured results — no production traffic has been benchmarked yet.
- The sandbox retry loop has a fixed maximum attempt count; there is no adaptive back-off or cost cap on repeated LLM calls per ticket.
- The validation stage does not execute code yet; it only checks that the proposed fix has content, so a pass does not prove the fix works.
- Review is automatic for now: the node marks every ticket approved and formats the reply. A manual approval step is not built yet.
- Only ticket creation is written to Supabase; the table schema is not included in the repo.
- No automated test suite yet (`evaluation/run_scenarios.py` only runs three sample tickets) — CI currently runs a syntax check, not a real test suite.
- CI builds the Docker image but does not push it to a registry or auto-deploy; deploying still means building, pushing and applying the manifests by hand.
- The Kubernetes manifests are written and were not deployed to a live cluster; `deploy/deployment.yaml` still has a placeholder image name to replace once an image is pushed somewhere.

---

## Roadmap

- [ ] Integrate real E2B sandbox execution in the validation stage
- [ ] Add a real human approval step
- [ ] Wire up agent-step, solution and metrics logging in the database, and add the SQL schema
- [ ] Replace illustrative benchmark chart with real measurements from test traffic
- [ ] Expand automated test coverage and run the real test suite in CI (not just a syntax check)
- [ ] Add a registry-push job to CI (Docker Hub or GHCR) and wire it to the K8s manifests
- [ ] Rate limiting / cost caps on the sandbox retry loop
- [ ] CONTRIBUTING guide for outside contributors

---

Independent project, built to learn and demonstrate agentic AI system design (LangGraph, RAG, retry-based self-correction). Not connected to a live production support system.

## Author

**Muhammad Abbas** — AI/ML Engineer
GitHub: [@MuhammadAbbas01](https://github.com/MuhammadAbbas01)

---

<sub>Built with LangGraph, FastAPI and ChromaDB.</sub>
