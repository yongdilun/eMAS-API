import chromadb
import os

def inspect_chunks():
    persist_directory = "factory_agent/rag/vector_db"
    client = chromadb.PersistentClient(path=persist_directory)
    collection = client.get_collection(name="emas_knowledge")
    
    doc_id = "osha_3120_lockout_tagout"
    results = collection.get(
        where={"doc_id": doc_id},
        include=["documents", "metadatas"]
    )
    
    combined = []
    for i in range(len(results["ids"])):
        combined.append({
            "id": results["ids"][i],
            "text": results["documents"][i],
            "metadata": results["metadatas"][i]
        })
    
    combined.sort(key=lambda x: x["id"])
    
    print(f"Total chunks for {doc_id}: {len(combined)}")
    for item in combined:
        # We know from the eval log that c0031 and c0032 are the ones.
        if "_c003" in item["id"]:
            print(f"=== {item['id']} ===")
            print(item['text'])
            print("-" * 20)

if __name__ == "__main__":
    inspect_chunks()
