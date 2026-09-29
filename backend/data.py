"""
data.py - Document loading and RAG setup

This file:
1. Loads the 3 company documentation files
2. Chunks them into smaller pieces
3. Creates vector database with ChromaDB
4. Makes them searchable
"""

import os
import chromadb
from sentence_transformers import SentenceTransformer


# ============================================
# FUNCTION 1: Chunk Text
# ============================================
def chunk_text(text, chunk_size=1000, overlap=100):
    """
    Split long text into smaller overlapping chunks

    Why overlap? So important info isn't split between chunks

    Example:
    Text: "The API key must be sk-live-xxx. This format is required..."
    Chunk 1: "The API key must be sk-live-xxx. This format..."
    Chunk 2: "...sk-live-xxx. This format is required for production..."
    (overlap ensures "sk-live-xxx" appears in both)
    """
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start = end - overlap  # Move back a bit for overlap
    return chunks


# ============================================
# FUNCTION 2: Load Documents
# ============================================
def load_documents():
    """
    Load the 3 markdown documentation files

    Returns: Dictionary {filename: content}
    """
    documents = {}
    doc_files = [
        'Company_Technical_Handbook.md',
        'support_tickets_archive.md',
        'engineering_wiki.md'
    ]

    # Check if we're in a 'data' folder or root
    data_folder = 'data' if os.path.exists('data') else '.'

    for filename in doc_files:
        filepath = os.path.join(data_folder, filename)
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                documents[filename] = content
                print(f"✅ Loaded {filename} - {len(content)} characters")
        else:
            print(f"⚠️ Warning: {filename} not found!")

    return documents


# ============================================
# FUNCTION 3: Setup RAG System
# ============================================
def setup_rag():
    """
    Complete RAG setup:
    1. Load documents
    2. Chunk them
    3. Generate embeddings
    4. Create vector database

    Returns: (collection, embedding_model) for use in agent
    """

    print("\n📚 Setting up RAG system...")

    # Step 1: Load documents
    print("\n1️⃣ Loading documents...")
    documents = load_documents()

    if not documents:
        raise Exception("No documents loaded! Check file paths.")

    # Step 2: Chunk all documents
    print("\n2️⃣ Chunking documents...")
    all_chunks = []
    chunk_metadata = []

    for doc_name, content in documents.items():
        chunks = chunk_text(content, chunk_size=1000, overlap=100)
        print(f"   📄 {doc_name}: {len(chunks)} chunks")

        for i, chunk in enumerate(chunks):
            all_chunks.append(chunk)
            chunk_metadata.append({
                "document": doc_name,
                "chunk_id": i,
                "source": doc_name
            })

    print(f"\n   ✅ Total chunks: {len(all_chunks)}")

    # Step 3: Load embedding model
    print("\n3️⃣ Loading embedding model...")
    embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
    print("   ✅ Model loaded!")

    # Step 4: Generate embeddings
    print("\n4️⃣ Generating embeddings...")
    all_embeddings = embedding_model.encode(
        all_chunks,
        show_progress_bar=True
    ).tolist()
    print("   ✅ Embeddings generated!")

    # Step 5: Create ChromaDB collection
    print("\n5️⃣ Creating vector database...")
    chroma_client = chromadb.Client()

    # Delete old collection if exists
    try:
        chroma_client.delete_collection("company_docs")
    except:
        pass

    # Create new collection
    collection = chroma_client.create_collection(
        name="company_docs",
        metadata={"description": "Company documentation for RAG"},
        embedding_function=None  # We provide embeddings manually
    )

    # Step 6: Add chunks to database in batches
    print("\n6️⃣ Adding chunks to database...")
    batch_size = 100
    for i in range(0, len(all_chunks), batch_size):
        batch_chunks = all_chunks[i:i + batch_size]
        batch_metadata = chunk_metadata[i:i + batch_size]
        batch_embeddings = all_embeddings[i:i + batch_size]
        batch_ids = [f"chunk_{j}" for j in range(i, i + len(batch_chunks))]

        collection.add(
            documents=batch_chunks,
            metadatas=batch_metadata,
            embeddings=batch_embeddings,
            ids=batch_ids
        )
        print(f"   ✅ Batch {i // batch_size + 1}/{(len(all_chunks) - 1) // batch_size + 1}")

    print("\n🎉 RAG SYSTEM READY!")
    print(f"   - {len(documents)} documents loaded")
    print(f"   - {len(all_chunks)} searchable chunks")
    print(f"   - Vector database created\n")

    return collection, embedding_model


# ============================================
# Run setup when file is imported
# ============================================
if __name__ == "__main__":
    # If running this file directly, setup RAG
    collection, embedding_model = setup_rag()
    print("✅ data.py setup complete!")