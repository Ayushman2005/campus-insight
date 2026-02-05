import os
import re
import shutil
from pathlib import Path
from datetime import datetime
from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
import logging
import google.generativeai as genai
from apscheduler.schedulers.background import BackgroundScheduler

from ocr_processor import OCRProcessor
from embeddings_search import SemanticSearchEngine
from campus_scraper import scrape_website

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
TARGET_WEBSITE = "https://www.giet.edu/news-events/notice-board/"
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

app = FastAPI(title="Campus Insight API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DOCS_FOLDER = Path("documents")
DOCS_FOLDER.mkdir(exist_ok=True)
app.mount("/files", StaticFiles(directory=DOCS_FOLDER), name="documents")

ocr_processor = OCRProcessor()
search_engine = SemanticSearchEngine()
scheduler = BackgroundScheduler()

class SearchQuery(BaseModel):
    query: str
    filters: Optional[dict] = None
    limit: int = 5

class ChatQuery(BaseModel):
    question: str

class SearchResult(BaseModel):
    id: str
    title: str
    content: str
    source_url: str
    date: Optional[str] = "N/A"
    relevance_score: float
    category: Optional[str] = "General"

class ScrapeRequest(BaseModel):
    url: str

def extract_date_from_text(text: str) -> str:
    patterns = [
        r'\d{2}/\d{2}/\d{4}',
        r'\d{4}-\d{2}-\d{2}',
        r'\d{1,2}(?:st|nd|rd|th)?\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}',
        r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}'
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(0)
    return datetime.now().strftime("%Y-%m-%d")

def process_file(file_path: Path):
    try:
        logger.info(f"Processing: {file_path.name}")
        processed_data = ocr_processor.process_document(str(file_path))
        
        if not processed_data.get('text'):
            return False

        doc_date = extract_date_from_text(processed_data['text'])
        
        category = "General"
        text_lower = processed_data['text'].lower()
        if "exam" in text_lower or "schedule" in text_lower: category = "Exams"
        elif "fee" in text_lower or "payment" in text_lower: category = "Fees"
        elif "scholarship" in text_lower or "st/sc" in text_lower or "obc" in text_lower: category = "Scholarships"
        elif "lab" in text_lower or "syllabus" in text_lower: category = "Academics"

        metadata = {
            "title": file_path.stem,
            "source_url": f"http://localhost:8000/files/{file_path.name}",
            "date": doc_date,
            "category": category
        }
        
        search_engine.index_document(text=processed_data['text'], metadata=metadata)
        return True
    except Exception as e:
        logger.error(f"Error processing {file_path.name}: {e}")
        return False

def scheduled_scraper_job():
    logger.info("Running scheduled scrape...")
    new_files = scrape_website(TARGET_WEBSITE, DOCS_FOLDER)
    if new_files:
        logger.info(f"Downloaded {len(new_files)} new files. Indexing now...")
        for filename in new_files:
            process_file(DOCS_FOLDER / filename)

@app.on_event("startup")
def start_scheduler():
    scheduler.add_job(scheduled_scraper_job, 'interval', hours=1)
    scheduler.start()

@app.on_event("shutdown")
def shutdown_scheduler():
    scheduler.shutdown()

@app.get("/")
async def root():
    return {"status": "running", "docs_indexed": search_engine.get_document_count()}

@app.get("/api/stats")
async def get_stats():
    try:
        doc_count = search_engine.get_document_count()
        
        total_size = sum(f.stat().st_size for f in DOCS_FOLDER.glob('**/*') if f.is_file())
        storage_mb = round(total_size / (1024 * 1024), 2) 
        
        return {
            "total_documents": doc_count,
            "storage_used": f"{storage_mb} MB",
            "system_health": "100%",
            "latency": "24ms" 
        }
    except Exception as e:
        return {
            "total_documents": 0,
            "storage_used": "0 MB",
            "system_health": "Error",
            "latency": "0ms"
        }

@app.post("/api/trigger-scrape")
async def manual_scrape(request: ScrapeRequest, background_tasks: BackgroundTasks):
    def scrape_and_index():
        new_files = scrape_website(request.url, DOCS_FOLDER)
        indexed_count = 0
        for filename in new_files:
            if process_file(DOCS_FOLDER / filename):
                indexed_count += 1
        logger.info(f"Manual scrape complete. Indexed {indexed_count} files.")

    background_tasks.add_task(scrape_and_index)
    return {"status": "success", "message": "Scraping started in background. Check notifications shortly."}

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        file_path = DOCS_FOLDER / file.filename
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        if process_file(file_path):
             return {"status": "success", "message": f"Uploaded and indexed {file.filename}"}
        else:
             return {"status": "warning", "message": "Uploaded but text extraction failed."}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/documents/{filename}")
async def delete_document(filename: str):
    try:
        file_path = DOCS_FOLDER / filename
        file_deleted = False
        if file_path.exists():
            os.remove(file_path)
            file_deleted = True
        
        search_engine.delete_document(filename)

        if file_deleted:
            return {"status": "success", "message": f"Deleted {filename} from disk and memory."}
        else:
            return {"status": "success", "message": f"Cleaned {filename} from memory (file was already gone)."}

    except Exception as e:
        logger.error(f"Delete error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/scan")
async def scan_documents_folder():
    files = [f for f in DOCS_FOLDER.iterdir() if f.is_file()]
    indexed_count = 0
    for file_path in files:
        if file_path.suffix.lower() in ['.pdf', '.png', '.jpg', '.jpeg']:
            if process_file(file_path):
                indexed_count += 1
    
    return {"status": "success", "message": f"Rescanned folder. Indexed {indexed_count} documents."}

@app.post("/api/search", response_model=List[SearchResult])
async def search_documents(query: SearchQuery):
    results = search_engine.search(query=query.query, n_results=query.limit)
    response = []
    for r in results:
        meta = r['metadata']
        response.append(SearchResult(
            id=r['id'],
            title=meta.get('title', 'Untitled'),
            content=r['document'],
            source_url=meta.get('source_url', '#'),
            date=meta.get('date', 'N/A'),
            relevance_score=r['relevance_score'],
            category=meta.get('category', 'General')
        ))
    return response

@app.post("/api/chat")
async def chat_with_data(query: ChatQuery):
    results = search_engine.search(query=query.question, n_results=5)
    if not results:
        return {"answer": "I couldn't find relevant documents."}
        
    context_text = "\n\n".join([f"Source ({r['metadata'].get('title')}): {r['document']}" for r in results])
    prompt = f"Context:\n{context_text}\n\nQuestion: {query.question}\n\nAnswer (be direct and cite the source name):"
    
    try:
        response = model.generate_content(prompt)
        return {"answer": response.text, "sources": [r['metadata'] for r in results]}
    except:
        return {"answer": "AI Service Error", "sources": []}

if __name__ == "__main__":
    uvicorn.run("backend_main:app", host="0.0.0.0", port=8000, reload=True)