"""
Configuration management for RAG pipeline
"""
import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv
import yaml

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
    def from_yaml_and_env(cls, yaml_path: str = "config.yaml", env_path: str = ".env") -> 'RAGConfig':
        """
        Load secrets from .env and other config from YAML. Environment variables take precedence for secrets.
        """
        # Load .env for secrets
        load_dotenv(env_path)
        # Load YAML for other config
        if not os.path.exists(yaml_path):
            raise FileNotFoundError(f"Config file '{yaml_path}' not found.")
        with open(yaml_path, "r") as f:
            config = yaml.safe_load(f)

        # Secrets from env
        huggingface_key = os.getenv("HUGGINGFACE_API_KEY")
        mongo_uri = os.getenv("MONGO_URI")
        openai_api_base = os.getenv("OPENAI_API_BASE")
        if not huggingface_key or not mongo_uri or not openai_api_base:
            raise ValueError("Missing required secrets in .env: HUGGINGFACE_API_KEY, MONGO_URI, OPENAI_API_BASE")

        return cls(
            huggingface_key=huggingface_key,
            mongo_uri=mongo_uri,
            openai_api_base=openai_api_base,
            embedding_model=config.get("embedding_model", "NeuML/pubmedbert-base-embeddings"),
            llm_model=config.get("llm_model", "ii-medical-8b-1706@q4_k_m"),
            summarization_model=config.get("summarization_model", "facebook/bart-large-cnn"),
            s3_bucket=config.get("s3_bucket", "pdf-storage-for-rag-1"),
            s3_prefix=config.get("s3_prefix", "extracted_data"),
            score_threshold=float(config.get("score_threshold", 0.75)),
            max_chunks=int(config.get("max_chunks", 5)),
            vector_search_candidates=int(config.get("vector_search_candidates", 100)),
            doc_selection_chunks=int(config.get("doc_selection_chunks", 30)),
            normalization_method=config.get("normalization_method", "sqrt"),
            min_document_chunks=int(config.get("min_document_chunks", 2)),
            max_documents_returned=int(config.get("max_documents_returned", 5)),
            max_summary_length=int(config.get("max_summary_length", 150)),
            min_summary_length=int(config.get("min_summary_length", 50)),
            llm_temperature=float(config.get("llm_temperature", 0.5)),
            embedding_retries=int(config.get("embedding_retries", 3)),
            embedding_delay=int(config.get("embedding_delay", 5)),
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
