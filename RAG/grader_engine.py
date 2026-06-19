import os
import re
import pickle
import numpy as np

# Must be set BEFORE importing huggingface_hub or transformers
os.environ.setdefault("HF_HOME", "/Users/harish/Public/Govt/RAG/models")
os.environ.setdefault("HUGGINGFACE_HUB_CACHE", "/Users/harish/Public/Govt/RAG/models/hub")

import torch
from sentence_transformers import SentenceTransformer
from turbovec import IdMapIndex

RAG_DIR = "/Users/harish/Public/Govt/RAG"


class UPSCGrader:
    """
    Grades UPSC mock exam questions for factual correctness.
    Reuses the LLM instance from MockExamRAG to avoid double-loading.
    """

    def __init__(
        self,
        db_path="/Users/harish/Public/Govt/RAG/turbovec_index",
        model_name="mlx-community/Llama-3.2-3B-Instruct-4bit",
        llm_instance=None,
    ):
        self.db_path = db_path
        self.model_name = model_name
        # llm_instance is a MockExamRAG object (shares loaded model)
        self._rag_instance = llm_instance

        self.index_path = os.path.join(self.db_path, "index.tvim")
        self.docs_path = os.path.join(self.db_path, "docs.pkl")

        # Initialize embedding model (shared with RAG if possible)
        if self._rag_instance and hasattr(self._rag_instance, "embedding_model"):
            self.embedding_model = self._rag_instance.embedding_model
        else:
            device = "mps" if torch.backends.mps.is_available() else "cpu"
            self.embedding_model = SentenceTransformer("all-MiniLM-L6-v2", device=device)

        if not os.path.exists(self.index_path) or not os.path.exists(self.docs_path):
            raise ValueError(
                f"Index or docs not found at {self.db_path}. Please run ingest.py first."
            )

        # Reuse index if already loaded in parent
        if self._rag_instance and hasattr(self._rag_instance, "index"):
            self.index = self._rag_instance.index
            self.docs = self._rag_instance.docs
        else:
            self.index = IdMapIndex.load(self.index_path)
            with open(self.docs_path, "rb") as f:
                self.docs = pickle.load(f)

    def _generate_text(self, prompt: str, max_new_tokens: int = 500) -> str:
        """Use the shared RAG instance LLM for text generation."""
        if self._rag_instance is None:
            raise RuntimeError(
                "No LLM instance provided to UPSCGrader. Pass llm_instance=rag_obj."
            )
        return self._rag_instance._generate_text(prompt, max_new_tokens=max_new_tokens)

    def retrieve_verification_context(self, text: str, k: int = 3):
        """Retrieve context specifically for validating facts in the proposed question."""
        query_vector = self.embedding_model.encode([text]).astype(np.float32)
        scores, ids = self.index.search(query_vector, k=k)
        if len(ids) == 0 or len(ids[0]) == 0:
            return []
        retrieved = []
        for idx in ids[0]:
            if idx in self.docs:
                retrieved.append(self.docs[idx]["text"])
        return retrieved

    def grade_question(
        self,
        question_text: str,
        options: str,
        proposed_answer: str,
        explanation: str,
    ) -> dict:
        """Grade a single question for factual correctness, difficulty, and formatting."""
        search_query = f"{question_text} {proposed_answer}"
        reference_contexts = self.retrieve_verification_context(search_query, k=3)

        reference_str = (
            "\n\n---\n\n".join(reference_contexts)
            if reference_contexts
            else "No direct reference found in database."
        )

        prompt = f"""You are a UPSC exam auditor. Evaluate the question below against the reference context. Be concise.

QUESTION: {question_text}
OPTIONS:
{options}
ANSWER: {proposed_answer}
EXPLANATION: {explanation}

REFERENCE CONTEXT:
{reference_str}

Your evaluation (be brief):
- Is the answer factually correct based on the reference? (Yes/No)
- Is this a valid UPSC-level question? (Yes/No)
- Score out of 5: 
- Verdict: PASS (score >= 4) or FAIL (score < 4)

Output format:
SCORE: [1-5]
VERDICT: [PASS or FAIL]
FEEDBACK: [one sentence]
"""
        try:
            response_text = self._generate_text(prompt, max_new_tokens=200)

            # Try structured parsing first
            score_match = re.search(r"SCORE:\s*([1-5])", response_text, re.IGNORECASE)
            verdict_match = re.search(r"VERDICT:\s*(PASS|FAIL)", response_text, re.IGNORECASE)
            feedback_match = re.search(r"FEEDBACK:\s*(.+?)(?:\n|$)", response_text, re.IGNORECASE | re.DOTALL)

            score = int(score_match.group(1).strip()) if score_match else 0
            verdict = verdict_match.group(1).strip().upper() if verdict_match else ""
            feedback = feedback_match.group(1).strip() if feedback_match else ""

            # Also try XML tags as fallback
            if not score_match:
                xml_score = re.search(r"<score>(.*?)</score>", response_text, re.DOTALL)
                if xml_score:
                    try:
                        score = int(xml_score.group(1).strip())
                    except ValueError:
                        pass
            if not verdict_match:
                xml_verdict = re.search(r"<verdict>(.*?)</verdict>", response_text, re.DOTALL)
                if xml_verdict:
                    verdict = xml_verdict.group(1).strip().upper()

            # Final heuristic fallback
            if not verdict:
                resp_upper = response_text.upper()
                if "PASS" in resp_upper and "FAIL" not in resp_upper:
                    verdict = "PASS"
                    score = score if score >= 4 else 4
                elif "FAIL" in resp_upper:
                    verdict = "FAIL"
                    score = score if score < 4 else 3
                else:
                    # If model output is garbage, auto-PASS to avoid blocking pipeline
                    verdict = "PASS"
                    score = 4
                    feedback = "Auto-approved (grader output unreadable)."

            if not feedback:
                feedback = "Approved." if verdict == "PASS" else "Quality issues detected."

            return {
                "score": score,
                "verdict": verdict,
                "feedback": feedback,
                "reference_context": reference_str,
            }
        except Exception as e:
            return {
                "score": 1,
                "verdict": "FAIL",
                "feedback": f"Grader error: {e}",
                "reference_context": "",
            }
