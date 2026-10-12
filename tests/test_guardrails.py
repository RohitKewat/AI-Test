import unittest

from safety_reporter.guardrails import find_unsupported_event_mentions
from safety_reporter.models import CoachingReport, DriverAggregate


class GuardrailTests(unittest.TestCase):
    def test_hallucination_check_flags_absent_event_type(self) -> None:
        aggregate = DriverAggregate(
            driver_id="D-001",
            driver_name="Driver Test",
            vehicles=["TRK-1"],
            total_events=2,
            counts_by_type={"speeding": 2},
            counts_by_severity={"medium": 2},
            risk_score=9.2,
            examples=[],
        )
        report = CoachingReport(
            summary="The driver had speeding events and phone use during the period.",
            recommendations=["Coach on speeding."],
            priority="medium",
        )

        self.assertEqual(find_unsupported_event_mentions(report, aggregate), ["phone_use"])

    def test_hallucination_check_allows_present_event_type(self) -> None:
        aggregate = DriverAggregate(
            driver_id="D-002",
            driver_name="Driver Safe",
            vehicles=["TRK-2"],
            total_events=1,
            counts_by_type={"harsh_braking": 1},
            counts_by_severity={"low": 1},
            risk_score=1.2,
            examples=[],
        )
        report = CoachingReport(
            summary="The driver had one harsh braking event.",
            recommendations=["Leave more following distance."],
            priority="low",
        )

        self.assertEqual(find_unsupported_event_mentions(report, aggregate), [])


if __name__ == "__main__":
    unittest.main()
