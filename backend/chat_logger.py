import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

class ChatLogger:
    """
    Chat-specific logger that stores logs per chat session
    """
    
    def __init__(self, base_log_dir: str = "chat_logs"):
        """
        Initialize chat logger
        
        Args:
            base_log_dir: Base directory to store chat logs
        """
        self.base_log_dir = Path(base_log_dir)
        self.base_log_dir.mkdir(exist_ok=True)
        self.chat_loggers: Dict[str, logging.Logger] = {}
        
    def get_chat_logger(self, chat_id: str) -> logging.Logger:
        """
        Get or create a logger for a specific chat
        
        Args:
            chat_id: Unique chat identifier
            
        Returns:
            Logger instance for the chat
        """
        if chat_id not in self.chat_loggers:
            chat_dir = self.base_log_dir / f"chat_{chat_id}"
            chat_dir.mkdir(exist_ok=True)
            
            logger = logging.getLogger(f"chat_{chat_id}")
            logger.setLevel(logging.DEBUG)
            
            logger.handlers.clear()
            
            log_file = chat_dir / "chat.log"
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(logging.DEBUG)
            
            formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
            
            logger.propagate = False
            
            self.chat_loggers[chat_id] = logger
            
        return self.chat_loggers[chat_id]
    
    def log_user_message(self, chat_id: str, message: str, timestamp: Optional[datetime] = None):
        """Log user message"""
        logger = self.get_chat_logger(chat_id)
        ts = timestamp or datetime.now()
        logger.info(f"USER_MESSAGE: {message}")
        
        # Also save as JSON for structured access
        self._save_chat_event(chat_id, {
            "type": "user_message",
            "content": message,
            "timestamp": ts.isoformat()
        })
    
    def log_bot_response(self, chat_id: str, response: str, metadata: Optional[Dict] = None, timestamp: Optional[datetime] = None):
        """Log bot response with metadata"""
        logger = self.get_chat_logger(chat_id)
        ts = timestamp or datetime.now()
        
        log_msg = f"BOT_RESPONSE: {response[:100]}..." if len(response) > 100 else f"BOT_RESPONSE: {response}"
        if metadata:
            log_msg += f" | METADATA: {json.dumps(metadata)}"
        logger.info(log_msg)
        
        # Save as JSON
        self._save_chat_event(chat_id, {
            "type": "bot_response",
            "content": response,
            "metadata": metadata or {},
            "timestamp": ts.isoformat()
        })
    
    def log_intent_classification(self, chat_id: str, query: str, intent: str, confidence: Optional[float] = None):
        """Log intent classification result"""
        logger = self.get_chat_logger(chat_id)
        logger.info(f"INTENT_CLASSIFICATION: query='{query[:50]}...' intent={intent} confidence={confidence}")
        
        self._save_chat_event(chat_id, {
            "type": "intent_classification",
            "query": query,
            "intent": intent,
            "confidence": confidence,
            "timestamp": datetime.now().isoformat()
        })
    
    def log_document_selection(self, chat_id: str, query: str, selected_doc: str, score: float, total_considered: int):
        """Log document selection process"""
        logger = self.get_chat_logger(chat_id)
        logger.info(f"DOCUMENT_SELECTION: query='{query[:50]}...' selected='{selected_doc}' score={score} considered={total_considered}")
        
        self._save_chat_event(chat_id, {
            "type": "document_selection",
            "query": query,
            "selected_document": selected_doc,
            "selection_score": score,
            "documents_considered": total_considered,
            "timestamp": datetime.now().isoformat()
        })
    
    def log_rag_process(self, chat_id: str, query: str, document: str, chunks_retrieved: int, response_length: int):
        """Log RAG pipeline process"""
        logger = self.get_chat_logger(chat_id)
        logger.info(f"RAG_PROCESS: query='{query[:50]}...' doc='{document}' chunks={chunks_retrieved} response_len={response_length}")
        
        self._save_chat_event(chat_id, {
            "type": "rag_process",
            "query": query,
            "document": document,
            "chunks_retrieved": chunks_retrieved,
            "response_length": response_length,
            "timestamp": datetime.now().isoformat()
        })
    
    def log_error(self, chat_id: str, error_type: str, error_message: str, context: Optional[Dict] = None):
        """Log error specific to chat"""
        logger = self.get_chat_logger(chat_id)
        logger.error(f"ERROR_{error_type.upper()}: {error_message}")
        
        if context:
            logger.error(f"ERROR_CONTEXT: {json.dumps(context)}")
        
        self._save_chat_event(chat_id, {
            "type": "error",
            "error_type": error_type,
            "error_message": error_message,
            "context": context or {},
            "timestamp": datetime.now().isoformat()
        })
    
    def log_debug(self, chat_id: str, debug_type: str, data: Any):
        """Log debug information"""
        logger = self.get_chat_logger(chat_id)
        logger.debug(f"DEBUG_{debug_type.upper()}: {json.dumps(data) if isinstance(data, (dict, list)) else str(data)}")
        
        self._save_chat_event(chat_id, {
            "type": "debug",
            "debug_type": debug_type,
            "data": data,
            "timestamp": datetime.now().isoformat()
        })
    
    def _save_chat_event(self, chat_id: str, event_data: Dict[str, Any]):
        """Save chat event as JSON for structured access"""
        chat_dir = self.base_log_dir / f"chat_{chat_id}"
        events_file = chat_dir / "events.jsonl"
        
        try:
            with open(events_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(event_data) + '\n')
        except Exception as e:
            main_logger = logging.getLogger(__name__)
            main_logger.error(f"Failed to save chat event for {chat_id}: {e}")
    
    def get_chat_summary(self, chat_id: str) -> Dict[str, Any]:
        """Get summary statistics for a chat"""
        chat_dir = self.base_log_dir / f"chat_{chat_id}"
        events_file = chat_dir / "events.jsonl"
        
        if not events_file.exists():
            return {"chat_id": chat_id, "message_count": 0, "error_count": 0, "last_activity": None}
        
        message_count = 0
        error_count = 0
        last_activity = None
        
        try:
            with open(events_file, 'r', encoding='utf-8') as f:
                for line in f:
                    event = json.loads(line.strip())
                    if event['type'] in ['user_message', 'bot_response']:
                        message_count += 1
                    elif event['type'] == 'error':
                        error_count += 1
                    
                    event_time = datetime.fromisoformat(event['timestamp'])
                    if last_activity is None or event_time > last_activity:
                        last_activity = event_time
        except Exception as e:
            main_logger = logging.getLogger(__name__)
            main_logger.error(f"Failed to read chat summary for {chat_id}: {e}")
        
        return {
            "chat_id": chat_id,
            "message_count": message_count,
            "error_count": error_count,
            "last_activity": last_activity.isoformat() if last_activity else None
        }
    
    def cleanup_old_logs(self, days_to_keep: int = 30):
        """Clean up logs older than specified days"""
        cutoff_date = datetime.now().timestamp() - (days_to_keep * 24 * 60 * 60)
        
        for chat_dir in self.base_log_dir.iterdir():
            if chat_dir.is_dir() and chat_dir.name.startswith('chat_'):
                try:
                    if chat_dir.stat().st_mtime < cutoff_date:
                        import shutil
                        shutil.rmtree(chat_dir)
                        logging.info(f"Cleaned up old chat logs: {chat_dir.name}")
                except Exception as e:
                    logging.error(f"Failed to cleanup {chat_dir.name}: {e}")

chat_logger = ChatLogger()
