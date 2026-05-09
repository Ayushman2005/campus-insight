import os
import re
import shutil
import traceback
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
import logging
from google import genai
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv

load_dotenv()

from ocr_processor import OCRProcessor
from embeddings_search import SemanticSearchEngine
from campus_scraper import scrape_website

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") 
TARGET_WEBSITE = "https://www.giet.edu/news-events/notice-board/"

if GEMINI_API_KEY:
    logger.info(f"GEMINI_API_KEY found (starts with {GEMINI_API_KEY[:8]}...)")
    client = genai.Client(api_key=GEMINI_API_KEY)
else:
    logger.error("GEMINI_API_KEY NOT FOUND in environment!")
    client = None

DOCS_FOLDER = Path("documents")
DOCS_FOLDER.mkdir(exist_ok=True)

ocr_processor = None
search_engine = None
scheduler = BackgroundScheduler()

import threading

def init_models():
    global ocr_processor, search_engine
    try:
        logger.info("Initializing ML Models in background...")
        ocr_processor = OCRProcessor(genai_client=client)
        search_engine = SemanticSearchEngine()
        logger.info("ML Models initialized successfully!")
    except Exception as e:
        logger.error(f"Failed to initialize ML models: {e}")

def scheduled_scraper_job():
    if search_engine is None:
        logger.warning("Search engine not ready, skipping scraper job.")
        return
    existing_filenames = search_engine.get_all_filenames()
    new_files = scrape_website(TARGET_WEBSITE, existing_filenames)
    if new_files:
        for file_data in new_files:
            process_memory_file(file_data['filename'], file_data['content'], file_data['url'])

@asynccontextmanager
async def lifespan(app: FastAPI):
    global ocr_processor, search_engine
    
    threading.Thread(target=init_models, daemon=True).start()
    
    logger.info("Starting up Background Scheduler...")
    scheduler.add_job(scheduled_scraper_job, 'interval', hours=1, misfire_grace_time=None)
    scheduler.start()
    
    yield
    
    logger.info("Shutting down Background Scheduler...")
    scheduler.shutdown()

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/files", StaticFiles(directory=DOCS_FOLDER), name="documents")

class SearchQuery(BaseModel):
    query: str
    filters: Optional[dict] = None
    limit: int = 5

class SearchResult(BaseModel):
    id: str
    title: str
    content: str
    source_url: str
    date: Optional[str] = "N/A"
    relevance_score: float
    category: Optional[str] = "General"
    extracted_answer: Optional[str] = None 

class ScrapeRequest(BaseModel):
    url: str
    extract_pdfs: bool = True
    extract_images: bool = True
    extract_text: bool = True
    max_links: int = 10

def extract_date_from_text(text: str) -> str:
    patterns = [
        r'\d{2}/\d{2}/\d{4}',
        r'\d{4}-\d{2}-\d{2}',
        r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}'
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(0)
    return datetime.now().strftime("%Y-%m-%d")

def calculate_smart_age(text: str) -> Optional[str]:
    try:
        current_year = datetime.now().year
        year_matches = re.findall(r'(199\d|200\d|201\d)', text)
        possible_ages = []
        for year_str in year_matches:
            y = int(year_str)
            if 1980 < y < (current_year - 15): 
                possible_ages.append(current_year - y)
        if possible_ages:
            return str(max(possible_ages))
        return None
    except:
        return None

def get_ai_extraction(text: str, query: str) -> str:
    if "age" in query.lower():
        math_age = calculate_smart_age(text)
        if math_age:
            return math_age
    try:
        current_year = datetime.now().year
        prompt = f"""
        Extract the exact answer.
        Query: "{query}"
        Context: "{text[:2000]}"
        Current Year: {current_year}
        
        Rules:
        - If query is 'Age' and you see a birth year or probable birth year (e.g. in email), calculate age.
        - Return ONLY the result (e.g. "21"). No text.
        - If not found, return "None".
        """
        if not client:
            return None
            
        response = client.models.generate_content(
            model='gemini-flash-latest',
            contents=prompt
        )
        answer = response.text.strip().replace('"', '').replace("'", "").replace(".", "")
        
        if "None" in answer or len(answer) > 50: 
            return None
        return answer
    except Exception:
        return None

def process_memory_file(filename: str, file_bytes: bytes, source_url: str):
    try:
        logger.info(f"Processing in memory: {filename}")
        processed_data = ocr_processor.process_document_bytes(file_bytes, filename)
        
        if not processed_data or not processed_data.get('text'):
            logger.warning(f"No text extracted from {filename}")
            return False

        doc_date = extract_date_from_text(processed_data['text'])
        
        category = "General"
        text_lower = processed_data['text'].lower()
        if "resume" in text_lower or "cv" in text_lower: category = "Resume"
        elif "exam" in text_lower: category = "Exams"
        elif "fee" in text_lower: category = "Fees"

        metadata = {
            "title": Path(filename).stem,
            "filename": filename,
            "source_url": source_url,
            "date": doc_date,
            "category": category
        }
        
        search_engine.index_document(text=processed_data['text'], metadata=metadata)
        logger.info(f"Successfully indexed {filename}")
        return True
    except Exception as e:
        logger.error(f"!!! Error processing {filename} !!!")
        traceback.print_exc()
        return False

