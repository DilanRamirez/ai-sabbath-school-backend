# app/routes/auth.py
import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from uuid import uuid4
from datetime import datetime
from passlib.context import CryptContext
from datetime import datetime, timedelta
from app.core.config import dynamodb, settings
from app.core.security import create_access_token
from fastapi import Depends


router = APIRouter()
table = dynamodb.Table("SabbathSchoolApp")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return pwd_context.verify(password, hashed)


class UserSignupRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str  # "student" or "teacher"


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str


@router.post("/signup")
def signup_user(payload: UserSignupRequest):
    user_id = str(uuid4())
    pk = f"USER#{user_id}"
    sk = "PROFILE"

    # Check if email already exists
    existing = table.scan(
        FilterExpression="email = :email",
        ExpressionAttributeValues={":email": payload.email},
    )
    if existing["Items"]:
        raise HTTPException(status_code=400, detail="Email already registered")

    item = {
        "PK": pk,
        "SK": sk,
        "user_id": user_id,
        "name": payload.name,
        "email": payload.email,
        "auth_provider": "email",
        "hashed_password": hash_password(payload.password),
        "role": payload.role,
        "joined_cohorts": [],
        "created_at": datetime.utcnow().isoformat(),
    }

    try:
        table.put_item(Item=item)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Automatically create access token after signup
    token = create_access_token(data={"sub": user_id, "roles": [payload.role]})

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user_id,
            "name": payload.name,
            "role": payload.role,
            "email": payload.email,
        },
    }


@router.post("/login")
def login_user(payload: UserLoginRequest):
    print("Login attempt for:", payload)
    response = table.scan(
        FilterExpression="email = :email",
        ExpressionAttributeValues={":email": payload.email},
    )
    items = response.get("Items")

    if not items:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    user = items[0]
    if not verify_password(payload.password, user.get("hashed_password")):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token(data={"sub": user["user_id"], "roles": [user["role"]]})

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user["user_id"],
            "name": user["name"],
            "role": user["role"],
            "email": user["email"],
        },
    }
