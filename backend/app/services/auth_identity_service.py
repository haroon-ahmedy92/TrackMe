from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import Principal, Role
from app.db.models import Organization, User, UserRole


class AuthIdentityService:
    def map_role(self, principal: Principal) -> UserRole:
        if Role.SECURITY in principal.roles or Role.INCIDENT_RESPONDER in principal.roles:
            return UserRole.SECURITY
        if Role.ADMIN in principal.roles or Role.ORG_ADMIN in principal.roles or Role.SUPER_ADMIN in principal.roles:
            return UserRole.ADMIN
        return UserRole.OWNER

    async def ensure_user(self, session: AsyncSession, principal: Principal) -> User | None:
        if principal.organization_id is None:
            return None

        org = await self._ensure_org(session, principal.organization_id)
        stmt = select(User).where(User.org_id == org.id, User.subject == principal.subject)
        user = (await session.execute(stmt)).scalar_one_or_none()
        if user:
            return user

        created = User(
            org_id=org.id,
            subject=principal.subject,
            role=self.map_role(principal),
            created_at=datetime.now(timezone.utc),
            is_active=True,
        )
        session.add(created)
        await session.flush()
        return created

    async def _ensure_org(self, session: AsyncSession, org_id_raw: str) -> Organization:
        org_id = UUID(org_id_raw)
        stmt = select(Organization).where(Organization.id == org_id)
        org = (await session.execute(stmt)).scalar_one_or_none()
        if org:
            return org
        org = Organization(
            id=org_id,
            slug=f'org-{str(org_id)[:8]}',
            name=f'Org {str(org_id)[:8]}',
            created_at=datetime.now(timezone.utc),
            is_active=True,
        )
        session.add(org)
        await session.flush()
        return org
