from RAG.rag_engine import MockExamRAG

rag = MockExamRAG()
contexts = rag.retrieve_context("ssc Tier 1", k=4, filters={"exam_slug": "ssc"})
print(f"Found {len(contexts)} contexts for SSC Tier 1 fallback query.")
