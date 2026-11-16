# Contributing

Thanks for your interest in improving this project. It is an agentic support system (LangGraph, hybrid RAG, E2B sandbox, human review), and contributions that make it more reliable, better measured, or easier to run are very welcome.

## Ways to help

- **Report a bug.** Open an issue with the ticket text that triggered it, the response you got, and the relevant server log lines. Please remove API keys and personal data first.
- **Improve retrieval.** Better chunking, a stronger reranker, or a larger and independently labelled evaluation set for the confidence gate.
- **Harden the agent.** For example, a clear "try again later" response when the LLM provider rate-limits, or tests for the review and escalation paths.
- **Deployment.** The planned next step is an Azure deployment with continuous delivery (registry push and a deploy job in CI).
- **Docs.** Fixes to the README, diagrams, or examples.

## Getting set up

```bash
git clone https://github.com/MuhammadAbbas01/Self_Healing_Customer_support_agent.git
cd Self_Healing_Customer_support_agent
python -m venv .venv && source .venv/bin/activate      # Python 3.11
pip install -r requirements.txt
cp .env.example .env                                    # then fill in your own keys
python backend/main.py                                  # run from the project root
```

You need your own accounts and keys for Groq, E2B, a Postgres database (Supabase works), and optionally LangSmith and Grafana Cloud. Create the five tables described in the README (a ready-made SQL file is on the roadmap). Never commit a `.env` file.

## Making a change

1. **Fork** the repo and create a branch from `main`: `git checkout -b feature/short-description`.
2. **Keep changes focused.** One topic per pull request is easier to review.
3. **Run the same checks as CI** before you push:
   ```bash
   python -m compileall -q backend monitoring evaluation
   docker build -t self-healing-ai-agent:local .
   ```
4. **If you touch retrieval or the confidence gate,** re-run the evaluation and include the before/after numbers in your pull request:
   ```bash
   python evaluation/rag_eval.py     # hit@k and MRR on the golden set
   python evaluation/gate_eval.py    # confidence-gate check (offline, no LLM calls)
   ```
5. **If you change the agent workflow,** run a short live check against a running server and describe what you saw:
   ```bash
   python evaluation/run_scenarios.py --quick
   ```
6. **Open a pull request** against `main`. Explain what changed and why, and link any related issue.

## Style

- Follow the existing code style: type hints on public functions, short docstrings that say what a node returns, and clear log messages.
- Keep secrets out of the code. All configuration comes from environment variables through `backend/config.py`.
- Generated code must only ever run inside the E2B sandbox, never on the API server.
- Write commit messages in the imperative mood, for example "Fix retry on parser errors".

## Security

If you find a security problem, such as a leaked credential or a way around the API-key check, please do not open a public issue. Contact the maintainer directly through the GitHub profile.

## Maintainer

[Muhammad Abbas](https://github.com/MuhammadAbbas01)
