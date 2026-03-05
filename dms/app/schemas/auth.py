from pydantic import BaseModel


class TokenResponse(BaseModel):
    """Define the schema for token response.

    Parameters:
        access_token (type=str): JWT access token returned after successful authentication.
        token_type (type=str): Token type, typically `bearer`.
    """
    access_token: str
    token_type: str = "bearer"
