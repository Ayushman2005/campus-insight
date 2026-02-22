# Digital Archaeology - Semantic Search for University Documents

## 🎯 Project Overview

Digital Archaeology is a semantic search and notification engine that makes university documents searchable and accessible. It uses OCR to extract text from scanned PDFs and images, then employs AI-powered semantic search to help students find information instantly.

**Problem Solved**: Universities often post critical information (exam schedules, fee notices, results) as scanned PDFs or images, making them difficult to search. Students waste hours browsing through dozens of notices manually.

**Solution**: Extract text using OCR, index documents with semantic embeddings, and provide a Perplexity-style search interface for instant answers.

**SDG Alignment**: SDG 4 (Quality Education) - Democratizing access to academic information

---

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- Node.js 16+ (for frontend)
- Tesseract OCR
- Chrome/Chromium (for web scraping with Selenium)

### Backend Setup

1. **Install Tesseract OCR**:
   ```bash
   # Ubuntu/Debian
   sudo apt-get install tesseract-ocr
   
   # macOS
   brew install tesseract
   
   # Windows
   # Download from: https://github.com/UB-Mannheim/tesseract/wiki
   ```

2. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the backend**:
   ```bash
   python backend_main.py
   ```
   
   Backend will start on `http://localhost:8000`

### Frontend Setup

1. **Create React + Vite project**:
   ```bash
   npm create vite@latest frontend -- --template react-ts
   cd frontend
   npm install
   ```

2. **Install Tailwind CSS**:
   ```bash
   npm install -D tailwindcss postcss autoprefixer
   npx tailwindcss init -p
   ```

3. **Install additional dependencies**:
   ```bash
   npm install lucide-react
   ```

4. **Copy the SearchPage component** to `frontend/src/pages/`

5. **Run the frontend**:
   ```bash
   npm run dev
   ```
   
   Frontend will start on `http://localhost:5173`

---

## 📁 Project Structure

```
digital-archaeology/
├── backend/
│   ├── backend_main.py           # FastAPI application
│   ├── ocr_processor.py          # OCR text extraction
│   ├── embeddings_search.py      # Semantic search engine
│   ├── web_scraper.py            # University website scraper
│   ├── requirements.txt          # Python dependencies
│   └── downloads/                # Downloaded documents
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   └── SearchPage.tsx    # Main search interface
│   │   └── App.tsx
│   └── package.json
├── chroma_db/                    # Vector database (auto-created)
└── README.md
```

---

## 🔧 Core Components

### 1. OCR Processor (`ocr_processor.py`)

Extracts text from scanned documents with preprocessing for better accuracy.

**Features**:
- Image preprocessing (contrast, denoising, sharpening)
- Multi-page PDF support
- Confidence scoring
- Batch processing

**Usage**:
```python
from ocr_processor import OCRProcessor

processor = OCRProcessor(language='eng')
result = processor.process_document('exam_schedule.pdf')
print(result['text'])
```

### 2. Semantic Search Engine (`embeddings_search.py`)

Converts text to embeddings and performs vector similarity search.

**Features**:
- Sentence transformer embeddings (free, offline)
- ChromaDB vector database
- Text chunking for better search
- Category filtering

**Usage**:
```python
from embeddings_search import SemanticSearchEngine

engine = SemanticSearchEngine()

# Index a document
engine.index_document(
    text="Exam schedule for CS department...",
    metadata={
        'title': 'CS Exam Schedule',
        'category': 'Exams',
        'date': '2026-02-01'
    }
)

# Search
results = engine.search("when is database exam?", n_results=5)
```

### 3. Web Scraper (`web_scraper.py`)

Crawls university websites to collect PDFs and images.

**Features**:
- Static and JavaScript-rendered pages
- Automatic file download
- Notice text extraction
- Polite scraping with delays

**Usage**:
```python
from web_scraper import UniversityScraper

scraper = UniversityScraper()
result = scraper.scrape_university_page(
    'https://university.edu/notices',
    download=True
)
print(f"Found {result['total_found']} documents")
```

### 4. Search Interface (`SearchPage.tsx`)

Clean, Perplexity-style React interface.

**Features**:
- Natural language search
- Category filtering
- Result highlighting
- Relevance scoring
- Mobile responsive

---

## 🎯 Hackathon Implementation Plan

### Phase 1: Setup (Hour 0-2)
- ✅ Install dependencies
- ✅ Set up project structure
- ✅ Test OCR with sample PDF
- ✅ Initialize vector database

### Phase 2: Backend Core (Hour 2-5)
- ✅ Implement OCR processing pipeline
- ✅ Set up semantic search with ChromaDB
- ✅ Create FastAPI endpoints
- ⬜ Test with sample documents

