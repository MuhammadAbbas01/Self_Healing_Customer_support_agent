"""Retrieval evaluation: vector only vs vector + rerank vs hybrid + rerank.

A question counts as a hit at position k when one of the top-k chunks contains a proof phrase
from the hand-labelled golden set (evaluation/golden.py).

Run from the project root:
    python evaluation/rag_eval.py
"""
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import rag                      # noqa: E402
from rag import loader          # noqa: E402
from golden import DEV, TEST    # noqa: E402

rag.setup_rag()
RETRIEVE_K, FINAL_K = loader.RETRIEVE_K, loader.FINAL_K


def retrieve_baseline(question):
    """Vector search only: top 5 chunks by meaning."""
    return [c.page_content for c in loader.store.similarity_search(question, k=FINAL_K)]


def retrieve_reranked(question):
    """Vector search for 30 candidates, then a cross-encoder re-sorts them."""
    texts = [c.page_content for c in loader.store.similarity_search(question, k=RETRIEVE_K)]
    scores = loader.reranker.predict([(question, t) for t in texts])
    ranked = sorted(zip(texts, scores), key=lambda x: x[1], reverse=True)
    return [t for t, _ in ranked[:FINAL_K]]


def retrieve_hybrid(question):
    """Vector + BM25 merged with RRF, then reranked (what the agent uses)."""
    return [t for t, _ in loader.retrieve_hybrid_scored(question)]


def evaluate(golden, retrieve):
    ranks = []
    for question, phrases in golden:
        rank = None
        for position, text in enumerate(retrieve(question), start=1):
            if any(p.lower() in text.lower() for p in phrases):
                rank = position
                break
        ranks.append(rank)
    n = len(ranks)
    hit = lambda k: sum(1 for r in ranks if r is not None and r <= k) / n
    mrr = sum(1 / r for r in ranks if r is not None) / n
    return hit(1), hit(3), hit(5), mrr


if __name__ == "__main__":
    for name, fn in [("vector only", retrieve_baseline),
                     ("vector + rerank", retrieve_reranked),
                     ("hybrid + rerank", retrieve_hybrid)]:
        h1, h3, h5, mrr = evaluate(DEV, fn)
        print(f"DEV  ({len(DEV)} q) {name:16} hit@1={h1:.0%} hit@3={h3:.0%} hit@5={h5:.0%} MRR={mrr:.2f}")
    print()
    for name, fn in [("vector only", retrieve_baseline), ("hybrid + rerank", retrieve_hybrid)]:
        h1, h3, h5, mrr = evaluate(TEST, fn)
        print(f"TEST ({len(TEST)} q, held out) {name:16} hit@1={h1:.0%} hit@3={h3:.0%} hit@5={h5:.0%} MRR={mrr:.2f}")
