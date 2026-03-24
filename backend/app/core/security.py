from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import base64
import hashlib
import hmac
import json

from fastapi import Depends, Header, HTTPException, Request, status
try:
    from jose import jwt
except ModuleNotFoundError:  # pragma: no cover
    class _FallbackJWT:
        @staticmethod
        def encode(claims: dict, secret: str, algorithm: str = 'HS256') -> str:
            if algorithm != 'HS256':
                raise ValueError('Fallback JWT encoder supports only HS256.')
            header = {'alg': algorithm, 'typ': 'JWT'}
            signing_input = '.'.join(
                [
                    _b64url(json.dumps(header, separators=(',', ':'), sort_keys=True).encode('utf-8')),
                    _b64url(json.dumps(claims, separators=(',', ':'), sort_keys=True).encode('utf-8')),
                ]
            )
            signature = hmac.new(secret.encode('utf-8'), signing_input.encode('ascii'), hashlib.sha256).digest()
            return f'{signing_input}.{_b64url(signature)}'

        @staticmethod
        def decode(
            token: str,
            secret: str,
            algorithms: list[str],
            audience: str | None = None,
            issuer: str | None = None,
            options: dict | None = None,
        ) -> dict:
            if 'HS256' not in algorithms:
                raise ValueError('Fallback JWT decoder supports only HS256.')
            try:
                header_b64, payload_b64, signature_b64 = token.split('.')
            except ValueError as exc:
                raise ValueError('Malformed JWT') from exc

            signing_input = f'{header_b64}.{payload_b64}'
            expected = hmac.new(secret.encode('utf-8'), signing_input.encode('ascii'), hashlib.sha256).digest()
            actual = _b64url_decode(signature_b64)
            if not hmac.compare_digest(expected, actual):
                raise ValueError('Invalid JWT signature')

            payload = json.loads(_b64url_decode(payload_b64))
            verify_options = options or {}
            if verify_options.get('verify_aud', audience is not None) and audience is not None:
                if payload.get('aud') != audience:
                    raise ValueError('Invalid audience')
            if verify_options.get('verify_iss', issuer is not None) and issuer is not None:
                if payload.get('iss') != issuer:
                    raise ValueError('Invalid issuer')
            return payload

        @staticmethod
        def get_unverified_claims(token: str) -> dict:
            try:
                _header_b64, payload_b64, _signature_b64 = token.split('.')
            except ValueError:
                return {}
            return json.loads(_b64url_decode(payload_b64))

    jwt = _FallbackJWT()


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b'=').decode('ascii')


def _b64url_decode(value: str) -> bytes:
    padding = '=' * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)

from app.core.config import settings
from app.services.observability_service import security_signal_store


class Role(str, Enum):
    OWNER = 'owner'
    ADMIN = 'admin'
    SECURITY = 'security'
    SECURITY_OPERATOR = 'security_operator'
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


def get_current_principal(
    request: Request,
    authorization: str | None = Header(default=None),
) -> Principal:
    if authorization is None or not authorization.startswith('Bearer '):
        security_signal_store.record_auth_failure(
            path=request.url.path,
            ip_address=request.client.host if request.client else 'unknown',
            actor_hint=None,
            org_id=request.query_params.get('org_id'),
            reason='missing_bearer_token',
            request_id=getattr(request.state, 'request_id', None),
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Missing bearer token')

    token = authorization.removeprefix('Bearer ').strip()
    try:
        claims = _decode_token(token)
    except HTTPException:
        security_signal_store.record_auth_failure(
            path=request.url.path,
            ip_address=request.client.host if request.client else 'unknown',
            actor_hint=None,
            org_id=request.query_params.get('org_id'),
            reason='token_verification_not_configured',
            request_id=getattr(request.state, 'request_id', None),
        )
        raise
    except Exception as exc:  # pragma: no cover
        security_signal_store.record_auth_failure(
            path=request.url.path,
            ip_address=request.client.host if request.client else 'unknown',
            actor_hint=None,
            org_id=request.query_params.get('org_id'),
            reason='invalid_token',
            request_id=getattr(request.state, 'request_id', None),
        )
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
    def _dep(request: Request, principal: Principal = Depends(get_current_principal)) -> Principal:
        if not principal.roles.intersection(set(allowed)):
            security_signal_store.record_auth_failure(
                path=request.url.path,
                ip_address=request.client.host if request.client else 'unknown',
                actor_hint=principal.subject,
                org_id=principal.organization_id or request.query_params.get('org_id'),
                reason='insufficient_role',
                request_id=getattr(request.state, 'request_id', None),
            )
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Insufficient role')
        return principal

    return _dep


def require_org_match(org_id: str):
    def _dep(principal: Principal = Depends(get_current_principal)) -> Principal:
        if principal.organization_id is None or principal.organization_id != org_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Tenant access denied')
        return principal

    return _dep
