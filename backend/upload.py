import boto3
import os
from pathlib import Path
from typing import Optional, List, Dict, Any
from botocore.exceptions import ClientError, NoCredentialsError
from dotenv import load_dotenv
from datetime import datetime
from logger_config import get_logger

# Load environment variables
load_dotenv()

# Set up logging
logger = get_logger(__name__)

BUCKET = "pdf-storage-for-rag-1" 
PDFS_FOLDER = "pdfs"

class PDFUploader:
    """
    A simple S3 uploader specifically designed for PDF files.
    """
    
    def __init__(self, aws_access_key_id: Optional[str] = None, 
                 aws_secret_access_key: Optional[str] = None, region_name: str = 'us-east-1'):
        """
        Initialize the PDF uploader.
        
        Args:
            aws_access_key_id: AWS access key (optional, can use env vars)
            aws_secret_access_key: AWS secret key (optional, can use env vars)
            region_name: AWS region name
        """
        self.bucket_name = BUCKET
        self.region_name = region_name
        
        # Initialize S3 client
        try:
            if aws_access_key_id and aws_secret_access_key:
                self.s3_client = boto3.client(
                    's3',
                    aws_access_key_id=aws_access_key_id,
                    aws_secret_access_key=aws_secret_access_key,
                    region_name=region_name
                )
            else:
                # Use environment variables or IAM role
                self.s3_client = boto3.client('s3', region_name=region_name)
                
        except NoCredentialsError:
            raise ValueError("AWS credentials not found. Please provide credentials or set environment variables.")
    
    def is_pdf_file(self, file_path: str) -> bool:
        """
        Check if the file is a PDF.
        
        Args:
            file_path: Path to the file
            
        Returns:
            bool: True if file is a PDF, False otherwise
        """
        return file_path.lower().endswith('.pdf')
    
    def upload_pdf(self, local_pdf_path: str, s3_key: Optional[str] = None, 
                   metadata: Optional[Dict[str, str]] = None) -> bool:
        """
        Upload a single PDF file to S3.
        
        Args:
            local_pdf_path: Path to the local PDF file
            s3_key: S3 object key (if None, uses filename)
            metadata: Additional metadata for the file
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Check if file exists
            if not os.path.exists(local_pdf_path):
                print(f"❌ PDF file not found: {local_pdf_path}")
                return False
            
            # Check if file is a PDF
            if not self.is_pdf_file(local_pdf_path):
                print(f"❌ File is not a PDF: {local_pdf_path}")
                return False
            
            # Always upload to /pdfs folder
            if s3_key is None:
                s3_key = os.path.join(PDFS_FOLDER, os.path.basename(local_pdf_path)).replace('\\', '/')
            else:
                s3_key = os.path.join(PDFS_FOLDER, s3_key).replace('\\', '/')
            
            # Prepare extra arguments for PDF
            extra_args: Dict[str, Any] = {
                'ContentType': 'application/pdf',
                'ContentDisposition': 'inline'  # Allow viewing in browser
            }
            if metadata:
                # Ensure all metadata keys and values are strings
                extra_args['Metadata'] = {str(k): str(v) for k, v in metadata.items()}
            
            # Upload the PDF
            logger.debug(f"Uploading PDF {local_pdf_path} to s3://{self.bucket_name}/{s3_key}")
            self.s3_client.upload_file(local_pdf_path, self.bucket_name, s3_key, ExtraArgs=extra_args)
            logger.info(f"Successfully uploaded PDF: {s3_key}")
            return True
            
        except ClientError as e:
            logger.error(f"AWS Error uploading PDF {local_pdf_path}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error uploading PDF {local_pdf_path}: {e}")
            return False
    
    def upload_pdf_directory(self, local_directory: str) -> Dict[str, Any]:
        """
        Upload all PDF files from a directory to S3.
        
        Args:
            local_directory: Path to the local directory containing PDFs
            
        Returns:
            Dict with upload results
        """
        if not os.path.exists(local_directory):
            print(f"❌ Directory not found: {local_directory}")
            return {"success": False, "uploaded": 0, "failed": 0, "skipped": 0}
        
        uploaded_count = 0
        failed_count = 0
        skipped_count = 0
        upload_results = []
        
        # Walk through directory and find PDF files
        for root, dirs, files in os.walk(local_directory):
            for file in files:
                local_file_path = os.path.join(root, file)
                
                # Skip non-PDF files
                if not self.is_pdf_file(local_file_path):
                    skipped_count += 1
                    continue
                
                # Generate S3 key
                relative_path = os.path.relpath(local_file_path, local_directory)
                s3_key = os.path.join(PDFS_FOLDER, relative_path).replace('\\', '/')
                
                # Upload PDF
                success = self.upload_pdf(local_file_path, s3_key)
                if success:
                    uploaded_count += 1
                else:
                    failed_count += 1
                
                upload_results.append({
                    "local_path": local_file_path,
                    "s3_key": s3_key,
                    "success": success
                })
        
        return {
            "success": failed_count == 0,
            "uploaded": uploaded_count,
            "failed": failed_count,
            "skipped": skipped_count,
            "results": upload_results
        }
    
    def list_pdfs(self, max_keys: int = 1000) -> List[Dict[str, Any]]:
        """
        List PDF files in the S3 bucket.
        
        Args:
            max_keys: Maximum number of keys to return
            
        Returns:
            List of PDF objects with metadata
        """
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=PDFS_FOLDER + '/',
                MaxKeys=max_keys
            )
            
            pdf_objects = []
            if 'Contents' in response:
                for obj in response['Contents']:
                    # Filter only PDF files
                    if obj['Key'].lower().endswith('.pdf'):
                        pdf_objects.append({
                            'key': obj['Key'],
                            'size': obj['Size'],
                            'last_modified': obj['LastModified'].isoformat(),
                            'etag': obj['ETag']
                        })
            
            return pdf_objects
            
        except ClientError as e:
            print(f"❌ Error listing PDF files: {e}")
            return []
    
    def delete_pdf(self, s3_key: str) -> bool:
        """
        Delete a PDF file from S3.
        
        Args:
            s3_key: S3 object key of the PDF to delete
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Always delete from /pdfs folder
            if not s3_key.lower().endswith('.pdf'):
                print(f"❌ File is not a PDF: {s3_key}")
                return False
            s3_key = os.path.join(PDFS_FOLDER, os.path.basename(s3_key)).replace('\\', '/')
            
            print(f"🗑️ Deleting PDF s3://{self.bucket_name}/{s3_key}")
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)
            print(f"✅ Successfully deleted PDF: {s3_key}")
            return True
            
        except ClientError as e:
            print(f"❌ Error deleting PDF {s3_key}: {e}")
            return False
    
    def upload_pdf_fileobj(self, fileobj, filename: str, metadata: Optional[Dict[str, str]] = None) -> bool:
        """
        Upload a PDF file-like object (e.g., from FastAPI UploadFile) directly to S3.
        
        Args:
            fileobj: File-like object (must support .read())
            filename: Name for the file in S3 (should end with .pdf)
            metadata: Optional metadata dict
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not filename.lower().endswith('.pdf'):
                print(f"❌ File is not a PDF: {filename}")
                return False
            s3_key = os.path.join(PDFS_FOLDER, filename).replace('\\', '/')
            extra_args: Dict[str, Any] = {
                'ContentType': 'application/pdf',
                'ContentDisposition': 'inline'
            }
            if metadata:
                extra_args['Metadata'] = metadata
            print(f"📤 Uploading PDF fileobj to s3://{self.bucket_name}/{s3_key}")
            self.s3_client.upload_fileobj(fileobj, self.bucket_name, s3_key, ExtraArgs=extra_args)
            print(f"✅ Successfully uploaded PDF: {s3_key}")
            return True
        except ClientError as e:
            print(f"❌ AWS Error uploading PDF fileobj: {e}")
            return False
        except Exception as e:
            print(f"❌ Unexpected error uploading PDF fileobj: {e}")
            return False


def main():
    """
    Main function for command-line usage.
    """
    import argparse
    
    parser = argparse.ArgumentParser(description='PDF S3 Upload Utility (fixed bucket and /pdfs folder)')
    parser.add_argument('--pdf', help='Single PDF file to upload')
    parser.add_argument('--directory', help='Directory containing PDFs to upload')
    parser.add_argument('--s3-key', help='S3 key for single PDF upload (filename only, will be placed in /pdfs)')
    parser.add_argument('--list', action='store_true', help='List PDF files in bucket')
    parser.add_argument('--delete', help='Delete a PDF by filename (will be deleted from /pdfs)')
    
    args = parser.parse_args()
    
    uploader = PDFUploader()

    if args.list:
        print(f"📋 Listing PDF files in bucket: {BUCKET}")
        pdf_objects = uploader.list_pdfs()
        if pdf_objects:
            for obj in pdf_objects:
                size_mb = obj['size'] / (1024 * 1024)
                print(f"  📄 {obj['key']} ({size_mb:.2f} MB, {obj['last_modified']})")
        else:
            print("  No PDF files found.")
    elif args.delete:
        uploader.delete_pdf(args.delete)
    elif args.pdf:
        uploader.upload_pdf(args.pdf, args.s3_key)
    elif args.directory:
        result = uploader.upload_pdf_directory(args.directory)
        print(f"📊 Upload complete: {result['uploaded']} PDFs uploaded, {result['failed']} failed, {result['skipped']} non-PDF files skipped")
    else:
        print("❌ Please specify --pdf, --directory, --list, or --delete")


if __name__ == "__main__":
    main()