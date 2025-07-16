import os
import time
import json
import datetime
import requests
import re
import csv
from io import StringIO
from dotenv import load_dotenv
from pymongo import MongoClient
import boto3
from botocore.exceptions import ClientError
from huggingface_hub import InferenceClient
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI
from fastapi import UploadFile
from logger_config import get_logger

# Set up logging
logger = get_logger(__name__)

# Load environment variables
load_dotenv()
huggingface_key = os.getenv("HUGGINGFACE_API_KEY")
MONGO_URI = os.getenv("MONGO_URI")
openai_api_base = os.getenv("OPENAI_API_BASE")
logger.debug(f"OPENAI_API_BASE from environment: {os.environ.get('OPENAI_API_BASE')}")
logger.debug(f"Loaded openai_api_base: {openai_api_base}")

if not all([huggingface_key, MONGO_URI, openai_api_base]):
    raise ValueError("One or more environment variables (HUGGINGFACE_API_KEY, MONGO_URI, OPENAI_API_BASE) are not set.")

prompt_template = """
You are a clinically informed medical AI assistant. Your task is to intelligently determine whether to use the provided document context or rely on your general medical knowledge.

------------------ BEGIN CONTEXT ------------------
{context}
------------------- END CONTEXT -------------------

If provided, also consider:
- **Tables**: These may contain clinical trial results, numerical data, or lab values.
- **Images**: These include figure captions or descriptive labels that may support the interpretation of clinical findings.

QUESTION:
{question}

INSTRUCTION:
Analyze the question and respond appropriately:

1. **For simple, general medical questions** (basic definitions, common knowledge, general concepts):
   - Answer directly using your medical knowledge
   - Do NOT force the use of document context if it's not relevant
   - Example: "What is diabetes?" → Answer directly without referencing documents

2. **For specific, document-related questions** (asking about specific studies, data, findings in the documents):
   - Use the provided context as your primary source
   - Reference specific information from the documents
   - Example: "What were the results of the clinical trial mentioned?" → Use document context

3. **For complex questions that could benefit from document support**:
   - Combine your general knowledge with relevant document information
   - Clearly distinguish between general medical knowledge and document-specific information

Always provide accurate, helpful responses. If the question is simple and doesn't require document context, don't force it. If the question specifically asks about document content or would benefit from document evidence, use the context appropriately.
"""
prompt = ChatPromptTemplate.from_template(prompt_template)

# Set environment variables for OpenAI API key and base
os.environ["OPENAI_API_KEY"] = "lm-studio"
if not openai_api_base or not isinstance(openai_api_base, str):
    raise ValueError("OPENAI_API_BASE environment variable is not set or is not a string.")
os.environ["OPENAI_API_BASE"] = openai_api_base

llm = ChatOpenAI(
    model="ii-medical-8b-1706",
    temperature=0.5
)

def get_text_embedding(text, retries=3, delay=5):
    hf_token = huggingface_key  
    client = InferenceClient(model="NeuML/pubmedbert-base-embeddings",token=hf_token)
    for attempt in range(retries):
        try:
            embedding = client.feature_extraction(
                text=text,
            )
            return embedding
        except Exception as e:
            error_msg = f"Embedding fetch failed (attempt {attempt+1}): {e}"
            print(error_msg)
            log_error_to_file(error_msg, error_type="embedding")
            if attempt < retries - 1:
                time.sleep(delay)
    raise RuntimeError("Failed to fetch embedding after multiple attempts.")

def fetch_data_from_s3(pdf_id, bucket_name, s3_prefix="extracted_data"):
    s3 = boto3.client('s3')
    result = {"tables": [], "images": []}
    tables_key = f"{s3_prefix}/{pdf_id}/tables.json"
    try:
        response = s3.get_object(Bucket=bucket_name, Key=tables_key)
        tables_json = json.loads(response['Body'].read())
        if isinstance(tables_json, list):
            result["tables"] = tables_json
        else:
            result["tables"] = tables_json.get("tables", [])
    except ClientError as e:
        if e.response['Error']['Code'] != "404":
            error_msg = f"Could not fetch tables for {pdf_id}: {e}"
            print(error_msg)
            log_error_to_file(error_msg, error_type="s3")
    except Exception as e:
        error_msg = f"An error occurred fetching tables for {pdf_id}: {e}"
        print(error_msg)
        log_error_to_file(error_msg, error_type="s3")
    images_key = f"{s3_prefix}/{pdf_id}/images.json"
    try:
        response = s3.get_object(Bucket=bucket_name, Key=images_key)
        images_json = json.loads(response['Body'].read())
        if isinstance(images_json, dict) and "images" in images_json:
            for image_data in images_json["images"]:
                page_num = image_data.get("page_number", -1) 
                caption = image_data.get("caption", "")
                img_info = [caption, page_num]
                result["images"].append(img_info)
    except ClientError as e:
        if e.response['Error']['Code'] != "404":
            error_msg = f"Could not fetch images for {pdf_id}: {e}"
            print(error_msg)
            log_error_to_file(error_msg, error_type="s3")
    except Exception as e:
        error_msg = f"An error occurred fetching images for {pdf_id}: {e}"
        print(error_msg)
        log_error_to_file(error_msg, error_type="s3")
    return result

