from datetime import datetime, timedelta, timezone

from app.schemas.telemetry import LocationSignalInput, LocationSignalMethod
from app.services.location_confidence import LocationConfidenceService


def test_confidence_prefers_precise_signal() -> None:
    service = LocationConfidenceService()
    now = datetime.now(timezone.utc)

    precise = LocationSignalInput(
        method=LocationSignalMethod.GPS,
        latitude=1.0,
        longitude=2.0,
        accuracy_meters=20,
        captured_at=now,
        is_approximate=False,
        method_label='GPS',
    )
    approximate = LocationSignalInput(
        method=LocationSignalMethod.IP_DERIVED,
        latitude=1.2,
        longitude=2.2,
        accuracy_meters=1200,
        captured_at=now - timedelta(minutes=10),
        is_approximate=True,
        method_label='IP-derived approximate',
    )

    best = service.choose_best_signal([approximate, precise], now=now)
    assert best is not None
    assert best.signal.method == LocationSignalMethod.GPS
