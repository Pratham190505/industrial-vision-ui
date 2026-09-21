from typing import Optional
from fastapi import Depends, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.core.database import get_database
from app.core.exceptions import AuthenticationError
from app.core.security import decode_access_token

security_scheme = HTTPBearer(auto_error=False)


async def get_db_dep() -> AsyncIOMotorDatabase:
    """Dependency that injects the shared async MongoDB database instance."""
    return get_database()


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    db: AsyncIOMotorDatabase = Depends(get_db_dep),
) -> Optional[dict]:
    """
    Extracts and validates optional bearer token.
    Returns user payload or None if not authenticated.
    """
    if credentials is None:
        return None

    payload = decode_access_token(credentials.credentials)
    if payload is None or "sub" not in payload:
        return None

    # TODO: In Prompt 2 (Authentication), fetch active user from `users` collection
    return {"user_id": payload["sub"], "email": payload.get("email")}


async def get_current_user(
    current_user: Optional[dict] = Depends(get_current_user_optional),
) -> dict:
    """
    Strict dependency enforcing authenticated user presence.
    Raises AuthenticationError if unauthenticated.
    """
    if current_user is None:
        raise AuthenticationError("Authentication token is required or expired.")
    return current_user
