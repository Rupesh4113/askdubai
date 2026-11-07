# CivicResolve AI - Production Container
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Install system dependencies including Tesseract OCR for document intelligence
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    tesseract-ocr \
    tesseract-ocr-ara \
    libmupdf-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Initialize FAISS official knowledge index and database
RUN python -c "from rag.ingestion import build_faiss_index; build_faiss_index(force_rebuild=True)"
RUN python -c "from database.database import init_db; init_db()"

EXPOSE 8501 8000

# Default command: launch Streamlit interface and FastAPI backend concurrently
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port 8000 & streamlit run app.py --server.port 8501 --server.address 0.0.0.0"]
