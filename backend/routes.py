from fastapi import APIRouter, File, UploadFile, Form, Body
from fastapi.responses import JSONResponse
from upload import PDFUploader
import os
from rag_pipeline import run_rag
from pydantic import BaseModel

router = APIRouter()
uploader = PDFUploader()

class QuestionRequest(BaseModel):
    message: str
    documents: list[str] = []
    document_ids: list[str] = []

@router.post("/upload_pdf/")
async def upload_pdf(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith('.pdf'):
        return JSONResponse({"error": "Only PDF files are allowed."}, status_code=400)
    file.file.seek(0)
    success = uploader.upload_pdf_fileobj(file.file, file.filename)
    if success:
        return {"message": "PDF uploaded successfully.", "filename": file.filename}
    else:
        return JSONResponse({"error": "Upload failed."}, status_code=500)

@router.post("/ask/")
async def ask_question(request: QuestionRequest):
    # Use the first document if multiple are provided
    pdf_filename = ""
    if request.documents:
        pdf_filename = request.documents[0]
    elif request.document_ids:
        pdf_filename = request.document_ids[0]
    
    if not pdf_filename:
        return JSONResponse({"error": "No document selected."}, status_code=400)
    
    result = run_rag(request.message, pdf_filename, debug_log_dir="logs")
    return {
        "message": result.get("cleaned_response", "No answer."),
        "response": result.get("cleaned_response", "No answer."),
        "answer": result.get("cleaned_response", "No answer.")
    }

@router.get("/list_pdfs/")
def list_pdfs():
    pdfs = uploader.list_pdfs()
    filenames = [os.path.basename(pdf['key']) for pdf in pdfs]
    documents = [{"id": filename, "name": filename, "type": "pdf", "status": "Ready"} 
                for filename in filenames]
    return {"pdfs": filenames, "documents": documents}
