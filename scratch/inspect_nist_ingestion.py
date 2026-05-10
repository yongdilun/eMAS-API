import chromadb
from chromadb.utils import embedding_functions

def inspect_chroma():
    client = chromadb.PersistentClient(path="factory-agent/factory_agent/rag/vector_db")
    collection = client.get_collection(name="emas_knowledge")
    
    # Check count
    count = collection.count()
    print(f"Total chunks in emas_knowledge: {count}")
    
    # Query for NIST chunks
    results = collection.get(
        where={"doc_id": "nist_csf_2_0"},
        limit=10
    )
    
    print(f"Chunks found for doc_id 'nist_csf_2_0': {len(results['ids'])}")
    for i in range(len(results['ids'])):
        print(f"ID: {results['ids'][i]}")
        print(f"Metadata: {results['metadatas'][i]}")
        print(f"Text Snippet: {results['documents'][i][:200]}...")
        print("-" * 40)

if __name__ == "__main__":
    inspect_chroma()
