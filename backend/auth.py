"""
Verify Supabase JWT and return user id for protected endpoints.
Uses supabase.auth.get_user(token) so asymmetric signing is supported.
"""
import os

from fastapi import HTTPException, Request, status
from supabase import create_client


def _supabase():
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Supabase not configured",
        )
    return create_client(url, key)


def get_user_id_from_request(request: Request) -> str:
    """Extract Bearer token from request and return user id. Raises 401 if invalid."""
    auth = request.headers.get("Authorization")
    if not auth or not auth.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
        )
    token = auth[7:].strip()
    return verify_supabase_jwt(token)


def verify_supabase_jwt(token: str) -> str:
    """Verify token via Supabase Auth (supports asymmetric signing). Return user id."""
    supabase = _supabase()
    try:
        response = supabase.auth.get_user(jwt=token)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        ) from e
    if not response or not getattr(response, "user", None):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )
    user = response.user
    user_id = getattr(user, "id", None)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )
    return str(user_id)
