from app.core.config import settings
from fastapi import HTTPException, Security, status, Depends
from fastapi.security.api_key import APIKeyHeader
from fastapi.security import OAuth2PasswordBearer
from typing import List
from pydantic import BaseModel
from datetime import datetime, timedelta
from jose import JWTError, jwt


# Name of the HTTP header
API_KEY_NAME = "X-API-Key"
# Read the expected key from your loaded settings (or os.getenv)
ADMIN_KEY = settings.ADMIN_KEY

#
# JWT key configuration from settings
# Decode PEM strings from settings into bytes once
_raw_private = settings.JWT_PRIVATE_KEY.replace("\\n", "\n")
_raw_public = settings.JWT_PUBLIC_KEY.replace("\\n", "\n")
PRIVATE_KEY = _raw_private.encode("utf-8")
PUBLIC_KEY = _raw_public.encode("utf-8")
ALGORITHM = settings.JWT_ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES

# Set up the header extractor
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


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


# JWT helper classes and functions
class TokenData(BaseModel):
    sub: str
    roles: List[str] = []


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    token = jwt.encode(to_encode, PRIVATE_KEY, algorithm=ALGORITHM)
    return token


def decode_access_token(token: str) -> TokenData:
    try:
        payload = jwt.decode(token, PUBLIC_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        roles: List[str] = payload.get("roles", [])
        if username is None:
            raise JWTError()
        return TokenData(sub=username, roles=roles)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user(token: str = Depends(oauth2_scheme)) -> TokenData:
    return decode_access_token(token)


def require_role(role: str):
    def role_checker(current: TokenData = Depends(get_current_user)):
        if role not in current.roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required role `{role}` missing",
            )
        return current

    return role_checker
