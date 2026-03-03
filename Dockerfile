# Use an official lightweight Python image
FROM python:3.12-slim

# Install Tesseract OCR and essential system packages
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libtesseract-dev \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your backend files
COPY . .

# Start the FastAPI server using the port Render assigns
CMD uvicorn app:app --host 0.0.0.0 --port $PORT