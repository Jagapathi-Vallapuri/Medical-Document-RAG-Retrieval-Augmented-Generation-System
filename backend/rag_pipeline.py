import os
import time
import json
import datetime
import requests
from typing import List, Dict, Optional, Tuple
from pymongo import MongoClient
import boto3
from botocore.exceptions import ClientError
from huggingface_hub import InferenceClient
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI
from fastapi import UploadFile

# Local imports
from rag_config import RAGConfig
from models import ContentType, ContextChunk, RetrievalResult, RAGResponse, S3Data
from utils import (
    save_log_to_file, 
    log_error_to_file, 
    clean_llm_response,
    format_tables_for_llm,
    generate_timestamp,
    extract_pdf_id_from_s3_key,
    normalize_s3_key
)
from logger_config import get_logger

# Set up logging
logger = get_logger(__name__)


class RAGPipeline:
    """Main RAG Pipeline class for document retrieval and generation"""
    
    def __init__(self, config: Optional[RAGConfig] = None):
        self.config = config or RAGConfig.from_env()
        self.config.validate()
        
        # Initialize MongoDB client
        self.mongo_client = MongoClient(self.config.mongo_uri)
        
        # Initialize S3 cache
        self.s3_data_cache: Dict[str, S3Data] = {}
        
        # Initialize LLM
        self._setup_llm()
        
        logger.info("RAG Pipeline initialized successfully")
    
    def _setup_llm(self) -> None:
        """Setup LLM with proper configuration"""
        prompt_template = """
You are a clinically informed medical AI assistant. Your task is to answer questions based on the provided context, which may include text, tables, and image captions from medical documents.

------------------ BEGIN CONTEXT ------------------
{context}
------------------- END CONTEXT -------------------

QUESTION: {question}

INSTRUCTIONS:
1.  Analyze the question and the provided context.
2.  If the context contains the answer, synthesize the information and provide a clear, concise answer.
3.  If the context does not contain the answer, use your general medical knowledge to respond.
4.  **Your final response should be direct and to the point. Do not include your reasoning, thought process, or self-reflection in the answer.**
5.  Format your answer using Markdown for clarity (e.g., headings, lists, bold text).
"""
        
        self.prompt = ChatPromptTemplate.from_template(prompt_template)
        
        # Set environment variables for LM Studio
        os.environ["OPENAI_API_KEY"] = "lm-studio"
        os.environ["OPENAI_API_BASE"] = self.config.openai_api_base
        
        self.llm = ChatOpenAI(
            model=self.config.llm_model,
            temperature=self.config.llm_temperature
        )
        
        self.chain = self.prompt | self.llm | StrOutputParser()

    def get_text_embedding(self, text: str) -> List[float]:
        """Get text embedding using HuggingFace API with retry logic"""
        client = InferenceClient(
            model=self.config.embedding_model,
            token=self.config.huggingface_key
        )
        
        for attempt in range(self.config.embedding_retries):
            try:
                embedding = client.feature_extraction(text=text)
                if hasattr(embedding, "tolist"):
                    return embedding.tolist()
                return embedding.tolist() if hasattr(embedding, 'tolist') else list(embedding)
            except Exception as e:
                error_msg = f"Embedding fetch failed (attempt {attempt+1}): {e}"
                logger.warning(error_msg)
                log_error_to_file(error_msg, error_type="embedding")
                
                if attempt < self.config.embedding_retries - 1:
                    time.sleep(self.config.embedding_delay)
        
        raise RuntimeError(
            f"Failed to fetch embedding after {self.config.embedding_retries} attempts"
        )

    def fetch_s3_data(self, pdf_id: str) -> S3Data:
        """Fetch tables and images metadata for a given PDF from S3"""
        if pdf_id in self.s3_data_cache:
            return self.s3_data_cache[pdf_id]
        
        s3 = boto3.client('s3')
        result = S3Data(tables=[], images=[])
        
        # Fetch tables
        tables_key = f"{self.config.s3_prefix}/{pdf_id}/tables.json"
        try:
            response = s3.get_object(Bucket=self.config.s3_bucket, Key=tables_key)
            tables_json = json.loads(response['Body'].read())
            if isinstance(tables_json, list):
                result.tables = tables_json
            else:
                result.tables = tables_json.get("tables", [])
        except ClientError as e:
            if e.response['Error']['Code'] != "NoSuchKey":
                error_msg = f"Could not fetch tables for {pdf_id}: {e}"
                logger.warning(error_msg)
                log_error_to_file(error_msg, error_type="s3")
        except Exception as e:
            error_msg = f"An error occurred fetching tables for {pdf_id}: {e}"
            logger.warning(error_msg)
            log_error_to_file(error_msg, error_type="s3")
        
        # Fetch images
        images_key = f"{self.config.s3_prefix}/{pdf_id}/images.json"
        try:
            response = s3.get_object(Bucket=self.config.s3_bucket, Key=images_key)
            images_json = json.loads(response['Body'].read())
            if isinstance(images_json, dict) and "images" in images_json:
                for image_data in images_json["images"]:
                    page_num = image_data.get("page_number", -1) 
                    caption = image_data.get("caption", "")
                    result.images.append([caption, page_num])
        except ClientError as e:
            if e.response['Error']['Code'] != "NoSuchKey":
                error_msg = f"Could not fetch images for {pdf_id}: {e}"
                logger.warning(error_msg)
                log_error_to_file(error_msg, error_type="s3")
        except Exception as e:
            error_msg = f"An error occurred fetching images for {pdf_id}: {e}"
            logger.warning(error_msg)
            log_error_to_file(error_msg, error_type="s3")
        
        # Cache the result
        self.s3_data_cache[pdf_id] = result
        return result

    def retrieve_context(
        self, 
        query: str, 
        limit: int = 5, 
        pdf_id: Optional[str] = None
    ) -> RetrievalResult:
        """Retrieve relevant context from MongoDB and enrich with S3 data"""
        db = self.mongo_client["vector_database"]
        query_embedding = self.get_text_embedding(query)
        
        # Search text embeddings
        text_pipeline = [
            {
                "$vectorSearch": {
                    "queryVector": query_embedding, 
                    "path": "embedding", 
                    "numCandidates": self.config.vector_search_candidates, 
                    "limit": limit, 
                    "index": "text_search"
                }
            }
        ]
        
        if pdf_id:
            text_pipeline.append({"$match": {"metadata.pdf_id": pdf_id}})
            
        text_pipeline.append({
            "$project": {
                "_id": 0, 
                "text": 1, 
                "pdf_id": "$metadata.pdf_id", 
                "page_start": "$metadata.page_start", 
                "score": {"$meta": "vectorSearchScore"}
            }
        })
        
        text_results = list(db["textEmbeddings"].aggregate(text_pipeline))
        text_results = [doc for doc in text_results if doc.get('score', 0) > self.config.score_threshold]
        
        # Search image embeddings
        image_pipeline = [
            {
                "$vectorSearch": {
                    "queryVector": query_embedding, 
                    "path": "embedding", 
                    "numCandidates": self.config.vector_search_candidates, 
                    "limit": limit, 
                    "index": "image_search"
                }
            }
        ]
        
        if pdf_id:
            image_pipeline.append({"$match": {"metadata.pdf_id": pdf_id}})
            
        image_pipeline.append({
            "$project": {
                "_id": 0, 
                "text": 1, 
                "pdf_id": "$metadata.pdf_id", 
                "page": "$metadata.page", 
                "score": {"$meta": "vectorSearchScore"}
            }
        })
        
        image_results = list(db["imageEmbeddings"].aggregate(image_pipeline))
        image_results = [img for img in image_results if img.get('score', 0) > self.config.score_threshold]
        
        # Build context chunks
        context_chunks = []
        
        # Process text results
        for doc in text_results:
            doc_pdf_id = doc.get("pdf_id")
            page = doc.get("page_start")
            
            # Fetch S3 data if needed
            s3_data = self.fetch_s3_data(doc_pdf_id) if doc_pdf_id else S3Data(tables=[], images=[])
            
            # Find tables for this page
            tables_for_chunk = [
                table for table in s3_data.tables 
                if table and table.get("page") == page
            ]
            
            chunk = ContextChunk(
                content_type=ContentType.TEXT,
                text=doc.get("text", ""),
                pdf_id=doc_pdf_id or "",
                page=page or 0,
                score=doc.get("score", 0.0),
                tables=tables_for_chunk
            )
            context_chunks.append(chunk)
        
        # Process image results
        for img_doc in image_results:
            chunk = ContextChunk(
                content_type=ContentType.IMAGE,
                text=img_doc.get("text", ""),
                pdf_id=img_doc.get("pdf_id", ""),
                page=img_doc.get("page", 0),
                score=img_doc.get("score", 0.0)
            )
            context_chunks.append(chunk)
        
        return RetrievalResult(
            context_chunks=context_chunks,
            raw_mongo_text=text_results,
            raw_mongo_images=image_results,
            s3_cache={k: v.__dict__ for k, v in self.s3_data_cache.items()}
        )

    def _fallback_retrieve(self, query: str, limit: int = 2) -> RetrievalResult:
        """Fallback retrieval without score threshold"""
        db = self.mongo_client["vector_database"]
        query_embedding = self.get_text_embedding(query)
        
        # Get top results regardless of score
        text_results = list(db["textEmbeddings"].aggregate([
            {
                "$vectorSearch": {
                    "queryVector": query_embedding, 
                    "path": "embedding", 
                    "numCandidates": self.config.vector_search_candidates, 
                    "limit": limit, 
                    "index": "text_search"
                }
            },
            {
                "$project": {
                    "_id": 0, 
                    "text": 1, 
                    "pdf_id": "$metadata.pdf_id", 
                    "page_start": "$metadata.page_start", 
                    "score": {"$meta": "vectorSearchScore"}
                }
            }
        ]))
        
        image_results = list(db["imageEmbeddings"].aggregate([
            {
                "$vectorSearch": {
                    "queryVector": query_embedding, 
                    "path": "embedding", 
                    "numCandidates": self.config.vector_search_candidates, 
                    "limit": limit, 
                    "index": "image_search"
                }
            },
            {
                "$project": {
                    "_id": 0, 
                    "text": 1, 
                    "pdf_id": "$metadata.pdf_id", 
                    "page": "$metadata.page", 
                    "score": {"$meta": "vectorSearchScore"}
                }
            }
        ]))
        
        # Build context chunks
        context_chunks = []
        
        for doc in text_results:
            doc_pdf_id = doc.get("pdf_id")
            page = doc.get("page_start")
            
            s3_data = self.fetch_s3_data(doc_pdf_id) if doc_pdf_id else S3Data(tables=[], images=[])
            tables_for_chunk = [
                table for table in s3_data.tables 
                if table and table.get("page") == page
            ]
            
            chunk = ContextChunk(
                content_type=ContentType.TEXT,
                text=doc.get("text", ""),
                pdf_id=doc_pdf_id or "",
                page=page or 0,
                score=doc.get("score", 0.0),
                tables=tables_for_chunk
            )
            context_chunks.append(chunk)
        
        for img_doc in image_results:
            chunk = ContextChunk(
                content_type=ContentType.IMAGE,
                text=img_doc.get("text", ""),
                pdf_id=img_doc.get("pdf_id", ""),
                page=img_doc.get("page", 0),
                score=img_doc.get("score", 0.0)
            )
            context_chunks.append(chunk)
        
        return RetrievalResult(
            context_chunks=context_chunks,
            raw_mongo_text=text_results,
            raw_mongo_images=image_results,
            s3_cache={k: v.__dict__ for k, v in self.s3_data_cache.items()}
        )

    def _build_context_string(
        self, 
        context_chunks: List[ContextChunk], 
        use_summarization: bool = False
    ) -> str:
        """Build context string from chunks"""
        context_parts = []
        
        # Limit to max chunks
        limited_chunks = context_chunks[:self.config.max_chunks]
        
        for chunk in limited_chunks:
            text = chunk.text
            if not text:
                continue

            
            context_str = f"Source: {chunk.pdf_id}, Page: {chunk.page}\nContent: {text}"
            
            # Add tables if available
            if chunk.tables:
                table_str = format_tables_for_llm(chunk.tables)
                if table_str:
                    context_str += f"\n\n--- Relevant Tables on this Page ---\n{table_str}\n---------------------------------"
            
            context_parts.append(context_str)
        
        return "\n\n---\n\n".join(context_parts)

    def generate_response(self, context: str, question: str) -> str:
        """Generate response using LLM"""
        logger.debug("About to call LM Studio with context")
        logger.info(f"Processing question: {question}")
        logger.debug(f"Using OPENAI_API_BASE: {self.config.openai_api_base}")
        
        raw_response = self.chain.invoke({"context": context, "question": question})
        return clean_llm_response(raw_response)

    def run(
        self, 
        question: str, 
        pdf_s3_key: str, 
        top_k: int = 3,
        use_summarization: bool = False,
        debug_log_dir: Optional[str] = None
    ) -> RAGResponse:
        """
        Main RAG pipeline execution
        
        Args:
            question: User's question
            pdf_s3_key: S3 key for the PDF (or filename)
            top_k: Number of top results to retrieve
            use_summarization: Whether to use text summarization
            debug_log_dir: Directory to save debug logs
            
        Returns:
            RAGResponse with the generated answer
        """
        timestamp = generate_timestamp()
        pdf_s3_key = normalize_s3_key(pdf_s3_key)
        pdf_id = extract_pdf_id_from_s3_key(pdf_s3_key)
        
        # Retrieve context
        retrieval_result = self.retrieve_context(question, limit=top_k, pdf_id=pdf_id)
        
        # Save debug logs if requested
        if debug_log_dir:
            save_log_to_file(debug_log_dir, f"{timestamp}_mongo_text_results", retrieval_result.raw_mongo_text)
            save_log_to_file(debug_log_dir, f"{timestamp}_mongo_image_results", retrieval_result.raw_mongo_images)
            save_log_to_file(debug_log_dir, f"{timestamp}_s3_cache", retrieval_result.s3_cache)
        
        # If no high-score content found, use fallback
        if not retrieval_result.has_content():
            logger.info("No high-score content found, using fallback retrieval")
            retrieval_result = self._fallback_retrieve(question, limit=2)
        
        # If still no content, return empty response
        if not retrieval_result.has_content():
            return RAGResponse(
                cleaned_response="No relevant information found.",
                raw_response="No relevant information found."
            )
        
        # Build context string
        context = self._build_context_string(retrieval_result.context_chunks, use_summarization)
        
        if not context:
            return RAGResponse(
                cleaned_response="No relevant information with content was found.",
                raw_response="No relevant information with content was found."
            )
        
        # Log context if debug mode
        if debug_log_dir:
            try:
                save_log_to_file(
                    debug_log_dir, 
                    f"{timestamp}_final_prompt_context", 
                    {
                        "context": context, 
                        "question": question, 
                        "context_chunks": [
                            {
                                "type": chunk.content_type.value,
                                "text": chunk.text,
                                "pdf_id": chunk.pdf_id,
                                "page": chunk.page,
                                "score": chunk.score
                            }
                            for chunk in retrieval_result.context_chunks
                        ]
                    }
                )
            except Exception as e:
                logger.error(f"Failed to log final prompt context: {e}")
        
        # Generate response
        cleaned_response = self.generate_response(context, question)
        
        # Save markdown response if debug mode
        markdown_filepath = None
        if debug_log_dir:
            md_path = os.path.join(debug_log_dir, f"{timestamp}_final_response.md")
            try:
                with open(md_path, 'w', encoding='utf-8') as f:
                    f.write(cleaned_response)
                logger.info(f"Final response saved to: {md_path}")
                markdown_filepath = md_path
            except Exception as e:
                logger.error(f"Failed to save Markdown response: {e}")
        
        return RAGResponse(
            cleaned_response=cleaned_response,
            raw_response=cleaned_response,  # Raw response is cleaned in generate_response
            markdown_filepath=markdown_filepath,
            context_used=retrieval_result.context_chunks
        )

    def upload_pdf_to_s3(self, file: UploadFile, s3_key: str) -> bool:
        """Upload PDF file to S3"""
        s3 = boto3.client('s3')
        try:
            file.file.seek(0)
            s3.upload_fileobj(
                file.file, 
                self.config.s3_bucket, 
                s3_key, 
                ExtraArgs={
                    'ContentType': 'application/pdf',
                    'ContentDisposition': 'inline'
                }
            )
            return True
        except Exception as e:
            error_msg = f"S3 upload failed: {e}"
            logger.error(error_msg)
            log_error_to_file(error_msg, error_type="s3_upload")
            return False

    def close(self):
        """Clean up resources"""
        if self.mongo_client:
            self.mongo_client.close()
            logger.info("MongoDB connection closed")

    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()


def run_rag(
    question: str, 
    pdf_filename_or_s3_key: str, 
    debug_log_dir: Optional[str] = None, 
    top_k: int = 3, 
    use_summarization: bool = False, 
    max_summary_length: int = 150
) -> dict:
    """
    Legacy wrapper for the RAG pipeline
    """
    pipeline = RAGPipeline()
    try:
        response = pipeline.run(
            question=question,
            pdf_s3_key=pdf_filename_or_s3_key,
            top_k=top_k,
            use_summarization=use_summarization,
            debug_log_dir=debug_log_dir
        )
        
        return {
            "cleaned_response": response.cleaned_response,
            "markdown_filepath": response.markdown_filepath,
            "raw_response": response.raw_response
        }
    finally:
        pipeline.close()
