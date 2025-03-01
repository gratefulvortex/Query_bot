import os
import shutil
import uvicorn
from fastapi import FastAPI, File, UploadFile, HTTPException
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings, GoogleGenerativeAI
from langchain_community.document_loaders import PyPDFLoader
from pydantic import BaseModel
import google.generativeai as genai
from dotenv import load_dotenv  # Optional: Loads environment variables from .env file

# Load environment variables
load_dotenv()

# Get API Key from Environment
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise ValueError("🚨 GEMINI_API_KEY is missing! Set it as an environment variable.")

# Configure Gemini API
genai.configure(api_key=API_KEY)

# Paths & Directories
UPLOAD_DIR = "uploads"
FAISS_INDEX_PATH = "faiss_index"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Initialize Embeddings and LLM
embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001", google_api_key=API_KEY)
llm = GoogleGenerativeAI(model="models/gemini-1.5-pro", google_api_key=API_KEY)

# Initialize FastAPI
app = FastAPI()

# FAISS Vector DB (Lazy load)
vector_db = None

# Text Splitting Helper
def split_text(text):
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100)
    return splitter.split_text(text)

# Upload & Process PDF
@app.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
    global vector_db

    # Save File Locally
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Load PDF & Extract Text
    loader = PyPDFLoader(file_path)
    docs = loader.load()

    if not docs:
        return {"error": "⚠️ No text found in PDF. Please upload a valid document."}

    chunks = split_text(" ".join([doc.page_content for doc in docs]))

    # Create FAISS Index
    vector_db = FAISS.from_texts(chunks, embeddings)
    vector_db.save_local(FAISS_INDEX_PATH)

    return {"message": "✅ File uploaded and processed successfully!", "filename": file.filename}

# Query Model
class QueryRequest(BaseModel):
    query: str

@app.post("/query/")
async def query_document(request: QueryRequest):
    global vector_db

    # Ensure FAISS is loaded before querying
    if vector_db is None:
        try:
            vector_db = FAISS.load_local(FAISS_INDEX_PATH, embeddings)
            print("✅ FAISS Index Loaded Successfully!")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"🚨 FAISS Index not found. Upload a document first. {str(e)}")

    # Perform Similarity Search
    docs = vector_db.similarity_search(request.query, k=3)

    if not docs:
        return {"answer": "⚠️ No relevant answer found in the document."}

    # Prepare LLM Prompt
    context = "\n\n".join([doc.page_content for doc in docs])
    prompt = f"Based on the following context, answer the question:\n\nContext: {context}\n\nQuestion: {request.query}"

    # Generate Response
    response = llm.invoke(prompt)

    return {"answer": response}

# Run Server
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=True)
