from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pickle
import faiss
from sentence_transformers import SentenceTransformer
from pathlib import Path
from openai import OpenAI
import os

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Paths
INDEX_FOLDER = Path("data/index")

# Load FAISS index & passages
index = faiss.read_index(str(INDEX_FOLDER / "faiss_index.index"))
with open(INDEX_FOLDER / "passages.pkl", "rb") as f:
    passages = pickle.load(f)

# SentenceTransformer model for retrieval
model = SentenceTransformer("all-MiniLM-L6-v2")

# FastAPI app
app = FastAPI()

# CORS middleware
origins = ["http://localhost:3000"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # or ["*"] to allow all
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic model for request
class Query(BaseModel):
    question: str

# Retrieve top-k passages from FAISS
def retrieve(query, top_k=5):
    q_vec = model.encode([query], convert_to_numpy=True)
    D, I = index.search(q_vec, top_k)
    return [passages[i] for i in I[0]]

# Generate answer using LLM with context
def generate_answer(question, contexts):
    context_text = "\n\n".join([f"[{i+1}] {c['text']}" for i, c in enumerate(contexts)])
    prompt = f"""
Answer the question using ONLY the context below.
Cite sources like [1], [2].

Context:
{context_text}

Question:
{question}
"""
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2
    )
    return response.choices[0].message.content

# API endpoint
@app.post("/ask")
def ask_pdf(query: Query):
    results = retrieve(query.question, top_k=5)
    sources = [{"pdf": r["pdf"], "page": r["page"], "snippet": r["text"][:100]} for r in results]

    try:
        llm_answer = generate_answer(query.question, results)
    except Exception as e:
        llm_answer = f"LLM call failed: {e}"

    return {"answer": llm_answer, "sources": sources}
