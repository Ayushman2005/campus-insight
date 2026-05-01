# backend/campus_scraper.py
import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import logging
from typing import List, Dict

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def scrape_website(target_url: str, existing_filenames: List[str]) -> List[Dict]:
    """
    Scrapes the target URL for PDF and Image links.
    Returns a list of dictionaries with filename, url, and content (bytes)
    for documents that are not in existing_filenames.
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
                if filename not in existing_filenames:
                    try:
                        logger.info(f"Downloading new notice to memory: {filename}")
                        file_response = requests.get(full_url, headers=HEADERS, timeout=15)
                        
                        new_files.append({
                            'filename': filename,
                            'url': full_url,
                            'content': file_response.content
                        })
                    except Exception as e:
                        logger.error(f"Failed to fetch {full_url}: {e}")
                        
    except Exception as e:
        logger.error(f"Scraping failed: {e}")
        
    return new_files