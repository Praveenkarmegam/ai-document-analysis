import base64
import re
import json
import io
import cv2
import numpy as np
import pdfplumber
import pytesseract
from docx import Document
import google.generativeai as genai
import os
import platform

# Auto-configure Tesseract path for Windows Local Testing
if platform.system() == 'Windows':
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def decode_base64(file_b64: str) -> bytes:
    return base64.b64decode(file_b64)

def clean_text(text: str) -> str:
    # Remove extra spaces and line breaks
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def extract_text_from_pdf(file_bytes: bytes) -> str:
    text = ""
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return clean_text(text)

def extract_text_from_docx(file_bytes: bytes) -> str:
    doc = Document(io.BytesIO(file_bytes))
    text = "\n".join([para.text for para in doc.paragraphs])
    return clean_text(text)

def extract_text_from_image(file_bytes: bytes) -> str:
    # Convert bytes to numpy array
    np_arr = np.frombuffer(file_bytes, np.uint8)
    image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    
    if image is None:
        raise ValueError("Could not decode image from base64.")
        
    # Preprocessing
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    # Apply thresholding
    _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
    
    # Extract text
    text = pytesseract.image_to_string(thresh)
    return clean_text(text)

def extract_entities_regex(text: str, current_entities: dict) -> dict:
    # Ensure all keys exist
    for key in ['names', 'dates', 'organizations', 'amounts']:
        if key not in current_entities:
            current_entities[key] = []
            
    # Fallback to extract dates like DD/MM/YYYY or Month YYYY
    date_pattern = r'\b(?:\d{1,2}[/\-]\d{1,2}[/\-]\d{4}|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{4})\b'
    # Fallback to extract amounts like $ or ₹
    amount_pattern = r'[\$₹]\s*\d+(?:,\d{3})*(?:\.\d{2})?\b'
    
    dates = re.findall(date_pattern, text)
    amounts = re.findall(amount_pattern, text)
    
    current_entities['dates'].extend(dates)
    current_entities['amounts'].extend(amounts)
    
    return current_entities

def deduplicate_entities(entities: dict) -> dict:
    return {k: list(set(v)) if isinstance(v, list) else v for k, v in entities.items()}

def analyze_document_with_llm(text: str) -> dict:
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    prompt = f"""
    Analyze the following text and extract information. 
    Return ONLY valid JSON in this format:
    {{
      "summary": "max 3 sentences",
      "entities": {{
        "names": [],
        "dates": [],
        "organizations": [],
        "amounts": []
      }},
      "sentiment": "Positive | Neutral | Negative"
    }}

    Rules:
    - Extract real entities only from text
    - Do not hallucinate
    - Keep summary concise (max 3 sentences)
    - Sentiment must be one of: Positive, Neutral, Negative

    Text:
    {text}
    """

    model = genai.GenerativeModel('gemini-2.5-flash')
    response = model.generate_content(
        prompt,
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json",
        ),
    )
    
    try:
        data = json.loads(response.text)
        
        # Apply regex fallbacks
        data['entities'] = extract_entities_regex(text, data.get('entities', {}))
        
        # Deduplication
        data['entities'] = deduplicate_entities(data['entities'])
        
        return data
    except Exception as e:
        # Fallback if the model doesn't return pure JSON somehow
        fallback_data = {
            "summary": "Failed to parse AI output.",
            "entities": {"names": [], "dates": [], "organizations": [], "amounts": []},
            "sentiment": "Neutral"
        }
        return fallback_data
