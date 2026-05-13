from pydantic import BaseModel, ConfigDict, Field


class RagSearchRequest(BaseModel):
    query: str = Field(
        min_length=3,
        max_length=1000,
        description="Search question or query to run against the approved Gold Collection.",
    )
    limit: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum number of chunk matches to return.",
    )
    min_score: float = Field(
        default=0.30,
        ge=0.0,
        le=1.0,
        description="Minimum similarity score required to return a chunk match.",
    )

    model_config = ConfigDict(extra="forbid")


class RagChunkMatchResponse(BaseModel):
    point_id: str
    score: float
    document_id: str | None
    original_filename: str | None
    document_category: str | None
    risk_score: int | None
    chunk_index: int | None
    chunk_text: str | None
    source: str | None


class RagSearchResponse(BaseModel):
    query: str
    min_score: float
    matches_count: int
    matches: list[RagChunkMatchResponse]