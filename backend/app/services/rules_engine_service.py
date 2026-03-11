from __future__ import annotations

import math
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Geofence, LocationPrecision
from app.schemas.platform import LocationIngestRequest


@dataclass(frozen=True)
class RuleEvaluation:
    matches: list[str]


class RulesEngineService:
    async def evaluate_location(
        self,
        session: AsyncSession,
        payload: LocationIngestRequest,
    ) -> RuleEvaluation:
        matches: list[str] = []

        if payload.precision == LocationPrecision.APPROXIMATE:
            matches.append('APPROXIMATE_SIGNAL_ONLY')
        if payload.confidence_score is not None and payload.confidence_score < 40:
            matches.append('LOW_CONFIDENCE_SCORE')

        if payload.latitude is None or payload.longitude is None:
            return RuleEvaluation(matches=matches)

        geofence_matches = await self._evaluate_geofence(
            session=session,
            org_id=payload.org_id,
            device_id=payload.device_id,
            latitude=payload.latitude,
            longitude=payload.longitude,
        )
        matches.extend(geofence_matches)
        return RuleEvaluation(matches=sorted(set(matches)))

    async def _evaluate_geofence(
        self,
        session: AsyncSession,
        org_id: UUID,
        device_id: UUID,
        latitude: float,
        longitude: float,
    ) -> list[str]:
        stmt = select(Geofence).where(
            Geofence.org_id == org_id,
            Geofence.is_enabled.is_(True),
            or_(Geofence.device_id.is_(None), Geofence.device_id == device_id),
        )
        geofences = list((await session.execute(stmt)).scalars().all())
        if not geofences:
            return []

        triggered: list[str] = []
        for geofence in geofences:
            distance_m = self._haversine_meters(
                lat1=float(latitude),
                lon1=float(longitude),
                lat2=float(geofence.center_latitude),
                lon2=float(geofence.center_longitude),
            )
            if distance_m > geofence.radius_meters:
                triggered.append(f'GEOFENCE_EXIT:{geofence.id}')
        return triggered

    def _haversine_meters(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        radius = 6_371_000.0
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
        return 2 * radius * math.atan2(math.sqrt(a), math.sqrt(1 - a))
