"""Security utilities for API authentication"""
import secrets
from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader
from config import SITE_API_KEY

api_key_header = APIKeyHeader(name="X-API-Key")


def verify_api_key(api_key: str = Security(api_key_header)):
    """Verify the API key from request header"""
    if not SITE_API_KEY or not secrets.compare_digest(api_key, SITE_API_KEY):
        raise HTTPException(status_code=403, detail="Invalid API key")
    return api_key
