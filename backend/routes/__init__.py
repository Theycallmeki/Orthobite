from routes.auth import router as auth_router
from routes.user import router as user_router
from routes.patient import router as patient_router
from routes.doctor import router as doctor_router
from routes.appointment import router as appointment_router
from routes.notification import router as notification_router
from routes.record import router as record_router
from routes.chat import router as chat_router, ws_router as ws_chat_router

__all__ = [
    "auth_router",
    "user_router",
    "patient_router",
    "doctor_router",
    "appointment_router",
    "notification_router",
    "record_router",
    "chat_router",
    "ws_chat_router",
]

