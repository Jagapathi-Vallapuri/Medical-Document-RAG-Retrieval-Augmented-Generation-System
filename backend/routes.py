from fastapi import APIRouter, File, UploadFile, Form, Body
from fastapi.responses import JSONResponse, StreamingResponse
from upload import PDFUploader
import os
import json
import uuid
from datetime import datetime
from rag_pipeline import RAGPipeline
from intent_classifier import classify_intent
from chat_models import ChatManager, ChatMessage
from pydantic import BaseModel
from logger_config import get_logger
from typing import List, Optional
from chat_models import ChatManager, ChatSession, ChatMessage, MessageType
from redis_chat_manager import RedisChatManager
from chat_logger import chat_logger

logger = get_logger(__name__)

router = APIRouter()
uploader = PDFUploader()
# Instantiate a singleton RAGPipeline for all requests
pipeline = RAGPipeline()

# Initialize Redis-based chat manager
try:
    redis_chat_manager = RedisChatManager()
    redis_chat_manager.connect()
    logger.info("Using Redis for chat storage")
    chat_manager = redis_chat_manager
except Exception as e:
    logger.warning(f"Failed to connect to Redis: {e}. Falling back to in-memory storage")
    chat_manager = ChatManager()  # Fallback to in-memory

class QuestionRequest(BaseModel):
    message: str
    chat_id: Optional[str] = None
    documents: List[str] = []
    document_ids: List[str] = []

class AutoQueryRequest(BaseModel):
    message: str
    chat_id: Optional[str] = None

class CreateChatRequest(BaseModel):
    title: Optional[str] = "New Chat"

class UpdateChatRequest(BaseModel):
    title: str

class UploadResponse(BaseModel):
    message: str
    filename: str

class ErrorResponse(BaseModel):
    error: str

class QuestionResponse(BaseModel):
    message: str
    response: str
    answer: str

class AutoQueryResponse(BaseModel):
    message: str
    response: str
    answer: str
    selected_document: str
    selection_score: float
    documents_considered: int

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



@router.post("/auto_ask/")
async def auto_ask_question(request: AutoQueryRequest):
    try:
        # Validate input
        if not request.message.strip():
            return JSONResponse({"error": "Question cannot be empty."}, status_code=400)

        # Determine intent using Hugging Face API
        intent = classify_intent(request.message)
        logger.info(f"Intent classified as: {intent}")

        if intent == "direct":
            # For direct questions, use a simple LLM call (no retrieval)
            # Here, we use the pipeline's LLM directly with no context
            answer = pipeline.generate_response(context="", question=request.message)
            return {
                "message": answer,
                "response": answer,
                "answer": answer,
                "selected_document": "",
                "selection_score": 0.0,
                "documents_considered": 0
            }
        else:
            # Use the singleton pipeline for auto-selection (retrieval-augmented)
            result = pipeline.ask_with_auto_selection(
                query=request.message,
                normalization="sqrt",
                top_k=5
            )
            if result.status == "no_documents_found":
                return JSONResponse({"error": "No relevant documents found."}, status_code=404)
            if result.status == "generation_failed":
                return JSONResponse({"error": result.answer}, status_code=500)
            return {
                "message": result.answer,
                "response": result.answer,
                "answer": result.answer,
                "selected_document": result.selected_document or "",
                "selection_score": result.selection_score or 0.0,
                "documents_considered": result.documents_considered
            }
    except Exception as e:
        logger.error(f"Error in auto_ask_question: {str(e)}")
        return JSONResponse({"error": "Internal server error occurred."}, status_code=500)

