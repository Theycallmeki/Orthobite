import json
import logging
from typing import Optional
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from jose import JWTError, jwt
from sqlalchemy.orm import Session

import controllers.chat as chat_controller
from config.database import SessionLocal, get_db
from config.settings import settings
from dependencies import get_current_user, require_staff
from models.chat import Conversation
from models.users import User, UserRole
from schemas.chat import (
    ChatHistoryResponse,
    ChatMessageCreate,
    ChatMessageResponse,
    ConversationCreate,
    ConversationListResponse,
    ConversationResponse,
    MarkReadResponse,
)
from services.websocket import manager

logger = logging.getLogger("orthobite.chat")

router = APIRouter(prefix="/chat", tags=["Live Chat & Messaging"])
ws_router = APIRouter(tags=["Live Chat & Messaging"])


# ---------------------------------------------------------------------------
# WebSocket Authentication Helper
# ---------------------------------------------------------------------------

def authenticate_ws_token(token: Optional[str], db: Session) -> Optional[User]:
    """Validates JWT access token passed via WebSocket query parameters."""
    if not token:
        return None
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id_str = payload.get("sub")
        if not user_id_str:
            return None
        user_id = int(user_id_str)
        user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
        return user
    except (JWTError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Live Bi-Directional WebSocket Connection
# ---------------------------------------------------------------------------

@ws_router.websocket("/ws/chat")
async def websocket_chat_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(None),
):
    """
    Live bi-directional WebSocket chat socket for Patients and Secretaries.
    Accepts JWT token in query parameter (?token=...).
    """
    db = SessionLocal()
    try:
        user = authenticate_ws_token(token, db)
        if not user:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        await manager.connect(user.id, websocket)

        # Connection acknowledgment frame
        await websocket.send_json({
            "type": "connection_ack",
            "user_id": user.id,
            "username": user.username,
            "role": user.role.value if hasattr(user.role, "value") else str(user.role),
            "message": "Connected to OrthoBite Live Chat.",
        })

        while True:
            data = await websocket.receive_json()
            frame_type = data.get("type", "send_message")

            if frame_type == "ping":
                await websocket.send_json({"type": "pong"})

            elif frame_type == "typing":
                conv_id = data.get("conversation_id")
                if conv_id:
                    conv = db.query(Conversation).filter(Conversation.id == conv_id).first()
                    if conv:
                        recipient_id = conv.secretary_id if user.id == conv.patient_id else conv.patient_id
                        if recipient_id:
                            await manager.send_personal_message(recipient_id, {
                                "type": "typing",
                                "conversation_id": conv_id,
                                "user_id": user.id,
                                "username": user.full_name or user.username,
                            })

            elif frame_type == "read":
                conv_id = data.get("conversation_id")
                if conv_id:
                    res = chat_controller.mark_conversation_as_read(db, conv_id, user.id)
                    conv = db.query(Conversation).filter(Conversation.id == conv_id).first()
                    if conv:
                        recipient_id = conv.secretary_id if user.id == conv.patient_id else conv.patient_id
                        if recipient_id:
                            await manager.send_personal_message(recipient_id, {
                                "type": "read_receipt",
                                "conversation_id": conv_id,
                                "read_by": user.id,
                                "marked_count": res.marked_read_count,
                            })

            elif frame_type == "send_message":
                conv_id = data.get("conversation_id")
                content = data.get("content", "").strip()

                if not conv_id or not content:
                    await websocket.send_json({
                        "type": "error",
                        "detail": "conversation_id and content are required.",
                    })
                    continue

                # Verify user is a participant or staff
                conv = db.query(Conversation).filter(Conversation.id == conv_id).first()
                if not conv:
                    await websocket.send_json({"type": "error", "detail": "Conversation not found."})
                    continue

                is_staff = user.role in (UserRole.ADMIN, UserRole.SECRETARY, UserRole.DOCTOR, UserRole.ORTHODONTIST)
                if not is_staff and conv.patient_id != user.id:
                    await websocket.send_json({"type": "error", "detail": "Not authorized in this conversation."})
                    continue

                # Persist message
                msg_response = chat_controller.create_chat_message(db, conv_id, user.id, content)
                payload = {
                    "type": "new_message",
                    "conversation_id": conv_id,
                    "message": msg_response.model_dump(mode="json"),
                }

                # Determine recipients
                # If patient sent -> notify assigned secretary (or all online staff if unassigned)
                if user.id == conv.patient_id:
                    if conv.secretary_id:
                        await manager.send_personal_message(conv.secretary_id, payload)
                    else:
                        # Broadcast to all staff online
                        staff_users = db.query(User.id).filter(
                            User.role.in_([UserRole.SECRETARY, UserRole.ADMIN])
                        ).all()
                        for (s_id,) in staff_users:
                            await manager.send_personal_message(s_id, payload)
                else:
                    # Staff sent -> notify patient
                    await manager.send_personal_message(conv.patient_id, payload)

                # Send confirmation back to sender's devices
                await manager.send_personal_message(user.id, payload)

    except WebSocketDisconnect:
        if user:
            manager.disconnect(user.id, websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        if user:
            manager.disconnect(user.id, websocket)
    finally:
        db.close()


# ---------------------------------------------------------------------------
# REST Endpoints
# ---------------------------------------------------------------------------

@router.get(
    "/conversations",
    response_model=ConversationListResponse,
    summary="Get conversation inbox with unread counts",
)
def get_conversations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns secretary inbox with unread counts, or the authenticated patient's conversation.
    """
    return chat_controller.list_conversations(db, current_user)


@router.post(
    "/conversations",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create or get active conversation",
)
def initiate_conversation(
    data: Optional[ConversationCreate] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Initiates a conversation between a patient and clinic staff."""
    is_staff = current_user.role in (UserRole.ADMIN, UserRole.SECRETARY, UserRole.DOCTOR, UserRole.ORTHODONTIST)
    if is_staff:
        if not data or not data.patient_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="patient_id is required when staff creates a conversation.",
            )
        target_patient_id = data.patient_id
        secretary_id = current_user.id
    else:
        target_patient_id = current_user.id
        secretary_id = None

    conv = chat_controller.get_or_create_conversation(db, target_patient_id, secretary_id)
    return chat_controller.format_conversation_response(db, conv, current_user.id)


