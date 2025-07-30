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
from models import (
    ContentType, ContextChunk, RetrievalResult, RAGResponse, S3Data,
    DocumentSelectionResult, QueryToDocResponse, AutoQueryResponse
)
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
from redis_cache import redis_cache_get, redis_cache_set

logger = get_logger(__name__)


class RAGPipeline:
    """Main RAG Pipeline class for document retrieval and generation"""
    
    def __init__(self, config: Optional[RAGConfig] = None):
        self.config = config or RAGConfig.from_env()
        self.config.validate()
        
        self.mongo_client = MongoClient(self.config.mongo_uri)        
        self.s3_data_cache: Dict[str, S3Data] = {}
        
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
1. Analyze the question and the provided context carefully.
2. If the question contains conversation history or previous context, only use it if the current question directly relates to previous topics (contains pronouns like "it", "this", "that", follow-up words like "also", "additionally", or explicitly references earlier topics).
3. If the context contains the answer, synthesize the information and provide a clear, concise answer.
4. If the context does not contain the answer, use your general medical knowledge to respond.
5. Focus primarily on answering the current question - don't unnecessarily reference previous conversation unless it's directly relevant.
6. **Your final response should be direct and to the point. Do not include your reasoning, thought process, or self-reflection in the answer.**
7. Format your answer using Markdown for clarity (e.g., headings, lists, bold text).
"""
        
        self.prompt = ChatPromptTemplate.from_template(prompt_template)
        
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
        """Fetch tables and images metadata for a given PDF from S3, with Redis cache"""
        if pdf_id in self.s3_data_cache:
            return self.s3_data_cache[pdf_id]

        redis_key = f"s3data:{pdf_id}"
        cached = redis_cache_get(redis_key)
        if cached:
            tables = cached.get('tables', []) if isinstance(cached, dict) else []
            images = cached.get('images', []) if isinstance(cached, dict) else []
            result = S3Data(tables=tables, images=images)
            self.s3_data_cache[pdf_id] = result
            return result

        s3 = boto3.client('s3')
        result = S3Data(tables=[], images=[])

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

        self.s3_data_cache[pdf_id] = result
        redis_cache_set(redis_key, result, ex=3600)
        return result

    def retrieve_context(
        self,
        query: str,
        limit: int = 5,
        pdf_id: Optional[str] = None
    ) -> RetrievalResult:
        """Retrieve relevant context from MongoDB and enrich with S3 data, with Redis cache for Mongo results"""
        db = self.mongo_client["vector_database"]
        query_embedding = self.get_text_embedding(query)

        redis_key = f"mongo:context:{query}:{limit}:{pdf_id}"
        cached = redis_cache_get(redis_key)

        if cached and isinstance(cached, dict):
            context_chunks = []
            for chunk in cached.get("context_chunks", []):
                if chunk.get("content_type") == "text" or chunk.get("content_type") == ContentType.TEXT:
                    context_chunks.append(ContextChunk(
                        content_type=ContentType.TEXT,
                        text=chunk.get("text", ""),
                        pdf_id=chunk.get("pdf_id", ""),
                        page=chunk.get("page", 0),
                        score=chunk.get("score", 0.0),
                        tables=chunk.get("tables", [])
                    ))
                else:
                    context_chunks.append(ContextChunk(
                        content_type=ContentType.IMAGE,
                        text=chunk.get("text", ""),
                        pdf_id=chunk.get("pdf_id", ""),
                        page=chunk.get("page", 0),
                        score=chunk.get("score", 0.0),
                        tables=[]
                    ))
            return RetrievalResult(
                context_chunks=context_chunks,
                raw_mongo_text=cached.get("raw_mongo_text", []),
                raw_mongo_images=cached.get("raw_mongo_images", []),
                s3_cache=cached.get("s3_cache", {})
            )

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

        result = RetrievalResult(
            context_chunks=context_chunks,
            raw_mongo_text=text_results,
            raw_mongo_images=image_results,
            s3_cache={k: v.__dict__ for k, v in self.s3_data_cache.items()}
        )
        
        redis_cache_set(redis_key, {
            "context_chunks": [chunk.__dict__ for chunk in context_chunks],
            "raw_mongo_text": text_results,
            "raw_mongo_images": image_results,
            "s3_cache": {k: v.__dict__ for k, v in self.s3_data_cache.items()}
        }, ex=600)
        return result

    def find_top_documents_with_normalization(
        self, 
        query: str, 
        top_k_chunks: Optional[int] = None, 
        normalization: Optional[str] = None, 
        min_chunks: Optional[int] = None
    ) -> List[Tuple[str, float]]:
        """
        Find the most relevant documents with configurable normalization methods.
        
        Args:
            query: Search query string
            top_k_chunks: Number of chunks to retrieve per collection (default from config)
            normalization: Normalization method ('none', 'linear', 'sqrt', 'log') (default from config)
            min_chunks: Minimum number of chunks required for a document to be considered (default from config)
        
        Returns:
            List of tuples: (doc_id, normalized_score)
        """
        import math
        
        # Use config defaults if not provided
        if top_k_chunks is None:
            top_k_chunks = self.config.doc_selection_chunks
        if normalization is None:
            normalization = self.config.normalization_method
        if min_chunks is None:
            min_chunks = self.config.min_document_chunks
        
        db = self.mongo_client["vector_database"]
        query_embedding = self.get_text_embedding(query)

        all_results = []
        
        text_pipeline = [
            {
                "$vectorSearch": {
                    "queryVector": query_embedding, 
                    "path": "embedding", 
                    "numCandidates": top_k_chunks * 2, 
                    "limit": top_k_chunks, 
                    "index": "text_search"
                }
            },
            {
                "$project": {
                    "_id": 0, 
                    "doc_id": "$metadata.pdf_id", 
                    "score": {"$meta": "vectorSearchScore"}
                }
            }
        ]
        all_results.extend(list(db["textEmbeddings"].aggregate(text_pipeline)))

        # Search image embeddings
        image_pipeline = [
            {
                "$vectorSearch": {
                    "queryVector": query_embedding, 
                    "path": "embedding", 
                    "numCandidates": top_k_chunks * 2, 
                    "limit": top_k_chunks, 
                    "index": "image_search"
                }
            },
            {
                "$project": {
                    "_id": 0, 
                    "doc_id": "$metadata.pdf_id", 
                    "score": {"$meta": "vectorSearchScore"}
                }
            }
        ]
        all_results.extend(list(db["imageEmbeddings"].aggregate(image_pipeline)))
        
        logger.info(f"Stage 1: Found {len(all_results)} candidate chunks across all documents.")
        
        doc_scores = {}
        doc_chunk_counts = {}
        for result in all_results:
            doc_id = result.get("doc_id")
            score = result.get("score")
            if doc_id and score:
                doc_scores[doc_id] = doc_scores.get(doc_id, 0.0) + score
                doc_chunk_counts[doc_id] = doc_chunk_counts.get(doc_id, 0) + 1
        
        filtered_docs = {doc_id: score for doc_id, score in doc_scores.items() 
                        if doc_chunk_counts[doc_id] >= min_chunks}
        
        filtered_count = len(doc_scores) - len(filtered_docs)
        if filtered_count > 0:
            logger.info(f"Filtered out {filtered_count} documents with < {min_chunks} chunks")
        
        if not filtered_docs:
            logger.warning(f"No documents found with >= {min_chunks} chunks")
            return []

        logger.info(f"Applied '{normalization}' normalization to {len(filtered_docs)} documents.")
        
        normalized_scores = []
        for doc_id, total_score in filtered_docs.items():
            chunk_count = doc_chunk_counts[doc_id]
            
            if normalization == 'none':
                normalized_score = total_score
            elif normalization == 'linear':
                normalized_score = total_score / chunk_count
            elif normalization == 'sqrt':
                normalized_score = total_score / (chunk_count ** 0.5)
            elif normalization == 'log':
                normalized_score = total_score / math.log(chunk_count + 1)
            else:
                raise ValueError(f"Unknown normalization method: {normalization}")
            
            normalized_scores.append((doc_id, normalized_score))
        
        sorted_docs = sorted(normalized_scores, key=lambda x: x[1], reverse=True)
        
        logger.debug(f"Top 3 Documents with {normalization.upper()} Normalization:")
        for i, (doc_id, norm_score) in enumerate(sorted_docs[:3], 1):
            raw_score = doc_scores[doc_id]
            chunk_count = doc_chunk_counts[doc_id]
            logger.debug(f"{i}. {doc_id}: norm_score={norm_score:.4f} (raw={raw_score:.4f}, chunks={chunk_count})")
        
        return sorted_docs

    def get_most_relevant_documents(
        self, 
        query: str, 
        top_n: Optional[int] = None, 
        show_previews: bool = True,
        normalization: Optional[str] = None
    ) -> QueryToDocResponse:
        """
        Get ranked list of most relevant documents for a query.
        
        Args:
            query: The search query
            top_n: Number of top documents to return (default from config)
            show_previews: Whether to show content previews (default True)
            normalization: Normalization method to use (default from config)
        
        Returns:
            QueryToDocResponse with ranked documents
        """
        if top_n is None:
            top_n = self.config.max_documents_returned
        if normalization is None:
            normalization = self.config.normalization_method
            
        logger.info(f"Finding most relevant documents for query: '{query[:60]}{'...' if len(query) > 60 else ''}'")
        
        ranked_docs = self.find_top_documents_with_normalization(
            query, normalization=normalization
        )
        
        if not ranked_docs:
            return QueryToDocResponse(
                status="no_documents_found",
                query=query,
                total_documents_found=0,
                documents_returned=0,
                documents=[],
                normalization_method=normalization
            )
        
        top_docs = ranked_docs[:top_n] if len(ranked_docs) >= top_n else ranked_docs
        
        logger.info(f"TOP {len(top_docs)} DOCUMENTS selected from {len(ranked_docs)} total")
        
        document_results = []
        
        for i, (doc_id, score) in enumerate(top_docs, 1):
            logger.debug(f"{i}. {doc_id} (score: {score:.3f})")
            
            doc_info = DocumentSelectionResult(
                doc_id=doc_id,
                relevance_score=score,
                rank=i
            )
            
            if show_previews:
                try:
                    preview_chunks = self.retrieve_context(
                        query, limit=1, pdf_id=doc_id
                    )
                    
                    if preview_chunks.context_chunks and preview_chunks.context_chunks[0].text:
                        preview_text = preview_chunks.context_chunks[0].text
                        short_preview = preview_text[:200] + "..." if len(preview_text) > 200 else preview_text
                        
                        doc_info.preview_text = short_preview
                        doc_info.content_summary = {
                            "full_text": preview_text,
                            "page": preview_chunks.context_chunks[0].page,
                            "chunk_score": preview_chunks.context_chunks[0].score,
                            "content_type": preview_chunks.context_chunks[0].content_type.value
                        }
                except Exception as e:
                    logger.warning(f"Failed to get preview for {doc_id}: {e}")
                    doc_info.preview_text = None
            
            document_results.append(doc_info)
        
        best_match = None
        if top_docs:
            best_match = {
                "doc_id": top_docs[0][0],
                "score": top_docs[0][1]
            }
        
        return QueryToDocResponse(
            status="success",
            query=query,
            total_documents_found=len(ranked_docs),
            documents_returned=len(top_docs),
            documents=document_results,
            best_match=best_match,
            normalization_method=normalization
        )

    def ask_with_auto_selection(
        self, 
        query: str, 
        normalization: Optional[str] = None,
        top_k: int = 5
    ) -> AutoQueryResponse:
        """
        Automatically select the best document and generate an answer.
        
        Args:
            query: User's question
            normalization: Normalization method to use
            top_k: Number of chunks to retrieve from selected document (default: 5)
            
        Returns:
            AutoQueryResponse with document selection and answer
        """
        if normalization is None:
            normalization = self.config.normalization_method
            
        logger.info(f"Auto-selecting document and answering query: '{query[:60]}{'...' if len(query) > 60 else ''}'")
        
        # Get the best document
        doc_selection = self.get_most_relevant_documents(
            query, top_n=1, show_previews=False, normalization=normalization
        )
        
        if doc_selection.status != "success" or not doc_selection.documents:
            return AutoQueryResponse(
                status="no_documents_found",
                query=query,
                answer="No relevant documents found in the knowledge base.",
                documents_considered=doc_selection.total_documents_found,
                selection_method=normalization
            )
        
        best_doc = doc_selection.documents[0]
        selected_doc_id = best_doc.doc_id
        selection_score = best_doc.relevance_score
        
        logger.info(f"Selected document: {selected_doc_id} (score: {selection_score:.4f})")
        
        try:
            rag_response = self.run(
                question=query,
                pdf_s3_key=selected_doc_id,
                top_k=top_k,
                use_summarization=False
            )
            
            return AutoQueryResponse(
                status="success",
                query=query,
                selected_document=selected_doc_id,
                selection_score=selection_score,
                answer=rag_response.cleaned_response,
                documents_considered=doc_selection.total_documents_found,
                selection_method=normalization
            )
            
        except Exception as e:
            logger.error(f"Failed to generate answer: {e}")
            return AutoQueryResponse(
                status="generation_failed",
                query=query,
                selected_document=selected_doc_id,
                selection_score=selection_score,
                answer=f"Document selected successfully but failed to generate answer: {str(e)}",
                documents_considered=doc_selection.total_documents_found,
                selection_method=normalization
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
        
        limited_chunks = context_chunks[:self.config.max_chunks]
        
        for chunk in limited_chunks:
            text = chunk.text
            if not text:
                continue

            
            context_str = f"Source: {chunk.pdf_id}, Page: {chunk.page}\nContent: {text}"
            
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
        
        if not retrieval_result.has_content():
            logger.info("No high-score content found, using fallback retrieval")
            retrieval_result = self._fallback_retrieve(question, limit=2)
        
        if not retrieval_result.has_content():
            return RAGResponse(
                cleaned_response="No relevant information found.",
                raw_response="No relevant information found."
            )
        
        context = self._build_context_string(retrieval_result.context_chunks, use_summarization)
        
        if not context:
            return RAGResponse(
                cleaned_response="No relevant information with content was found.",
                raw_response="No relevant information with content was found."
            )
        
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
            raw_response=cleaned_response,  
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
