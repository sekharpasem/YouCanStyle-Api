from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
from typing import List, Optional
from app.core.auth import get_current_user
from app.utils.file_upload import upload_file, delete_file
import os

router = APIRouter()

@router.post("/profile-image")
async def upload_profile_image(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Upload a profile image for the current user
    """
    # Validate file type
    allowed_types = ["image/jpeg", "image/png", "image/jpg"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only JPEG and PNG images are allowed"
        )
    
    # Upload file to profile-images folder
    file_url = await upload_file(file, folder="profile-images")
    
    # Update user profile image in database
    # This is just a placeholder - in a real implementation, you would update the user's profile image in the database
    # Example: await update_user_profile_image(str(current_user["_id"]), file_url)
    
    return {"fileUrl": file_url}

@router.post("/stylist-portfolio")
async def upload_stylist_portfolio_image(
    file: UploadFile = File(...),
    caption: str = Form(None),
    current_user: dict = Depends(get_current_user)
):
    """
    Upload a portfolio image for stylist
    """
    # Validate file type
    allowed_types = ["image/jpeg", "image/png", "image/jpg"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only JPEG and PNG images are allowed"
        )
    
    # Upload file to stylist-portfolio folder
    file_url = await upload_file(file, folder="stylist-portfolio")
    
    # Add image to stylist portfolio in database
    # This is just a placeholder - in a real implementation, you would add the image to the stylist's portfolio in the database
    # Example: await add_portfolio_image(stylist_id, file_url, caption)
    
    return {"fileUrl": file_url, "caption": caption}

@router.post("/chat-attachment")
async def upload_chat_attachment(
    file: UploadFile = File(...),
    chat_room_id: str = Form(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Upload an attachment for a chat message
    """
    # Determine file type and appropriate folder
    content_type = file.content_type
    folder = "chat-attachments"
    
    if content_type.startswith("image/"):
        folder = "chat-images"
    elif content_type.startswith("video/"):
        folder = "chat-videos"
    elif content_type.startswith("audio/"):
        folder = "chat-audio"
    
    # Upload file
    file_url = await upload_file(file, folder=folder)
    
    # Get file info
    file_size = os.path.getsize(f"./uploads/{folder}/{os.path.basename(file_url)}")
    
    return {
        "fileUrl": file_url,
        "fileName": file.filename,
        "fileType": content_type,
        "fileSize": file_size
    }

@router.post("/documents")
async def upload_document(
    file: UploadFile = File(...),
    document_type: str = Form(...),  # ID, certificate, license, etc.
    current_user: dict = Depends(get_current_user)
):
    """
    Upload identity or verification documents
    """
    # Validate file type
    allowed_types = ["application/pdf", "image/jpeg", "image/png", "image/jpg"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF and images are allowed"
        )
    
    # Upload file to documents folder
    file_url = await upload_file(file, folder=f"documents/{document_type}")
    
    # Store document information in database
    # This is just a placeholder - in a real implementation, you would store the document information in the database
    # Example: await add_user_document(str(current_user["_id"]), document_type, file_url)
    
    return {"fileUrl": file_url, "documentType": document_type}

@router.delete("/{file_path:path}")
async def delete_uploaded_file(
    file_path: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Delete an uploaded file
    Note: In production, you would need proper authorization checks to ensure 
    the user has permission to delete the file
    """
    # Format file path to match the expected format
    formatted_path = f"/uploads/{file_path}"
    
    # Delete file
    success = await delete_file(formatted_path)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found or could not be deleted"
        )
    
    return {"message": "File deleted successfully"}

@router.post("/multiple")
async def upload_multiple_files(
    files: List[UploadFile] = File(...),
    folder: str = Form("general"),
    current_user: dict = Depends(get_current_user)
):
    """
    Upload multiple files
    """
    results = []
    
    for file in files:
        file_url = await upload_file(file, folder=folder)
        results.append({
            "fileName": file.filename,
            "fileUrl": file_url
        })
    
    return {"files": results}
