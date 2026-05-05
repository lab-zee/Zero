"""
File storage and validation utilities.
Uses local filesystem storage (works for both local dev and Railway volumes).
"""
import os
import uuid
from pathlib import Path
from typing import Optional

# Allowed file types for office documents
ALLOWED_EXTENSIONS = {
    # Documents
    '.pdf', '.doc', '.docx', '.txt', '.rtf',
    # Spreadsheets
    '.xls', '.xlsx', '.csv',
    # Presentations
    '.ppt', '.pptx',
    # Other common office formats
    '.odt', '.ods', '.odp',
    # Images (for generated images)
    '.png', '.jpg', '.jpeg', '.gif', '.webp',
}

ALLOWED_MIME_TYPES = {
    # PDF
    'application/pdf',
    # Microsoft Office
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.ms-powerpoint',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    # CSV
    'text/csv',
    'text/plain',
    # OpenDocument
    'application/vnd.oasis.opendocument.text',
    'application/vnd.oasis.opendocument.spreadsheet',
    'application/vnd.oasis.opendocument.presentation',
    # RTF
    'application/rtf',
    # Images
    'image/png',
    'image/jpeg',
    'image/jpg',
    'image/gif',
    'image/webp',
}

# Get upload directory from environment (defaults to 'uploads')
# For Railway, you can mount a volume to this directory
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
Path(UPLOAD_DIR).mkdir(parents=True, exist_ok=True)

def save_file(file_content: bytes, filename: str) -> str:
    """Save file to local filesystem and return the file path"""
    file_path = os.path.join(UPLOAD_DIR, filename)
    with open(file_path, "wb") as f:
        f.write(file_content)
    return file_path

def get_file(file_path: str) -> bytes:
    """Read file from local filesystem"""
    with open(file_path, "rb") as f:
        return f.read()

def delete_file_from_storage(file_path: str) -> bool:
    """Delete file from local filesystem"""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
        return False
    except Exception:
        return False

def file_exists(file_path: str) -> bool:
    """Check if file exists on local filesystem"""
    return os.path.exists(file_path)

def validate_file_type(filename: str, content_type: Optional[str] = None) -> tuple[bool, Optional[str]]:
    """
    Validate if file type is allowed.
    Returns (is_valid, error_message)
    """
    # Check file extension
    file_ext = Path(filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        return False, f"File type '{file_ext}' is not allowed. Allowed types: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
    
    # Check MIME type if provided
    if content_type:
        # Normalize MIME type (remove charset, etc.)
        mime_base = content_type.split(';')[0].strip().lower()
        if mime_base not in ALLOWED_MIME_TYPES:
            # Some browsers send generic MIME types, so we're lenient if extension is valid
            if file_ext in ALLOWED_EXTENSIONS:
                return True, None  # Allow if extension is valid
            return False, f"MIME type '{content_type}' is not allowed"
    
    return True, None

def generate_unique_filename(original_filename: str) -> str:
    """Generate a unique filename while preserving extension"""
    file_ext = Path(original_filename).suffix
    return f"{uuid.uuid4()}{file_ext}"

