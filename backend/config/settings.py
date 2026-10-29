from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # App
    APP_NAME: str = "OrthoBite API"
    DEBUG: bool = True

    # Database — override in .env for PostgreSQL (e.g. postgresql://user:pass@localhost:5432/orthobite)
    DATABASE_URL: str = "sqlite:///./orthobite.db"

    # JWT
    SECRET_KEY: str = "change-me-in-production-orthobite-secret-key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # Frontend
    FRONTEND_URL: str = "http://localhost:5173"

    # Uploads
    UPLOAD_DIR: str = "uploads"

    # Email / SMTP
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "noreply@orthobite.com"

    # Resend API (HTTP email over Port 443)
    RESEND_API_KEY: str = ""
    RESEND_FROM_EMAIL: str = "OrthoBite <onboarding@resend.dev>"

    # Brevo (Sendinblue) API
    BREVO_API_KEY: str = ""
    BREVO_FROM_EMAIL: str = ""
    BREVO_FROM_NAME: str = "OrthoBite"

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
