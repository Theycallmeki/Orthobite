import logging
from typing import Optional
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Response,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from jose import JWTError, jwt
from sqlalchemy.orm import Session

import controllers.chat as chat_controller
from config.database import SessionLocal, get_db
from config.settings import settings
from dependencies import require_role
from models.chat import ChatAttachment, ChatMessage
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
from services.images import MAX_IMAGE_SIZE_BYTES, validate_image_bytes

logger = logging.getLogger("orthobite.chat")

router = APIRouter(prefix="/chat", tags=["Live Chat & Messaging"])
ws_router = APIRouter(tags=["Live Chat & Messaging"])
require_chat_user = require_role(*chat_controller.CHAT_ROLES)
require_chat_secretary = require_role(UserRole.SECRETARY)


def authenticate_ws_token(token: Optional[str], db: Session) -> Optional[User]:
    """Validates JWT access token passed via WebSocket query parameters."""
    if not token:
        return None
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id_str = payload.get("sub")
        if not user_id_str or payload.get("type", "access") != "access":
            return None
        user_id = int(user_id_str)
        user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
        return user
    except (JWTError, ValueError):
        return None


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
    connected_user_id = None
    try:
        user = authenticate_ws_token(token, db)
        if not user or user.role not in chat_controller.CHAT_ROLES:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        await manager.connect(user.id, websocket)
        connected_user_id = user.id


        await websocket.send_json({
            "type": "connection_ack",
            "user_id": user.id,
            "username": user.username,
            "role": user.role.value if hasattr(user.role, "value") else str(user.role),
            "message": "Connected to OrthoBite Live Chat.",
        })
        db.commit()

        while True:
            data = await websocket.receive_json()
            if not isinstance(data, dict):
                await websocket.send_json({"type": "error", "detail": "Invalid chat frame."})
                continue

            frame_type = data.get("type", "send_message")
            if frame_type == "ping":
                await websocket.send_json({"type": "pong"})
                continue

            conv_id = data.get("conversation_id")
            if type(conv_id) is not int or conv_id <= 0:
                await websocket.send_json({"type": "error", "detail": "A conversation ID is required."})
                continue
            try:
                conv = chat_controller.get_accessible_conversation(db, conv_id, user, lock=frame_type == "send_message")
                if frame_type == "typing":
                    payload = {
                        "type": "typing", "conversation_id": conv_id, "user_id": user.id,
                        "username": user.full_name or user.username,
                    }
                elif frame_type == "read":
                    result = chat_controller.mark_conversation_as_read(db, conv_id, user.id)
                    payload = {
                        "type": "read_receipt", "conversation_id": conv_id, "read_by": user.id,
                        "marked_count": result.marked_read_count,
                    }
                elif frame_type == "send_message":
                    content = data.get("content")
                    if not isinstance(content, str):
                        raise HTTPException(status_code=422, detail="Message text is required.")
                    message = chat_controller.create_chat_message(db, conv, user, content)
                    payload = _message_payload(message)
                else:
                    raise HTTPException(status_code=422, detail="Unsupported chat frame.")
                recipients = chat_controller.get_recipient_ids(db, conv, user)
                if frame_type == "send_message":
                    recipients.add(user.id)
                db.commit()
                await manager.broadcast_to_users(recipients, payload)
            except HTTPException as exc:
                db.rollback()
                await websocket.send_json({"type": "error", "detail": exc.detail})

    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("WebSocket chat failed")
    finally:
        if connected_user_id is not None:
            manager.disconnect(connected_user_id, websocket)
        db.close()


def _message_payload(message: ChatMessageResponse) -> dict:
    return {
        "type": "new_message",
        "conversation_id": message.conversation_id,
        "message": message.model_dump(mode="json"),
    }


