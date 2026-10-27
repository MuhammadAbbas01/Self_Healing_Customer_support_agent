"""
rag.py - Production RAG for the support agent (copied from D:\\production-rag, evaluation code removed).

Pipeline:
  docs/*.md -> split by headings -> embed (all-MiniLM-L6-v2) -> Chroma (chroma_db_v2)
  question  -> vector top 30 + BM25 top 30 -> merge (RRF) -> cross-encoder rerank -> best 5
            -> confidence gate: best score below GATE_THRESHOLD -> no documents returned

Use:
  rag.setup_rag()            # once, at app startup
  rag.search_docs(question)  # returns (relevant_docs, similar_tickets, confidence_score)
"""
import re
from pathlib import Path

from langchain_core.documents import Document
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from rank_bm25 import BM25Okapi
from sentence_transformers import CrossEncoder

BASE_DIR = Path(__file__).parent
DOCS_DIR = BASE_DIR / "docs"
CHROMA_DIR = str(BASE_DIR / "chroma_db_v2")   # new folder: the old chroma_db (V1 chunks) is not touched

RETRIEVE_K = 30          # first search: wide
FINAL_K = 5              # after reranking: narrow
GATE_THRESHOLD = -5.0    # best rerank score below this = "not enough information"

store = None
reranker = None
bm25 = None
all_texts = []
source_by_text = {}


def load_documents(folder):
    docs = []
    for f in sorted(Path(folder).glob("*")):
        if f.suffix.lower() in (".md", ".txt"):
            docs.append(Document(page_content=f.read_text(encoding="utf-8"), metadata={"source": f.name}))
    return docs


def split_documents(documents):
    """Split by markdown headings first, then cut long sections. The heading path is put in front of each chunk."""
    header_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=[("#", "h1"), ("##", "h2"), ("###", "h3")],
        strip_headers=False,
    )
    size_splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
    chunks = []

    for doc in documents:
        sections = header_splitter.split_text(doc.page_content)
        for section in sections:
            section.metadata["source"] = doc.metadata.get("source", "")

        for chunk in size_splitter.split_documents(sections):
            path = " > ".join(chunk.metadata[h] for h in ("h1", "h2", "h3") if h in chunk.metadata)
            if path:
                chunk.page_content = path + "\n" + chunk.page_content
            chunks.append(chunk)

    return chunks


def setup_rag():
    """Build (first run only) and load the store, the keyword index and the reranker."""
    global store, reranker, bm25, all_texts, source_by_text

    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    store = Chroma(
        collection_name="company_docs",
        embedding_function=embeddings,
        persist_directory=CHROMA_DIR,
    )

    if not store.get(limit=1)["ids"]:
        chunks = split_documents(load_documents(DOCS_DIR))
        if not chunks:
            raise RuntimeError(f"No documents found in {DOCS_DIR}")
        store.add_documents(chunks)

    stored = store.get()
    all_texts = stored["documents"]
    source_by_text = {
        text: (meta or {}).get("source", "")
        for text, meta in zip(stored["documents"], stored["metadatas"])
    }

    tokenize = _tokenize
    bm25 = BM25Okapi([tokenize(t) for t in all_texts])
    reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

    print(f"RAG ready: {len(all_texts)} chunks")


def _tokenize(text):
    return re.findall(r"[a-z0-9_]+", text.lower())


def retrieve_hybrid_scored(question):
    """Hybrid: vector list + keyword list, merged with RRF, then reranked. Returns [(text, score)]."""
    if store is None:
        setup_rag()

    # 1. list by meaning
    vector = [c.page_content for c in store.similarity_search(question, k=RETRIEVE_K)]

    # 2. list by keywords
    scores = bm25.get_scores(_tokenize(question))
    best = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:RETRIEVE_K]
    keyword = [all_texts[i] for i in best]

    # 3. merge the two lists (RRF: each list gives 1 / (60 + position))
    merged = {}
    for one_list in (vector, keyword):
        for position, text in enumerate(one_list, start=1):
            merged[text] = merged.get(text, 0) + 1 / (60 + position)
    candidates = sorted(merged, key=merged.get, reverse=True)[:RETRIEVE_K]

    # 4. rerank and keep the best 5
    rerank_scores = reranker.predict([(question, t) for t in candidates])
    ranked = sorted(zip(candidates, rerank_scores), key=lambda x: x[1], reverse=True)
    return [(t, float(s)) for t, s in ranked[:FINAL_K]]


def search_docs(question):
    """Returns (relevant_docs, similar_tickets, confidence_score).
    If the best score is under the gate, no documents are returned (so the agent is not grounded on weak matches)."""
    results = retrieve_hybrid_scored(question)

    if not results or results[0][1] < GATE_THRESHOLD:
        return [], [], 0.3

    relevant_docs = [text for text, _ in results]
    similar_tickets = [t for t in relevant_docs if "support_tickets" in source_by_text.get(t, "")]
    return relevant_docs, similar_tickets, 0.9
