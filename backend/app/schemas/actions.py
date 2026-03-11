from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import RemoteActionKind


class RemoteActionRequestBody(BaseModel):
    device_id: UUID
    action: RemoteActionKind
    ticket_reference: str = Field(min_length=2, max_length=80)
    reason: str = Field(min_length=2, max_length=250)
    elevated_confirmation: bool = False
    acknowledge_wipe_tradeoff: bool = False


class RemoteActionResponse(BaseModel):
    action_id: UUID
    status: str
    requested_at: datetime