# Persistent S3 data cache for all PDFs
s3_data_cache = {}

def retrieve(mongo_client, query, limit=5, s3_bucket=None, s3_prefix="extracted_data", pdf_id=None):
    db = mongo_client["vector_database"]
    text_collection = db["textEmbeddings"]
    query_embedding = get_text_embedding(query)
    if hasattr(query_embedding, "tolist"):
        query_embedding = query_embedding.tolist()
    text_pipeline = [
        {"$vectorSearch": {"queryVector": query_embedding, "path": "embedding", "numCandidates": 100, "limit": limit, "index": "text_search"}}
    ]
    if pdf_id:
        text_pipeline.append({"$match": {"pdf_id": pdf_id}})
    text_pipeline.append({"$project": {"_id": 0, "text": 1, "pdf_id": "$metadata.pdf_id", "page_start": "$metadata.page_start", "score": {"$meta": "vectorSearchScore"}}})
    text_results = list(text_collection.aggregate(text_pipeline))
    # Filter texts by score > 0.75
    text_results = [doc for doc in text_results if doc.get('score', 0) > 0.75]
    image_collection = db["imageEmbeddings"]
    image_pipeline = [
        {"$vectorSearch": {"queryVector": query_embedding, "path": "embedding", "numCandidates": 100, "limit": limit, "index": "image_search"}}
    ]
    if pdf_id:
        image_pipeline.append({"$match": {"pdf_id": pdf_id}})
    image_pipeline.append({"$project": {"_id": 0, "text": 1, "pdf_id": "$metadata.pdf_id", "page": "$metadata.page", "score": {"$meta": "vectorSearchScore"}}})
    image_results = list(image_collection.aggregate(image_pipeline))
    # Filter images by score > 0.75
    image_results = [img for img in image_results if img.get('score', 0) > 0.75]
    context_chunks = []
    global s3_data_cache
    if text_results:
        for doc in text_results:
            doc_pdf_id = doc.get("pdf_id")
            page = doc.get("page_start")
            if s3_bucket and doc_pdf_id and doc_pdf_id not in s3_data_cache:
                s3_data_cache[doc_pdf_id] = fetch_data_from_s3(doc_pdf_id, s3_bucket, s3_prefix)
            tables_for_chunk = []
            if doc_pdf_id in s3_data_cache:
                s3_data = s3_data_cache[doc_pdf_id]
                all_tables = s3_data.get("tables", [])
                tables_for_chunk = [
                    table for table in all_tables if table and table.get("page") == page
                ]
            chunk = {
                "type": "text", "text": doc.get("text"), "pdf_id": doc_pdf_id,
                "score": doc.get("score"), "page": page, "tables": tables_for_chunk,
            }
            context_chunks.append(chunk)
    for img_doc in image_results:
        context_chunks.append({
            "type": "image", "text": img_doc.get("text"), "pdf_id": img_doc.get("pdf_id"),
            "page": img_doc.get("page"), "score": img_doc.get("score")
        })
    return {
        "context_chunks": context_chunks,
        "raw_mongo_text": text_results,
        "raw_mongo_images": image_results,
        "s3_cache": s3_data_cache
    }

def save_log_to_file(log_dir, file_prefix, content):
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    file_path = os.path.join(log_dir, f"{file_prefix}.json")
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(content, f, indent=4, ensure_ascii=False)
        print(f"Successfully saved log to {file_path}")
    except Exception as e:
        txt_path = os.path.join(log_dir, f"{file_prefix}.txt")
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(str(content))
        print(f"Could not save as JSON, saved as plain text to {txt_path}. Error: {e}")

