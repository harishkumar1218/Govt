import json
from django.utils import timezone
from rag_pipeline.retriever import retrieve_context
from essay.models import EssayAnswerTranscript, EssayAIReview, EssayQuestion

def evaluate_essay(transcript_id: int):
    """
    Fetch transcript, retrieve context, build prompt, and call LLM (mocked).
    """
    try:
        transcript = EssayAnswerTranscript.objects.get(id=transcript_id)
    except EssayAnswerTranscript.DoesNotExist:
        return None

    question = transcript.question
    
    # Update or create review object as Processing
    review, created = EssayAIReview.objects.update_or_create(
        transcript=transcript,
        defaults={
            'session': transcript.session,
            'user': transcript.user,
            'question': question,
            'status': 'processing'
        }
    )

    try:
        # Retrieve RAG context based on prompt
        retrieved_chunks = retrieve_context(question.prompt_text, top_k=5)
        
        system_prompt = f"""You are an expert UPSC Mains evaluator.
Evaluate the following essay based on the provided RAG context and the essay text.
Provide your evaluation STRICTLY in JSON format matching the following schema. Ensure you output ONLY JSON and no surrounding text.
{{
  "summary": "Overall summary of the evaluation",
  "score": integer (out of 125),
  "max_score": 125,
  "percentage": float,
  "rating_band": "excellent" | "good" | "average" | "weak" | "poor",
  "positives": ["list", "of", "strengths"],
  "negatives": ["list", "of", "weaknesses"],
  "missing_dimensions": ["list", "of", "missing", "perspectives"],
  "factual_or_logic_issues": ["list", "of", "issues"],
  "structure_feedback": {{
    "intro": "feedback on intro",
    "body": "feedback on body",
    "conclusion": "feedback on conclusion"
  }},
  "suggested_outline": ["list", "of", "points", "for", "ideal", "structure"],
  "model_answer_direction": "how an ideal answer should be",
  "next_practice_tasks": ["list", "of", "tasks"],
  "rubric": [
    {{
      "criterion": "Relevance and thesis",
      "score": integer (out of 15),
      "max_score": 15,
      "reasoning": "Why this score",
      "positive": "What was good",
      "negative": "What was bad",
      "improvement": "How to improve"
    }},
    {{
      "criterion": "Structure and flow",
      "score": integer (out of 15),
      "max_score": 15,
      "reasoning": "Why this score",
      "positive": "What was good",
      "negative": "What was bad",
      "improvement": "How to improve"
    }},
    {{
      "criterion": "Depth and multidimensional analysis",
      "score": integer (out of 25),
      "max_score": 25,
      "reasoning": "Why this score",
      "positive": "What was good",
      "negative": "What was bad",
      "improvement": "How to improve"
    }},
    {{
      "criterion": "Examples, facts, and current relevance",
      "score": integer (out of 20),
      "max_score": 20,
      "reasoning": "Why this score",
      "positive": "What was good",
      "negative": "What was bad",
      "improvement": "How to improve"
    }},
    {{
      "criterion": "Critical reasoning and balance",
      "score": integer (out of 15),
      "max_score": 15,
      "reasoning": "Why this score",
      "positive": "What was good",
      "negative": "What was bad",
      "improvement": "How to improve"
    }},
    {{
      "criterion": "Language and expression",
      "score": integer (out of 15),
      "max_score": 15,
      "reasoning": "Why this score",
      "positive": "What was good",
      "negative": "What was bad",
      "improvement": "How to improve"
    }},
    {{
      "criterion": "Introduction and conclusion",
      "score": integer (out of 10),
      "max_score": 10,
      "reasoning": "Why this score",
      "positive": "What was good",
      "negative": "What was bad",
      "improvement": "How to improve"
    }},
    {{
      "criterion": "Presentation/readability",
      "score": integer (out of 10),
      "max_score": 10,
      "reasoning": "Why this score",
      "positive": "What was good",
      "negative": "What was bad",
      "improvement": "How to improve"
    }}
  ]
}}

Question: {question.prompt_text}

Context from relevant materials:
{chr(10).join(retrieved_chunks)}

Essay Text:
{transcript.combined_text}

JSON Output:"""

        import requests
        url = "http://localhost:11434/api/generate"
        payload = {
            "model": "llama3.2:latest",
            "prompt": system_prompt,
            "format": "json",
            "stream": False,
            "options": {
                "temperature": 0.2
            }
        }
        
        response = requests.post(url, json=payload, timeout=180)
        if response.status_code == 200:
            review_json = json.loads(response.json()['response'])
        else:
            raise Exception(f"Ollama API error: {response.text}")
            
        base_score = review_json.get('score', 0)
        percentage = review_json.get('percentage', 0)
        rating_band = review_json.get('rating_band', 'average')
        
        review.status = 'completed'
        review.total_score = base_score
        review.percentage = percentage
        review.rating_band = rating_band
        review.review_json = review_json
        review.strengths = review_json.get('positives', [])
        review.weaknesses = review_json.get('negatives', [])
        review.suggestions = review_json.get('next_practice_tasks', [])
        review.retrieved_context = retrieved_chunks
        review.model_name = "llama3.2_rag"
        review.save()

        
    except Exception as e:
        review.status = 'failed'
        review.error_message = str(e)
        review.save()
        
    return review
