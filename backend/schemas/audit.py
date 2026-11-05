from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from models.audit import AuditAction


class AuditLogResponse(BaseModel):
    id:          int
    actor_id:    Optional[int]
    action:      AuditAction
    resource:    str
    resource_id: Optional[int]
    ip_address:  Optional[str]
    extra:       Optional[Dict[str, Any]]
    timestamp:   datetime

    model_config = {"from_attributes": True}


class AuditLogListResponse(BaseModel):
    total:  int
    page:   int
    limit:  int
    items:  List[AuditLogResponse]


class AuditPurgeResponse(BaseModel):
    deleted_count: int
    cutoff_date:   datetime
    message:       str
