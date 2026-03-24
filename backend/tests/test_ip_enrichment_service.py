import asyncio
import time

from app.core.config import settings
from app.services.ip_enrichment_service import IpEnrichmentService


def test_ip_enrichment_returns_unavailable_when_provider_disabled() -> None:
    settings.ip_enrichment_provider = 'none'
    service = IpEnrichmentService()

    result = asyncio.run(service.approximate('8.8.8.8'))

    assert result.is_approximate is True
    assert result.status == 'unavailable'
    assert result.reason == 'provider_disabled'


def test_ip_enrichment_identifies_private_ip_without_provider_call() -> None:
    settings.ip_enrichment_provider = 'ipinfo'
    service = IpEnrichmentService()

    assert service._is_non_public_ip('192.168.1.20') is True  # noqa: SLF001 - unit test
    assert service._is_non_public_ip('8.8.8.8') is False  # noqa: SLF001 - unit test


def test_ip_enrichment_caches_results() -> None:
    settings.ip_enrichment_provider = 'none'
    service = IpEnrichmentService()
    result = service._result(ip_address='8.8.8.8', status='advisory', reason='provider_success')  # noqa: SLF001 - unit test

    now = time.monotonic()
    service._cache_result('8.8.8.8', result, now)  # noqa: SLF001 - unit test

    assert service._cache['8.8.8.8'].value == result  # noqa: SLF001 - unit test
    assert service._cache['8.8.8.8'].expires_at_monotonic > now  # noqa: SLF001 - unit test
