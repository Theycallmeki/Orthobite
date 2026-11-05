from datetime import datetime
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, or_

from models.chat import Conversation, ChatMessage
from models.users import User, UserRole
from schemas.chat import (
    ChatMessageResponse,
    ConversationListResponse,
    ConversationResponse,
    ChatHistoryResponse,
    MarkReadResponse,
)


def get_conversation_or_404(db: Session, conversation_id: int) -> Conversation:
    """Fetch conversation by ID or raise 404."""
    conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation with ID {conversation_id} not found.",
        )
    return conv


def get_or_create_conversation(
    db: Session, patient_id: int, secretary_id: Optional[int] = None
) -> Conversation:
    """
    Finds existing conversation for a patient or initiates a new one.
    """
    patient = db.query(User).filter(User.id == patient_id).first()
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
    elif secretary_id is not None and conv.secretary_id is None:

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

    return ConversationResponse(
        id=conv.id,
        patient_id=conv.patient_id,
        patient_name=conv.patient.full_name if conv.patient else None,
        secretary_id=conv.secretary_id,
        secretary_name=conv.secretary.full_name if conv.secretary else None,
        unread_count=unread_count,
        last_message=format_message_response(last_msg) if last_msg else None,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
    )


def list_conversations(db: Session, current_user: User) -> ConversationListResponse:
    """
    Returns inbox list for staff with unread badge counts, or the patient's own conversation.
    """
    is_staff = current_user.role in (
        UserRole.ADMIN,
        UserRole.SECRETARY,
        UserRole.DOCTOR,
        UserRole.ORTHODONTIST,
    )

    if is_staff:
        conversations = (
            db.query(Conversation)
            .order_by(Conversation.updated_at.desc())
            .all()
        )
    else:

        conversations = (
            db.query(Conversation)
            .filter(Conversation.patient_id == current_user.id)
            .order_by(Conversation.updated_at.desc())
            .all()
        )
        if not conversations:

            conv = get_or_create_conversation(db, current_user.id)
            conversations = [conv]

    conv_responses = [
        format_conversation_response(db, c, current_user.id) for c in conversations
    ]
    total_unread = sum(c.unread_count for c in conv_responses)

    return ConversationListResponse(
        conversations=conv_responses,
        total_unread=total_unread,
    )


def get_chat_history(
    db: Session, conversation_id: int, page: int = 1, page_size: int = 50
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
    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.conversation_id == conversation_id)
        .order_by(ChatMessage.created_at.asc())
        .offset(offset)
        .limit(page_size)
        .all()
    )

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
    db: Session, conversation_id: int, sender_id: int, content: str
) -> ChatMessageResponse:
    """Stores a new message in the database and updates conversation timestamp."""
    conv = get_conversation_or_404(db, conversation_id)

    sender = db.query(User).filter(User.id == sender_id).first()
    if not sender:
        raise HTTPException(status_code=404, detail="Sender user not found.")


    if conv.secretary_id is None and sender.role in (UserRole.ADMIN, UserRole.SECRETARY):
        conv.secretary_id = sender.id

    msg = ChatMessage(
        conversation_id=conversation_id,
        sender_id=sender_id,
        content=content.strip(),
        is_read=False,
    )
    db.add(msg)
    conv.updated_at = func.now()
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
