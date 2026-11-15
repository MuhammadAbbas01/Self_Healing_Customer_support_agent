"""Confidence-gate evaluation (retrieval layer only: no LLM, no API quota used).

The gate refuses to hand weak evidence to the model: if the best reranker score is below
GATE_THRESHOLD, no documents are returned and the ticket is escalated to a human.

Groups:
  - held-out in-scope questions (golden TEST)  -> must NOT be refused
  - calibration out-of-scope (golden UNANSWERABLE) -> used to pick the threshold (in-sample, reported separately)
  - NEW out-of-scope questions never used for tuning -> the independent refusal check

Run from the project root:
    python evaluation/gate_eval.py
"""
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import rag                              # noqa: E402
from golden import TEST, UNANSWERABLE   # noqa: E402

# Never used for tuning. Mix of plainly off-topic and "sounds like our product, but is not in the docs".
NEW_OUT_OF_SCOPE = [
    "what is the weather in london today",
    "write me a poem about the sea",
    "what is the capital of france",
    "how do i cook pasta carbonara",
    "who won the football world cup in 2018",
    "can you recommend a good laptop for gaming",
    "how do i integrate with quickbooks accounting software",
    "do you offer on-premise installation of your platform",
    "can customers pay with bitcoin or other crypto",
    "how do i change my profile photo in the mobile app",
    "what is your companys vacation and leave policy",
    "translate good morning into japanese",
]


def question(item):
    return item[0] if isinstance(item, (tuple, list)) else item


def run(name, questions, should_refuse):
    refused, best_scores = 0, []
    for q in questions:
        results = rag.retrieve_hybrid_scored(q)
        best_scores.append(results[0][1] if results else float("-inf"))
        refused += rag.search_docs(q)[0] == []
    ok = refused if should_refuse else len(questions) - refused
    print(f"{name:58} refused {refused:2}/{len(questions):2}   "
          f"best-score range [{min(best_scores):6.1f} .. {max(best_scores):6.1f}]")
    return ok


if __name__ == "__main__":
    rag.setup_rag()
    print(f"gate threshold: {rag.GATE_THRESHOLD}\n")
    run("held-out in-scope (TEST)  - should NOT be refused", [question(x) for x in TEST], False)
    run("calibration out-of-scope  - in-sample, used to tune", UNANSWERABLE, True)
    run("NEW out-of-scope          - never seen, independent", NEW_OUT_OF_SCOPE, True)
