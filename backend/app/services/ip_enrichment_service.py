from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IpApproximation:
    ip_address: str
    is_approximate: bool
    country: str | None
    city: str | None
    latitude: float | None
    longitude: float | None
    accuracy_km: float | None


class IpEnrichmentService:
    async def approximate(self, ip_address: str | None) -> IpApproximation:
        # Placeholder enrichment strategy:
        # Production should integrate a privacy-reviewed geo-IP source and cache results.
        if ip_address is None or ip_address.strip() == '':
            return IpApproximation(
                ip_address='unknown',
                is_approximate=True,
                country=None,
                city=None,
                latitude=None,
                longitude=None,
                accuracy_km=None,
            )
        pseudo_seed = sum(ord(ch) for ch in ip_address) % 1000
        # Tanzania-centered approximation placeholder for East Africa regional deployments.
        lat = -6.80 + (pseudo_seed % 7) * 0.02
        lng = 39.25 + (pseudo_seed % 11) * 0.02
        return IpApproximation(
            ip_address=ip_address,
            is_approximate=True,
            country='TZ',
            city='Approximate',
            latitude=round(lat, 6),
            longitude=round(lng, 6),
            accuracy_km=30.0,
        )
