"""Live end-to-end run against a running API: answerable tickets, out-of-scope tickets, code tickets and
human-review reject -> retry -> approve. Writes one JSON record per ticket.

Start the API first (python backend/main.py), then from the project root:
    python evaluation/run_scenarios.py            # full 20-ticket run (about 15 minutes, paced for the rate limit)
    python evaluation/run_scenarios.py --quick    # 4 tickets: one of each kind (about 3 minutes)

Needs APP_API_KEY in .env (or the environment). Optional: --base-url, --out.
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from golden import TEST, UNANSWERABLE  # noqa: E402

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
except ImportError:
    pass

PAUSE = 14  # seconds between calls: the API allows 5 requests/minute per endpoint

CODE_TICKETS = [
    ("My Python script crashes with KeyError: 'total'. Return the complete corrected Python script "
     "(full runnable code in exact_code_to_use) that prints the charged amount in dollars from the amount field.",
     'import json\n\nraw = \'{"id": 101, "amount": 4999, "currency": "usd"}\'\npayment = json.loads(raw)\n'
     'print("Total charged:", payment["total"] / 100)\n'),
    ("My Python script crashes with ZeroDivisionError when there are no payments. Return the complete corrected "
     "Python script (full runnable code in exact_code_to_use) that prints the average payment safely.",
     'payments = []\naverage = sum(payments) / len(payments)\nprint("Average payment:", average)\n'),
]
RETRY_TICKETS = [  # the human REJECTS the first draft, the agent re-researches, the human then approves
    ("payments timing out during our flash sale, 504 gateway timeout",
     "Too generic. Give concrete numbers and the exact configuration change, step by step."),
    ("customers got charged twice when they retried a failed payment",
     "Not enough. Show a complete example of sending an idempotency key and explain how long keys are kept."),
]


def make_client(base_url, key):
    def post(path, body, timeout=420):
        for attempt in range(3):
            req = urllib.request.Request(base_url + path, data=json.dumps(body).encode(), method="POST",
                                         headers={"x-api-key": key, "Content-Type": "application/json"})
            t0 = time.time()
            try:
                with urllib.request.urlopen(req, timeout=timeout) as r:
                    return r.status, json.loads(r.read().decode()), time.time() - t0
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    print("   rate limited, waiting 65 s ...", flush=True)
                    time.sleep(65)
                    continue
                return e.code, {"error": e.read().decode()[:200]}, time.time() - t0
            except Exception as e:  # noqa: BLE001
                return 0, {"error": str(e)[:200]}, time.time() - t0
        return 429, {"error": "rate limited 3 times"}, 0.0
    return post


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default=os.getenv("BASE_URL", "http://localhost:8000"))
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent / "results" / "latest_run.json"))
    args = ap.parse_args()
    key = os.getenv("APP_API_KEY")
    if not key:
        sys.exit("APP_API_KEY is not set (put it in .env)")
    post = make_client(args.base_url.rstrip("/"), key)

    answerable = [q for q, _ in TEST]
    out_of_scope = list(UNANSWERABLE)
    code, retry = CODE_TICKETS, RETRY_TICKETS
    if args.quick:
        answerable, out_of_scope, code, retry = answerable[:1], out_of_scope[:1], code[:1], retry[:1]

    results = []
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)

    def save(kind, msg, **kw):
        results.append({"kind": kind, "message": msg[:90], **kw})
        Path(args.out).write_text(json.dumps(results, indent=1), encoding="utf-8")

    def review(tid, approved, feedback):
        c, d, s = post("/review", {"ticket_id": tid, "human_approved": approved, "human_feedback": feedback})
        return d, round(s, 1)

    for msg in answerable:
        c, d, s = post("/ticket/stream", {"customer_message": msg})
        rec = dict(ticket_id=d.get("ticket_id"), status=d.get("status"), stream_secs=round(s, 1),
                   test_result=d.get("test_result"), http=c)
        print(f"[answerable]   {rec['status']} {rec['ticket_id']} {s:.1f}s", flush=True)
        if rec["status"] == "pending_review":
            d2, s2 = review(rec["ticket_id"], True, "Approved in test run")
            rec.update(review_status=d2.get("status"), review_secs=s2)
        save("answerable", msg, **rec)
        time.sleep(PAUSE)

    for msg in out_of_scope:
        c, d, s = post("/ticket/stream", {"customer_message": msg})
        print(f"[out of scope] {d.get('status')} {d.get('ticket_id')} {s:.1f}s", flush=True)
        save("unanswerable", msg, ticket_id=d.get("ticket_id"), status=d.get("status"), stream_secs=round(s, 1), http=c)
        time.sleep(PAUSE)

    for msg, code_text in code:
        c, d, s = post("/ticket/stream", {"customer_message": msg, "customer_code": code_text})
        rec = dict(ticket_id=d.get("ticket_id"), status=d.get("status"), stream_secs=round(s, 1),
                   test_result=d.get("test_result"), http=c)
        print(f"[code]         {rec['status']} {rec['ticket_id']} sandbox={rec['test_result']} {s:.1f}s", flush=True)
        if rec["status"] == "pending_review":
            d2, s2 = review(rec["ticket_id"], True, "Approved in test run")
            rec.update(review_status=d2.get("status"), review_secs=s2)
        save("code", msg, **rec)
        time.sleep(PAUSE)

    for msg, feedback in retry:
        c, d, s = post("/ticket/stream", {"customer_message": msg})
        rec = dict(ticket_id=d.get("ticket_id"), status=d.get("status"), stream_secs=round(s, 1), http=c)
        first_fix = str(d.get("proposed_fix"))
        print(f"[retry]        draft 1: {rec['status']} {rec['ticket_id']} {s:.1f}s", flush=True)
        if rec["status"] == "pending_review":
            time.sleep(PAUSE)
            d2, s2 = review(rec["ticket_id"], False, feedback)
            rec.update(reject_status=d2.get("status"), reject_secs=s2,
                       draft_changed=first_fix != str(d2.get("proposed_fix")))
            print(f"               rejected -> {d2.get('status')} {s2}s, new draft: {rec['draft_changed']}", flush=True)
            time.sleep(PAUSE)
            d3, s3 = review(rec["ticket_id"], True, "Better, approved")
            rec.update(review_status=d3.get("status"), review_secs=s3)
            print(f"               approved -> {d3.get('status')} {s3}s", flush=True)
        save("self_heal_retry", msg, **rec)
        time.sleep(PAUSE)

    print(f"\nDone. {len(results)} tickets written to {args.out}")


if __name__ == "__main__":
    main()
