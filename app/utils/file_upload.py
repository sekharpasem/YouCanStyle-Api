import os
import shutil
import uuid
from fastapi import UploadFile
from datetime import datetime
from pathlib import Path

# Create uploads directory
UPLOADS_DIR = Path("./uploads")
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

async def upload_file(file: UploadFile, folder: str = "general") -> str:
    """
    Upload a file to local storage and return the URL
    
    In production, this would upload to cloud storage like AWS S3,
    Google Cloud Storage, or Azure Blob Storage
    """
    # Create directory if it doesn't exist
    folder_path = UPLOADS_DIR / folder
    folder_path.mkdir(parents=True, exist_ok=True)
    
    # Generate unique filename
    file_extension = os.path.splitext(file.filename)[1] if file.filename else ""
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    
    # Save file
    file_path = folder_path / unique_filename
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Return relative URL
    # In production, this would be a full URL to the cloud storage
    return f"/uploads/{folder}/{unique_filename}"

async def delete_file(file_path: str) -> bool:
    """
    Delete a file from local storage
    """
    try:
        # Get absolute path
        abs_path = Path(".") / file_path.lstrip("/")
        
        # Check if file exists
        if not abs_path.exists():
            return False
            
        # Delete file
        os.remove(abs_path)
        return True
    except Exception:
        return False
