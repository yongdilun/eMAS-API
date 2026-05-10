import chromadb
from chromadb.utils import embedding_functions

client = chromadb.PersistentClient(path="factory_agent/rag/vector_db")
collection = client.get_collection(name="emas_knowledge")

results = collection.get(where={"doc_id": "osha_3120_lockout_tagout"}, limit=5, include=["metadatas"])
print(results["metadatas"])
