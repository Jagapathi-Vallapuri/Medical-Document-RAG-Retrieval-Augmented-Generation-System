"""
Data models for RAG pipeline
"""
from dataclasses import dataclass
from typing import List, Dict, Optional, Any
from enum import Enum

class ContentType(Enum):
    """Types of content chunks"""
    TEXT = "text"
    IMAGE = "image"

@dataclass
class ContextChunk:
    """Individual context chunk from retrieval"""
    content_type: ContentType
    text: str
    pdf_id: str
    page: int
    score: float
    tables: Optional[List[Dict]] = None
    
    def __post_init__(self):
        if self.tables is None:
            self.tables = []

@dataclass
class RetrievalResult:
    """Result from document retrieval"""
    context_chunks: List[ContextChunk]
    raw_mongo_text: List[Dict]
    raw_mongo_images: List[Dict]
    s3_cache: Dict[str, Dict]
    
    def has_content(self) -> bool:
        """Check if retrieval found any content"""
        return len(self.context_chunks) > 0
    
    def get_high_score_chunks(self, threshold: float = 0.75) -> List[ContextChunk]:
        """Get chunks above score threshold"""
        return [chunk for chunk in self.context_chunks if chunk.score > threshold]

@dataclass
class RAGResponse:
    """Final response from RAG pipeline"""
    cleaned_response: str
    raw_response: str
    markdown_filepath: Optional[str] = None
    context_used: Optional[List[ContextChunk]] = None
    
    def __post_init__(self):
        if self.context_used is None:
            self.context_used = []

@dataclass
class S3Data:
    """Data retrieved from S3"""
    tables: List[Dict]
    images: List[List]  
    
    def __post_init__(self):
        if self.tables is None:
            self.tables = []
        if self.images is None:
            self.images = []

@dataclass
class DocumentSelectionResult:
    """Result from document selection process"""
    doc_id: str
    relevance_score: float
    rank: int
    preview_text: Optional[str] = None
    total_chunks: int = 0
    content_summary: Optional[Dict] = None

@dataclass
class QueryToDocResponse:
    """Response for query-to-document mapping"""
    status: str
    query: str
    total_documents_found: int
    documents_returned: int
    documents: List[DocumentSelectionResult]
    best_match: Optional[Dict] = None
    normalization_method: str = "sqrt"

@dataclass
class AutoQueryResponse:
    """Response for automatic document selection + QA"""
    status: str
    query: str
    selected_document: Optional[str] = None
    selection_score: Optional[float] = None
    answer: str = ""
    documents_considered: int = 0
    selection_method: str = "sqrt"
