from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Organization, User
from app.schemas.platform import OrganizationCreateRequest, UserUpsertRequest


class TenantService:
    async def create_org(self, session: AsyncSession, payload: OrganizationCreateRequest) -> Organization:
        existing = (await session.execute(select(Organization).where(Organization.slug == payload.slug))).scalar_one_or_none()
        if existing is not None:
            raise ValueError('Organization slug already exists')

        org = Organization(
            slug=payload.slug,
            name=payload.name,
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )
        session.add(org)
        await session.flush()
        return org

    async def upsert_user(self, session: AsyncSession, payload: UserUpsertRequest) -> User:
        existing = (await session.execute(
            select(User).where(User.org_id == payload.org_id, User.subject == payload.subject)
        )).scalar_one_or_none()
        if existing:
            existing.role = payload.role
            existing.display_name = payload.display_name
            existing.email = payload.email
            existing.is_active = True
            await session.flush()
            return existing

        user = User(
            org_id=payload.org_id,
            subject=payload.subject,
            role=payload.role,
            display_name=payload.display_name,
            email=payload.email,
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )
        session.add(user)
        await session.flush()
        return user
