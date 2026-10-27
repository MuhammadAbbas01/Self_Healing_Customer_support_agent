from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from golden import DEV

embedding = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
store = Chroma(collection_name="company_docs",
               embedding_function=embedding,
               persist_directory="chroma_db")

def evaluate(golden, k=5):
    hits = 0
    missed = []
    for question, phrases in golden:
        chunks = store.similarity_search(question, k=k)
        found = False
        for chunk in chunks:
            for p in phrases:
                if p.lower() in chunk.page_content.lower():
                    found = True
        if found:
            hits += 1
        else:
            missed.append(question)
    return hits / len(golden), missed

rate, missed = evaluate(DEV)
print(f"Hit rate@5 on DEV: {rate:.0%}")
for q in missed:
    print("MISSED:", q)