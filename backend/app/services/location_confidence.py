from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from app.schemas.telemetry import LocationSignalInput


@dataclass(frozen=True)
class ScoredSignal:
    signal: LocationSignalInput
    confidence_score: int


class LocationConfidenceService:
    def score_signal(self, signal: LocationSignalInput, now: datetime) -> int:
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        captured_at = signal.captured_at if signal.captured_at.tzinfo else signal.captured_at.replace(tzinfo=timezone.utc)

        accuracy_score = 95
        if signal.accuracy_meters > 25:
            accuracy_score = 85
        if signal.accuracy_meters > 75:
            accuracy_score = 75
        if signal.accuracy_meters > 150:
            accuracy_score = 60
        if signal.accuracy_meters > 500:
            accuracy_score = 45
        if signal.accuracy_meters > 1000:
            accuracy_score = 30

        age_minutes = max(0, int((now - captured_at).total_seconds() // 60))
        age_penalty = min(35, age_minutes * 2)
        approximate_penalty = 12 if signal.is_approximate else 0

        score = accuracy_score - age_penalty - approximate_penalty
        return max(5, min(99, score))

    def choose_best_signal(self, signals: list[LocationSignalInput], now: datetime | None = None) -> ScoredSignal | None:
        if not signals:
            return None

        current_time = now or datetime.now(timezone.utc)
        scored = [
            ScoredSignal(signal=signal, confidence_score=self.score_signal(signal, current_time))
            for signal in signals
        ]
        return max(scored, key=lambda item: item.confidence_score)
