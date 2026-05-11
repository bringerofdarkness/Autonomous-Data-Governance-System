import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.document_metadata import DocumentMetadata, DocumentStatus
from app.models.user import User


settings = get_settings()


async def save_uploaded_document(
    db: AsyncSession,
    file: UploadFile,
    uploaded_by: User,
) -> DocumentMetadata:
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must have a filename.",
        )

    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)

    file_extension = Path(file.filename).suffix
    stored_filename = f"{uuid.uuid4()}{file_extension}"
    stored_file_path = upload_dir / stored_filename

    file_content = await file.read()

    if not file_content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    stored_file_path.write_bytes(file_content)

    document = DocumentMetadata(
        original_filename=file.filename,
        stored_filename=stored_filename,
        content_type=file.content_type,
        file_size_bytes=len(file_content),
        status=DocumentStatus.UPLOADED,
        uploaded_by_id=uploaded_by.id,
    )

    db.add(document)
    await db.commit()
    await db.refresh(document)

    return document