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
    AWS_ACCESS_KEY_ID: str = os.getenv("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY: str = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    AWS_REGION: str = os.getenv("AWS_REGION", "")
    S3_BUCKET: str = os.getenv("S3_BUCKET", "")
    JWT_SECRET: str = os.getenv("JWT_SECRET", "secret-key")


settings = Settings()
# build a valid S3 client, with a fallback if region is bogus
_region = settings.AWS_REGION or "us-east-2"
_bucket = settings.S3_BUCKET or "my-default-bucket"

try:
    # Initialize S3 client and bucket name for all environments (moto can mock this)
    s3 = boto3.client(
        "s3",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=_region,
    )
    dynamodb = boto3.resource(
        "dynamodb",
        region_name=os.getenv("AWS_REGION"),
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    )
except ValueError:
    # boto3 complained about the endpoint—fall back to the default region lookup
    s3 = boto3.client("s3")

BUCKET = _bucket
