from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
import os
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    # App Settings
    APP_NAME: str = os.getenv("APP_NAME", "YouCanStyle")
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:3000")
    
    # MongoDB Settings
    MONGO_URI: str = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    DB_NAME: str = os.getenv("DB_NAME", "youcanstyle_db")
    
    # JWT Auth
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your_secret_key_here")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "120"))
    
    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",  # React frontend
        "http://localhost:8080",  # Flutter web
    ]
    
    # Email settings
    EMAIL_HOST: str = os.getenv("EMAIL_HOST", "smtp.gmail.com")
    EMAIL_PORT: int = int(os.getenv("EMAIL_PORT", "587"))
    EMAIL_USERNAME: str = os.getenv("EMAIL_USERNAME", "")
    EMAIL_PASSWORD: str = os.getenv("EMAIL_PASSWORD", "")
    EMAIL_FROM: str = os.getenv("EMAIL_FROM", "")

    # AWS S3 (optional)
    AWS_S3_BUCKET: str | None = os.getenv("AWS_S3_BUCKET")
    AWS_S3_REGION: str | None = os.getenv("AWS_S3_REGION")
    AWS_ACCESS_KEY_ID: str | None = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY: str | None = os.getenv("AWS_SECRET_ACCESS_KEY")
    AWS_S3_PUBLIC_BASE_URL: str | None = os.getenv("AWS_S3_PUBLIC_BASE_URL")
    AWS_S3_ACL: str | None = os.getenv("AWS_S3_ACL", "public-read")

    # Gemini settings (sole provider)
    GEMINI_API_KEY: str | None = os.getenv("GEMINI_API_KEY")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    # WhatsApp Business Cloud API
    WHATSAPP_ENABLED: bool = os.getenv("WHATSAPP_ENABLED", "false").lower() in ("1", "true", "yes")
    WHATSAPP_TOKEN: str | None = os.getenv("WHATSAPP_TOKEN")
    WHATSAPP_PHONE_NUMBER_ID: str | None = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
    WHATSAPP_WEBHOOK_VERIFY_TOKEN: str | None = os.getenv("WHATSAPP_WEBHOOK_VERIFY_TOKEN")
    WHATSAPP_DEFAULT_LANG: str = os.getenv("WHATSAPP_DEFAULT_LANG", "en")

    # Zoom Server-to-Server OAuth
    ZOOM_ACCOUNT_ID: str | None = os.getenv("ZOOM_ACCOUNT_ID")
    ZOOM_CLIENT_ID: str | None = os.getenv("ZOOM_CLIENT_ID")
    ZOOM_CLIENT_SECRET: str | None = os.getenv("ZOOM_CLIENT_SECRET")
    ZOOM_USER_ID: str | None = os.getenv("ZOOM_USER_ID")  # email or userId of licensed host

    # Pydantic v2 settings config
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra='ignore',  # ignore any env keys not declared above
    )

settings = Settings()
