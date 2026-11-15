"""Turn a run from evaluation/run_scenarios.py into measured numbers (API timings + LangSmith traces + Supabase rows).

    python evaluation/analyze_run.py                      # uses evaluation/results/latest_run.json
    python evaluation/analyze_run.py path/to/run.json

Needs DATABASE_URL and LANGCHAIN_API_KEY in .env (LANGCHAIN_PROJECT optional).
LangSmith only returns the 100 most recent root runs, so analyse a run soon after it finishes.
"""
import json
import os
import statistics
import sys
import warnings
from collections import defaultdict
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from langsmith import Client

warnings.filterwarnings("ignore")
HERE = Path(__file__).resolve().parent
load_dotenv(HERE.parent / ".env")

results_path = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "results" / "latest_run.json"
R = json.loads(results_path.read_text(encoding="utf-8"))
ids = [r["ticket_id"] for r in R if r.get("ticket_id")]
out = {}


def pct(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(round(p * (len(xs) - 1))))]


def stats(xs):
    return (f"median {statistics.median(xs):.1f}s | p95 {pct(xs, 0.95):.1f}s | "
            f"min {min(xs):.1f}s | max {max(xs):.1f}s | n={len(xs)}")


by = defaultdict(list)
for r in R:
    by[r["kind"]].append(r)
ans, un, code, rt = by["answerable"], by["unanswerable"], by["code"], by["self_heal_retry"]

print("A. OUTCOMES")
out["outcomes"] = {
    "answerable_draft_then_approved": f"{sum(1 for r in ans if r.get('review_status') == 'approved')}/{len(ans)}",
    "out_of_scope_escalated": f"{sum(1 for r in un if r['status'] == 'escalated')}/{len(un)}",
    "code_sandbox_passed": f"{sum(1 for r in code if r.get('test_result') == 'passed')}/{len(code)}",
    "reject_gave_new_draft": f"{sum(1 for r in rt if r.get('draft_changed'))}/{len(rt)}",
    "retry_finally_approved": f"{sum(1 for r in rt if r.get('review_status') == 'approved')}/{len(rt)}",
    "http_errors_on_submit": sum(1 for r in R if r.get("http") != 200),
    "tickets": len(R),
}
for k, v in out["outcomes"].items():
    print(f"  {k:34} {v}")

print("\nB. LATENCY (seen by the client)")
drafted = [r["stream_secs"] for r in R if r["kind"] in ("answerable", "code", "self_heal_retry") and r.get("http") == 200]
escalated = [r["stream_secs"] for r in un if r.get("http") == 200]
resume = [r["review_secs"] for r in R if r.get("review_secs")]
print("  ticket -> AI draft :", stats(drafted))
print("  ticket -> escalation:", stats(escalated))
print("  approve + resume    :", stats(resume))
out["latency_s"] = {"draft_median": round(statistics.median(drafted), 1), "draft_p95": round(pct(drafted, .95), 1),
                    "escalation_median": round(statistics.median(escalated), 1),
                    "approve_resume_median": round(statistics.median(resume), 1)}

print("\nC. LANGSMITH")
client = Client(api_key=os.environ["LANGCHAIN_API_KEY"])
project = os.getenv("LANGCHAIN_PROJECT", "AI-Support-Agent")
per = defaultdict(list)
for run in client.list_runs(project_name=project, is_root=True, limit=100):
    thread = ((run.extra or {}).get("metadata") or {}).get("thread_id", "")
    if thread in ids and run.end_time:
        per[thread].append((run.start_time, (run.end_time - run.start_time).total_seconds(),
                            run.total_tokens or 0, float(run.total_cost or 0), run))
first = {t: sorted(v, key=lambda x: x[0])[0] for t, v in per.items()}
graph_lat = [v[1] for v in first.values()]
tokens = [sum(x[2] for x in v) for v in per.values() if sum(x[2] for x in v) > 0]
cost = [sum(x[3] for x in v) for v in per.values() if sum(x[3] for x in v) > 0]
failed = {}
for thread, v in first.items():
    run = v[4]
    kids = [k for k in client.list_runs(project_name=project, trace_id=str(run.trace_id), limit=100)
            if k.id != run.id and k.end_time]
    failed[thread] = sum(1 for k in kids if k.error)
print(f"  tickets traced: {len(per)}/{len(ids)}")
print("  graph run latency:", stats(graph_lat))
print(f"  tokens per ticket: median {statistics.median(tokens):.0f} | max {max(tokens)}")
print(f"  LLM cost per ticket: median ${statistics.median(cost):.5f} | total ${sum(cost):.4f}")
print(f"  failed model calls: {sum(failed.values())} over {len(failed)} tickets "
      f"({sum(failed.values()) / len(failed):.2f}/ticket); tickets with >=1: {sum(1 for v in failed.values() if v)}")
out["langsmith"] = {"tickets": len(per), "graph_median_s": round(statistics.median(graph_lat), 1),
                    "graph_p95_s": round(pct(graph_lat, .95), 1), "tokens_median": int(statistics.median(tokens)),
                    "cost_median_usd": round(statistics.median(cost), 5), "cost_total_usd": round(sum(cost), 4),
                    "failed_model_calls": sum(failed.values()), "failed_per_ticket": round(sum(failed.values()) / len(failed), 2)}

print("\nD. SUPABASE")
with psycopg.connect(os.environ["DATABASE_URL"], prepare_threshold=None, connect_timeout=20) as conn:
    status = dict(conn.execute("select status, count(*) from tickets where ticket_id = any(%s) group by status", (ids,)).fetchall())
    print("  tickets by status:", status)
    optional = {("tickets", "customer_code"), ("tickets", "escalation_summary"), ("tickets", "human_approved")}
    for table in ("tickets", "solution", "ticket_draft", "agent_step"):
        cols = [c[0] for c in conn.execute("select column_name from information_schema.columns "
                                           "where table_schema='public' and table_name=%s", (table,)).fetchall()]
        total = conn.execute(f'select count(*) from "{table}" where ticket_id = any(%s)', (ids,)).fetchone()[0]
        empty = []
        for col in cols:
            n = conn.execute(f'select count(*) from "{table}" where ticket_id = any(%s) and '
                             f'("{col}" is null or "{col}"::text in (\'\', \'{{}}\', \'[]\', \'null\'))', (ids,)).fetchone()[0]
            if n and (table, col) not in optional:
                empty.append(f"{col} {n}/{total}")
        print(f"  {table:13} rows={total:3} -> " + ("all filled" if not empty else "empty: " + ", ".join(empty)))
    steps = conn.execute("select count(*) from agent_step where ticket_id = any(%s)", (ids,)).fetchone()[0]
    print(f"  agent steps logged: {steps} (~{steps / len(ids):.1f} per ticket)")
    out["supabase"] = {"tickets_by_status": status, "agent_steps": steps}

metrics_path = results_path.with_name(results_path.stem + "_metrics.json")
metrics_path.write_text(json.dumps(out, indent=1), encoding="utf-8")
print(f"\nsaved {metrics_path}")
