import os
import django
import urllib.request
from django.core.files import File

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth.models import User
from essay.models import EssayPracticeSession, EssayQuestion, EssayAnswerImage
from essay.services.ocr_service import extract_text_from_question_images
from essay.services.evaluation_service import evaluate_essay

def run_test():
    print("1. Setting up test data...")
    # Clean up old data to prevent interference
    EssayPracticeSession.objects.filter(title='Test Session').delete()
    
    # Create a test user
    user, created = User.objects.get_or_create(username='test_essay_user', email='test@example.com')
    
    # Create a session
    session = EssayPracticeSession.objects.create(
        user=user,
        track_slug='upsc',
        roadmap_item_id='u-17',
        title='Test Session'
    )
    
    # Create a question
    question = EssayQuestion.objects.create(
        session=session,
        prompt_text='Discuss the role of technology in modern democracy.',
        order=1,
        max_marks=125
    )
    
    print("2. Downloading sample handwritten image...")
    # A public domain image of handwriting from Wikimedia Commons (Declaration of Independence excerpt or similar)
    # Actually, let's use a clear handwritten note image that tesseract can read decently well.
    img_path = "/tmp/sample_handwriting.jpg"
    from PIL import Image, ImageDraw, ImageFont
    # Create an image with text
    img = Image.new('RGB', (800, 400), color=(255, 255, 255))
    d = ImageDraw.Draw(img)
    text = "Technology has fundamentally transformed modern democracy.\nIt provides new platforms for civic engagement, but also\nintroduces challenges like misinformation and polarization.\nOverall, its role is complex and ever-evolving."
    
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 30)
    except Exception:
        font = ImageFont.load_default()
        
    d.text((20, 20), text, fill=(0, 0, 0), font=font)
    img.save(img_path)
    
    print("3. Attaching image to question...")
    with open(img_path, 'rb') as f:
        EssayAnswerImage.objects.create(
            question=question,
            user=user,
            page_number=1,
            original_filename='sample.jpg',
            image=File(f, name='sample.jpg')
        )
        
    print("4. Running OCR Extraction...")
    transcript = extract_text_from_question_images(question.id)
    if not transcript:
        print("Failed to create transcript.")
        return
        
    print("================== EXTRACTED TEXT ==================")
    print(transcript.combined_text)
    print(f"Word Count: {transcript.word_count}")
    print(f"Quality: {transcript.extraction_quality}")
    print("====================================================\n")
    
    print("5. Running LLM/Mock Evaluation...")
    review = evaluate_essay(transcript.id)
    if not review:
        print("Failed to create review.")
        return
        
    print("================== AI REVIEW ==================")
    print(f"Status: {review.status}")
    print(f"Score: {review.total_score} / {review.max_score}")
    print(f"Band: {review.rating_band}")
    import json
    print("Feedback JSON summary:")
    print(json.dumps(review.review_json, indent=2)[:500] + "\n... (truncated)")
    print("===============================================")
    
    print("\nTest completed successfully!")

if __name__ == '__main__':
    run_test()
