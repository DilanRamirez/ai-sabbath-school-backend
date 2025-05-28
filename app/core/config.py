# app/core/config.py
from dotenv import load_dotenv
import os
import boto3

load_dotenv()  # Load variables from .env


class Settings:
    APP_NAME: str = os.getenv("APP_NAME", "SabbathSchoolApp")
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    ADMIN_KEY: str = os.getenv("ADMIN_KEY", "")
    AWS_ACCESS_KEY_ID: str = os.environ["AWS_ACCESS_KEY_ID"]
    AWS_SECRET_KEY: str = os.environ["AWS_SECRET_KEY"]
    AWS_REGION: str = os.environ["AWS_REGION"]
    S3_BUCKET: str = os.environ["S3_BUCKET"]


settings = Settings()


s3 = boto3.client(
    "s3",
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_KEY,
    region_name=settings.AWS_REGION,
)

BUCKET = settings.S3_BUCKET
