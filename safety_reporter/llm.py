from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from safety_reporter.models import CoachingReport, DriverAggregate


SYSTEM_PROMPT = """You are a fleet safety analyst.
Return only valid JSON with keys: summary, recommendations, priority.
Use only facts present in the aggregate data. Do not invent event types, locations, vehicles, or incident counts.
The summary must be 2-3 plain-English sentences.
Recommendations must contain 1-2 concise coaching recommendations.
Priority must be exactly one of: low, medium, high."""


def build_user_prompt(aggregate: DriverAggregate) -> str:
    return (
        "Create a coaching report from this driver aggregate. "
        "Base the priority on the risk score, event mix, and severity counts.\n\n"
        + json.dumps(aggregate.to_dict(), indent=2)
    )


def fallback_report(aggregate: DriverAggregate, reason: str) -> CoachingReport:
    top_types = sorted(aggregate.counts_by_type.items(), key=lambda item: item[1], reverse=True)[:2]
    type_text = ", ".join(f"{count} {event_type.replace('_', ' ')}" for event_type, count in top_types)
    if aggregate.risk_score >= 35:
        priority = "high"
    elif aggregate.risk_score >= 15:
        priority = "medium"
    else:
        priority = "low"

    return CoachingReport(
        summary=(
            f"{aggregate.driver_name} recorded {aggregate.total_events} safety events, led by {type_text}. "
            f"The calculated risk score is {aggregate.risk_score}, so this report used a deterministic fallback because {reason}."
        ),
        recommendations=[
            "Review the most frequent event category and agree on one measurable improvement target.",
            "Use recent event examples during coaching and verify improvement on the next scorecard.",
        ],
        priority=priority,
    )


def mock_report(aggregate: DriverAggregate) -> CoachingReport:
    return fallback_report(aggregate, "mock LLM mode is enabled")


def cache_key(aggregate: DriverAggregate, model: str, prompt_version: str) -> str:
    payload = {
        "aggregate": aggregate.to_dict(),
        "model": model,
        "prompt_version": prompt_version,
    }
    raw = json.dumps(payload, sort_keys=True).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def load_cached_report(cache_dir: Path, key: str) -> CoachingReport | None:
    path = cache_dir / f"{key}.json"
    if not path.exists():
        return None
    try:
        return CoachingReport.from_json(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
        return None


def save_cached_report(cache_dir: Path, key: str, report: CoachingReport) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    (cache_dir / f"{key}.json").write_text(report.to_json(indent=2), encoding="utf-8")


def call_openai(aggregate: DriverAggregate, model: str) -> CoachingReport:
    from openai import OpenAI

    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(aggregate)},
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
    )
    content = response.choices[0].message.content or "{}"
    return CoachingReport.from_json(content)


def summarize_driver(
    aggregate: DriverAggregate,
    model: str,
    cache_dir: Path,
    use_mock: bool = False,
    prompt_version: str = "v1",
) -> CoachingReport:
    key = cache_key(aggregate, model if not use_mock else "mock", prompt_version)
    cached = load_cached_report(cache_dir, key)
    if cached:
        return cached

    if use_mock:
        report = mock_report(aggregate)
        save_cached_report(cache_dir, key, report)
        return report

    if not os.environ.get("OPENAI_API_KEY"):
        report = fallback_report(aggregate, "OPENAI_API_KEY is not set")
        save_cached_report(cache_dir, key, report)
        return report

    try:
        report = call_openai(aggregate, model)
    except Exception as exc:
        report = fallback_report(aggregate, f"the LLM response failed validation or the API call failed: {exc}")

    save_cached_report(cache_dir, key, report)
    return report
