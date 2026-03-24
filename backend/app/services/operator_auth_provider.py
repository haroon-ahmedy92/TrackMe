from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User


@dataclass(frozen=True)
class AuthenticatedOperator:
    user: User
    email: str
    full_name: str
    token: str
    ui_role: str


class OperatorAuthProvider(ABC):
    @abstractmethod
    def is_enabled(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def authenticate(self, session: AsyncSession, *, email: str, password: str) -> AuthenticatedOperator:
        raise NotImplementedError