def summarize_with_hf(text, hf_token, max_length=150, min_length=50):
    API_URL = "https://api-inference.huggingface.co/models/facebook/bart-large-cnn"
    headers = {"Authorization": f"Bearer {hf_token}"}
    payload = {
        "inputs": text,
        "parameters": {
            "max_length": max_length,
            "min_length": min_length,
            "do_sample": False
        }
    }
    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=20)
        response.raise_for_status()
        result = response.json()
        if isinstance(result, list) and len(result) > 0:
            return result[0].get('summary_text', text)
        return text
    except requests.exceptions.RequestException as e:
        error_msg = f"Summarization request failed: {e}"
        print(error_msg)
        log_error_to_file(error_msg, error_type="summarization")
        return text 

def clean_llm_response(raw_response: str) -> str:
    pattern = re.compile(r"<think>.*?</think>", re.DOTALL)
    cleaned_response = re.sub(pattern, "", raw_response)
    return cleaned_response.strip()

def format_tables_for_llm(tables_data):
    markdown_tables = []
    for i, table in enumerate(tables_data):
        csv_string = table.get("csv_string", "")
        if not csv_string:
            continue
        reader = csv.reader(StringIO(csv_string))
        rows = list(reader)
        if not rows:
            continue
        header = " | ".join(rows[0])
        separator = " | ".join(["---"] * len(rows[0]))
        body = "\n".join([" | ".join(row) for row in rows[1:]])
        markdown_tables.append(f"Table {i+1}:\n{header}\n{separator}\n{body}")
    return "\n\n".join(markdown_tables)

def run_rag_pipeline(question: str, pdf_s3_key: str, top_k=3, use_summarization=False, max_summary_length=150, debug_log_dir=None) -> dict:
    client = MongoClient(MONGO_URI)
    chain = prompt | llm | StrOutputParser()
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    pdf_id = os.path.splitext(os.path.basename(pdf_s3_key))[0]
    retrieval_data = retrieve(client, question, top_k, s3_bucket=os.getenv("BUCKET", "pdf-storage-for-rag-1"), s3_prefix="extracted_data", pdf_id=pdf_id)
    context_chunks = retrieval_data["context_chunks"]
    if debug_log_dir:
        save_log_to_file(debug_log_dir, f"{timestamp}_mongo_text_results", retrieval_data["raw_mongo_text"])
        save_log_to_file(debug_log_dir, f"{timestamp}_mongo_image_results", retrieval_data["raw_mongo_images"])
        save_log_to_file(debug_log_dir, f"{timestamp}_s3_cache", retrieval_data["s3_cache"])
    # If no relevant chunks, use top 3 chunks regardless of score
    if not context_chunks:
        # Fetch top 3 text and image results without score filtering
        embedding = get_text_embedding(question)
        if hasattr(embedding, "tolist"):
            embedding = embedding.tolist()
        text_results_raw = list(client["vector_database"]["textEmbeddings"].aggregate([
            {"$vectorSearch": {"queryVector": embedding, "path": "embedding", "numCandidates": 100, "limit": 3, "index": "text_search"}},
            {"$project": {"_id": 0, "text": 1, "pdf_id": "$metadata.pdf_id", "page_start": "$metadata.page_start", "score": {"$meta": "vectorSearchScore"}}}
        ]))
        image_results_raw = list(client["vector_database"]["imageEmbeddings"].aggregate([
            {"$vectorSearch": {"queryVector": embedding, "path": "embedding", "numCandidates": 100, "limit": 3, "index": "image_search"}},
            {"$project": {"_id": 0, "text": 1, "pdf_id": "$metadata.pdf_id", "page": "$metadata.page", "score": {"$meta": "vectorSearchScore"}}}
        ]))
        context_chunks = []
        for doc in text_results_raw:
            doc_pdf_id = doc.get("pdf_id")
            page = doc.get("page_start")
            if os.getenv("BUCKET", "pdf-storage-for-rag-1") and doc_pdf_id and doc_pdf_id not in s3_data_cache:
                s3_data_cache[doc_pdf_id] = fetch_data_from_s3(doc_pdf_id, os.getenv("BUCKET", "pdf-storage-for-rag-1"), "extracted_data")
            tables_for_chunk = []
            if doc_pdf_id in s3_data_cache:
                s3_data = s3_data_cache[doc_pdf_id]
                all_tables = s3_data.get("tables", [])
                tables_for_chunk = [table for table in all_tables if table and table.get("page") == page]
            chunk = {
                "type": "text", "text": doc.get("text"), "pdf_id": doc_pdf_id,
                "score": doc.get("score"), "page": page, "tables": tables_for_chunk,
            }
            context_chunks.append(chunk)
        for img_doc in image_results_raw:
            context_chunks.append({
                "type": "image", "text": img_doc.get("text"), "pdf_id": img_doc.get("pdf_id"),
                "page": img_doc.get("page"), "score": img_doc.get("score")
            })
        # If still no context, return as before
        if not context_chunks:
            return {"cleaned_response": "No relevant information found.", "markdown_filepath": None, "raw_response": ""}
    context_parts = []
    for chunk in context_chunks: 
        text = chunk.get("text")
        if not text:
            continue
        if use_summarization and chunk["type"] == "text" and len(text) > 500:
            text = summarize_with_hf(text, huggingface_key, max_summary_length)
        context_str = f"Source: {chunk.get('pdf_id')}, Page: {chunk.get('page')}\nContent: {text}"
        if chunk.get("tables"):
            table_str = format_tables_for_llm(chunk["tables"])
            if table_str:
                context_str += f"\n\n--- Relevant Tables on this Page ---\n{table_str}\n---------------------------------"
        context_parts.append(context_str)
    MAX_CHUNKS = 2
    context_parts = context_parts[:MAX_CHUNKS]
    if not context_parts:
        return {"cleaned_response": "No relevant information with content was found.", "markdown_filepath": None, "raw_response": ""}
    context = "\n\n---\n\n".join(context_parts)
    logger.debug("About to call LM Studio with context:")
    logger.debug(f"Context: {context}")
    logger.info(f"Processing question: {question}")
    logger.debug(f"Using OPENAI_API_BASE: {openai_api_base}")
    if debug_log_dir:
        try:
            save_log_to_file(debug_log_dir, f"{timestamp}_final_prompt_context", {"context": context, "question": question, "context_parts": context_parts})
        except Exception as e:
            logger.error(f"Failed to log final prompt context: {e}")
    raw_response = chain.invoke({"context": context, "question": question})
    cleaned_response = clean_llm_response(raw_response)
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
    return {
        "cleaned_response": cleaned_response,
        "markdown_filepath": markdown_filepath,
        "raw_response": raw_response  
    }

