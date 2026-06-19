from RAG.rag_engine import MockExamRAG

rag = MockExamRAG()
contexts = rag.retrieve_context("ssc", k=5, filters={"exam_slug": "ssc"})
print(f"Found {len(contexts)} contexts for SSC.")
if not contexts:
    # Try without filters
    contexts = rag.retrieve_context("ssc", k=5)
    print(f"Found {len(contexts)} contexts for SSC WITHOUT filters.")
