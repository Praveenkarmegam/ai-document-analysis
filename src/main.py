import os
from fastapi import FastAPI, HTTPException, Security, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel
from dotenv import load_dotenv

import src.utils as utils

load_dotenv()

app = FastAPI(title="AI Document Analysis API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_KEY = os.getenv("API_KEY")
API_KEY_NAME = "x-api-key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

async def get_api_key(api_key_header: str = Security(api_key_header)):
    if not api_key_header or api_key_header != API_KEY:
        raise HTTPException(
            status_code=401, detail="Invalid or missing API Key"
        )
    return api_key_header

class DocumentRequest(BaseModel):
    fileName: str
    fileType: str
    fileBase64: str

@app.post("/api/document-analyze")
@app.post("/api/document-analyze/")
async def analyze_document(request: DocumentRequest, api_key: str = Depends(get_api_key)):
    from src.celery_worker import process_document_task

    try:
        # Offload the processing heavily onto Celery worker
        task = process_document_task.delay(request.fileBase64, request.fileType)
        
        # We wait for the asynchronous celery worker synchronously here to respect 
        # the exact hackathon format requirements which need the JSON immediately.
        result = task.get(timeout=60)
        
        if result.get("status") == "error":
            return result

        response = {
            "status": "success",
            "fileName": request.fileName,
        }
        response.update(result)

        return response

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

@app.post("/{full_path:path}")
async def catch_all_post(full_path: str, request: DocumentRequest, api_key: str = Depends(get_api_key)):
    # Automatically route ANY mistyped POST request directly to the analysis engine!
    return await analyze_document(request, api_key=api_key)

from fastapi.staticfiles import StaticFiles
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
