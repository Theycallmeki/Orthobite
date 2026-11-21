from datetime import datetime
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from models.chat import ChatAttachment, Conversation, ChatMessage
from models.users import User, UserRole
from schemas.chat import (
    ChatMessageResponse,
    ConversationListResponse,
    ConversationResponse,
    ChatHistoryResponse,
    MarkReadResponse,
)


CHAT_ROLES = (UserRole.PATIENT, UserRole.SECRETARY)


def get_conversation_or_404(db: Session, conversation_id: int, *, lock: bool = False) -> Conversation:
    """Fetch conversation by ID or raise 404."""
    query = db.query(Conversation).filter(Conversation.id == conversation_id)
    conv = (query.with_for_update() if lock else query).first()
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation with ID {conversation_id} not found.",
        )
    return conv


def get_accessible_conversation(db: Session, conversation_id: int, user: User, *, lock: bool = False) -> Conversation:
    conversation = get_conversation_or_404(db, conversation_id, lock=lock)
    if (
        user.role not in CHAT_ROLES
        or conversation.patient.role != UserRole.PATIENT
        or (user.role == UserRole.PATIENT and conversation.patient_id != user.id)
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have access to this conversation.")
    return conversation


def active_secretary(conversation: Conversation) -> Optional[User]:
    secretary = conversation.secretary
    if secretary and secretary.role == UserRole.SECRETARY and secretary.is_active:
        return secretary
    return None


def get_recipient_ids(db: Session, conversation: Conversation, sender: User) -> set[int]:
    if sender.role == UserRole.SECRETARY:
        return {conversation.patient_id} if conversation.patient.is_active else set()
    secretary = active_secretary(conversation)
    if secretary:
        return {secretary.id}
    return get_active_secretary_ids(db)


def get_active_secretary_ids(db: Session) -> set[int]:
    return {
        user_id for (user_id,) in db.query(User.id).filter(
            User.role == UserRole.SECRETARY, User.is_active.is_(True),
        )
    }


def get_or_create_conversation(
    db: Session, patient_id: int, secretary_id: Optional[int] = None
) -> Conversation:
    """
    Finds existing conversation for a patient or initiates a new one.
    """
    patient = db.query(User).filter(
        User.id == patient_id, User.role == UserRole.PATIENT, User.is_active.is_(True),
    ).with_for_update().first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient user with ID {patient_id} does not exist.",
        )

    conv = db.query(Conversation).filter(Conversation.patient_id == patient_id).first()
    if not conv:
        conv = Conversation(
            patient_id=patient_id,
            secretary_id=secretary_id,
        )
        db.add(conv)
        db.commit()
        db.refresh(conv)
    elif secretary_id is not None and active_secretary(conv) is None:

        conv.secretary_id = secretary_id
        db.commit()
        db.refresh(conv)

    return conv


def format_message_response(msg: ChatMessage) -> ChatMessageResponse:
    """Helper to convert ChatMessage ORM model to Pydantic response."""
    return ChatMessageResponse(
        id=msg.id,
        conversation_id=msg.conversation_id,
        sender_id=msg.sender_id,
        sender_name=msg.sender.full_name if msg.sender else None,
        sender_role=msg.sender.role.value if msg.sender and hasattr(msg.sender.role, "value") else None,
        content=msg.content,
        has_image=msg.attachment is not None,
        is_read=msg.is_read,
        created_at=msg.created_at,
    )


def format_conversation_response(
    db: Session, conv: Conversation, for_user_id: int
) -> ConversationResponse:
    """
    Builds conversation summary including unread message count and last message.
    """

    unread_count = (
        db.query(func.count(ChatMessage.id))
        .filter(
            ChatMessage.conversation_id == conv.id,
            ChatMessage.sender_id != for_user_id,
            ChatMessage.is_read == False,
        )
        .scalar()
        or 0
    )

    last_msg = (
        db.query(ChatMessage)
        .filter(ChatMessage.conversation_id == conv.id)
        .order_by(ChatMessage.created_at.desc())
        .first()
    )

    secretary = active_secretary(conv)
    return ConversationResponse(
        id=conv.id,
        patient_id=conv.patient_id,
        patient_name=conv.patient.full_name if conv.patient else None,
        secretary_id=secretary.id if secretary else None,
        secretary_name=secretary.full_name if secretary else None,
        unread_count=unread_count,
        last_message=format_message_response(last_msg) if last_msg else None,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
    )


