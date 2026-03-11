from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from fastapi import Depends, Header, HTTPException, status
try:
    from jose import jwt
except ModuleNotFoundError:  # pragma: no cover
    class _FallbackJWT:
        @staticmethod
        def get_unverified_claims(token: str) -> dict:
            return {}

    jwt = _FallbackJWT()

from app.core.config import settings


class Role(str, Enum):
    OWNER = 'owner'
    ADMIN = 'admin'
    SECURITY = 'security'
    SUPER_ADMIN = 'super_admin'
    ORG_ADMIN = 'org_admin'
    INCIDENT_RESPONDER = 'incident_responder'
    AUDITOR = 'auditor'


@dataclass(frozen=True)
class Principal:
    subject: str
    roles: set[Role]
    organization_id: str | None


def _decode_token(token: str) -> dict:
    """
    Decode and verify JWT when verification config is present.
    Insecure unverified fallback is allowed only in development/test when explicitly enabled.
    """
    if settings.jwt_shared_secret:
        options = {
            'verify_signature': True,
            'verify_aud': settings.jwt_audience is not None,
            'verify_iss': settings.jwt_issuer is not None,
        }
        return jwt.decode(
            token,
            settings.jwt_shared_secret,
            algorithms=settings.jwt_algorithms,
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
            options=options,
        )

    if settings.environment in {'development', 'test'} and settings.allow_insecure_jwt_for_dev:
        return jwt.get_unverified_claims(token)

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail='Token verification is not configured',
    )


def get_current_principal(authorization: str | None = Header(default=None)) -> Principal:
    if authorization is None or not authorization.startswith('Bearer '):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Missing bearer token')

    token = authorization.removeprefix('Bearer ').strip()
    try:
        claims = _decode_token(token)
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid token') from exc

    roles_raw = claims.get('roles', [])
    if isinstance(roles_raw, str):
        roles_raw = [roles_raw]
    role_values = {r.value for r in Role}
    roles = {Role(role) for role in roles_raw if isinstance(role, str) and role in role_values}
    principal = Principal(
        subject=str(claims.get('sub', 'unknown')),
        roles=roles,
        organization_id=claims.get('org_id') or claims.get('organization_id'),
    )
    return principal


def require_roles(*allowed: Role):
    def _dep(principal: Principal = Depends(get_current_principal)) -> Principal:
        if not principal.roles.intersection(set(allowed)):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Insufficient role')
        return principal

    return _dep


def require_org_match(org_id: str):
    def _dep(principal: Principal = Depends(get_current_principal)) -> Principal:
        if principal.organization_id is None or principal.organization_id != org_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Tenant access denied')
        return principal

    return _dep
