import chromadb
import os

def list_collections():
    persist_directory = "factory-agent/factory_agent/rag/vector_db"
    client = chromadb.PersistentClient(path=persist_directory)
    print(f"Collections: {client.list_collections()}")

if __name__ == "__main__":
    list_collections()
