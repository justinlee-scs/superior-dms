from uuid import UUID

from pydantic import BaseModel, Field


class TagUpdateRequest(BaseModel):
    tags: list[str] = Field(default_factory=list)


class DocumentVersionTagsResponse(BaseModel):
    document_id: UUID
    version_id: UUID
    tags: list[str] = Field(default_factory=list)
