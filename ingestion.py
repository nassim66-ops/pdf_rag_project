# ingestion.py
from pathlib import Path
import PyPDF2
import pickle
from sentence_transformers import SentenceTransformer
import faiss

PDF_FOLDER = Path("data/pdfs")
INDEX_FOLDER = Path("data/index")
INDEX_FOLDER.mkdir(parents=True, exist_ok=True)

# 1️⃣ Extract text from PDFs
def extract_pdf_text(pdf_path):
    reader = PyPDF2.PdfReader(str(pdf_path))
    pages = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        if text.strip():
            pages.append({"pdf": pdf_path.name, "page": i+1, "text": text.strip()})
    return pages

def chunk_text(text, chunk_size=500, overlap=100):
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks

def prepare_passages(pages):
    passages = []
    for page in pages:
        for c in chunk_text(page["text"]):
            passages.append({"pdf": page["pdf"], "page": page["page"], "text": c})
    return passages

# 2️⃣ Build FAISS index
def build_index(passages, model_name="all-MiniLM-L6-v2"):
    model = SentenceTransformer(model_name)
    embeddings = model.encode([p["text"] for p in passages], convert_to_numpy=True)

    dim = embeddings.shape[1]
    index = faiss.IndexFlatL2(dim)
    index.add(embeddings)

    # save index & passages
    faiss.write_index(index, str(INDEX_FOLDER / "faiss_index.index"))
    with open(INDEX_FOLDER / "passages.pkl", "wb") as f:
        pickle.dump(passages, f)
    print(f"FAISS index built with {len(passages)} passages")

if __name__ == "__main__":
    all_pages = []
    for pdf_file in PDF_FOLDER.glob("*.pdf"):
        all_pages.extend(extract_pdf_text(pdf_file))

    passages = prepare_passages(all_pages)
    build_index(passages)
