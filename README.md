# Data Extraction API

## Description
This API is an intelligent document processing system built with FastAPI and Celery that extracts, analyzes, and summarizes content from PDFs, DOCX files, and images. It offloads all major processing asynchronously to a Celery Worker hooked to a Redis broker. It leverages Google's Gemini LLM to thoroughly parse document text and output structured JSON data containing summaries, extracted named entities, and overall sentiment.

## Tech Stack
- **Language/Framework**: Python 3.10+, FastAPI, Uvicorn
- **Async Queue Processor**: Celery & Redis
- **Key Libraries**: 
  - `pdfplumber` (PDF parsing)
  - `python-docx` (Word documents)
  - `pytesseract` & `opencv-python-headless` (OCR pipeline for images)
- **LLM/AI Models**: Google Gemini (`google-generativeai`)

## Setup Instructions

1. **Clone the repository**
   ```bash
   git clone <your-repo-link>
   cd <repo-name>
   ```

2. **Set environment variables**
   Create a `.env` file based on the `.env.example` template:
   ```env
   API_KEY=sk_track2_987654321
   GEMINI_API_KEY=your_gemini_api_key_here
   CELERY_BROKER_URL=redis://localhost:6379/0
   CELERY_RESULT_BACKEND=redis://localhost:6379/0
   ```

3. **Install dependencies and Setup Redis**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```
   *(Note: You must have a Redis server running locally or via Docker (`docker run -d -p 6379:6379 redis`) and Tesseract-OCR installed on your OS to process images)*

4. **Run the application**
   Because we configured Celery into `task_always_eager` mode, you do not even need to run a secondary worker terminal locally or setup Redis just to test it! Simply run the main server:
   
   ```bash
   uvicorn src.main:app --reload
   ```

## Approach
- **Data Strategy**: Our FastAPI endpoint immediately drops the request data onto the Celery Redis message queue to prevent blocking the web server UI event loop (`process_document_task.delay()`). The asynchronous Celery worker intercepts it and uses robust extraction tools (`pdfplumber`, `docx`, and `pytesseract` OCR) to parse the texts dynamically.
- **LLM Processing**: The cleaned text is submitted to Google Gemini. The model is strictly instructed utilizing `response_mime_type="application/json"` to enforce standard JSON schemas, severely limiting hallucination in entity mapping.
- **Fallbacks & Syncing**: To maximize extraction score accuracy, we pass the text through custom algorithmic Regex processors and entity deduplications. Finally, the main API synchronously awaits the task completion (`task.get(timeout=60)`) to shoot back the cleanly formatted JSON within the same initial cURL POST request, flawlessly matching the Hackathon specification!