@router.post("/auto_ask_stream/")
async def auto_ask_question_stream(request: AutoQueryRequest):
    """Streaming version that sends document selection info first, then the answer"""
    
    async def generate_stream():
        try:
            logger.info(f"🚀 Starting stream for message: '{request.message[:30]}...' chat_id: {request.chat_id}")
            
            # Log to chat-specific logger
            if request.chat_id:
                chat_logger.log_user_message(request.chat_id, request.message)
            
            # Validate input
            if not request.message.strip():
                yield f"data: {json.dumps({'error': 'Question cannot be empty.'})}\n\n"
                return

            # Get or create chat session
            chat_id = request.chat_id
            if not chat_id:
                chat_id = chat_manager.create_chat("New Chat")
            
            chat = chat_manager.get_chat(chat_id)
            if not chat:
                yield f"data: {json.dumps({'error': 'Chat session not found.'})}\n\n"
                return

            # Add user message to chat history
            user_message = ChatMessage(
                id=str(uuid.uuid4()),
                content=request.message,
                message_type=MessageType.USER,
                timestamp=datetime.now()
            )
            
            # Save user message to Redis if using Redis chat manager
            if hasattr(chat_manager, 'add_message'):
                chat_manager.add_message(chat_id, user_message)
            else:
                chat.add_message(user_message)

            # Determine intent using Hugging Face API
            intent = classify_intent(request.message)
            logger.info(f"🎯 Intent classified as: {intent} for message: '{request.message[:50]}...'")
            
            # Log intent classification
            if chat_id:
                chat_logger.log_intent_classification(chat_id, request.message, intent)

            if intent == "direct":
                # For direct questions, send immediate response
                
                # Include conversation context for direct answers
                # Optimized: Simple context injection, letting the smart prompt template handle relevance
                conversation_context = chat.get_conversation_summary()
                if conversation_context:
                    # Simple context injection - let the model decide relevance
                    enhanced_query = f"Previous conversation context:\n{conversation_context}\n\nCurrent question: {request.message}"
                else:
                    enhanced_query = request.message
                
                answer = pipeline.generate_response(context="", question=enhanced_query)
                
                # Log direct answer
                if chat_id:
                    chat_logger.log_bot_response(chat_id, answer, {
                        "type": "direct_answer",
                        "selected_document": "",
                        "selection_score": 0.0,
                        "documents_considered": 0
                    })
                
                # Add bot response to chat history
                bot_message = ChatMessage(
                    id=str(uuid.uuid4()),
                    content=answer,
                    message_type=MessageType.BOT,
                    timestamp=datetime.now(),
                    metadata={
                        "selected_document": "",
                        "selection_score": 0.0,
                        "documents_considered": 0
                    }
                )
                # Save bot message to Redis
                chat_manager.add_message(chat_id, bot_message)
                
                yield f"data: {json.dumps({
                    'type': 'final_answer',
                    'message': answer,
                    'response': answer,
                    'answer': answer,
                    'selected_document': '',
                    'selection_score': 0.0,
                    'documents_considered': 0,
                    'chat_id': chat_id
                })}\n\n"
            else:
                # Step 1: Get document selection (fast)
                logger.info(f"🔍 Starting document selection for query: '{request.message[:50]}...'")
                doc_selection = pipeline.get_most_relevant_documents(
                    query=request.message,
                    top_n=1,
                    show_previews=False,
                    normalization="sqrt"
                )
                
                logger.info(f"📊 Document selection result: status={doc_selection.status}, total_found={doc_selection.total_documents_found}, documents={len(doc_selection.documents) if doc_selection.documents else 0}")
                
                if doc_selection.status != "success" or not doc_selection.documents:
                    yield f"data: {json.dumps({
                        'type': 'error',
                        'error': 'No relevant documents found.',
                        'documents_considered': doc_selection.total_documents_found,
                        'chat_id': chat_id
                    })}\n\n"
                    return
                
                best_doc = doc_selection.documents[0]
                selected_doc_id = best_doc.doc_id
                selection_score = best_doc.relevance_score
                
                # Log document selection
                if chat_id:
                    chat_logger.log_document_selection(
                        chat_id, 
                        request.message, 
                        selected_doc_id, 
                        selection_score, 
                        doc_selection.total_documents_found
                    )
                
                logger.info(f"📄 Sending document selection: {selected_doc_id} with score {selection_score}")
                yield f"data: {json.dumps({
                    'type': 'document_selected',
                    'selected_document': selected_doc_id,
                    'selection_score': selection_score,
                    'documents_considered': doc_selection.total_documents_found,
                    'chat_id': chat_id
                })}\n\n"
                
                conversation_context = chat.get_conversation_summary()
                if conversation_context:
                    # Simple context injection - the model will determine relevance
                    enhanced_query = f"Previous conversation context:\n{conversation_context}\n\nCurrent question: {request.message}"
                else:
                    enhanced_query = request.message
                
                rag_response = pipeline.run(
                    question=enhanced_query,
                    pdf_s3_key=selected_doc_id,
                    top_k=5,
                    use_summarization=False
                )
                
                logger.info(f"✅ Generated answer for {selected_doc_id}, length: {len(rag_response.cleaned_response) if rag_response.cleaned_response else 0}")
                
                # Log RAG process
                if chat_id:
                    chat_logger.log_rag_process(
                        chat_id,
                        enhanced_query,
                        selected_doc_id,
                        5,  # top_k chunks
                        len(rag_response.cleaned_response) if rag_response.cleaned_response else 0
                    )
                    
                    # Log bot response
                    chat_logger.log_bot_response(chat_id, rag_response.cleaned_response, {
                        "type": "rag_answer",
                        "selected_document": selected_doc_id,
                        "selection_score": selection_score,
                        "documents_considered": doc_selection.total_documents_found
                    })
                
                # Add bot response to chat history
                bot_message = ChatMessage(
                    id=str(uuid.uuid4()),
                    content=rag_response.cleaned_response,
                    message_type=MessageType.BOT,
                    timestamp=datetime.now(),
                    metadata={
                        "selected_document": selected_doc_id,
                        "selection_score": selection_score,
                        "documents_considered": doc_selection.total_documents_found
                    }
                )
                chat_manager.add_message(chat_id, bot_message)
                
                # Step 4: Send final answer
                logger.info(f"📤 Sending final answer for chat {chat_id} with document {selected_doc_id}")
                yield f"data: {json.dumps({
                    'type': 'final_answer',
                    'message': rag_response.cleaned_response,
                    'response': rag_response.cleaned_response,
                    'answer': rag_response.cleaned_response,
                    'selected_document': selected_doc_id,
                    'selection_score': selection_score,
                    'documents_considered': doc_selection.total_documents_found,
                    'chat_id': chat_id
                })}\n\n"
                
        except Exception as e:
            logger.error(f"Error in auto_ask_question_stream: {str(e)}")
            
            # Log error to chat logger
            if request.chat_id:
                chat_logger.log_error(request.chat_id, "stream_error", str(e), {
                    "message": request.message,
                    "error_type": type(e).__name__
                })
            
            yield f"data: {json.dumps({'type': 'error', 'error': 'Internal server error occurred.'})}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream"
        }
    )

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
    logger.info(f"Found {len(filenames)} PDFs: {filenames}")
    return {"pdfs": filenames, "documents": documents}

