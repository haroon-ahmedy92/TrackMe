from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_local_auth_service
from app.db.base import get_db_session
from app.schemas.auth import AuthUserProfile, LoginRequest, LoginResponse
from app.services.operator_auth_provider import OperatorAuthProvider

router = APIRouter(prefix='/auth', tags=['auth'])


@router.post('/login', response_model=LoginResponse)
async def login(
    payload: LoginRequest,
    session: AsyncSession = Depends(get_db_session),
    auth_service: OperatorAuthProvider = Depends(get_local_auth_service),
) -> LoginResponse:
    try:
        authenticated = await auth_service.authenticate(
            session,
            email=payload.email,
            password=payload.password,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    await session.commit()
    return LoginResponse(
        access_token=authenticated.token,
        profile=AuthUserProfile(
            id=str(authenticated.user.id),
            full_name=authenticated.full_name,
            email=authenticated.email,
            role=authenticated.ui_role,
            tenant_id=str(authenticated.user.org_id),
        ),
    )
