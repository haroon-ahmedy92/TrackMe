from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


class Mode(str, Enum):
    NORMAL = 'normal'
    LOST_MODE = 'lost_mode'


class RemoteActionKind(str, Enum):
    LOCK = 'lock'
    WIPE = 'wipe'


class IncidentState(str, Enum):
    NORMAL = 'normal'
    SUSPECTED_LOST = 'suspected_lost'
    CONFIRMED_STOLEN = 'confirmed_stolen'
    RECOVERED = 'recovered'
    WIPED = 'wiped'
    DECOMMISSIONED = 'decommissioned'


class APIMessage(BaseModel):
    message: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