def list_conversations(db: Session, current_user: User) -> ConversationListResponse:
    """
    Returns the secretary inbox, or the patient's own conversation.
    """
    if current_user.role == UserRole.SECRETARY:
        conversations = (
            db.query(Conversation)
            .filter(Conversation.patient.has(User.role == UserRole.PATIENT))
            .order_by(Conversation.updated_at.desc())
            .all()
        )
    elif current_user.role == UserRole.PATIENT:

        conversations = (
            db.query(Conversation)
            .filter(Conversation.patient_id == current_user.id)
            .order_by(Conversation.updated_at.desc())
            .all()
        )
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Chat is available to patients and secretaries.")

    conv_responses = [
        format_conversation_response(db, c, current_user.id) for c in conversations
    ]
    total_unread = sum(c.unread_count for c in conv_responses)

    return ConversationListResponse(
        conversations=conv_responses,
        total_unread=total_unread,
    )


def get_chat_history(
    db: Session, conversation_id: int, page: int = 1, page_size: int = 50, newest: bool = False,
) -> ChatHistoryResponse:
    """Retrieves paginated chat history for a conversation (chronological asc order)."""
    get_conversation_or_404(db, conversation_id)

    total_count = (
        db.query(func.count(ChatMessage.id))
        .filter(ChatMessage.conversation_id == conversation_id)
        .scalar()
        or 0
    )

    offset = (page - 1) * page_size
    order = (ChatMessage.created_at.desc(), ChatMessage.id.desc()) if newest else (
        ChatMessage.created_at.asc(), ChatMessage.id.asc(),
    )
    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.conversation_id == conversation_id)
        .order_by(*order)
        .offset(offset)
        .limit(page_size)
        .all()
    )
    if newest:
        messages.reverse()

    has_more = (offset + len(messages)) < total_count

    return ChatHistoryResponse(
        conversation_id=conversation_id,
        messages=[format_message_response(m) for m in messages],
        total_count=total_count,
        page=page,
        page_size=page_size,
        has_more=has_more,
    )


def create_chat_message(
    db: Session, conversation: Conversation, sender: User, content: str,
    attachment: Optional[ChatAttachment] = None,
) -> ChatMessageResponse:
    """Store a message in an authorized patient-secretary conversation."""
    content = content.strip()
    if len(content) > 2000 or (not content and attachment is None):
        raise HTTPException(status_code=422, detail="Enter a message of up to 2000 characters or attach an image.")
    if sender.role == UserRole.SECRETARY and active_secretary(conversation) is None:
        conversation.secretary_id = sender.id

    msg = ChatMessage(
        conversation_id=conversation.id,
        sender_id=sender.id,
        content=content,
        is_read=False,
        attachment=attachment,
    )
    db.add(msg)
    conversation.updated_at = func.now()
    db.commit()
    db.refresh(msg)
    return format_message_response(msg)


def mark_conversation_as_read(
    db: Session, conversation_id: int, current_user_id: int
) -> MarkReadResponse:
    """Marks incoming messages in this conversation as read."""
    get_conversation_or_404(db, conversation_id)

    updated_count = (
        db.query(ChatMessage)
        .filter(
            ChatMessage.conversation_id == conversation_id,
            ChatMessage.sender_id != current_user_id,
            ChatMessage.is_read == False,
        )
        .update({"is_read": True}, synchronize_session="fetch")
    )
    db.commit()

    return MarkReadResponse(
        conversation_id=conversation_id,
        marked_read_count=updated_count,
        message=f"{updated_count} messages marked as read.",
    )
