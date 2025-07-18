"""
Chat management models for maintaining conversation history
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class MessageType(Enum):
    USER = "user"
    BOT = "bot"
    SYSTEM = "system"

@dataclass
class ChatMessage:
    """Individual message in a chat conversation"""
    id: str
    content: str
    message_type: MessageType
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "type": self.message_type.value,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata or {}
        }

@dataclass
class ChatSession:
    """A complete chat conversation"""
    chat_id: str
    title: str
    messages: List[ChatMessage] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    context_window: int = 2  # Number of recent messages to include in context
    
    def add_message(self, message: ChatMessage) -> None:
        """Add a message to the chat"""
        self.messages.append(message)
        self.updated_at = datetime.now()
    
    def get_recent_context(self, limit: Optional[int] = None) -> List[ChatMessage]:
        """Get recent messages for context"""
        context_limit = limit or self.context_window
        return self.messages[-context_limit:] if len(self.messages) > context_limit else self.messages
    
    def get_conversation_summary(self) -> str:
        """Generate a summary of the conversation for context"""
        if not self.messages:
            return ""
        
        recent_messages = self.get_recent_context()
        context_parts = []
        
        for msg in recent_messages:
            if msg.message_type == MessageType.USER:
                context_parts.append(f"User: {msg.content}")
            elif msg.message_type == MessageType.BOT:
                # Truncate long bot responses for context
                content = msg.content[:200] + "..." if len(msg.content) > 200 else msg.content
                context_parts.append(f"Assistant: {content}")
        
        return "\n".join(context_parts)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "chat_id": self.chat_id,
            "title": self.title,
            "message_count": len(self.messages),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "messages": [msg.to_dict() for msg in self.messages]
        }

@dataclass
class ChatManager:
    """Manages multiple chat sessions"""
    sessions: Dict[str, ChatSession] = field(default_factory=dict)
    
    def create_chat(self, title: str = "New Chat") -> str:
        """Create a new chat session"""
        chat_id = f"chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(self.sessions)}"
        self.sessions[chat_id] = ChatSession(
            chat_id=chat_id,
            title=title
        )
        return chat_id
    
    def get_chat(self, chat_id: str) -> Optional[ChatSession]:
        """Get a specific chat session"""
        return self.sessions.get(chat_id)
    
    def list_chats(self) -> List[Dict[str, Any]]:
        """List all chat sessions"""
        return [
            {
                "chat_id": chat.chat_id,
                "title": chat.title,
                "message_count": len(chat.messages),
                "updated_at": chat.updated_at.isoformat(),
                "last_message": chat.messages[-1].content[:100] + "..." if chat.messages else ""
            }
            for chat in sorted(self.sessions.values(), key=lambda x: x.updated_at, reverse=True)
        ]
    
    def delete_chat(self, chat_id: str) -> bool:
        """Delete a chat session"""
        if chat_id in self.sessions:
            del self.sessions[chat_id]
            return True
        return False
    
    def update_chat_title(self, chat_id: str, title: str) -> bool:
        """Update chat title"""
        if chat_id in self.sessions:
            self.sessions[chat_id].title = title
            self.sessions[chat_id].updated_at = datetime.now()
            return True
        return False
    
    def add_message(self, chat_id: str, message: ChatMessage) -> bool:
        """Add a message to a chat"""
        if chat_id in self.sessions:
            self.sessions[chat_id].add_message(message)
            return True
        return False
