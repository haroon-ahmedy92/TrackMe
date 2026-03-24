from __future__ import annotations

import hmac
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import NAMESPACE_DNS, UUID, uuid5

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import Role, jwt
from app.db.models import Organization, User, UserRole


@dataclass(frozen=True)
class AuthenticatedOperator:
    user: User
    email: str
    full_name: str
    token: str
    ui_role: str


class LocalAuthService:
    def is_enabled(self) -> bool:
        return settings.local_auth_enabled

    async def authenticate(self, session: AsyncSession, *, email: str, password: str) -> AuthenticatedOperator:
        if not self.is_enabled():
            raise PermissionError('Local operator authentication is disabled.')
        if not settings.jwt_shared_secret:
            raise RuntimeError('JWT_SHARED_SECRET must be configured for local operator authentication.')

        account = self._bootstrap_account()
        if account is None:
            raise RuntimeError('Pilot bootstrap operator credentials are not configured.')
        if not hmac.compare_digest(account.email.lower(), email.strip().lower()):
            raise PermissionError('Invalid email or password.')
        if not hmac.compare_digest(account.password, password):
            raise PermissionError('Invalid email or password.')

        organization = await self._ensure_org(session, account.org_id, account.org_slug, account.org_name)
        user = await self._ensure_user(session, organization.id, account)
        token = self._issue_token(account)
        return AuthenticatedOperator(
            user=user,
            email=account.email,
            full_name=account.full_name,
            token=token,
            ui_role=account.ui_role,
        )

    async def _ensure_org(self, session: AsyncSession, org_id: UUID, slug: str, name: str) -> Organization:
        organization = (
            await session.execute(select(Organization).where(Organization.id == org_id))
        ).scalar_one_or_none()
        if organization is None:
            organization = Organization(
                id=org_id,
                slug=slug,
                name=name,
                created_at=datetime.now(timezone.utc),
                is_active=True,
            )
            session.add(organization)
            await session.flush()
            return organization

        organization.slug = slug
        organization.name = name
        organization.is_active = True
        await session.flush()
        return organization

    async def _ensure_user(self, session: AsyncSession, org_id: UUID, account: '_BootstrapAccount') -> User:
        user = (
            await session.execute(select(User).where(User.org_id == org_id, User.subject == account.subject))
        ).scalar_one_or_none()
        if user is None:
            user = User(
                org_id=org_id,
                subject=account.subject,
                display_name=account.full_name,
                email=account.email,
                role=account.user_role,
                is_active=True,
                created_at=datetime.now(timezone.utc),
            )
            session.add(user)
            await session.flush()
            return user

        user.display_name = account.full_name
        user.email = account.email
        user.role = account.user_role
        user.is_active = True
        await session.flush()
        return user

    def _issue_token(self, account: '_BootstrapAccount') -> str:
        now = datetime.now(timezone.utc)
        claims = {
            'sub': account.subject,
            'org_id': str(account.org_id),
            'roles': [role.value for role in account.claim_roles],
            'email': account.email,
            'name': account.full_name,
            'iat': int(now.timestamp()),
            'exp': int((now + timedelta(hours=12)).timestamp()),
        }
        if settings.jwt_issuer:
            claims['iss'] = settings.jwt_issuer
        if settings.jwt_audience:
            claims['aud'] = settings.jwt_audience
        return jwt.encode(claims, settings.jwt_shared_secret, algorithm=settings.jwt_algorithms[0])

    def _bootstrap_account(self) -> '_BootstrapAccount' | None:
        if not settings.pilot_bootstrap_admin_email or not settings.pilot_bootstrap_admin_password:
            return None

        org_id = (
            UUID(settings.pilot_bootstrap_org_id)
            if settings.pilot_bootstrap_org_id
            else uuid5(NAMESPACE_DNS, f'trackme:{settings.pilot_bootstrap_org_slug}')
        )
        role_name = settings.pilot_bootstrap_admin_role.lower().strip()
        if role_name == 'security':
            user_role = UserRole.SECURITY_OPERATOR
            claim_roles = {Role.SECURITY, Role.SECURITY_OPERATOR}
            ui_role = 'security'
        elif role_name == 'owner':
            user_role = UserRole.OWNER
            claim_roles = {Role.OWNER}
            ui_role = 'owner'
        else:
            user_role = UserRole.ADMIN
            claim_roles = {Role.ADMIN, Role.ORG_ADMIN}
            ui_role = 'admin'

        email = settings.pilot_bootstrap_admin_email.strip().lower()
        return _BootstrapAccount(
            email=email,
            password=settings.pilot_bootstrap_admin_password,
            full_name=settings.pilot_bootstrap_admin_name.strip() or 'Pilot Admin',
            org_id=org_id,
            org_slug=settings.pilot_bootstrap_org_slug.strip(),
            org_name=settings.pilot_bootstrap_org_name.strip(),
            subject=f'local:{email}',
            user_role=user_role,
            claim_roles=claim_roles,
            ui_role=ui_role,
        )


@dataclass(frozen=True)
class _BootstrapAccount:
    email: str
    password: str
    full_name: str
    org_id: UUID
    org_slug: str
    org_name: str
    subject: str
    user_role: UserRole
    claim_roles: set[Role]
    ui_role: str
