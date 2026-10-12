from __future__ import annotations

import re

from safety_reporter.models import CoachingReport, DriverAggregate


EVENT_LABELS = {
    "speeding": "speeding",
    "harsh braking": "harsh_braking",
    "harsh acceleration": "harsh_acceleration",
    "phone use": "phone_use",
    "distracted driving": "distracted_driving",
    "tailgating": "tailgating",
    "lane departure": "lane_departure",
    "rolling stop": "rolling_stop",
    "collision warning": "collision_warning",
}


def find_unsupported_event_mentions(report: CoachingReport, aggregate: DriverAggregate) -> list[str]:
    text = " ".join([report.summary, *report.recommendations]).lower()
    present_types = set(aggregate.counts_by_type)
    unsupported: list[str] = []

    for label, event_type in EVENT_LABELS.items():
        pattern = r"\b" + re.escape(label) + r"\b"
        if re.search(pattern, text) and event_type not in present_types:
            unsupported.append(event_type)

    return sorted(set(unsupported))


def guardrail_flags(report: CoachingReport, aggregate: DriverAggregate) -> list[str]:
    flags: list[str] = []
    unsupported = find_unsupported_event_mentions(report, aggregate)
    if unsupported:
        flags.append("summary_mentions_absent_event_types:" + ",".join(unsupported))
    return flags
