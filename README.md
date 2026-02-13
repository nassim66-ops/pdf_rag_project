# PDF RAG Project

A **Retrieval Augmented Generation (RAG)** pipeline for querying PDF documents. The project consists of three components:

1. **PDF Crawler** – Crawls websites to discover and download PDF files using Selenium
2. **Ingestion** – Extracts text from PDFs, chunks it, and builds a FAISS vector index
3. **Chatbot API** – FastAPI service that retrieves relevant passages and generates answers using OpenAI
4. **Frontend** – Web UI for querying the chatbot

## Prerequisites

- Python 3.8+
- Node.js and pnpm
- Chrome/Chromium browser (for the crawler)
- OpenAI API key (for the chatbot)

## Installation

```bash
pip install -r requirements.txt
```

## Environment Variables

Set your OpenAI API key:

```bash
# Windows (PowerShell)
$env:OPENAI_API_KEY = "your-api-key"

# Windows (CMD) / Linux / macOS
export OPENAI_API_KEY=your-api-key
```

## How to Run

### 1. Run the Crawler

Crawl a website to discover and download PDFs:

```bash
python pdf_crawler_selenium.py https://www.technology1.com/company/investors -o ./data/pdfs -d 3
```

- `-o ./data/pdfs` – Output directory for downloaded PDFs
- `-d 3` – Maximum crawl depth (how many link levels to follow)

### 2. Run Ingestion

Extract text from PDFs, chunk it, and build the FAISS vector index:

```bash
python ingestion.py
```

This reads PDFs from `data/pdfs`, creates embeddings, and saves the index to `data/index`.

### 3. Run the Chatbot

Start the FastAPI server:

```bash
python -m uvicorn app:app --reload
```

The API will be available at `http://localhost:8000`. Use the `/ask` endpoint with a JSON body `{"question": "your question"}` to query your PDF documents.

### 4. Run the Frontend

Install dependencies and start the frontend:

```bash
cd frontend
pnpm i
pnpm start
```

The frontend will typically run at `http://localhost:3000` and connects to the chatbot API.