@router.get(
    "/conversations/{conversation_id}/history",
    response_model=ChatHistoryResponse,
    summary="Get paginated message history",
)
def get_conversation_history(
    conversation_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieves paginated chat history for a conversation."""
    conv = chat_controller.get_conversation_or_404(db, conversation_id)
    is_staff = current_user.role in (UserRole.ADMIN, UserRole.SECRETARY, UserRole.DOCTOR, UserRole.ORTHODONTIST)
    if not is_staff and conv.patient_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this conversation.",
        )
    return chat_controller.get_chat_history(db, conversation_id, page=page, page_size=page_size)


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=ChatMessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Send message via HTTP fallback",
)
async def send_message_http(
    conversation_id: int,
    data: ChatMessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """HTTP fallback endpoint to send a message without a WebSocket."""
    conv = chat_controller.get_conversation_or_404(db, conversation_id)
    is_staff = current_user.role in (UserRole.ADMIN, UserRole.SECRETARY, UserRole.DOCTOR, UserRole.ORTHODONTIST)
    if not is_staff and conv.patient_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this conversation.",
        )

    msg_resp = chat_controller.create_chat_message(db, conversation_id, current_user.id, data.content)

    # Real-time notification to active WebSocket listeners
    payload = {
        "type": "new_message",
        "conversation_id": conversation_id,
        "message": msg_resp.model_dump(mode="json"),
    }
    recipient_id = conv.secretary_id if current_user.id == conv.patient_id else conv.patient_id
    if recipient_id:
        await manager.send_personal_message(recipient_id, payload)

    return msg_resp


@router.post(
    "/conversations/{conversation_id}/read",
    response_model=MarkReadResponse,
    summary="Mark messages as read",
)
async def mark_messages_read(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Marks all incoming messages in this conversation as read."""
    conv = chat_controller.get_conversation_or_404(db, conversation_id)
    is_staff = current_user.role in (UserRole.ADMIN, UserRole.SECRETARY, UserRole.DOCTOR, UserRole.ORTHODONTIST)
    if not is_staff and conv.patient_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this conversation.",
        )

    res = chat_controller.mark_conversation_as_read(db, conversation_id, current_user.id)

    # Real-time read receipt notification
    recipient_id = conv.secretary_id if current_user.id == conv.patient_id else conv.patient_id
    if recipient_id:
        await manager.send_personal_message(recipient_id, {
            "type": "read_receipt",
            "conversation_id": conversation_id,
            "read_by": current_user.id,
            "marked_count": res.marked_read_count,
        })

    return res
