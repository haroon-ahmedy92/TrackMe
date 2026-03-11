from __future__ import annotations

from fastapi import APIRouter

from app.schemas.common import APIMessage

router = APIRouter(tags=['health'])


@router.get('/health', response_model=APIMessage)
async def health() -> APIMessage:
    return APIMessage(message='ok')
