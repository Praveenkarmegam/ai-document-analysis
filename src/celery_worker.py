import os
from celery import Celery
import src.utils as utils
from dotenv import load_dotenv

load_dotenv()

redis_url = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "document_worker",
    broker=redis_url,
    backend=redis_url
)

# Enable eager mode so the Hackathon code executes perfectly
# synchronously on local machines without requiring a Redis server.
celery_app.conf.update(
    task_always_eager=True,
    task_eager_propagates=True,
)

@celery_app.task(name="process_document")
def process_document_task(file_base64: str, file_type: str) -> dict:
    try:
        file_bytes = utils.decode_base64(file_base64)
    except Exception:
        return {"status": "error", "message": "Invalid Base64 string"}

    file_type = file_type.lower()
    extracted_text = ""

    try:
        if file_type == "pdf":
            extracted_text = utils.extract_text_from_pdf(file_bytes)
        elif file_type == "docx":
            extracted_text = utils.extract_text_from_docx(file_bytes)
        elif file_type in ["jpg", "jpeg", "png", "image"]:
            extracted_text = utils.extract_text_from_image(file_bytes)
        else:
            return {"status": "error", "message": "Unsupported fileType. Use pdf, docx, or image files."}

        if not extracted_text:
            return {"status": "error", "message": "No text could be extracted from the file."}

        # AI Processing
        ai_result = utils.analyze_document_with_llm(extracted_text)
        
        ai_result["status"] = "success"
        return ai_result

    except Exception as e:
        return {"status": "error", "message": str(e)}
