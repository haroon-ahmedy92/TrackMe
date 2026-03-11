from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Device, DeviceKey
from app.schemas.platform import DeviceKeyRegisterRequest, DeviceKeyRotateRequest


class DeviceKeyService:
    async def register_key(self, session: AsyncSession, payload: DeviceKeyRegisterRequest) -> DeviceKey:
        device = await self._get_device(session, payload.device_id)
        if device.organization_id != payload.org_id:
            raise ValueError('Device does not belong to tenant org.')
        if not payload.public_key_pem.strip().startswith('-----BEGIN'):
            raise ValueError('public_key_pem must be in PEM format.')

        existing_same_key = (await session.execute(
            select(DeviceKey).where(DeviceKey.device_id == payload.device_id, DeviceKey.key_id == payload.key_id)
        )).scalar_one_or_none()
        if existing_same_key and existing_same_key.is_active:
            raise ValueError('An active key with this key_id already exists for the device.')

        if payload.rotate_existing_active:
            await session.execute(
                update(DeviceKey)
                .where(DeviceKey.device_id == payload.device_id, DeviceKey.is_active.is_(True))
                .values(is_active=False, rotated_at=datetime.now(timezone.utc))
            )

        record = DeviceKey(
            org_id=payload.org_id,
            device_id=payload.device_id,
            key_id=payload.key_id,
            public_key_pem=payload.public_key_pem,
            algorithm=payload.algorithm,
            is_active=True,
            created_at=datetime.now(timezone.utc),
            rotated_at=None,
        )
        session.add(record)
        await session.flush()
        return record

    async def rotate_key(self, session: AsyncSession, payload: DeviceKeyRotateRequest) -> DeviceKey:
        return await self.register_key(
            session=session,
            payload=DeviceKeyRegisterRequest(
                org_id=payload.org_id,
                device_id=payload.device_id,
                key_id=payload.key_id,
                public_key_pem=payload.public_key_pem,
                algorithm=payload.algorithm,
                rotate_existing_active=True,
            ),
        )

    async def _get_device(self, session: AsyncSession, device_id: UUID) -> Device:
        device = (await session.execute(select(Device).where(Device.id == device_id))).scalar_one_or_none()
        if device is None:
            raise ValueError('Unknown device_id')
        return device
