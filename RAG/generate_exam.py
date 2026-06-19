import argparse
import sys
import json
import os
from rag_engine import MockExamRAG

def main():
    parser = argparse.ArgumentParser(description="Generate Track-Specific Mock Exams using RAG with local Ollama")
    parser.add_argument("--topic", type=str, required=True, help="Topic for the mock exam (e.g., 'Modern Indian History')")
    parser.add_argument("--config", type=str, help="Path to the JSON prompt config file")
    parser.add_argument("--num_questions", type=int, default=2, help="Number of questions to generate")
    parser.add_argument("--model", type=str, default="mlx-community/Llama-3.2-3B-Instruct-4bit")
    parser.add_argument("--output", type=str, help="Output file to save the results")
    
    args = parser.parse_args()
    
    try:
        config = None
        
        # Resolve config if not provided
        if not args.config:
            # Match topic keywords to prompt config files in backend/prompts
            backend_prompts_dir = "/Users/harish/Public/Govt/backend/prompts"
            topic_lower = args.topic.lower()
            
            config_name = None
            if "upsc" in topic_lower or "civil services" in topic_lower:
                config_name = "upsc-civil-services-prelims-gs.json"
            elif "ssc" in topic_lower or "staff selection" in topic_lower:
                config_name = "ssc-cgl-tier-1.json"
            elif "nda" in topic_lower or "defence academy" in topic_lower:
                config_name = "nda-maths.json"
            elif "cds" in topic_lower or "combined defence" in topic_lower:
                config_name = "cds-gk.json"
            elif "ese" in topic_lower or "engineering services" in topic_lower:
                config_name = "ese-prelims-paper-1.json"
                
            if config_name:
                config_path = os.path.join(backend_prompts_dir, config_name)
                if os.path.exists(config_path):
                    with open(config_path, 'r') as f:
                        config = json.load(f)
            
            # Default fallback if no match found
            if not config:
                config = {
                    "track_slug": "upsc",
                    "exam_name": "UPSC Civil Services Examination",
                    "stage": "Prelims",
                    "paper": "General Studies Paper I",
                    "question_count": args.num_questions,
                    "duration_seconds": 120,
                    "marks_per_question": 2.0,
                    "negative_marking": 0.66,
                    "system_prompt": "You are an expert exam setter. Generate realistic, high-quality MCQs based on the provided retrieved context.",
                    "generation_prompt": f"Generate a JSON containing {args.num_questions} MCQs. Do NOT output any markdown blocks, only pure JSON.",
                    "retrieval_filters": {}
                }
        else:
            with open(args.config, 'r') as f:
                config = json.load(f)
                
        # Override question count if num_questions is passed
        if args.num_questions:
            config["question_count"] = args.num_questions
            config["num_questions"] = args.num_questions
            
        rag = MockExamRAG(model_name=args.model)
        
        print(f"\n{'='*50}")
        print(f"Generating for: {config.get('exam_name', 'Unknown')} - {config.get('stage', 'Unknown')}")
        print(f"Topic: {args.topic}")
        print(f"{'='*50}\n")
        
        exam_content = rag.generate_mock_exam(topic=args.topic, config=config)
        
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(exam_content)
            print(f"\n✅ Results saved successfully to {args.output}")
        else:
            print("\n" + exam_content)
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
