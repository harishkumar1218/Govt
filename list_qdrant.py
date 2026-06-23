import qdrant_client
client = qdrant_client.QdrantClient(url="http://localhost:6333")
for collection in client.get_collections().collections:
    print(collection.name)
