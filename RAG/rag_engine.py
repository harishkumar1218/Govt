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
import mlx_lm

RAG_DIR = "/Users/harish/Public/Govt/RAG"

# ─── Model Loading ───────────────────────────────────────────────────────────

def _get_device():
    if torch.backends.mps.is_available():
        return "mps"
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


class MockExamRAG:
    def __init__(
        self,
        db_path="/Users/harish/Public/Govt/RAG/turbovec_index",
        model_name="mlx-community/Llama-3.2-3B-Instruct-4bit",
    ):
        self.db_path = db_path
        self.model_name = model_name
        self.llm = None
        self.tokenizer = None

        self.index_path = os.path.join(self.db_path, "index.tvim")
        self.docs_path = os.path.join(self.db_path, "docs.pkl")

        # Load SentenceTransformer for embedding generation
        device = _get_device()
        print(f"Loading embedding model on {device}...")
        self.embedding_model = SentenceTransformer("all-MiniLM-L6-v2", device=device)

        # Load Turbovec index and document metadata
        print("Loading Turbovec index...")
        if not os.path.exists(self.index_path) or not os.path.exists(self.docs_path):
            raise ValueError(
                f"Index or docs not found at {self.db_path}. Please run ingest.py first."
            )

        self.index = IdMapIndex.load(self.index_path)
        with open(self.docs_path, "rb") as f:
            self.docs = pickle.load(f)

    # ─── LLM Lazy Loading ────────────────────────────────────────────────────

    def _ensure_llm_loaded(self):
        if self.llm is not None:
            return

        print(f"Loading LLM '{self.model_name}' using MLX...")
        self.llm, self.tokenizer = mlx_lm.load(self.model_name)
        print("LLM loaded via MLX.")

    # ─── Inference Helper ────────────────────────────────────────────────────

    def _generate_text(self, prompt: str, max_new_tokens: int = 1500) -> str:
        """Run inference using the chat template (required for Instruct models)."""
        self._ensure_llm_loaded()

        # Wrap in chat format — critical for Instruct models
        messages = [
            {"role": "system", "content": "You are a helpful UPSC exam assistant."},
            {"role": "user", "content": prompt},
        ]
        
        if hasattr(self.tokenizer, "apply_chat_template"):
            text = self.tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
            )
        else:
            text = prompt

        response = mlx_lm.generate(
            self.llm,
            self.tokenizer,
            prompt=text,
            max_tokens=max_new_tokens,
            verbose=False
        )
        return response

    # ─── Retrieval ───────────────────────────────────────────────────────────

    def retrieve_context(self, query: str, k: int = 5, filters: dict = None):
        """Retrieve relevant context chunks from the Turbovec index with filtering."""
        query_vector = self.embedding_model.encode([query]).astype(np.float32)
        
        # If filters are provided, search across all documents to prevent smaller tracks (e.g. SSC) from being overshadowed by larger ones (like UPSC)
        search_k = len(self.docs) if filters else k
        scores, ids = self.index.search(query_vector, k=search_k)
        if len(ids) == 0 or len(ids[0]) == 0:
            return []
            
        retrieved = []
        for idx in ids[0]:
            if idx in self.docs:
                doc_info = self.docs[idx]
                
                # Apply filters
                match = True
                if filters:
                    for field, value in filters.items():
                        if value:
                            doc_val = doc_info.get(field)
                            # Perform case-insensitive comparison
                            if doc_val is None or str(doc_val).lower() != str(value).lower():
                                match = False
                                break
                if match:
                    retrieved.append(doc_info["text"])
                    if len(retrieved) >= k:
                        break
        return retrieved

    # ─── Mock Exam Generation ────────────────────────────────────────────────

    def generate_mock_exam(self, topic: str, config: dict) -> str:
        """Generate mock exam questions using LLM based on retrieved context."""
        import json
        print(f"Retrieving context for topic: {topic}...")
        
        # Add filters to query
        track = config.get('track_slug', '')
        stage = config.get('stage', '')
        query_str = f"{track} {stage} {topic}"
        
        # Construct retrieval filters
        filters = {}
        if track:
            # Map upsc to upsc-civil-services slug
            mapped_track = "upsc-civil-services" if track.lower() == "upsc" else track.lower()
            filters["exam_slug"] = mapped_track
        if stage:
            filters["stage"] = stage
            
        # Incorporate custom config-level filters
        config_filters = config.get('retrieval_filters', {})
        if isinstance(config_filters, dict):
            for f_key, f_val in config_filters.items():
                if f_key == "track":
                    filters["exam_slug"] = "upsc-civil-services" if f_val == "upsc" else f_val
                else:
                    filters[f_key] = f_val
                    
        k_count = config.get('question_count', config.get('num_questions', 3))
        contexts = self.retrieve_context(query_str, k=k_count * 2, filters=filters)

        if not contexts:
            # Fallback 1: Try broader query with just track and stage, relaxing strict filters
            print("⚠️ No specific context found. Trying broader track-level fallback query...")
            fallback_query = f"{track} {stage}"
            fallback_filters = {"exam_slug": filters.get("exam_slug")} if "exam_slug" in filters else None
            contexts = self.retrieve_context(fallback_query, k=k_count * 2, filters=fallback_filters)
            
        if not contexts:
            # Fallback 2: Try general syllabus query, relaxing strict filters
            print("⚠️ Still no context. Trying general syllabus fallback query...")
            fallback_query = "syllabus exam details pattern"
            fallback_filters = {"exam_slug": filters.get("exam_slug")} if "exam_slug" in filters else None
            contexts = self.retrieve_context(fallback_query, k=k_count * 2, filters=fallback_filters)

        if not contexts:
            return json.dumps({"error": "No relevant context found in the database to generate questions."})

        context_str = "\n\n---\n\n".join(contexts)

        gen_prompt = config['generation_prompt'].replace('{question_count}', str(k_count))
        prompt = f"""{config['system_prompt']}

{gen_prompt}

Topic: {topic}

Context material extracted from Previous Year Papers and official documents:
{context_str}

Ensure the output is STRICTLY a JSON object formatted as follows:
{{
  "quiz": {{
    "track_slug": "{config['track_slug']}",
    "exam_name": "{config['exam_name']}",
    "stage": "{config['stage']}",
    "paper": "{config['paper']}",
    "duration_seconds": {config['duration_seconds']},
    "marks_per_question": {config['marks_per_question']},
    "negative_marking": {config['negative_marking']}
  }},
  "questions": [
    {{
      "order": 1,
      "text": "Question text here",
      "options": {{
        "A": "Option A text",
        "B": "Option B text",
        "C": "Option C text",
        "D": "Option D text"
      }},
      "correct_answer": "A",
      "explanation": "Detailed explanation citing the source.",
      "subject": "{topic}",
      "difficulty": "medium",
      "source_refs": []
    }}
  ]
}}

Generate the JSON now:
"""
        print(f"Generating mock exam with '{self.model_name}'...")
        try:
            raw_exam = self._generate_text(prompt, max_new_tokens=2500)
            raw_exam = raw_exam.strip()
            if raw_exam.startswith("```json"):
                raw_exam = raw_exam[7:]
            if raw_exam.endswith("```"):
                raw_exam = raw_exam[:-3]
            return raw_exam.strip()
        except Exception as e:
            return json.dumps({"error": str(e)})

    # ─── Prediction ──────────────────────────────────────────────────────────

    def predict_expected_questions(self, topic: str, num_questions: int = 3) -> str:
        """Analyze past years' questions to predict expected future exam questions."""
        print(f"Retrieving past context and syllabus for topic: {topic}...")
        contexts = self.retrieve_context(topic, k=num_questions * 3)

        if not contexts:
            return "No relevant past papers or syllabus materials found to analyze trends."

        context_str = "\n\n---\n\n".join(contexts)

        prompt = f"""You are an elite UPSC examiner and strategist. Analyze historical exam trends to predict the most likely questions for the upcoming UPSC Civil Services Exam.

Topic: {topic}

Historical contexts retrieved from Past Papers, Syllabus Guides, and Cutoffs:
{context_str}

Instructions:
1. Provide a brief **Trend Analysis** (1-2 paragraphs) identifying what subtopics have been heavily tested.
2. Generate exactly {num_questions} predicted MCQs with high probability of appearing in future exams.
3. For each question provide 4 options, correct answer, and rationale for prediction.
4. Format the output clearly in Markdown.

## Trend Analysis
[Trend analysis text]

## Predicted Questions

### Expected Question [number]
[Question text]

**Options:**
A) [Option A]
B) [Option B]
C) [Option C]
D) [Option D]

**Answer:** [Correct Option Letter]
**Rationale for Prediction:** [Explanation]

Begin:
"""
        print(f"Analyzing trends and predicting questions using '{self.model_name}'...")
        try:
            raw_predictions = self._generate_text(prompt, max_new_tokens=1500)
            return self._run_critique_correction_loop(raw_predictions)
        except Exception as e:
            return f"Error during prediction: {e}"

    # ─── Critique-Correction Loop ────────────────────────────────────────────

    def _parse_questions(self, raw_text: str):
        """Parse raw generated text into individual question dicts."""
        pattern = r"(### (?:Expected )?Question \d+.*?)(?=### (?:Expected )?Question \d+|\Z)"
        matches = re.findall(pattern, raw_text, re.DOTALL | re.IGNORECASE)

        parsed_questions = []
        for match in matches:
            lines = match.strip().split("\n")
            header = lines[0]
            match_str = match.strip()

            options_match = re.search(
                r"\*\*Options:\*\*(.*?)(?=\*\*Answer:|\Z)", match_str, re.DOTALL | re.IGNORECASE
            )
            answer_match = re.search(r"\*\*Answer:\*\*\s*([A-D])", match_str, re.IGNORECASE)
            explanation_match = re.search(
                r"\*\*(?:Explanation|Rationale for Prediction):\*\*(.*)",
                match_str,
                re.DOTALL | re.IGNORECASE,
            )

            options_start = match_str.find("**Options:**")
            if options_start != -1:
                question_text = match_str[len(header) : options_start].strip()
            else:
                question_text = match_str[len(header) :].strip()

            parsed_questions.append(
                {
                    "raw_block": match_str,
                    "header": header,
                    "question_text": question_text,
                    "options": options_match.group(1).strip() if options_match else "",
                    "proposed_answer": answer_match.group(1).strip() if answer_match else "",
                    "explanation": explanation_match.group(1).strip() if explanation_match else "",
                }
            )

        return parsed_questions

    def _refine_question(self, question_data: dict, feedback: str, reference_context: str) -> str:
        """Refine a question based on grader feedback."""
        prompt = f"""You are an expert UPSC examiner. A proposed question failed audit. Correct it based on the grader feedback and reference context.

FAILED QUESTION:
Header: {question_data['header']}
Question: {question_data['question_text']}
Options:
{question_data['options']}
Proposed Answer: {question_data['proposed_answer']}
Explanation: {question_data['explanation']}

GRADER FEEDBACK:
{feedback}

GROUND-TRUTH REFERENCE CONTEXT:
{reference_context}

INSTRUCTIONS:
Revise the question to be factually correct. Output ONLY the corrected question in this format:
{question_data['header']}
[Corrected Question text]

**Options:**
A) [Option A]
B) [Option B]
C) [Option C]
D) [Option D]

**Answer:** [Correct Option Letter]
**Explanation:** [Correct explanation]
"""
        try:
            return self._generate_text(prompt, max_new_tokens=800).strip()
        except Exception as e:
            print(f"Error refining question: {e}")
            return question_data["raw_block"]

    def _run_critique_correction_loop(self, raw_text: str) -> str:
        """Grade each question and refine those that fail audit."""
        from grader_engine import UPSCGrader

        grader = UPSCGrader(
            db_path=self.db_path,
            model_name=self.model_name,
            llm_instance=self,  # Share the loaded LLM instance
        )

        parsed_questions = self._parse_questions(raw_text)
        if not parsed_questions:
            return raw_text

        final_blocks = []
        first_q_index = raw_text.lower().find("### ")
        intro_text = raw_text[:first_q_index] if first_q_index != -1 else ""

        for idx, q_data in enumerate(parsed_questions):
            print(f"Auditing question {idx + 1}...")
            result = grader.grade_question(
                question_text=q_data["question_text"],
                options=q_data["options"],
                proposed_answer=q_data["proposed_answer"],
                explanation=q_data["explanation"],
            )

            if result["verdict"] == "PASS":
                print(f"  -> Question {idx + 1} passed audit (Score: {result['score']}/5)")
                final_blocks.append(q_data["raw_block"])
            else:
                print(
                    f"  -> Question {idx + 1} failed audit (Score: {result['score']}/5). Refining..."
                )
                print(f"     Feedback: {result['feedback']}")
                refined_block = self._refine_question(
                    question_data=q_data,
                    feedback=result["feedback"],
                    reference_context=result["reference_context"],
                )
                final_blocks.append(refined_block)

        return intro_text + "\n\n" + "\n\n---\n\n".join(final_blocks)
