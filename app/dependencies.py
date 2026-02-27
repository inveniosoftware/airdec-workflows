from typing import Annotated

from fastapi import Header, HTTPException


async def get_token_header(x_token: Annotated[str, Header()]):
    """Validate the X-Token header.

    This is a temporary token for development purposes.
    """
    if x_token != "fake-super-secret-token":
        raise HTTPException(status_code=400, detail="X-Token header invalid")


async def get_query_token(token: str):
    """Validate the query token."""
    if token != "jessica":
        raise HTTPException(status_code=400, detail="No Jessica token provided")
