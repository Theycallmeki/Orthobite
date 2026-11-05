from datetime import datetime as py_datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, Field


class ChatMessageCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000, description="Message text content")


class ChatMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    conversation_id: int
    sender_id: int
    sender_name: Optional[str] = None
    sender_role: Optional[str] = None
    content: str
    is_read: bool
    created_at: py_datetime


class ConversationCreate(BaseModel):
    patient_id: Optional[int] = Field(
        None, description="Target Patient User ID (required if Staff is initiating chat)"
    )


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    patient_id: int
    patient_name: Optional[str] = None
    secretary_id: Optional[int] = None
    secretary_name: Optional[str] = None
    unread_count: int = 0
    last_message: Optional[ChatMessageResponse] = None
    created_at: py_datetime
    updated_at: py_datetime


class ConversationListResponse(BaseModel):
    conversations: List[ConversationResponse]
    total_unread: int = 0


class ChatHistoryResponse(BaseModel):
    conversation_id: int
    messages: List[ChatMessageResponse]
    total_count: int
    page: int = 1
    page_size: int = 50
    has_more: bool = False


class MarkReadResponse(BaseModel):
    conversation_id: int
    marked_read_count: int
    message: str = "Messages marked as read."


class WebSocketFrame(BaseModel):
    type: str = Field(..., description="Frame type: 'message', 'typing', 'read', 'error', 'ack'")
    conversation_id: Optional[int] = None
    sender_id: Optional[int] = None
    content: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    timestamp: Optional[py_datetime] = None