def process_file(file_path: Path):
    try:
        logger.info(f"Processing: {file_path.name}")
        processed_data = ocr_processor.process_document(str(file_path))
        
        if not processed_data or not processed_data.get('text'):
            logger.warning(f"No text extracted from {file_path.name}")
            return False

        doc_date = extract_date_from_text(processed_data['text'])
        
        category = "General"
        text_lower = processed_data['text'].lower()
        if "resume" in text_lower or "cv" in text_lower: category = "Resume"
        elif "exam" in text_lower: category = "Exams"
        elif "fee" in text_lower: category = "Fees"

        # Use an environment variable for the backend URL, defaulting to local
        backend_url = os.getenv("BACKEND_BASE_URL", "http://localhost:5000")
        metadata = {
            "title": file_path.stem,
            "filename": file_path.name,
            "source_url": f"{backend_url}/files/{file_path.name}",
            "date": doc_date,
            "category": category
        }
        
        search_engine.index_document(text=processed_data['text'], metadata=metadata)
        logger.info(f"Successfully indexed {file_path.name}")
        return True
    except Exception as e:
        logger.error(f"!!! Error processing {file_path.name} !!!")
        traceback.print_exc()
        return False

@app.get("/")
async def root():
    return {"status": "FastAPI running on Render"}

@app.get("/api/stats")
async def get_stats():
    if search_engine is None:
        return {"total_documents": 0, "storage_used": "In-Memory", "system_health": "Initializing...", "latency": "0ms", "activity_data": []}
    try:
        doc_count = search_engine.get_document_count()
        storage_mb = "In-Memory"
        
        # Activity data could be fetched from DB, but we keep a dummy for now since we no longer track local files
        days_order = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        activity_data = [{"name": day, "files": 0} for day in days_order]
        
        return {
            "total_documents": doc_count,
            "storage_used": storage_mb,
            "system_health": "100%",
            "latency": "24ms", 
            "activity_data": activity_data
        }
    except Exception as e:
        logger.error(f"Stats error: {e}")
        return {"total_documents": 0, "storage_used": "In-Memory", "system_health": "Error", "latency": "0ms", "activity_data": []}

@app.post("/api/trigger-scrape")
async def manual_scrape(request: ScrapeRequest, background_tasks: BackgroundTasks):
    if search_engine is None:
        raise HTTPException(status_code=503, detail="Models are still initializing. Please try again.")
    def scrape_and_index():
        existing_filenames = search_engine.get_all_filenames()
        new_files = scrape_website(
            request.url, 
            existing_filenames,
            extract_pdfs=request.extract_pdfs,
            extract_images=request.extract_images,
            extract_text=request.extract_text,
            max_links=request.max_links
        )
        for file_data in new_files:
            process_memory_file(file_data['filename'], file_data['content'], file_data['url'])
    background_tasks.add_task(scrape_and_index)
    return {"status": "success"}

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    if ocr_processor is None or search_engine is None:
        raise HTTPException(status_code=503, detail="Models are still initializing. Please try again.")
    try:
        file_bytes = await file.read()
        if process_memory_file(file.filename, file_bytes, source_url="#"):
             return {"status": "success", "message": f"Uploaded and indexed {file.filename} in memory"}
        
        raise HTTPException(status_code=422, detail="Failed to extract text or index the document. Check backend terminal.")
    except HTTPException as he:
        raise he
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/documents/{filename}")
async def delete_document(filename: str):
    if search_engine is None:
        raise HTTPException(status_code=503, detail="Models are still initializing. Please try again.")
    try:
        file_path = DOCS_FOLDER / filename
        if file_path.exists(): os.remove(file_path)
        search_engine.delete_document(filename)
        return {"status": "success", "message": f"Deleted {filename}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/scan")
async def scan_documents_folder():
    if ocr_processor is None or search_engine is None:
        raise HTTPException(status_code=503, detail="Models are still initializing. Please try again.")
    files = [f for f in DOCS_FOLDER.iterdir() if f.is_file()]
    count = 0
    for file_path in files:
        if file_path.suffix.lower() in ['.pdf', '.png', '.jpg', '.jpeg']:
            if process_file(file_path): count += 1
    return {"status": "success", "message": f"Rescanned. Indexed {count}."}

@app.post("/api/search", response_model=List[SearchResult])
async def search_documents(query: SearchQuery):
    if search_engine is None:
        raise HTTPException(status_code=503, detail="Search engine is still initializing. Please try again.")
    results = search_engine.search(query=query.query, n_results=query.limit)
    response_items = []
    
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = []
        for r in results:
            if len(futures) < 3: 
                futures.append(executor.submit(get_ai_extraction, r['document'], query.query))
            else:
                futures.append(None)
        
        for i, r in enumerate(results):
            meta = r['metadata']
            extracted = None
            if i < len(futures) and futures[i] is not None:
                extracted = futures[i].result()

            response_items.append(SearchResult(
                id=r['id'],
                title=meta.get('title', 'Untitled'),
                content=r['document'],
                source_url=meta.get('source_url', '#'),
                date=meta.get('date', 'N/A'),
                relevance_score=r['relevance_score'],
                category=meta.get('category', 'General'),
                extracted_answer=extracted 
            ))
            
    return response_items

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    uvicorn.run("app:app", host="0.0.0.0", port=port)