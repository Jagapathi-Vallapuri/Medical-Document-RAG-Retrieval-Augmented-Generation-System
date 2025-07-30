"""
Redis-based chat management for persistent storage
"""
import json
import redis
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from dataclasses import asdict
from chat_models import ChatSession, ChatMessage, MessageType
from logger_config import get_logger
import os

logger = get_logger(__name__)

class RedisChatManager:
    """Redis-based chat manager for persistent storage"""
    
    def __init__(self, redis_url: Optional[str] = None):
        """Initialize Redis connection"""
        self.redis_url = redis_url or os.getenv('REDIS_URL', 'redis://localhost:6379')
        self.redis_client: Optional[redis.Redis] = None
        self.key_prefix = "chat:"
        self.chat_list_key = "chat_list"
        
    def connect(self):
        """Establish Redis connection"""
        try:
            self.redis_client = redis.from_url(
                self.redis_url, 
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True
            )
            # Test connection
            self.redis_client.ping()
            logger.info("Successfully connected to Redis")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    def disconnect(self):
        """Close Redis connection"""
        if self.redis_client:
            self.redis_client.close()
            logger.info("Redis connection closed")
    
    def _serialize_chat(self, chat: ChatSession) -> str:
        """Serialize chat session to JSON"""
        try:
            chat_data = {
                "chat_id": chat.chat_id,
                "title": chat.title,
                "created_at": chat.created_at.isoformat(),
                "updated_at": chat.updated_at.isoformat(),
                "context_window": chat.context_window,
                "messages": [
                    {
                        "id": msg.id,
                        "content": msg.content,
                        "message_type": msg.message_type.value,
                        "timestamp": msg.timestamp.isoformat(),
                        "metadata": msg.metadata or {}
                    }
                    for msg in chat.messages
                ]
            }
            return json.dumps(chat_data)
        except Exception as e:
            logger.error(f"Error serializing chat {chat.chat_id}: {e}")
            raise
    
    def _deserialize_chat(self, chat_data: str) -> ChatSession:
        """Deserialize JSON to chat session"""
        try:
            data = json.loads(chat_data)
            
            # Create messages
            messages = []
            for msg_data in data.get("messages", []):
                message = ChatMessage(
                    id=msg_data["id"],
                    content=msg_data["content"],
                    message_type=MessageType(msg_data["message_type"]),
                    timestamp=datetime.fromisoformat(msg_data["timestamp"]),
                    metadata=msg_data.get("metadata")
                )
                messages.append(message)
            
            chat = ChatSession(
                chat_id=data["chat_id"],
                title=data["title"],
                messages=messages,
                created_at=datetime.fromisoformat(data["created_at"]),
                updated_at=datetime.fromisoformat(data["updated_at"]),
                context_window=data.get("context_window", 5)
            )
            
            return chat
        except Exception as e:
            logger.error(f"Error deserializing chat data: {e}")
            raise
    
    def create_chat(self, title: str = "New Chat") -> str:
        """Create a new chat session"""
        try:
            if not self.redis_client:
                self.connect()
            assert self.redis_client is not None
            
            chat_id = f"chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{self.redis_client.incr('chat_counter')}"
            
            chat = ChatSession(
                chat_id=chat_id,
                title=title
            )
            
            # Store chat in Redis
            chat_key = f"{self.key_prefix}{chat_id}"
            assert self.redis_client is not None
            self.redis_client.set(chat_key, self._serialize_chat(chat))
            
            # Add to chat list
            self.redis_client.zadd(
                self.chat_list_key, 
                {chat_id: chat.updated_at.timestamp()}
            )
            
            logger.info(f"Created chat {chat_id} in Redis")
            return chat_id
            
        except Exception as e:
            logger.error(f"Error creating chat: {e}")
            raise
    
    def get_chat(self, chat_id: str) -> Optional[ChatSession]:
        """Get a specific chat session"""
        try:
            if not self.redis_client:
                self.connect()
            
            if not self.redis_client:
                return None
            
            chat_key = f"{self.key_prefix}{chat_id}"
            chat_data = self.redis_client.get(chat_key)
            
            if not chat_data or not isinstance(chat_data, str):
                return None
                
            return self._deserialize_chat(chat_data)
            
        except Exception as e:
            logger.error(f"Error getting chat {chat_id}: {e}")
            return None
    
    def save_chat(self, chat: ChatSession) -> bool:
        """Save chat session to Redis"""
        try:
            if not self.redis_client:
                self.connect()
            
            if not self.redis_client:
                return False
            
            chat_key = f"{self.key_prefix}{chat.chat_id}"
            self.redis_client.set(chat_key, self._serialize_chat(chat))
            
            # Update in chat list with new timestamp
            self.redis_client.zadd(
                self.chat_list_key, 
                {chat.chat_id: chat.updated_at.timestamp()}
            )
            
            logger.debug(f"Saved chat {chat.chat_id} to Redis")
            return True
            
        except Exception as e:
            logger.error(f"Error saving chat {chat.chat_id}: {e}")
            return False
    
    def list_chats(self) -> List[Dict[str, Any]]:
        """List all chat sessions (sorted by most recent)"""
        try:
            if not self.redis_client:
                self.connect()
            
            if not self.redis_client:
                return []
            
            chat_ids = self.redis_client.zrevrange(self.chat_list_key, 0, -1)
            
            chats = []
            for chat_id in chat_ids:
                if isinstance(chat_id, str):
                    chat = self.get_chat(chat_id)
                    if chat:
                        chats.append({
                            "chat_id": chat.chat_id,
                            "title": chat.title,
                            "message_count": len(chat.messages),
                            "updated_at": chat.updated_at.isoformat(),
                            "created_at": chat.created_at.isoformat(),
                            "last_message": chat.messages[-1].content[:100] + "..." if chat.messages else ""
                        })
            
            return chats
            
        except Exception as e:
            logger.error(f"Error listing chats: {e}")
            return []
    
    def delete_chat(self, chat_id: str) -> bool:
        """Delete a chat session"""
        try:
            if not self.redis_client:
                self.connect()
            
            if not self.redis_client:
                return False
            
            chat_key = f"{self.key_prefix}{chat_id}"
            
            # Remove from Redis
            deleted = self.redis_client.delete(chat_key)
            
            self.redis_client.zrem(self.chat_list_key, chat_id)
            
            if deleted:
                logger.info(f"Deleted chat {chat_id} from Redis")
                return True
            else:
                logger.warning(f"Chat {chat_id} not found for deletion")
                return False
                
        except Exception as e:
            logger.error(f"Error deleting chat {chat_id}: {e}")
            return False
    
    def update_chat_title(self, chat_id: str, title: str) -> bool:
        """Update chat title"""
        try:
            chat = self.get_chat(chat_id)
            if not chat:
                return False
            
            chat.title = title
            chat.updated_at = datetime.now()
            
            return self.save_chat(chat)
            
        except Exception as e:
            logger.error(f"Error updating chat title {chat_id}: {e}")
            return False
    
    def add_message(self, chat_id: str, message: ChatMessage) -> bool:
        """Add a message to a chat"""
        try:
            chat = self.get_chat(chat_id)
            if not chat:
                logger.error(f"Chat {chat_id} not found")
                return False
            
            chat.add_message(message)
            return self.save_chat(chat)
            
        except Exception as e:
            logger.error(f"Error adding message to chat {chat_id}: {e}")
            return False
    
    def get_conversation_context(self, chat_id: str, limit: Optional[int] = None) -> str:
        """Get conversation context for a chat"""
        try:
            chat = self.get_chat(chat_id)
            if not chat:
                return ""
            
            return chat.get_conversation_summary()
            
        except Exception as e:
            logger.error(f"Error getting context for chat {chat_id}: {e}")
            return ""
    
    def health_check(self) -> bool:
        """Check Redis connection health"""
        try:
            if not self.redis_client:
                self.connect()
            
            if not self.redis_client:
                return False
            
            self.redis_client.ping()
            return True
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get Redis storage statistics"""
        try:
            if not self.redis_client:
                self.connect()
            
            if not self.redis_client:
                return {}
            
            info = self.redis_client.info()
            total_chats = self.redis_client.zcard(self.chat_list_key)
            
            if isinstance(info, dict):
                return {
                    "total_chats": total_chats,
                    "redis_version": info.get("redis_version", "unknown"),
                    "used_memory": info.get("used_memory_human", "unknown"),
                    "connected_clients": info.get("connected_clients", 0),
                    "uptime_in_seconds": info.get("uptime_in_seconds", 0)
                }
            else:
                return {
                    "total_chats": total_chats,
                    "redis_version": "unknown",
                    "used_memory": "unknown",
                    "connected_clients": 0,
                    "uptime_in_seconds": 0
                }
            
        except Exception as e:
            logger.error(f"Error getting Redis stats: {e}")
            return {}
