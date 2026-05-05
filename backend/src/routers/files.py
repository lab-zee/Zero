from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File as FastAPIFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import Optional, List

from ..database import get_db
from .. import schemas, crud

router = APIRouter(tags=["files"])


@router.post("/api/files/upload", response_model=schemas.FileUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = FastAPIFile(...),
    user_id: int = Query(...),
    organization_id: int = Query(...),
    db: Session = Depends(get_db)
):
    """Upload a file for a user and organization"""
    # Verify user exists
    user = crud.get_user(db, user_id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Verify organization exists and user has access
    org = crud.get_organization(db, org_id=organization_id)
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )

    # Uploading a file is a mutation — require write access
    has_access = crud.check_org_permission(db, organization_id, user_id, require_write=True)
    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have write access to this organization"
        )

    # Read file content
    file_content = await file.read()

    # Validate file type
    from ..storage import validate_file_type
    is_valid, error_msg = validate_file_type(file.filename or "unnamed", file.content_type)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )

    # Create file record
    db_file = crud.create_file(
        db=db,
        user_id=user_id,
        organization_id=organization_id,
        original_filename=file.filename or "unnamed",
        file_content=file_content,
        content_type=file.content_type
    )

    # Generate embeddings for the file in the background
    # This is done asynchronously to avoid blocking the upload response
    try:
        from ..file_extraction import extract_text_from_file
        from ..vector_store import add_document_to_store

        # Extract text content
        text_content, error = extract_text_from_file(
            db_file.file_path,
            db_file.content_type,
            db_file.original_filename
        )

        if text_content and not error:
            # Add to vector store (this may take a moment, but we don't block)
            try:
                add_document_to_store(
                    organization_id=organization_id,
                    file_id=db_file.id,
                    filename=db_file.original_filename,
                    text_content=text_content
                )
            except Exception as e:
                print(f"Warning: Failed to add file to vector store: {e}")
                # Don't fail the upload if vector store fails
        else:
            print(f"Warning: Could not extract text from file {db_file.original_filename}: {error}")
    except Exception as e:
        print(f"Warning: Error processing file for vector store: {e}")
        # Don't fail the upload if vector store processing fails

    return schemas.FileUploadResponse(
        id=db_file.id,
        filename=db_file.filename,
        original_filename=db_file.original_filename,
        content_type=db_file.content_type,
        file_size=db_file.file_size,
        created_at=db_file.created_at
    )


@router.get("/api/files/{file_id}", response_model=schemas.FileResponse)
async def get_file_info(
    file_id: int,
    user_id: int = Query(...),
    db: Session = Depends(get_db)
):
    """Get file information"""
    db_file = crud.get_file(db, file_id=file_id)
    if not db_file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )

    # Check if user has access (must be owner or have access to organization)
    if db_file.user_id != user_id:
        has_access = crud.check_org_permission(db, db_file.organization_id, user_id, require_write=False)
        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this file"
            )

    return schemas.FileResponse(
        id=db_file.id,
        user_id=db_file.user_id,
        organization_id=db_file.organization_id,
        filename=db_file.filename,
        original_filename=db_file.original_filename,
        content_type=db_file.content_type,
        file_size=db_file.file_size,
        created_at=db_file.created_at
    )


@router.get("/api/files/{file_id}/download")
async def download_file(
    file_id: int,
    user_id: int = Query(...),
    db: Session = Depends(get_db)
):
    """Download a file"""
    db_file = crud.get_file(db, file_id=file_id)
    if not db_file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )

    # Check if user has access
    if db_file.user_id != user_id:
        has_access = crud.check_org_permission(db, db_file.organization_id, user_id, require_write=False)
        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this file"
            )

    # Check if file exists
    from ..storage import file_exists
    if not file_exists(db_file.file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )

    return FileResponse(
        path=db_file.file_path,
        filename=db_file.original_filename,
        media_type=db_file.content_type or "application/octet-stream"
    )


@router.get("/api/files", response_model=List[schemas.FileResponse])
async def get_files(
    user_id: int = Query(...),
    organization_id: Optional[int] = Query(None),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get files for a user, optionally filtered by organization"""
    files = crud.get_files_by_user(db, user_id=user_id, organization_id=organization_id, skip=skip, limit=limit)
    return [
        schemas.FileResponse(
            id=file.id,
            user_id=file.user_id,
            organization_id=file.organization_id,
            filename=file.filename,
            original_filename=file.original_filename,
            content_type=file.content_type,
            file_size=file.file_size,
            created_at=file.created_at
        )
        for file in files
    ]


@router.delete("/api/files/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_file_endpoint(
    file_id: int,
    user_id: int = Query(...),
    db: Session = Depends(get_db)
):
    """Delete a file (by owner or organization member with write access)"""
    success = crud.delete_file(db, file_id=file_id, user_id=user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found or you don't have permission to delete it"
        )
    return None
