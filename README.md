# AI Driver Safety Event Summarizer

Small Python app that turns raw telematics events into a ranked driver coaching report. It aggregates safety events in plain Python, asks an LLM for a structured coaching summary, validates the response, writes `report.json`, and prints a console table.

## Run in 5 commands

```bash
cd ai-driver-safety-summarizer
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py --input events.json --output report.json
```

Optional: copy `.env.example` to `.env` and set `OPENAI_API_KEY` to call OpenAI. Without a key, the app uses a deterministic fallback instead of crashing. For a no-network demo, run `python main.py --mock-llm`.

## Output

The app writes `report.json` as an array sorted from highest to lowest risk. Each item includes:

- driver identity and vehicles
- counts by event type and severity
- numeric risk score
- validated LLM coaching JSON
- guardrail flags, if the summary appears to mention event types absent from that driver's data

It also prints a readable ranked table in the terminal.

## Risk Score Formula

Each event contributes:

```text
severity_weight * event_type_multiplier + speeding_bonus
```

Severity weights:

- low = 1
- medium = 3
- high = 6
- critical = 10

Event type multipliers:

- collision_warning = 2.0
- phone_use = 1.8
- distracted_driving = 1.6
- tailgating = 1.5
- speeding and lane_departure = 1.4
- harsh_braking = 1.2
- harsh_acceleration and rolling_stop = 1.1

Speeding receives an extra bonus of `(speed_mph - speed_limit_mph) / 5`, capped at 5 points. I chose this formula because it keeps the score easy to explain, gives serious behaviors more weight, and distinguishes mild speeding from materially over-limit driving.

## Prompt

System prompt:

```text
You are a fleet safety analyst.
Return only valid JSON with keys: summary, recommendations, priority.
Use only facts present in the aggregate data. Do not invent event types, locations, vehicles, or incident counts.
The summary must be 2-3 plain-English sentences.
Recommendations must contain 1-2 concise coaching recommendations.
Priority must be exactly one of: low, medium, high.
```

User prompt:

```text
Create a coaching report from this driver aggregate. Base the priority on the risk score, event mix, and severity counts.
<aggregated driver JSON>
```

Design choices:

- The LLM receives aggregated data, not the full raw feed, which reduces token cost and limits what it can cite.
- The system prompt requires JSON only and explicitly forbids invented event types, locations, vehicles, and counts.
- The app validates the response with Pydantic before writing the report.
- If the API call fails or returns malformed JSON, the app writes a deterministic fallback report.

## Guardrails Against Invented Events

The app prevents and checks hallucinations in three places:

1. Raw events are grouped and counted in Python before the LLM is called.
2. The prompt tells the model to use only the provided aggregate and return strict JSON.
3. A post-processing guardrail scans the summary and recommendations for known safety event labels. If the LLM mentions an event type not present for that driver, the report gets a `summary_mentions_absent_event_types` flag.

The bonus hallucination check is covered by `tests/test_guardrails.py`.

## Caching

LLM responses are cached in `.cache/` using a SHA-256 hash of the driver aggregate, model name, and prompt version. Re-running the app with unchanged data reuses cached summaries and avoids repeat LLM calls.

## Tests

```bash
python -m unittest discover -s tests
```

## Docker

```bash
docker build -t driver-safety-summarizer .
docker run --rm --env-file .env -v "$PWD:/app" driver-safety-summarizer
```

## Approximate LLM Cost Per 100 Drivers

The prompt sends compact aggregate JSON. A typical driver is roughly 300-600 input tokens and 80-150 output tokens. With `gpt-4o-mini` pricing around low fractions of a cent per thousand tokens, 100 drivers should usually cost well under $0.25. The exact cost depends on the selected model, prompt size, and response length.

## Known Limitations

- The hallucination check uses phrase matching for known event labels, so subtle paraphrases may be missed.
- Risk scoring is explainable but not calibrated against crash or claim outcomes.
- The fallback summary is intentionally conservative and less nuanced than a real LLM response.
- The sample data is small, so priority thresholds should be tuned on production distributions.

With another week, I would add JSON Schema response enforcement for providers that support it, build a small FastAPI review page, tune the risk formula against historical outcomes, add richer hallucination checks, and add observability for LLM latency, cost, cache hit rate, and validation failures.
