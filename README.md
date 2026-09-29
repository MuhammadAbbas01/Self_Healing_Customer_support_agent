# Self-Healing AI Customer Support Agent

An autonomous support-ticket agent built with LangGraph: it triages a ticket, retrieves relevant context with RAG, proposes a fix, tests that fix in an isolated sandbox, and retries automatically before handing verified solutions to a human reviewer.

![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-async%20API-009688?logo=fastapi&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-agent%20orchestration-1C3C3C)
![Groq](https://img.shields.io/badge/LLM-Groq-black)
![ChromaDB](https://img.shields.io/badge/Vector%20DB-ChromaDB-orange)
![Supabase](https://img.shields.io/badge/DB-Supabase%20Postgres-3ECF8E?logo=supabase&logoColor=white)

---

## Overview

Traditional support bots answer from a static script and stop when they're wrong. This agent goes further: when a ticket looks like a code or config issue, it generates a candidate fix, runs it inside an isolated E2B sandbox to check whether it actually works, and retries with a revised fix if the test fails — instead of handing an unverified answer straight to the customer.

Context for each ticket comes from a small RAG pipeline over three markdown sources: a company technical handbook, a wiki, and a searchable archive of past tickets.

---

## How It Works

```mermaid
graph TD
    START((Start)) --> TRIAGE[Triage Node]
    TRIAGE --> RESEARCH[Research Node - RAG]
    RESEARCH --> ANALYZER[Analyzer Node]
    ANALYZER --> FIXER[Fixer Node]
    FIXER --> SANDBOX[Sandbox Node - E2B]
    SANDBOX -- "Test passed" --> HUMAN_REVIEW[Human Review Node]
    SANDBOX -- "Test failed, retries left" --> FIXER
    SANDBOX -- "Test failed, retries exhausted" --> HUMAN_REVIEW
    HUMAN_REVIEW --> END((End))

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
5. **Sandbox (E2B)** — the proposed fix is executed in an isolated sandbox to check whether it actually resolves the problem.
6. **Adaptive routing** — a passing test goes to human review; a failing test loops back to the Fixer (up to a retry limit) before being escalated for human review.
7. **Human review** — a person gives final sign-off before a solution reaches the customer. Metrics from each run are pushed to Grafana Cloud.

---

## Tech Stack

| Category | Technology | Role |
|---|---|---|
| Agent orchestration | LangGraph | State machine for the triage → research → fix → test → review workflow |
| Vector database | ChromaDB | Semantic search over docs, wiki and ticket archive |
| Relational database | Supabase (Postgres) | Persists ticket data and agent state |
| Secure execution | E2B sandbox | Isolated environment to test a proposed fix before it reaches a human |
| Observability | Grafana Cloud | Metrics on ticket volume and success/failure counts |
| LLM | Groq | Classification, analysis and fix generation across agent nodes |
| Embeddings | Sentence Transformers | Vector embeddings for RAG retrieval |
| API | FastAPI | Async HTTP API for submitting and processing tickets |
| Deployment | Docker, Kubernetes manifests (`deploy/`), Railway | Containerized run, optional K8s deployment with HPA |

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
GRAFANA_URL="your_grafana_loki_endpoint_here"
GRAFANA_USER="your_grafana_username_here"
GRAFANA_TOKEN="your_grafana_api_token_here"
```

- `GROQ_API_KEY` — from the [Groq Console](https://console.groq.com/)
- `DATABASE_URL` — a Postgres connection string, e.g. from [Supabase](https://supabase.com/)
- `E2B_API_KEY` — from [E2B.dev](https://e2b.dev/)
- `GRAFANA_URL` / `GRAFANA_USER` / `GRAFANA_TOKEN` — from your Grafana Cloud instance

### 3. Run locally

```bash
python main.py
```

On first run, `data.py` loads, chunks and embeds `Company_Technical_Handbook.md`, `support_tickets_archive.md` and `engineering_wiki.md` into ChromaDB.

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

## Deployment

### Docker

```bash
docker build -t self-healing-ai-agent:latest .
docker run -p 8000:8000 --env-file ./.env self-healing-ai-agent:latest
```

### Kubernetes

The `deploy/` directory has manifests for a deployment, a service, and horizontal pod autoscaling:

```bash
kubectl apply -f deploy/
```

---

## About the Benchmark Chart

The chart generated by `generate_benchmarks.py` (comparing manual support, a standard AI bot, and this agent on resolution time and accuracy) uses illustrative, assumed figures to show the *shape* of the intended improvement — it is not measured production data from a real deployment. Treat it as a design goal, not a claim.

---

## Known Limitations

- The comparison chart in `generate_benchmarks.py` uses illustrative numbers, not measured results — no production traffic has been benchmarked yet.
- The sandbox retry loop has a fixed maximum attempt count; there is no adaptive back-off or cost cap on repeated LLM calls per ticket.
- Human review is a required final step for every ticket; the agent does not (and should not) auto-send unverified fixes to customers.
- No automated test suite yet (`testing.py` exists but coverage is limited).

---

## Roadmap

- [ ] Replace illustrative benchmark chart with real measurements from test traffic
- [ ] Expand automated test coverage
- [ ] Rate limiting / cost caps on the sandbox retry loop
- [ ] CONTRIBUTING guide for outside contributors

---

Independent project, built to learn and demonstrate agentic AI system design (LangGraph, RAG, sandboxed self-correction). Not connected to a live production support system.

## Author

**Muhammad Abbas** — AI/ML Engineer
GitHub: [@MuhammadAbbas01](https://github.com/MuhammadAbbas01)

---

<sub>Built with LangGraph, FastAPI, ChromaDB and E2B.</sub>
