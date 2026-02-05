# backend/campus_scraper.py
import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def scrape_website(target_url: str, save_dir: Path):
    """
    Scrapes the target URL for PDF and Image links.
    Downloads new files to save_dir.
    Returns a list of newly downloaded filenames.
    """
    new_files = []
    
    try:
        logger.info(f"Scraping {target_url}...")
        response = requests.get(target_url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find all links (a tags)
        links = soup.find_all('a', href=True)
        
        for link in links:
            href = link['href']
            
            # Filter for documents
            if href.lower().endswith(('.pdf', '.jpg', '.png', '.jpeg')):
                full_url = urljoin(target_url, href)
                filename = os.path.basename(urlparse(full_url).path)
                
                # Check if file already exists
                file_path = save_dir / filename
                if not file_path.exists():
                    try:
                        logger.info(f"Downloading new notice: {filename}")
                        file_response = requests.get(full_url, headers=HEADERS, timeout=15)
                        
                        with open(file_path, 'wb') as f:
                            f.write(file_response.content)
                            
                        new_files.append(filename)
                    except Exception as e:
                        logger.error(f"Failed to download {full_url}: {e}")
                        
    except Exception as e:
        logger.error(f"Scraping failed: {e}")
        
    return new_files