"""
Utility functions for RAG pipeline
"""
import os
import json
import datetime
import re
import csv
from io import StringIO
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

def save_log_to_file(log_dir: str, file_prefix: str, content) -> None:
    """Save content to log file"""
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    file_path = os.path.join(log_dir, f"{file_prefix}.json")
    
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(content, f, indent=4, ensure_ascii=False)
        logger.info(f"Successfully saved log to {file_path}")
    except Exception as e:
        txt_path = os.path.join(log_dir, f"{file_prefix}.txt")
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(str(content))
        logger.warning(f"Could not save as JSON, saved as plain text to {txt_path}. Error: {e}")

def log_error_to_file(error_message: str, error_type: str = "general") -> None:
    """Log error message to file"""
    error_dir = os.path.join(os.path.dirname(__file__), "error_logs")
    if not os.path.exists(error_dir):
        os.makedirs(error_dir)
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = os.path.join(error_dir, f"{timestamp}_{error_type}_error.log")
    
    with open(file_path, 'a', encoding='utf-8') as f:
        f.write(f"[{datetime.datetime.now().isoformat()}] {error_message}\n")

def clean_llm_response(raw_response: str) -> str:
    """Remove thinking tags from LLM response"""
    pattern = re.compile(r"<think>.*?</think>", re.DOTALL)
    cleaned_response = re.sub(pattern, "", raw_response)
    return cleaned_response.strip()

def format_tables_for_llm(tables_data: List[Dict]) -> str:
    """Format table data as markdown for LLM consumption"""
    if not tables_data:
        return ""
    
    markdown_tables = []
    
    for i, table in enumerate(tables_data):
        csv_string = table.get("csv_string", "")
        if not csv_string:
            continue
        
        try:
            reader = csv.reader(StringIO(csv_string))
            rows = list(reader)
            
            if not rows:
                continue
            
            # Create markdown table
            header = " | ".join(rows[0])
            separator = " | ".join(["---"] * len(rows[0]))
            body = "\n".join([" | ".join(row) for row in rows[1:]])
            
            markdown_tables.append(f"Table {i+1}:\n{header}\n{separator}\n{body}")
        except Exception as e:
            logger.warning(f"Failed to format table {i+1}: {e}")
            continue
    
    return "\n\n".join(markdown_tables)

def generate_timestamp() -> str:
    """Generate timestamp string for file naming"""
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

def extract_pdf_id_from_s3_key(s3_key: str) -> str:
    """Extract PDF ID from S3 key"""
    return os.path.splitext(os.path.basename(s3_key))[0]

def normalize_s3_key(pdf_filename_or_s3_key: str) -> str:
    """Normalize filename to full S3 key"""
    if not ("/" in pdf_filename_or_s3_key or "\\" in pdf_filename_or_s3_key):
        return f"pdfs/{pdf_filename_or_s3_key}"
    return pdf_filename_or_s3_key
