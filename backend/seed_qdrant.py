import os
import django
import uuid

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from rag_pipeline.ingestor import index_document

def seed():
    print("Seeding Qdrant gov_exam_knowledge collection...")
    
    docs = [
        {
            "id": uuid.uuid4(),
            "text": "UPSC Mains Essay Writing Guidelines: The essay should be structured, concise, and multi-dimensional. It must cover social, political, economic, environmental, and ethical aspects of the topic. A strong introduction hook (story, quote, or historical anecdote) is highly recommended, followed by a balanced body of arguments supported by concrete examples, facts, committee recommendations, or reports. The conclusion should be positive, visionary, and forward-looking.",
            "metadata": {"exam": "upsc", "subject": "essay", "topic": "guidelines"}
        },
        {
            "id": uuid.uuid4(),
            "text": "Technology and Democracy: In modern democracies, technology provides platforms for civic engagement, decentralized discourse, and public service delivery. However, it also introduces challenges like polarization, deepfakes, spread of misinformation, and cyber warfare. The impact of technology on public policy and constitutional rights is double-edged.",
            "metadata": {"exam": "upsc", "subject": "essay", "topic": "technology_democracy"}
        },
        {
            "id": uuid.uuid4(),
            "text": "Economic Growth vs Sustainable Development: UPSC Mains essays on economic growth must balance GDP growth metrics with environmental sustainability, inclusivity, human development index (HDI), gender equality, and future generations. The concept of green GDP and circular economy are key dimensions.",
            "metadata": {"exam": "upsc", "subject": "essay", "topic": "economy_sustainability"}
        }
    ]
    
    for doc in docs:
        num_points = index_document(doc["id"], doc["text"], doc["metadata"])
        print(f"Indexed document '{doc['metadata']['topic']}' into {num_points} chunks.")
        
    print("Qdrant seeding completed successfully!")

if __name__ == '__main__':
    seed()
