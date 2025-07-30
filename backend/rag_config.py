"""
Configuration management for RAG pipeline
"""
import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

@dataclass
class RAGConfig:
    """Configuration settings for RAG pipeline"""
    
    # API Keys and endpoints
    huggingface_key: str
    mongo_uri: str
    openai_api_base: str
    
    # Model configurations
    embedding_model: str = "NeuML/pubmedbert-base-embeddings"
    llm_model: str = "ii-medical-8b-1706@q4_k_m"
    summarization_model: str = "facebook/bart-large-cnn"
    
    # S3 Configuration
    s3_bucket: str = "pdf-storage-for-rag-1"
    s3_prefix: str = "extracted_data"
    
    # Pipeline parameters
    score_threshold: float = 0.75
    max_chunks: int = 1
    vector_search_candidates: int = 100

    # Document selection parameters
    doc_selection_chunks: int = 30
    normalization_method: str = "sqrt"
    min_document_chunks: int = 2
    max_documents_returned: int = 5
    
    # Summarization parameters
    max_summary_length: int = 150
    min_summary_length: int = 50
    
    # LLM parameters
    llm_temperature: float = 0.5
    
    # Retry settings
    embedding_retries: int = 3
    embedding_delay: int = 5
    
    @classmethod
    def from_env(cls) -> 'RAGConfig':
        """Load configuration from environment variables"""
        load_dotenv()
        
        huggingface_key = os.getenv("HUGGINGFACE_API_KEY")
        mongo_uri = os.getenv("MONGO_URI")
        openai_api_base = os.getenv("OPENAI_API_BASE")
        
        if huggingface_key is None or mongo_uri is None or openai_api_base is None:
            raise ValueError(
                "Missing required environment variables: "
                "HUGGINGFACE_API_KEY, MONGO_URI, OPENAI_API_BASE"
            )
        
        return cls(
            huggingface_key=huggingface_key,
            mongo_uri=mongo_uri,
            openai_api_base=openai_api_base,
            s3_bucket=os.getenv("BUCKET", "pdf-storage-for-rag-1"),
            embedding_model=os.getenv("EMBEDDING_MODEL", "NeuML/pubmedbert-base-embeddings"),
            llm_model=os.getenv("LLM_MODEL", "ii-medical-8b-1706@q4_k_m"),
            score_threshold=float(os.getenv("SCORE_THRESHOLD", "0.75")),
            max_chunks=int(os.getenv("MAX_CHUNKS", "5")),
            doc_selection_chunks=int(os.getenv("DOC_SELECTION_CHUNKS", "30")),
            normalization_method=os.getenv("NORMALIZATION_METHOD", "sqrt"),
            min_document_chunks=int(os.getenv("MIN_DOCUMENT_CHUNKS", "2")),
            max_documents_returned=int(os.getenv("MAX_DOCUMENTS_RETURNED", "5")),
        )
    
    def validate(self) -> None:
        """Validate configuration values"""
        if self.score_threshold < 0 or self.score_threshold > 1:
            raise ValueError("score_threshold must be between 0 and 1")
        
        if self.max_chunks < 1:
            raise ValueError("max_chunks must be at least 1")
        
        if self.embedding_retries < 1:
            raise ValueError("embedding_retries must be at least 1")
        
        if self.normalization_method not in ['none', 'linear', 'sqrt', 'log']:
            raise ValueError("normalization_method must be one of: none, linear, sqrt, log")
        
        if self.min_document_chunks < 1:
            raise ValueError("min_document_chunks must be at least 1")
        
        if self.max_documents_returned < 1:
            raise ValueError("max_documents_returned must be at least 1")
