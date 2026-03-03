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
import google.generativeai as genai
from apscheduler.schedulers.background import BackgroundScheduler

from ocr_processor import OCRProcessor
from embeddings_search import SemanticSearchEngine
from campus_scraper import scrape_website

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") 
TARGET_WEBSITE = "https://www.giet.edu/news-events/notice-board/"

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

DOCS_FOLDER = Path("documents")
DOCS_FOLDER.mkdir(exist_ok=True)

ocr_processor = OCRProcessor()
search_engine = SemanticSearchEngine()
scheduler = BackgroundScheduler()

def scheduled_scraper_job():
    new_files = scrape_website(TARGET_WEBSITE, DOCS_FOLDER)
    if new_files:
        for filename in new_files:
            process_file(DOCS_FOLDER / filename)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up Background Scheduler...")
    scheduler.add_job(scheduled_scraper_job, 'interval', hours=1)
    scheduler.start()
    
    yield
    
    logger.info("Shutting down Background Scheduler...")
    scheduler.shutdown()

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173", 
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174"
    ],
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
        response = model.generate_content(prompt)
        answer = response.text.strip().replace('"', '').replace("'", "").replace(".", "")
        
        if "None" in answer or len(answer) > 50: 
            return None
        return answer
    except Exception:
        return None

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

        metadata = {
            "title": file_path.stem,
            "source_url": f"http://localhost:8000/files/{file_path.name}",
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
    return {"status": "FastAPI running on Vercel/Localhost"}

@app.get("/api/stats")
async def get_stats():
    try:
        doc_count = search_engine.get_document_count()
        total_size = sum(f.stat().st_size for f in DOCS_FOLDER.glob('**/*') if f.is_file())
        storage_mb = round(total_size / (1024 * 1024), 2)
        
        activity_counts = {"Mon": 0, "Tue": 0, "Wed": 0, "Thu": 0, "Fri": 0, "Sat": 0, "Sun": 0}
        days_order = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        
        for file_path in DOCS_FOLDER.iterdir():
            if file_path.is_file():
                try:
                    mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                    day_name = mtime.strftime("%a")
                    if day_name in activity_counts:
                        activity_counts[day_name] += 1
                except Exception:
                    continue

        activity_data = [{"name": day, "files": activity_counts[day]} for day in days_order]
        
        return {
            "total_documents": doc_count,
            "storage_used": f"{storage_mb} MB",
            "system_health": "100%",
            "latency": "24ms", 
            "activity_data": activity_data
        }
    except Exception as e:
        logger.error(f"Stats error: {e}")
        return {"total_documents": 0, "storage_used": "0 MB", "system_health": "Error", "latency": "0ms", "activity_data": []}

@app.post("/api/trigger-scrape")
async def manual_scrape(request: ScrapeRequest, background_tasks: BackgroundTasks):
    def scrape_and_index():
        new_files = scrape_website(request.url, DOCS_FOLDER)
        for filename in new_files:
            process_file(DOCS_FOLDER / filename)
    background_tasks.add_task(scrape_and_index)
    return {"status": "success"}

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        file_path = DOCS_FOLDER / file.filename
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        if process_file(file_path):
             return {"status": "success", "message": f"Uploaded and indexed {file.filename}"}
        
        raise HTTPException(status_code=422, detail="Failed to extract text or index the document. Check backend terminal.")
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/documents/{filename}")
async def delete_document(filename: str):
    try:
        file_path = DOCS_FOLDER / filename
        if file_path.exists(): os.remove(file_path)
        search_engine.delete_document(filename)
        return {"status": "success", "message": f"Deleted {filename}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/scan")
async def scan_documents_folder():
    files = [f for f in DOCS_FOLDER.iterdir() if f.is_file()]
    count = 0
    for file_path in files:
        if file_path.suffix.lower() in ['.pdf', '.png', '.jpg', '.jpeg']:
            if process_file(file_path): count += 1
    return {"status": "success", "message": f"Rescanned. Indexed {count}."}

@app.post("/api/search", response_model=List[SearchResult])
async def search_documents(query: SearchQuery):
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
    uvicorn.run("app:app", host="127.0.0.1", port=5000, reload=True)