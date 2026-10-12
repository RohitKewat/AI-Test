from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from safety_reporter.models import DriverAggregate


SEVERITY_WEIGHTS = {
    "low": 1.0,
    "medium": 3.0,
    "high": 6.0,
    "critical": 10.0,
}

EVENT_TYPE_MULTIPLIERS = {
    "speeding": 1.4,
    "harsh_braking": 1.2,
    "harsh_acceleration": 1.1,
    "phone_use": 1.8,
    "distracted_driving": 1.6,
    "tailgating": 1.5,
    "lane_departure": 1.4,
    "rolling_stop": 1.1,
    "collision_warning": 2.0,
}


def event_risk_score(event: dict[str, Any]) -> float:
    severity = str(event.get("severity", "low")).lower()
    event_type = str(event.get("event_type", "unknown")).lower()
    score = SEVERITY_WEIGHTS.get(severity, 1.0) * EVENT_TYPE_MULTIPLIERS.get(event_type, 1.0)

    if event_type == "speeding":
        speed = event.get("speed_mph")
        limit = event.get("speed_limit_mph")
        if isinstance(speed, (int, float)) and isinstance(limit, (int, float)) and speed > limit:
            score += min((speed - limit) / 5.0, 5.0)

    return round(score, 2)


def aggregate_events(events: list[dict[str, Any]]) -> list[DriverAggregate]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        grouped[str(event["driver_id"])].append(event)

    aggregates: list[DriverAggregate] = []
    for driver_id, driver_events in grouped.items():
        first = driver_events[0]
        counts_by_type = Counter(str(event.get("event_type", "unknown")) for event in driver_events)
        counts_by_severity = Counter(str(event.get("severity", "unknown")) for event in driver_events)
        risk_score = round(sum(event_risk_score(event) for event in driver_events), 2)
        examples = sorted(driver_events, key=lambda item: str(item.get("timestamp", "")), reverse=True)[:3]

        aggregates.append(
            DriverAggregate(
                driver_id=driver_id,
                driver_name=str(first.get("driver_name", driver_id)),
                vehicles=sorted({str(event.get("vehicle_id", "unknown")) for event in driver_events}),
                total_events=len(driver_events),
                counts_by_type=dict(sorted(counts_by_type.items())),
                counts_by_severity=dict(sorted(counts_by_severity.items())),
                risk_score=risk_score,
                examples=[
                    {
                        "event_id": event.get("event_id"),
                        "event_type": event.get("event_type"),
                        "severity": event.get("severity"),
                        "timestamp": event.get("timestamp"),
                        "location": event.get("location"),
                        "speed_mph": event.get("speed_mph"),
                        "speed_limit_mph": event.get("speed_limit_mph"),
                    }
                    for event in examples
                ],
            )
        )

    return sorted(aggregates, key=lambda item: item.risk_score, reverse=True)
