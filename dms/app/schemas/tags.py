from uuid import UUID

from pydantic import BaseModel, Field


class TagUpdateRequest(BaseModel):
    """Define the schema for tag update request.

    Parameters:
        tags (type=list[str]): Normalized tags associated with the document/version.
    """
    tags: list[str] = Field(default_factory=list)


class TagPoolCreateRequest(BaseModel):
    """Define the schema for tag pool create request.

    Parameters:
        tag (type=str): Tag value used by this model/schema.
    """
    tag: str


class TagPoolResponse(BaseModel):
    """Define the schema for tag pool response.

    Parameters:
        tags (type=list[str]): Normalized tags associated with the document/version.
    """
    tags: list[str] = Field(default_factory=list)


class TagPoolCreateResponse(BaseModel):
    """Define the schema for tag pool create response.

    Parameters:
        tag (type=str): Tag value used by this model/schema.
    """
    tag: str


class DocumentVersionTagsResponse(BaseModel):
    """Define the schema for document version tags response.

    Parameters:
        document_id (type=UUID): Identifier of the parent document.
        version_id (type=UUID): Identifier of the document version.
        tags (type=list[str]): Normalized tags associated with the document/version.
    """
    document_id: UUID
    version_id: UUID
    tags: list[str] = Field(default_factory=list)
