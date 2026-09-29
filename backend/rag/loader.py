from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

DATA_DIR = Path(__file__).resolve().parents[2] / "data"

DOC_FILES = [
    "Company_Technical_Handbook.md",
    "support_tickets_archive.md",
    "engineering_wiki.md",
]


def chunk_text(text, chunk_size=1000, overlap=100):
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap
    return chunks


def load_documents():
    documents = {}
    for name in DOC_FILES:
        path = DATA_DIR / name
        if path.exists():
            documents[name] = path.read_text(encoding="utf-8")
            print(f"Loaded {name} ({len(documents[name])} chars)")
        else:
            print(f"Missing file: {path}")
    return documents


def setup_rag():
    documents = load_documents()
    if not documents:
        raise FileNotFoundError(f"No documents found in {DATA_DIR}")

    all_chunks = []
    chunk_metadata = []
    for doc_name, content in documents.items():
        chunks = chunk_text(content)
        print(f"{doc_name}: {len(chunks)} chunks")
        for i, chunk in enumerate(chunks):
            all_chunks.append(chunk)
            chunk_metadata.append({
                "document": doc_name,
                "chunk_id": i,
                "source": doc_name,
            })

    embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
    all_embeddings = embedding_model.encode(all_chunks, show_progress_bar=True).tolist()

    chroma_client = chromadb.Client()
    try:
        chroma_client.delete_collection("company_docs")
    except Exception:
        pass

    collection = chroma_client.create_collection(
        name="company_docs",
        metadata={"description": "Company documentation for RAG"},
        embedding_function=None,
    )

    batch_size = 100
    for i in range(0, len(all_chunks), batch_size):
        end = i + batch_size
        collection.add(
            documents=all_chunks[i:end],
            metadatas=chunk_metadata[i:end],
            embeddings=all_embeddings[i:end],
            ids=[f"chunk_{j}" for j in range(i, min(end, len(all_chunks)))],
        )

    print(f"RAG ready: {len(documents)} documents, {len(all_chunks)} chunks")
    return collection, embedding_model