### Phase 3: Frontend & Search (Hour 5-8)
- ⬜ Build search UI
- ⬜ Connect to backend API
- ⬜ Add filtering and sorting
- ⬜ Implement result highlighting

### Phase 4: Integration & Polish (Hour 8-12)
- ⬜ End-to-end testing
- ⬜ Add notification system
- ⬜ Error handling
- ⬜ Demo preparation

---

## 🧪 Testing the System

### 1. Test OCR Processing

```python
from ocr_processor import OCRProcessor

processor = OCRProcessor()
result = processor.process_document('sample_notice.pdf')
print(f"Extracted {result['word_count']} words")
print(f"Confidence: {result['confidence']:.2f}%")
```

### 2. Test Search Engine

```python
from embeddings_search import SemanticSearchEngine

engine = SemanticSearchEngine()

# Index sample document
engine.index_document(
    text="Computer Science exam on Feb 15, 2026 at 10 AM",
    metadata={'title': 'Exam Schedule', 'category': 'Exams'}
)

# Search
results = engine.search("CS exam date")
for r in results:
    print(f"Score: {r['relevance_score']:.2f}")
    print(f"Text: {r['document']}")
```

### 3. Test API

```bash
# Start backend
python backend_main.py

# In another terminal, test search endpoint
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "exam schedule", "limit": 5}'
```

---

## 📊 Demo Script

### Opening (30 seconds)
"Imagine searching 'when is my CS exam?' and getting instant answers from scanned PDFs. That's Digital Archaeology."

### Problem Statement (1 minute)
- Universities post critical info as scanned documents
- Students manually browse dozens of notices
- Important deadlines are often missed

### Live Demo (3 minutes)
1. Show web scraper collecting documents
2. Demonstrate OCR on scanned exam schedule
3. Perform semantic searches
4. Show notification for new announcements

### Impact (1 minute)
- Supports SDG 4 (Quality Education)
- Saves students hours per week
- Reduces information inequality
- Makes legacy documents searchable

### Closing (30 seconds)
"From hours of searching to seconds. Every document discoverable, every deadline visible."

---

## 🎨 Sample Queries to Demo

- "When is my computer science exam?"
- "Fee payment deadline"
- "Holiday list 2026"
- "Results announcement date"
- "Admission schedule"
- "Scholarship application process"

---

## 🔮 Post-Hackathon Enhancements

- [ ] Multi-university support
- [ ] Mobile app with push notifications
- [ ] AI-powered document summaries
- [ ] Calendar integration
- [ ] Collaborative annotations
- [ ] Analytics dashboard
- [ ] Email notifications
- [ ] Multi-language support

---

## 📚 Resources & Documentation

### Libraries Used
- **Tesseract OCR**: https://tesseract.projectnaptha.com/
- **sentence-transformers**: https://www.sbert.net/
- **ChromaDB**: https://www.trychroma.com/
- **FastAPI**: https://fastapi.tiangolo.com/
- **React + Vite**: https://vitejs.dev/
- **Tailwind CSS**: https://tailwindcss.com/

### Useful Links
- [OCR Best Practices](https://nanonets.com/blog/ocr-with-tesseract/)
- [Semantic Search Tutorial](https://www.pinecone.io/learn/semantic-search/)
- [FastAPI Tutorial](https://fastapi.tiangolo.com/tutorial/)

---

## 🐛 Troubleshooting

### OCR Not Working
- Ensure Tesseract is installed: `tesseract --version`
- Check image quality (higher DPI = better results)
- Try preprocessing: contrast, denoising

### Search Returns No Results
- Check if documents are indexed: `engine.get_document_count()`
- Verify embeddings are generated correctly
- Try simpler queries first

### CORS Errors in Frontend
- Ensure backend CORS middleware is configured
- Check API URL in frontend (http://localhost:8000)
- Use browser dev tools to inspect requests

### Scraper Not Finding Documents
- Check website structure (use browser inspect)
- Try with Selenium for JavaScript sites
- Verify document link selectors

---

## 🤝 Contributing

Feel free to fork, improve, and submit pull requests!

---

## 📄 License

MIT License - feel free to use for educational purposes

---

## 🏆 Team

Built for GDG - Techsprint 2026 - PS2: Digital Archaeology Challenge

1. KAUSHIK MOHANTY
2. NILAMANI KUNDU
3. DEEPAK KUMAR DAS

---

## 💡 Tips for Success

1. **Start Simple**: Get basic OCR + search working first
2. **Use Free Tools**: Prioritize open-source to avoid costs
3. **Focus on Demo**: Make core workflow smooth
4. **Highlight Impact**: Emphasize SDG 4 alignment
5. **Document Well**: Clear README helps judges understand
6. **Test Edge Cases**: Different qualities, languages, formats

---

*Making every university document searchable, one PDF at a time.* 📚✨
