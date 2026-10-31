import os
import logging
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from config.settings import settings
from config.database import Base, engine
import models.users    # Ensure User model is registered
import models.patient  # Ensure Patient model is registered
import models.doctor   # Ensure Doctor models are registered
import models.appointment  # Ensure Appointment model is registered
from middleware import setup_middleware
from routes.auth import router as auth_router
from routes.user import router as user_router
from routes.patient import router as patient_router
from routes.doctor import router as doctor_router
from routes.appointment import router as appointment_router


logger = logging.getLogger("orthobite")

# Initialize FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    description="Backend API for the OrthoBite Orthodontics and Bite Alignment Platform.",
)

# ---------------------------------------------------------------------------
# Database table creation
# ---------------------------------------------------------------------------
try:
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialized successfully.")
except Exception as e:
    logger.warning(f"Database initialization warning: {e}")

# ---------------------------------------------------------------------------
# Middleware (CORS, logging, security headers)
# ---------------------------------------------------------------------------
setup_middleware(app)

# ---------------------------------------------------------------------------
# Static files — serve uploads at /uploads/...
# ---------------------------------------------------------------------------
upload_dirs = [
    settings.TOOTH_CHART_DIR,
    settings.SIGNATURES_DIR,
    settings.DOCTORS_DIR,
    settings.SCANS_DIR,
    settings.PROFILES_DIR,
]
for folder in upload_dirs:
    os.makedirs(folder, exist_ok=True)

app.mount(f"/{settings.UPLOAD_DIR}", StaticFiles(directory=settings.UPLOAD_DIR), name=settings.UPLOAD_DIR)

# ---------------------------------------------------------------------------
# Health / Root Endpoints
# ---------------------------------------------------------------------------
@app.get("/", tags=["Health"])
def root():
    return {
        "app": settings.APP_NAME,
        "status": "online",
        "version": "0.1.0",
        "docs_url": "/docs",
    }


@app.get("/health", tags=["Health"])
def health():
    return {
        "status": "healthy",
        "database": engine.name,
    }

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(auth_router)
app.include_router(user_router)
app.include_router(patient_router)
app.include_router(doctor_router)
app.include_router(appointment_router)

