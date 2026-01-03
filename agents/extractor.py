from utils.pdf_extractor import extract_text_and_images, ocr_images
from agents.classifier import classify_document
from agents.groq_llm import groq_attendance_extraction
from agents.regex import regex_extract

def extract_attendance(pdf_bytes: bytes):
    """
    Main extraction pipeline with fallback logic
    """
    # Step 1: Extract text from PDF
    text, images = extract_text_and_images(pdf_bytes)
    
    print(f"\n{'='*60}")
    print(f"Extracted {len(text)} characters of text")
    print(f"Found {len(images)} images")
    
    # Step 2: OCR if text is too short
    if len(text) < 50 and images:
        print("Text too short, running OCR...")
        ocr_text = ocr_images(images)
        text += "\n" + ocr_text
        print(f"After OCR: {len(text)} characters")
    
    # Step 3: Classify document (optional, for logging)
    doc_type = classify_document(text)
    print(f"Document type: {doc_type}")
    
    # Step 4: Try LLM extraction first
    print("Attempting LLM extraction...")
    llm_result = groq_attendance_extraction(text)
    
    if llm_result and llm_result.get("records"):
        print(f"✅ LLM extraction successful!")
        print(f"   Employee: {llm_result.get('employee_name')}")
        print(f"   Records: {len(llm_result.get('records', []))}")
        return llm_result
    
    # Step 5: Fallback to regex
    print("⚠️ LLM extraction failed, trying regex fallback...")
    regex_result = regex_extract(text)
    
    if regex_result and regex_result.get("records"):
        print(f"✅ Regex extraction successful!")
        print(f"   Employee: {regex_result.get('employee_name')}")
        print(f"   Records: {len(regex_result.get('records', []))}")
        return regex_result
    
    # Step 6: Return empty result if all fail
    print("❌ All extraction methods failed")
    print(f"Text preview: {text[:200]}")
    
    return {
        "employee_name": "EXTRACTION_FAILED",
        "employee_code": "",
        "records": []
    }