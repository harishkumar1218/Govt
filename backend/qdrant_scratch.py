from qdrant_client import QdrantClient
client = QdrantClient(host="localhost", port=6333)
results = client.query_points(collection_name="gov_exam_knowledge", query=[0.1]*384, limit=1)
print(type(results))
print(results)
