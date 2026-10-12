from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from typing import Literal


Priority = Literal["low", "medium", "high"]


@dataclass
class CoachingReport:
    summary: str
    recommendations: list[str]
    priority: Priority

    def __post_init__(self) -> None:
        if not isinstance(self.summary, str) or not self.summary.strip():
            raise ValueError("summary must be a non-empty string")
        if not isinstance(self.recommendations, list) or not 1 <= len(self.recommendations) <= 2:
            raise ValueError("recommendations must contain 1-2 items")
        if not all(isinstance(item, str) and item.strip() for item in self.recommendations):
            raise ValueError("recommendations must be non-empty strings")
        if self.priority not in {"low", "medium", "high"}:
            raise ValueError("priority must be low, medium, or high")

    @classmethod
    def from_dict(cls, data: dict) -> "CoachingReport":
        return cls(
            summary=data["summary"],
            recommendations=list(data["recommendations"]),
            priority=data["priority"],
        )

    @classmethod
    def from_json(cls, data: str) -> "CoachingReport":
        return cls.from_dict(json.loads(data))

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self, indent: int | None = None) -> str:
        return json.dumps(self.to_dict(), indent=indent)


@dataclass
class DriverAggregate:
    driver_id: str
    driver_name: str
    vehicles: list[str]
    total_events: int
    counts_by_type: dict[str, int]
    counts_by_severity: dict[str, int]
    risk_score: float
    examples: list[dict[str, str | int | None]]

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class DriverReport:
    driver_id: str
    driver_name: str
    vehicles: list[str]
    total_events: int
    counts_by_type: dict[str, int]
    counts_by_severity: dict[str, int]
    risk_score: float
    examples: list[dict[str, str | int | None]]
    llm: CoachingReport
    guardrail_flags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        data = asdict(self)
        data["llm"] = self.llm.to_dict()
        return data
