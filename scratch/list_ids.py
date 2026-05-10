import chromadb
import os

def list_ids():
    persist_directory = "factory-agent/factory_agent/rag/vector_db"
    client = chromadb.PersistentClient(path=persist_directory)
    collection = client.get_collection(name="emas_knowledge")
    
    doc_id = "osha_3120_lockout_tagout"
    results = collection.get(
        where={"doc_id": doc_id},
        include=["metadatas"]
    )
    
    print(f"Total chunks for {doc_id}: {len(results['ids'])}")
    print("Sample IDs:")
    for id in sorted(results['ids'])[:100]:
        print(id)

if __name__ == "__main__":
    list_ids()
