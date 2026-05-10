import chromadb

def inspect_osha():
    client = chromadb.PersistentClient(path="factory_agent/rag/vector_db")
    collection = client.get_collection(name="emas_knowledge")
    
    results = collection.get(
        where={"doc_id": "osha_3120_lockout_tagout"},
        limit=1
    )
    
    if results['ids']:
        print(f"Metadata for OSHA: {results['metadatas'][0]}")
    else:
        print("OSHA document not found in vector DB.")

if __name__ == "__main__":
    inspect_osha()
