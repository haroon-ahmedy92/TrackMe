from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.endpoints import actions, audit, devices, health, incidents, platform, telemetry

router = APIRouter()
router.include_router(health.router)
router.include_router(devices.router)
router.include_router(telemetry.router)
router.include_router(actions.router)
router.include_router(incidents.router)
router.include_router(platform.router)
router.include_router(audit.router)
