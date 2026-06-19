from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer
from qdrant_client.http import models as qmodels

import os
qdrant_host = os.environ.get('QDRANT_HOST', 'localhost')
client = QdrantClient(host=qdrant_host, port=6333)
model = SentenceTransformer("all-MiniLM-L6-v2")
COLLECTION_NAME = "gov_exam_knowledge"

def retrieve_context(query: str, exam: str = None, top_k: int = 10):
    query_vector = model.encode(query).tolist()
    
    filter_query = None
    if exam:
        filter_query = qmodels.Filter(
            must=[
                qmodels.FieldCondition(
                    key="exam",
                    match=qmodels.MatchValue(value=exam)
                )
            ]
        )
        
    try:
        results = client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_vector,
            query_filter=filter_query,
            limit=top_k
        )
        return [hit.payload["chunk_text"] for hit in results.points]
    except Exception as e:
        print(f"Retrieval error: {e}")
        return []