@router.get("/debug/available_docs/")
def debug_available_docs():
    """Debug endpoint to check available documents"""
    try:
        pdfs = uploader.list_pdfs()
        doc_selection = pipeline.get_most_relevant_documents(
            query="test query",
            top_n=5,
            show_previews=False,
            normalization="sqrt"
        )
        return {
            "uploaded_pdfs": len(pdfs),
            "pdf_list": [os.path.basename(pdf['key']) for pdf in pdfs],
            "doc_selection_status": doc_selection.status,
            "total_documents_found": doc_selection.total_documents_found if hasattr(doc_selection, 'total_documents_found') else 0,
            "available_documents": len(doc_selection.documents) if hasattr(doc_selection, 'documents') and doc_selection.documents else 0
        }
    except Exception as e:
        return {"error": str(e)}

# Chat Management Endpoints

@router.post("/chats/")
def create_chat(request: CreateChatRequest):
    """Create a new chat session"""
    title = request.title or "New Chat"
    chat_id = chat_manager.create_chat(title)
    chat = chat_manager.get_chat(chat_id)
    if not chat:
        return JSONResponse({"error": "Failed to create chat"}, status_code=500)
    return {"chat_id": chat_id, "title": chat.title, "created_at": chat.created_at.isoformat()}

@router.get("/chats/")
def list_chats():
    """List all chat sessions"""
    return {"chats": chat_manager.list_chats()}

