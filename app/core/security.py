from app.core.config import settings
from fastapi import HTTPException, Security, status
from fastapi.security.api_key import APIKeyHeader

# Name of the HTTP header
API_KEY_NAME = "X-API-Key"

# Read the expected key from your loaded settings (or os.getenv)
ADMIN_KEY = settings.ADMIN_KEY

# Set up the header extractor
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)


def get_api_key(api_key: str = Security(api_key_header)) -> str:
    """
    Dependency: raises 403 unless a valid X-API-Key header is present.
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Missing {API_KEY_NAME} header",
        )
    if api_key != ADMIN_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Invalid API key"
        )
    return api_key
