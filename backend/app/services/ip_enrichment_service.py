from __future__ import annotations

import asyncio
import ipaddress
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

from app.core.config import settings


@dataclass(frozen=True)
class IpApproximation:
    ip_address: str
    is_approximate: bool
    country: str | None
    city: str | None
    latitude: float | None
    longitude: float | None
    accuracy_km: float | None
    provider: str
    status: str
    reason: str


@dataclass
class _CachedEntry:
    value: IpApproximation
    expires_at_monotonic: float


class IpEnrichmentService:
    def __init__(self) -> None:
        self.provider = settings.ip_enrichment_provider
        self.api_url = settings.ip_enrichment_api_url
        self.api_key = settings.ip_enrichment_api_key
        self.cache_ttl_seconds = settings.ip_enrichment_cache_ttl_seconds
        self._cache: dict[str, _CachedEntry] = {}
        self._request_timestamps: list[float] = []

    async def approximate(self, ip_address: str | None) -> IpApproximation:
        normalized_ip = (ip_address or '').strip()
        if not normalized_ip:
            return self._result(
                ip_address='unknown',
                status='unavailable',
                reason='missing_ip',
            )

        if self._is_non_public_ip(normalized_ip):
            return self._result(
                ip_address=normalized_ip,
                status='unavailable',
                reason='non_public_ip',
            )

        cached = self._cache.get(normalized_ip)
        now = time.monotonic()
        if cached is not None and cached.expires_at_monotonic > now:
            return cached.value

        if self.provider in {'', 'none', 'disabled'}:
            result = self._result(
                ip_address=normalized_ip,
                status='unavailable',
                reason='provider_disabled',
            )
            self._cache_result(normalized_ip, result, now)
            return result

        if self._rate_limited(now):
            result = self._result(
                ip_address=normalized_ip,
                status='advisory',
                reason='provider_rate_limited',
            )
            self._cache_result(normalized_ip, result, now)
            return result

        try:
            result = await asyncio.to_thread(self._fetch_provider_result, normalized_ip)
        except Exception:
            result = self._result(
                ip_address=normalized_ip,
                status='unavailable',
                reason='provider_failed',
            )

        self._cache_result(normalized_ip, result, now)
        return result

    def _fetch_provider_result(self, ip_address: str) -> IpApproximation:
        if self.provider == 'ipapi':
            return self._fetch_ipapi(ip_address)
        if self.provider == 'ipinfo':
            return self._fetch_ipinfo(ip_address)
        return self._result(
            ip_address=ip_address,
            status='unavailable',
            reason='unknown_provider',
        )

    def _fetch_ipapi(self, ip_address: str) -> IpApproximation:
        base_url = (self.api_url or 'https://ipapi.co').rstrip('/')
        query = f'{base_url}/{urllib.parse.quote(ip_address)}/json/'
        payload = self._http_json(query, headers=self._bearer_headers())
        latitude = _to_float(payload.get('latitude'))
        longitude = _to_float(payload.get('longitude'))
        return IpApproximation(
            ip_address=ip_address,
            is_approximate=True,
            country=_truncate(payload.get('country_code'), 16),
            city=_truncate(payload.get('city'), 80),
            latitude=latitude,
            longitude=longitude,
            accuracy_km=payload.get('accuracy') if isinstance(payload.get('accuracy'), (int, float)) else None,
            provider='ipapi',
            status='advisory' if latitude is not None and longitude is not None else 'unavailable',
            reason='provider_success' if latitude is not None and longitude is not None else 'provider_no_coordinates',
        )

    def _fetch_ipinfo(self, ip_address: str) -> IpApproximation:
        base_url = (self.api_url or 'https://ipinfo.io').rstrip('/')
        query = f'{base_url}/{urllib.parse.quote(ip_address)}/json'
        payload = self._http_json(query, headers=self._bearer_headers())
        latitude = None
        longitude = None
        loc_value = payload.get('loc')
        if isinstance(loc_value, str) and ',' in loc_value:
            lat_raw, lng_raw = loc_value.split(',', maxsplit=1)
            latitude = _to_float(lat_raw)
            longitude = _to_float(lng_raw)
        return IpApproximation(
            ip_address=ip_address,
            is_approximate=True,
            country=_truncate(payload.get('country'), 16),
            city=_truncate(payload.get('city'), 80),
            latitude=latitude,
            longitude=longitude,
            accuracy_km=None,
            provider='ipinfo',
            status='advisory' if latitude is not None and longitude is not None else 'unavailable',
            reason='provider_success' if latitude is not None and longitude is not None else 'provider_no_coordinates',
        )

    def _http_json(self, url: str, *, headers: dict[str, str]) -> dict:
        request = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=5) as response:  # noqa: S310 - provider is explicitly configured
                return json.loads(response.read().decode('utf-8'))
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f'IP provider HTTP error: {exc.code}') from exc
        except urllib.error.URLError as exc:
            raise RuntimeError('IP provider network error') from exc

    def _bearer_headers(self) -> dict[str, str]:
        if not self.api_key:
            return {}
        return {'Authorization': f'Bearer {self.api_key}'}

    def _cache_result(self, ip_address: str, result: IpApproximation, now: float) -> None:
        self._cache[ip_address] = _CachedEntry(
            value=result,
            expires_at_monotonic=now + max(self.cache_ttl_seconds, 60),
        )

    def _rate_limited(self, now: float) -> bool:
        self._request_timestamps = [item for item in self._request_timestamps if now - item < 60]
        if len(self._request_timestamps) >= 60:
            return True
        self._request_timestamps.append(now)
        return False

    def _is_non_public_ip(self, ip_address: str) -> bool:
        try:
            parsed = ipaddress.ip_address(ip_address)
        except ValueError:
            return True
        return (
            parsed.is_private
            or parsed.is_loopback
            or parsed.is_reserved
            or parsed.is_link_local
            or parsed.is_multicast
            or parsed.is_unspecified
        )

    def _result(
        self,
        *,
        ip_address: str,
        status: str,
        reason: str,
        country: str | None = None,
        city: str | None = None,
        latitude: float | None = None,
        longitude: float | None = None,
        accuracy_km: float | None = None,
    ) -> IpApproximation:
        return IpApproximation(
            ip_address=ip_address,
            is_approximate=True,
            country=country,
            city=city,
            latitude=latitude,
            longitude=longitude,
            accuracy_km=accuracy_km,
            provider=self.provider or 'disabled',
            status=status,
            reason=reason,
        )


def _to_float(value: object) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _truncate(value: object, limit: int) -> str | None:
    if not isinstance(value, str):
        return None
    trimmed = value.strip()
    return trimmed[:limit] if trimmed else None
