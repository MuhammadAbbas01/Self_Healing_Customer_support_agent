from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

embedding = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

store = Chroma(collection_name = "company_docs",
embedding_function = embedding,
persist_directory = "chroma_db")

results = store.similarity_search_with_score("my api key gives 401 error", k=3)

for chunk, distance in results:
    #print(distance, chunks.metadata["source"])
    print(distance, chunk.metadata["source"])
    #print(chunk.page_content[:150])
    print("-----")