@router.get(
    "/conversations",
    response_model=ConversationListResponse,
    summary="Get conversation inbox with unread counts",
)
def get_conversations(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_chat_user),
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
async def initiate_conversation(
    data: Optional[ConversationCreate] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_chat_user),
):
    """Initiates a conversation between a patient and the clinic secretary."""
    if current_user.role == UserRole.SECRETARY:
        if not data or not data.patient_id:
            raise HTTPException(status_code=400, detail="patient_id is required when a secretary creates a conversation.")
        target_patient_id = data.patient_id
        secretary_id = current_user.id
    else:
        target_patient_id = current_user.id
        secretary_id = None

    conv = chat_controller.get_or_create_conversation(db, target_patient_id, secretary_id)
    recipients = chat_controller.get_recipient_ids(db, conv, current_user)
    await manager.broadcast_to_users(recipients, {"type": "conversation_updated", "conversation_id": conv.id})
    return chat_controller.format_conversation_response(db, conv, current_user.id)


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_chat_secretary),
):
    conv = chat_controller.get_accessible_conversation(db, conversation_id, current_user, lock=True)
    recipients = chat_controller.get_active_secretary_ids(db) | {conv.patient_id}
    db.delete(conv)
    db.commit()
    await manager.broadcast_to_users(recipients, {"type": "conversation_deleted", "conversation_id": conversation_id})
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/conversations/{conversation_id}/history",
    response_model=ChatHistoryResponse,
    summary="Get paginated message history",
)
def get_conversation_history(
    conversation_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    newest: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_chat_user),
):
    """Retrieves paginated chat history for a conversation."""
    chat_controller.get_accessible_conversation(db, conversation_id, current_user)
    return chat_controller.get_chat_history(db, conversation_id, page=page, page_size=page_size, newest=newest)


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
    current_user: User = Depends(require_chat_user),
):
    """HTTP fallback endpoint to send a message without a WebSocket."""
    conv = chat_controller.get_accessible_conversation(db, conversation_id, current_user, lock=True)
    msg_resp = chat_controller.create_chat_message(db, conv, current_user, data.content)
    recipients = chat_controller.get_recipient_ids(db, conv, current_user) | {current_user.id}
    await manager.broadcast_to_users(recipients, _message_payload(msg_resp))
    return msg_resp


@router.post("/conversations/{conversation_id}/images", response_model=ChatMessageResponse, status_code=status.HTTP_201_CREATED)
async def send_image(
    conversation_id: int,
    file: UploadFile = File(...),
    caption: str = Form("", max_length=2000),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_chat_user),
):
    chat_controller.get_accessible_conversation(db, conversation_id, current_user)
    data = await file.read(MAX_IMAGE_SIZE_BYTES + 1)
    extension = validate_image_bytes(data)
    media_type = "image/jpeg" if extension == ".jpg" else f"image/{extension[1:]}"
    conv = chat_controller.get_accessible_conversation(db, conversation_id, current_user, lock=True)
    message = chat_controller.create_chat_message(
        db, conv, current_user, caption, ChatAttachment(media_type=media_type, image_data=data),
    )
    recipients = chat_controller.get_recipient_ids(db, conv, current_user) | {current_user.id}
    await manager.broadcast_to_users(recipients, _message_payload(message))
    return message


@router.get("/conversations/{conversation_id}/messages/{message_id}/image")
def get_message_image(
    conversation_id: int,
    message_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_chat_user),
):
    chat_controller.get_accessible_conversation(db, conversation_id, current_user)
    attachment = db.query(ChatAttachment).join(ChatMessage).filter(
        ChatAttachment.message_id == message_id, ChatMessage.conversation_id == conversation_id,
    ).first()
    if attachment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="This message has no image.")
    return Response(
        content=attachment.image_data,
        media_type=attachment.media_type,
        headers={"Cache-Control": "private, no-store"},
    )


@router.post(
    "/conversations/{conversation_id}/read",
    response_model=MarkReadResponse,
    summary="Mark messages as read",
)
async def mark_messages_read(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_chat_user),
):
    """Marks all incoming messages in this conversation as read."""
    conv = chat_controller.get_accessible_conversation(db, conversation_id, current_user)
    res = chat_controller.mark_conversation_as_read(db, conversation_id, current_user.id)
    recipients = chat_controller.get_recipient_ids(db, conv, current_user)
    await manager.broadcast_to_users(recipients, {
        "type": "read_receipt",
        "conversation_id": conversation_id,
        "read_by": current_user.id,
        "marked_count": res.marked_read_count,
    })
    return res
