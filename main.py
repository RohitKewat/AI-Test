from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from safety_reporter.aggregation import aggregate_events
from safety_reporter.guardrails import guardrail_flags
from safety_reporter.llm import summarize_driver
from safety_reporter.models import DriverReport


def load_dotenv_file(path: Path = Path(".env")) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def load_events(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, list):
        raise ValueError("Input JSON must be a list of events.")
    return data


def build_reports(events_path: Path, output_path: Path, cache_dir: Path, use_mock: bool) -> list[DriverReport]:
    events = load_events(events_path)
    aggregates = aggregate_events(events)
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

    reports: list[DriverReport] = []
    for aggregate in aggregates:
        llm_report = summarize_driver(aggregate, model=model, cache_dir=cache_dir, use_mock=use_mock)
        reports.append(
            DriverReport(
                **aggregate.to_dict(),
                llm=llm_report,
                guardrail_flags=guardrail_flags(llm_report, aggregate),
            )
        )

    output_path.write_text(
        json.dumps([report.to_dict() for report in reports], indent=2),
        encoding="utf-8",
    )
    return reports


def print_table(reports: list[DriverReport]) -> None:
    rows = [
        [
            report.driver_id,
            report.driver_name,
            report.risk_score,
            report.llm.priority,
            report.total_events,
            ", ".join(f"{key}:{value}" for key, value in report.counts_by_type.items()),
            "; ".join(report.guardrail_flags) or "-",
        ]
        for report in reports
    ]
    headers = ["Driver ID", "Name", "Risk", "Priority", "Events", "Event counts", "Guardrails"]
    table = [headers, *[[str(cell) for cell in row] for row in rows]]
    widths = [max(len(row[index]) for row in table) for index in range(len(headers))]
    separator = "| " + " | ".join("-" * width for width in widths) + " |"
    print("| " + " | ".join(headers[index].ljust(widths[index]) for index in range(len(headers))) + " |")
    print(separator)
    for row in table[1:]:
        print("| " + " | ".join(row[index].ljust(widths[index]) for index in range(len(headers))) + " |")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate driver safety coaching reports from event JSON.")
    parser.add_argument("--input", default="events.json", help="Path to the input events JSON file.")
    parser.add_argument("--output", default="report.json", help="Path to write the report JSON file.")
    parser.add_argument("--cache-dir", default=".cache", help="Directory for cached LLM responses.")
    parser.add_argument("--mock-llm", action="store_true", help="Use deterministic local summaries instead of calling an LLM.")
    return parser.parse_args()


def main() -> None:
    load_dotenv_file()
    args = parse_args()
    reports = build_reports(
        events_path=Path(args.input),
        output_path=Path(args.output),
        cache_dir=Path(args.cache_dir),
        use_mock=args.mock_llm,
    )
    print_table(reports)
    print(f"\nWrote {args.output}")


if __name__ == "__main__":
    main()
