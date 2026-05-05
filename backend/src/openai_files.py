"""
OpenAI Files API integration for handling file uploads and attachments.
Uses OpenAI's native file handling instead of manual text extraction.
"""
import os
from typing import Optional, List
from openai import OpenAI
from io import BytesIO

def upload_file_to_openai(client: OpenAI, file_content: bytes, filename: str, purpose: str = "user_data") -> str:
    """
    Upload a file to OpenAI's Files API.
    For PDFs, use purpose="user_data" to allow direct use in chat completions.
    Returns the file ID that can be used in chat completions.
    """
    try:
        # Create a file-like object from bytes
        file_obj = BytesIO(file_content)
        file_obj.name = filename
        
        # Upload to OpenAI
        # For PDFs and other user files, use "user_data" purpose
        uploaded_file = client.files.create(
            file=file_obj,
            purpose=purpose
        )
        return uploaded_file.id
    except Exception as e:
        raise Exception(f"Failed to upload file to OpenAI: {str(e)}")

def create_file_attachment(file_id: str, filename: str) -> dict:
    """
    Create a file attachment object for use in chat completions.
    Note: File attachments in chat completions may require specific model support.
    """
    return {
        "type": "file",
        "file_id": file_id,
        "name": filename
    }

def upload_files_to_openai(client: OpenAI, db_files: List) -> List[dict]:
    """
    Upload multiple files to OpenAI and return attachment objects.
    Returns a list of file attachment dictionaries.
    """
    attachments = []
    for db_file in db_files:
        try:
            from .storage import get_file
            file_content = get_file(db_file.file_path)
            file_id = upload_file_to_openai(client, file_content, db_file.original_filename)
            attachments.append({
                "file_id": file_id,
                "filename": db_file.original_filename
            })
        except Exception as e:
            # Log error but continue with other files
            print(f"Error uploading file {db_file.original_filename} to OpenAI: {str(e)}")
            continue
    return attachments

def cleanup_openai_file(client: OpenAI, file_id: str) -> None:
    """Delete a file from OpenAI's storage."""
    try:
        client.files.delete(file_id)
    except Exception as e:
        print(f"Error deleting OpenAI file {file_id}: {str(e)}")

