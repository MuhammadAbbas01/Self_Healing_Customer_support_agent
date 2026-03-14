# AI Support Agent - Production System

AI-powered support ticket resolution system using LangGraph, RAG, and E2B sandbox.

## Features
- Automatic ticket classification
- RAG-based solution generation
- Real code execution testing (E2B)
- Self-healing loop (max 3 attempts)
- Grafana monitoring
- Kubernetes-ready

## Tech Stack
- LangGraph (agent orchestration)
- ChromaDB (vector database)
- Supabase (PostgreSQL)
- E2B (code sandbox)
- Grafana Cloud (monitoring)
- Railway (deployment)

## Setup
1. Install dependencies: `pip install -r requirements.txt`
2. Set environment variables in `app/config.py`
3. Run: `python app/main.py`

## Deployment
- Docker: `docker build -t langgraph-agent .`
- Kubernetes: `kubectl apply -f deploy/`