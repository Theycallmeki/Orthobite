from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):

    APP_NAME: str = "OrthoBite API"
    VERSION: str = "0.1.0"
    DEBUG: bool = True
    CLINIC_TIMEZONE: str = "Asia/Manila"


    DATABASE_URL: str = "sqlite:///./orthobite.db"


    SECRET_KEY: str = "change-me-in-production-orthobite-secret-key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24            
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7                  


    REDIS_URL: str = "redis://localhost:6379/0"


    FRONTEND_URL: str = "http://localhost:5173"


    UPLOAD_DIR: str = "uploads"
    TOOTH_CHART_DIR: str = "uploads/tooth_charts"
    SIGNATURES_DIR: str = "uploads/signatures"
    DOCTORS_DIR: str = "uploads/doctors"
    SCANS_DIR: str = "uploads/scans"
    PROFILES_DIR: str = "uploads/profiles"


    BREVO_API_KEY: str = ""
    BREVO_SENDER_EMAIL: str = "reminders@orthobite.com"
    BREVO_SENDER_NAME: str = "OrthoBite Dental Clinic"


    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "noreply@orthobite.com"

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