@router.get("/chats/{chat_id}")
def get_chat(chat_id: str):
    """Get a specific chat with all messages"""
    chat = chat_manager.get_chat(chat_id)
    if not chat:
        return JSONResponse({"error": "Chat not found"}, status_code=404)
    return chat.to_dict()

@router.put("/chats/{chat_id}")
def update_chat(chat_id: str, request: UpdateChatRequest):
    """Update chat title"""
    success = chat_manager.update_chat_title(chat_id, request.title)
    if not success:
        return JSONResponse({"error": "Chat not found"}, status_code=404)
    return {"message": "Chat updated successfully"}

@router.delete("/chats/{chat_id}")
def delete_chat(chat_id: str):
    """Delete a chat session"""
    success = chat_manager.delete_chat(chat_id)
    if not success:
        return JSONResponse({"error": "Chat not found"}, status_code=404)
    return {"message": "Chat deleted successfully"}

@router.get("/chats/{chat_id}/logs")
def get_chat_logs(chat_id: str):
    """Get logs for a specific chat"""
    try:
        import os
        from pathlib import Path
        
        chat_dir = Path("chat_logs") / f"chat_{chat_id}"
        
        if not chat_dir.exists():
            return JSONResponse({"error": "No logs found for this chat"}, status_code=404)
        
        # Read events file
        events_file = chat_dir / "events.jsonl"
        events = []
        
        if events_file.exists():
            with open(events_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        events.append(json.loads(line.strip()))
                    except json.JSONDecodeError:
                        continue
        
        # Read log file
        log_file = chat_dir / "chat.log"
        log_content = ""
        
        if log_file.exists():
            with open(log_file, 'r', encoding='utf-8') as f:
                log_content = f.read()
        
        # Get summary
        summary = chat_logger.get_chat_summary(chat_id)
        
        return {
            "chat_id": chat_id,
            "summary": summary,
            "events": events,
            "raw_logs": log_content.split('\n') if log_content else []
        }
        
    except Exception as e:
        logger.error(f"Error retrieving chat logs for {chat_id}: {e}")
        return JSONResponse({"error": "Failed to retrieve chat logs"}, status_code=500)

@router.get("/chats/logs/summary")
def get_all_chat_logs_summary():
    """Get summary of all chat logs"""
    try:
        from pathlib import Path
        
        chat_logs_dir = Path("chat_logs")
        
        if not chat_logs_dir.exists():
            return {"chats": []}
        
        summaries = []
        for chat_dir in chat_logs_dir.iterdir():
            if chat_dir.is_dir() and chat_dir.name.startswith('chat_'):
                chat_id = chat_dir.name.replace('chat_', '')
                summary = chat_logger.get_chat_summary(chat_id)
                summaries.append(summary)
        
        return {"chats": summaries}
        
    except Exception as e:
        logger.error(f"Error retrieving chat logs summary: {e}")
        return JSONResponse({"error": "Failed to retrieve chat logs summary"}, status_code=500)

@router.post("/admin/cleanup-logs")
def cleanup_old_chat_logs(days_to_keep: int = 30):
    """Admin endpoint to cleanup old chat logs"""
    try:
        chat_logger.cleanup_old_logs(days_to_keep)
        return {"message": f"Successfully cleaned up chat logs older than {days_to_keep} days"}
    except Exception as e:
        logger.error(f"Error cleaning up chat logs: {e}")
        return JSONResponse({"error": "Failed to cleanup chat logs"}, status_code=500)
