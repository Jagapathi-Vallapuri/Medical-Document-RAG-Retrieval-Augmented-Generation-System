from fastapi import APIRouter, File, UploadFile, Form, Body
from fastapi.responses import JSONResponse
from upload import PDFUploader
import os
from rag_pipeline import run_rag
from pydantic import BaseModel
from logger_config import get_logger
from typing import List

logger = get_logger(__name__)

router = APIRouter()
uploader = PDFUploader()

class QuestionRequest(BaseModel):
    message: str
    documents: List[str] = []
    document_ids: List[str] = []

class UploadResponse(BaseModel):
    message: str
    filename: str

class ErrorResponse(BaseModel):
    error: str

class QuestionResponse(BaseModel):
    message: str
    response: str
    answer: str

class DocumentInfo(BaseModel):
    id: str
    name: str
    type: str
    status: str

class ListPDFsResponse(BaseModel):
    pdfs: List[str]
    documents: List[DocumentInfo]

@router.post("/upload_pdf/")
async def upload_pdf(file: UploadFile = File(...)):
    try:
        # Validate file type
        if not file.filename or not file.filename.lower().endswith('.pdf'):
            return JSONResponse({"error": "Only PDF files are allowed."}, status_code=400)
        
        max_size = 50 * 1024 * 1024  # 50MB
        if file.size and file.size > max_size:
            return JSONResponse({"error": "File size exceeds 50MB limit."}, status_code=400)
        
        if len(file.filename) > 255:
            return JSONResponse({"error": "Filename too long."}, status_code=400)
        
        file.file.seek(0)
        success = uploader.upload_pdf_fileobj(file.file, file.filename)
        
        if success:
            return {"message": "PDF uploaded successfully.", "filename": file.filename}
        else:
            return JSONResponse({"error": "Upload failed."}, status_code=500)
    except Exception as e:
        logger.error(f"Error in upload_pdf: {str(e)}")
        return JSONResponse({"error": "Internal server error occurred."}, status_code=500)

@router.post("/ask/")
async def ask_question(request: QuestionRequest):
    try:
        # Validate input
        if not request.message.strip():
            return JSONResponse({"error": "Question cannot be empty."}, status_code=400)
        
        pdf_filename = ""
        if request.documents:
            pdf_filename = request.documents[0]
        elif request.document_ids:
            pdf_filename = request.document_ids[0]
        
        if not pdf_filename:
            return JSONResponse({"error": "No document selected."}, status_code=400)
        
        result = run_rag(request.message, pdf_filename, debug_log_dir="logs")
        
        if not result or not result.get("cleaned_response"):
            return JSONResponse({"error": "Failed to generate response."}, status_code=500)
        
        return {
            "message": result.get("cleaned_response", "No answer."),
            "response": result.get("cleaned_response", "No answer."),
            "answer": result.get("cleaned_response", "No answer.")
        }
    except Exception as e:
        logger.error(f"Error in ask_question: {str(e)}")
        return JSONResponse({"error": "Internal server error occurred."}, status_code=500)

@router.get("/health/")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "RAG Pipeline API"}

@router.get("/list_pdfs/")
def list_pdfs():
    pdfs = uploader.list_pdfs()
    filenames = [os.path.basename(pdf['key']) for pdf in pdfs]
    documents = [{"id": filename, "name": filename, "type": "pdf", "status": "Ready"} 
                for filename in filenames]
    return {"pdfs": filenames, "documents": documents}