def upload_pdf_to_s3(file: UploadFile, bucket: str, s3_key: str) -> bool:
    s3 = boto3.client('s3')
    try:
        file.file.seek(0)  # Ensure pointer is at start
        s3.upload_fileobj(file.file, bucket, s3_key, ExtraArgs={
            'ContentType': 'application/pdf',
            'ContentDisposition': 'inline'
        })
        return True
    except Exception as e:
        error_msg = f"S3 upload failed: {e}"
        print(error_msg)
        log_error_to_file(error_msg, error_type="s3_upload")
        return False

def log_error_to_file(error_message, error_type="general"):
    error_dir = os.path.join(os.path.dirname(__file__), "error_logs")
    if not os.path.exists(error_dir):
        os.makedirs(error_dir)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = os.path.join(error_dir, f"{timestamp}_{error_type}_error.log")
    with open(file_path, 'a', encoding='utf-8') as f:
        f.write(error_message + "\n")

def run_rag(question: str, pdf_filename_or_s3_key: str, debug_log_dir=None, top_k=3, use_summarization=False, max_summary_length=150) -> dict:
    """
    Unified RAG pipeline entry point. Accepts either a PDF filename (assumed to be in /pdfs) or a full S3 key.
    Args:
        question: The user's question
        pdf_filename_or_s3_key: The PDF filename (e.g. myfile.pdf) or S3 key (e.g. pdfs/myfile.pdf)
        debug_log_dir: Optional directory to save debug logs
        top_k: Number of top results to retrieve
        use_summarization: Whether to summarize long context chunks
        max_summary_length: Max length for summarization
    Returns:
        dict with at least a 'cleaned_response' key
    """
    # If the input is just a filename, prepend 'pdfs/'
    if not ("/" in pdf_filename_or_s3_key or "\\" in pdf_filename_or_s3_key):
        pdf_s3_key = f"pdfs/{pdf_filename_or_s3_key}"
    else:
        pdf_s3_key = pdf_filename_or_s3_key
    return run_rag_pipeline(question, pdf_s3_key, top_k=top_k, use_summarization=use_summarization, max_summary_length=max_summary_length, debug_log_dir=debug_log_dir)
