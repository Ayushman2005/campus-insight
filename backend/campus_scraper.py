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

def scrape_website(
    target_url: str, 
    existing_filenames: List[str], 
    extract_pdfs: bool = True,
    extract_images: bool = True,
    extract_text: bool = True,
    max_links: int = 20
) -> List[Dict]:
    """
    Scrapes the target URL with dynamic functionalities.
    Can extract the page's raw text and selectively download PDFs/Images.
    """
    new_files = []
    
    try:
        logger.info(f"Scraping {target_url}...")
        response = requests.get(target_url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 1. Extract the main page text if requested
        if extract_text:
            # Clean up scripts and styles
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.decompose()
            
            page_text = soup.get_text(separator=' ', strip=True)
            if len(page_text) > 100:
                domain = urlparse(target_url).netloc
                page_filename = f"{domain}_page_content.txt"
                if page_filename not in existing_filenames:
                    new_files.append({
                        'filename': page_filename,
                        'url': target_url,
                        'content': page_text.encode('utf-8')
                    })
        
        # 2. Extract Links
        links = soup.find_all('a', href=True)
        valid_extensions = []
        if extract_pdfs:
            valid_extensions.append('.pdf')
        if extract_images:
            valid_extensions.extend(['.jpg', '.png', '.jpeg'])
            
        if valid_extensions:
            processed_count = 0
            for link in links:
                if processed_count >= max_links:
                    break
                    
                href = link['href']
                if href.lower().endswith(tuple(valid_extensions)):
                    full_url = urljoin(target_url, href)
                    filename = os.path.basename(urlparse(full_url).path)
                    
                    if filename not in existing_filenames:
                        try:
                            logger.info(f"Fetching dynamically: {filename}")
                            file_response = requests.get(full_url, headers=HEADERS, timeout=15)
                            new_files.append({
                                'filename': filename,
                                'url': full_url,
                                'content': file_response.content
                            })
                            processed_count += 1
                        except Exception as e:
                            logger.error(f"Failed to fetch {full_url}: {e}")
                            
    except Exception as e:
        logger.error(f"Scraping failed: {e}")
        
    return new_files