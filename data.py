from pathlib import Path
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
# 1. folder name "docs"


"""  

def load_documents(Folder):
    document = list(Path(Folder).glob("*"))
    return document

"""

# 2. function load_documents(folder) that returns a list
def load_documents(Folder):

# 3.     empty list
    files = []
# 4.     for each file in the folder (sorted), only if it ends with .md or .txt
    for f in sorted(Path(Folder).glob("*")):
        
        #read teh text
        text = f.read_text(encoding="utf-8")
        #print(f" Filename: {f.name}, length: {len(text)}")
        doc = Document(page_content=text, metadata={"source": f.name}) 

        files.append(doc)

    return files    

def split_documents(documents):
    #initalize the text splitter
    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
    chunks = splitter.split_documents(documents)

    return chunks


def build_store(chunks):
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    store = Chroma(
        collection_name="company_docs",
        embedding_function=embeddings,
        persist_directory="chroma_db",
    )

    if not store.get(limit=1)["ids"]:
        store.add_documents(chunks)

    return store    
  


    




  

if __name__ == "__main__":
    document = load_documents("docs")
    #print(len(document), document[0].metadata)

    chunks = split_documents(document)
    #print(len(document), "documents ->", len(chunks), "chunks")
    #print(chunks[0].metadata)
    #print(chunks[0].page_content)

    store = build_store(chunks)
    print("stored chunks:", len(store.get()["ids"]))