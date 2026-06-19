import requests
import json

def call_ollama():
    url = "http://localhost:11434/api/generate"
    prompt = """You are an expert UPSC Mains evaluator.
Evaluate the following essay based on the prompt.
Provide your evaluation STRICTLY in JSON format matching the following schema:
{
  "summary": "Overall summary of the evaluation",
  "score": 50,
  "max_score": 125,
  "percentage": 40.0,
  "rating_band": "average",
  "positives": ["list", "of", "strengths"],
  "negatives": ["list", "of", "weaknesses"],
  "missing_dimensions": ["list", "of", "missing", "perspectives"],
  "factual_or_logic_issues": ["list", "of", "issues"],
  "structure_feedback": {
    "intro": "feedback on intro",
    "body": "feedback on body",
    "conclusion": "feedback on conclusion"
  },
  "suggested_outline": ["list", "of", "points", "for", "ideal", "structure"],
  "model_answer_direction": "how an ideal answer should be",
  "next_practice_tasks": ["list", "of", "tasks"],
  "rubric": [
    {
      "criterion": "Relevance and thesis",
      "score": 5,
      "max_score": 15,
      "reasoning": "Reason",
      "positive": "Good",
      "negative": "Bad",
      "improvement": "Improve"
    }
  ]
}

Question: Evaluate the role of technology in modern democracy.
Essay Text: Technology is good but also bad. It causes fake news.

JSON Output:"""

    payload = {
        "model": "llama3.2:latest",
        "prompt": prompt,
        "format": "json",
        "stream": False
    }
    print("Calling Ollama...")
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        data = response.json()
        print("Response OK. Parsing JSON...")
        try:
            parsed = json.loads(data['response'])
            print(json.dumps(parsed, indent=2))
        except Exception as e:
            print("Failed to parse JSON:", e)
            print("Raw:", data['response'])
    else:
        print("Failed:", response.text)

if __name__ == '__main__':
    call_ollama()
