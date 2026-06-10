import uuid
from pathlib import Path
from rest_framework import exceptions
from django.core.files.uploadedfile import UploadedFile

from app.core.config import get_settings
from app.models import DocumentMetadata, DocumentStatus, User

settings = get_settings()


def save_uploaded_document(
    file: UploadedFile,
    uploaded_by: User,
) -> DocumentMetadata:
    if not file.name:
        raise exceptions.ValidationError("Uploaded file must have a filename.")

    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)

    file_extension = Path(file.name).suffix
    stored_filename = f"{uuid.uuid4()}{file_extension}"
    stored_file_path = upload_dir / stored_filename

    file_content = file.read()

    if not file_content:
        raise exceptions.ValidationError("Uploaded file is empty.")

    stored_file_path.write_bytes(file_content)

    document = DocumentMetadata.objects.create(
        original_filename=file.name,
        stored_filename=stored_filename,
        content_type=file.content_type,
        file_size_bytes=len(file_content),
        status=DocumentStatus.UPLOADED,
        uploaded_by=uploaded_by,
    )

    return document