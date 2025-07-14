"""
Firebase Storage services
"""
from typing import Optional, Dict, Any
from firebase_admin import storage
import mimetypes
import os
from ..core.logging import logger, log_error


class StorageService:
    """Firebase Storage service for file operations"""
    
    def __init__(self, bucket_name: str = None):
        self.bucket = storage.bucket(bucket_name)
    
    def upload_file(self, local_path: str, storage_path: str, 
                   metadata: Optional[Dict[str, Any]] = None) -> str:
        """Upload a file to Firebase Storage"""
        try:
            blob = self.bucket.blob(storage_path)
            
            # Set content type
            content_type, _ = mimetypes.guess_type(local_path)
            if content_type:
                blob.content_type = content_type
            
            # Set metadata
            if metadata:
                blob.metadata = metadata
            
            # Upload file
            blob.upload_from_filename(local_path)
            
            logger.info("File uploaded successfully",
                       local_path=local_path,
                       storage_path=storage_path,
                       size=os.path.getsize(local_path))
            
            return blob.public_url
            
        except Exception as e:
            log_error(e, context="upload_file", 
                     local_path=local_path, storage_path=storage_path)
            raise
    
    def upload_from_string(self, content: str, storage_path: str,
                          content_type: str = "text/plain",
                          metadata: Optional[Dict[str, Any]] = None) -> str:
        """Upload string content to Firebase Storage"""
        try:
            blob = self.bucket.blob(storage_path)
            blob.content_type = content_type
            
            if metadata:
                blob.metadata = metadata
            
            blob.upload_from_string(content)
            
            logger.info("Content uploaded successfully",
                       storage_path=storage_path,
                       content_length=len(content))
            
            return blob.public_url
            
        except Exception as e:
            log_error(e, context="upload_from_string", storage_path=storage_path)
            raise
    
    def download_file(self, storage_path: str, local_path: str) -> bool:
        """Download a file from Firebase Storage"""
        try:
            blob = self.bucket.blob(storage_path)
            blob.download_to_filename(local_path)
            
            logger.info("File downloaded successfully",
                       storage_path=storage_path,
                       local_path=local_path)
            
            return True
            
        except Exception as e:
            log_error(e, context="download_file",
                     storage_path=storage_path, local_path=local_path)
            raise
    
    def download_as_string(self, storage_path: str) -> str:
        """Download file content as string"""
        try:
            blob = self.bucket.blob(storage_path)
            content = blob.download_as_text()
            
            logger.info("Content downloaded successfully",
                       storage_path=storage_path,
                       content_length=len(content))
            
            return content
            
        except Exception as e:
            log_error(e, context="download_as_string", storage_path=storage_path)
            raise
    
    def delete_file(self, storage_path: str) -> bool:
        """Delete a file from Firebase Storage"""
        try:
            blob = self.bucket.blob(storage_path)
            blob.delete()
            
            logger.info("File deleted successfully", storage_path=storage_path)
            return True
            
        except Exception as e:
            log_error(e, context="delete_file", storage_path=storage_path)
            raise
    
    def get_file_metadata(self, storage_path: str) -> Optional[Dict[str, Any]]:
        """Get file metadata"""
        try:
            blob = self.bucket.blob(storage_path)
            blob.reload()
            
            if blob.exists():
                return {
                    "name": blob.name,
                    "size": blob.size,
                    "content_type": blob.content_type,
                    "created": blob.time_created.isoformat() if blob.time_created else None,
                    "updated": blob.updated.isoformat() if blob.updated else None,
                    "md5_hash": blob.md5_hash,
                    "metadata": blob.metadata or {}
                }
            return None
            
        except Exception as e:
            log_error(e, context="get_file_metadata", storage_path=storage_path)
            raise
    
    def file_exists(self, storage_path: str) -> bool:
        """Check if file exists"""
        try:
            blob = self.bucket.blob(storage_path)
            return blob.exists()
            
        except Exception as e:
            log_error(e, context="file_exists", storage_path=storage_path)
            return False
    
    def list_files(self, prefix: str = None, delimiter: str = None) -> list:
        """List files in storage"""
        try:
            blobs = self.bucket.list_blobs(prefix=prefix, delimiter=delimiter)
            
            files = []
            for blob in blobs:
                files.append({
                    "name": blob.name,
                    "size": blob.size,
                    "content_type": blob.content_type,
                    "created": blob.time_created.isoformat() if blob.time_created else None,
                    "public_url": blob.public_url
                })
            
            return files
            
        except Exception as e:
            log_error(e, context="list_files", prefix=prefix)
            raise
    
    def generate_signed_url(self, storage_path: str, expiration_minutes: int = 60) -> str:
        """Generate a signed URL for temporary access"""
        try:
            from datetime import timedelta, datetime
            
            blob = self.bucket.blob(storage_path)
            expiration = datetime.utcnow() + timedelta(minutes=expiration_minutes)
            
            url = blob.generate_signed_url(expiration=expiration)
            
            logger.info("Signed URL generated",
                       storage_path=storage_path,
                       expiration_minutes=expiration_minutes)
            
            return url
            
        except Exception as e:
            log_error(e, context="generate_signed_url", storage_path=storage_path)
            raise