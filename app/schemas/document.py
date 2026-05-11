import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.document_metadata import DocumentStatus


class DocumentUploadResponse(BaseModel):
    id: uuid.UUID
    original_filename: str
    stored_filename: str
    content_type: str | None
    file_size_bytes: int
    status: DocumentStatus
    celery_task_id: str | None
    uploaded_by_id: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentStatusResponse(BaseModel):
    id: uuid.UUID
    original_filename: str
    status: DocumentStatus
    document_category: str | None
    risk_score: int | None
    conflict_found: bool
    conflict_summary: str | None
    conflict_checked_at: datetime | None
    celery_task_id: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime


    model_config = ConfigDict(from_attributes=True)


class DocumentTaskStatusResponse(BaseModel):
    document_id: uuid.UUID
    original_filename: str
    database_status: DocumentStatus
    document_category: str | None
    risk_score: int | None
    celery_task_id: str | None
    celery_state: str | None
    celery_result: Any | None
    error_message: str | None


class DocumentDecisionRequest(BaseModel):
    reason: str = Field(
        min_length=5,
        max_length=500,
        description="Human-readable reason for approving or rejecting the document.",
    )

    model_config = ConfigDict(extra="forbid")


class DocumentDecisionResponse(BaseModel):
    id: uuid.UUID
    original_filename: str
    status: DocumentStatus
    document_category: str | None
    risk_score: int | None
    decision_message: str

    model_config = ConfigDict(from_attributes=True)

class DocumentListItemResponse(BaseModel):
    id: uuid.UUID
    original_filename: str
    stored_filename: str
    cleaned_text_filename: str | None
    content_type: str | None
    file_size_bytes: int

    status: DocumentStatus
    document_category: str | None
    risk_score: int | None

    conflict_found: bool
    conflict_summary: str | None
    conflict_checked_at: datetime | None

    qdrant_point_id: uuid.UUID | None
    indexed_at: datetime | None

    celery_task_id: str | None
    uploaded_by_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class DocumentSummaryResponse(BaseModel):
    total: int
    uploaded: int
    processing: int
    waiting_for_admin: int
    approved: int
    rejected: int
    failed: int

    conflict_found_count: int
    indexed_count: int
    waiting_for_admin_with_conflict: int

class DocumentReprocessResponse(BaseModel):
    id: uuid.UUID
    original_filename: str
    status: DocumentStatus
    celery_task_id: str
    message: str

    model_config = ConfigDict(from_attributes=True)

class DocumentIndexResponse(BaseModel):
    id: uuid.UUID
    original_filename: str
    status: DocumentStatus
    document_category: str | None
    risk_score: int | None
    qdrant_point_id: uuid.UUID
    indexed_at: datetime
    chunks_indexed: int
    points_indexed: int
    message: str

    model_config = ConfigDict(from_attributes=True)

class DocumentQdrantPointResponse(BaseModel):
    document_id: uuid.UUID
    original_filename: str
    indexed: bool
    qdrant_point_id: uuid.UUID | None
    collection_name: str | None
    payload: dict[str, Any] | None
    message: str

class ConflictMatchResponse(BaseModel):
    point_id: str
    score: float
    payload: dict[str, Any] | None


class DocumentConflictCheckResponse(BaseModel):
    document_id: uuid.UUID
    original_filename: str
    conflict_found: bool
    similarity_threshold: float
    matches_checked: int
    potential_conflicts: list[ConflictMatchResponse]
    message: str


class DocumentResumeRequest(BaseModel):
    decision: Literal["approve", "reject"]
    reason: str = Field(
        min_length=10,
        max_length=1000,
        description="Admin reason for resuming the paused HITL workflow.",
    )

    model_config = ConfigDict(extra="forbid")


class DocumentResumeResponse(BaseModel):
    id: uuid.UUID
    original_filename: str
    status: DocumentStatus
    hitl_decision: str
    hitl_reason: str
    message: str

    model_config = ConfigDict(from_attributes=True)

class QdrantChunkResponse(BaseModel):
    point_id: str
    chunk_index: int | None
    chunk_text: str | None
    char_count: int | None
    payload: dict[str, Any] | None


class DocumentQdrantChunksResponse(BaseModel):
    document_id: uuid.UUID
    original_filename: str
    indexed: bool
    chunks_count: int
    chunks: list[QdrantChunkResponse]
    message: str