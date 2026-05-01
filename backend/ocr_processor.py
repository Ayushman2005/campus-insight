"""
OCR Processor Module
Handles text extraction from PDFs and images using Tesseract
"""

import os
import io
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
import pdf2image
import numpy as np
import cv2
from pathlib import Path
import logging
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OCRProcessor:
    """
    OCR Processor for extracting text from images and PDFs
    Includes preprocessing for better accuracy
    """
    
    def __init__(self, language='eng'):
        self.language = language
        self.supported_formats = ['.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.bmp']
    
    def cleanup_text(self, text: str) -> str:
        """
        Cleans up OCR garbage (random symbols, short lines)
        """
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            # Skip empty lines
            if not line:
                continue
                
            # Skip lines that are just symbols (e.g. "| | )")
            # This regex looks for lines that have at least 2 alphanumeric characters
            if len(re.findall(r'[a-zA-Z0-9]', line)) < 2:
                continue

            # Skip lines that are mostly symbols (>50% non-alphanumeric)
            alnum_count = sum(c.isalnum() for c in line)
            if len(line) > 0 and (alnum_count / len(line)) < 0.5:
                continue
                
            cleaned_lines.append(line)
            
        return "\n".join(cleaned_lines)

    def preprocess_image_obj(self, img: Image.Image) -> Image.Image:
        """
        Preprocess Image object for better OCR accuracy
        """
        # 1. Resize: Scale up 2x. Tesseract works better on larger text.
        width, height = img.size
        img = img.resize((width * 2, height * 2), Image.Resampling.LANCZOS)
        
        # 2. Convert to Grayscale
        img = img.convert('L')
        
        # 3. Increase Contrast / Binarization
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(2.0)
        
        # Optional: Apply a threshold to make it purely black and white
        img = img.point(lambda x: 0 if x < 140 else 255, '1')
        
        return img

    def preprocess_image(self, image_path: str) -> Image:
        """
        Preprocess image from path (Legacy method)
        """
        img = Image.open(image_path)
        return self.preprocess_image_obj(img)
    
    def extract_text_from_image_obj(self, img: Image.Image, preprocess: bool = True) -> str:
        try:
            if preprocess:
                img = self.preprocess_image_obj(img)
            
            # --- KEY FIX HERE ---
            custom_config = r'--oem 3 --psm 3'
            
            text = pytesseract.image_to_string(
                img,
                lang=self.language,
                config=custom_config
            )
            
            clean_text = self.cleanup_text(text)
            return clean_text.strip()
        
        except Exception as e:
            logger.error(f"Error extracting text from image object: {str(e)}")
            return ""

    def extract_text_from_image_bytes(self, image_bytes: bytes, preprocess: bool = True) -> str:
        try:
            img = Image.open(io.BytesIO(image_bytes))
            return self.extract_text_from_image_obj(img, preprocess)
        except Exception as e:
            logger.error(f"Error loading image from bytes: {str(e)}")
            return ""

    def extract_text_from_image(self, image_path: str, preprocess: bool = True) -> str:
        try:
            img = Image.open(image_path)
            res = self.extract_text_from_image_obj(img, preprocess)
            logger.info(f"Successfully extracted text from {image_path}")
            return res
        except Exception as e:
            logger.error(f"Error extracting text from {image_path}: {str(e)}")
            return ""

    def extract_text_from_pdf_bytes(self, pdf_bytes: bytes, dpi: int = 300) -> str:
        try:
            poppler_path = r"C:\Program Files\Poppler\Library\bin" if os.name == 'nt' else None
            images = pdf2image.convert_from_bytes(pdf_bytes, dpi=dpi, poppler_path=poppler_path)
            
            all_text = []
            for image in images:
                page_text = self.extract_text_from_image_obj(image, preprocess=True)
                all_text.append(page_text)
                
            return "\n\n".join(all_text)
        
        except Exception as e:
            logger.error(f"Error extracting text from PDF bytes: {str(e)}")
            return ""
    
    def extract_text_from_pdf(self, pdf_path: str, dpi: int = 300) -> str:
        try:
            poppler_path = r"C:\Program Files\Poppler\Library\bin" if os.name == 'nt' else None
            images = pdf2image.convert_from_path(pdf_path, dpi=dpi, poppler_path=poppler_path)
            
            all_text = []
            for image in images:
                page_text = self.extract_text_from_image_obj(image, preprocess=True)
                all_text.append(page_text)
                
            return "\n\n".join(all_text)
        
        except Exception as e:
            logger.error(f"Error extracting text from PDF {pdf_path}: {str(e)}")
            return ""

    def process_document_bytes(self, file_bytes: bytes, filename: str) -> dict:
        filename_path = Path(filename)
        
        if filename_path.suffix.lower() == '.pdf':
            text = self.extract_text_from_pdf_bytes(file_bytes)
        else:
            text = self.extract_text_from_image_bytes(file_bytes)
        
        word_count = len(text.split())
        
        return {
            'text': text,
            'filename': filename,
            'format': filename_path.suffix.lower(),
            'word_count': word_count
        }
    
    def process_document(self, file_path: str) -> dict:
        file_path = Path(file_path)
        
        if file_path.suffix.lower() == '.pdf':
            text = self.extract_text_from_pdf(str(file_path))
        else:
            text = self.extract_text_from_image(str(file_path))
        
        word_count = len(text.split())
        
        return {
            'text': text,
            'filename': file_path.name,
            'format': file_path.suffix.lower(),
            'word_count': word_count
        }