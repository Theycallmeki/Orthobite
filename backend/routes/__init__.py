from routes.auth import router as auth_router
from routes.user import router as user_router
from routes.patient import router as patient_router
from routes.doctor import router as doctor_router

__all__ = ["auth_router", "user_router", "patient_router", "doctor_router"]
