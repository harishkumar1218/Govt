import uuid
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels
from sentence_transformers import SentenceTransformer

client = QdrantClient(host="localhost", port=6333)
COLLECTION_NAME = "gov_exam_knowledge"
model = SentenceTransformer("all-MiniLM-L6-v2") # Placeholder for BGE-M3

def init_qdrant():
    try:
        client.get_collection(COLLECTION_NAME)
    except Exception:
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=qmodels.VectorParams(
                size=384, # all-MiniLM-L6-v2 size. BGE-M3 is 1024
                distance=qmodels.Distance.COSINE
            )
        )

def chunk_text(text, chunk_size=800, overlap=120):
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size - overlap):
        chunks.append(" ".join(words[i:i + chunk_size]))
    return chunks

def index_document(doc_id, text, metadata):
    init_qdrant()
    chunks = chunk_text(text)
    points = []
    for i, chunk in enumerate(chunks):
        vector = model.encode(chunk).tolist()
        payload = {
            "document_id": str(doc_id),
            "chunk_index": i,
            "chunk_text": chunk,
            **metadata
        }
        points.append(qmodels.PointStruct(id=str(uuid.uuid4()), vector=vector, payload=payload))
        
    client.upsert(
        collection_name=COLLECTION_NAME,
        points=points
    )
    return len(points)
