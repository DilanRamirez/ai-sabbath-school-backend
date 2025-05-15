# app/core/config.py
from dotenv import load_dotenv
import os

load_dotenv()  # Load variables from .env


class Settings:
    APP_NAME: str = os.getenv("APP_NAME", "SabbathSchoolApp")
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    ADMIN_KEY: str = os.getenv("ADMIN_KEY", "")


settings = Settings()
