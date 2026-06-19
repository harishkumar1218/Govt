import os
from PIL import Image
import pytesseract
from essay.models import EssayQuestion, EssayAnswerImage, EssayOCRPage, EssayAnswerTranscript

def extract_text_from_question_images(question_id: int):
    """
    Given a question_id, fetch all uploaded images, extract text using pytesseract,
    save EssayOCRPage per image, and create an aggregated EssayAnswerTranscript.
    """
    question = EssayQuestion.objects.get(id=question_id)
    images = question.images.all().order_by('page_number')
    
    if not images.exists():
        return None
        
    combined_text_parts = []
    total_words = 0
    overall_quality = 'medium'
    
    for img_obj in images:
        try:
            # Open image using Pillow
            img_path = img_obj.image.path
            if not os.path.exists(img_path):
                continue
                
            img = Image.open(img_path)
            
            # Simple pytesseract OCR
            text = pytesseract.image_to_string(img)
            
            # Note: Tesseract confidence requires image_to_data, but for simplicity we'll estimate
            # or just default confidence if basic image_to_string is used.
            # Using basic len as a proxy for "did we get something"
            confidence = 80.0 if len(text.strip()) > 50 else 30.0
            
            ocr_page, created = EssayOCRPage.objects.update_or_create(
                answer_image=img_obj,
                defaults={
                    'extracted_text': text,
                    'confidence_score': confidence
                }
            )
            
            combined_text_parts.append(text)
            total_words += len(text.split())
            
            if confidence < 50.0:
                overall_quality = 'low'
                
        except Exception as e:
            print(f"Error processing image {img_obj.id}: {e}")
            overall_quality = 'low'

    # Create Transcript
    combined_text = "\n\n".join(combined_text_parts)
    
    transcript, created = EssayAnswerTranscript.objects.update_or_create(
        question=question,
        defaults={
            'session': question.session,
            'user': question.session.user,
            'combined_text': combined_text,
            'word_count': total_words,
            'extraction_quality': overall_quality
        }
    )
    
    return transcript
