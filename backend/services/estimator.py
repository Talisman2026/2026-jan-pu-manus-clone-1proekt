"""Pre-run task estimation using OUR OpenAI GPT-4o-mini key.

The estimation gives the user an idea of how many steps the agent will
take, how long it might run and a rough cost upper-bound — all before any
user API key is involved.
"""

import json
import logging
from typing import Any

from openai import AsyncOpenAI, OpenAIError

from config import settings
from security import sanitize

logger = logging.getLogger(__name__)

_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    return _client


_SYSTEM_PROMPT = (
    "You are a task complexity estimator for an autonomous AI agent. "
    "Given a task description, estimate how complex the task is. "
    "Respond ONLY with valid JSON — no markdown fences, no explanation."
)

_USER_TEMPLATE = """\
Task: {description}

Return JSON only with these exact keys:
{{
  "steps": <integer, expected number of tool calls>,
  "duration_min": <integer, optimistic duration in seconds>,
  "duration_max": <integer, conservative duration in seconds>,
  "cost_estimate_usd": <float, rough upper-bound cost in USD>
}}"""


async def estimate_task(description: str) -> dict[str, Any]:
    """Return estimation dict for *description* using GPT-4o-mini (our key).

    Returns a dict with keys: steps, duration_min, duration_max,
    cost_estimate_usd.  Raises RuntimeError on LLM or parse failure.
    """
    client = _get_client()

    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": _USER_TEMPLATE.format(description=description)},
            ],
            temperature=0.2,
            max_tokens=256,
        )
    except OpenAIError as exc:
        sanitized = sanitize(str(exc))
        logger.error("Estimation LLM call failed: %s", sanitized)
        raise RuntimeError(f"Estimation failed: {sanitized}") from exc

    raw = response.choices[0].message.content or ""
    raw = raw.strip()

    # Strip markdown code fences if the model disobeyed instructions
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    try:
        data: dict[str, Any] = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error("Estimation response parse error, raw=%r", raw[:200])
        raise RuntimeError("Estimation returned invalid JSON") from exc

    required_keys = {"steps", "duration_min", "duration_max", "cost_estimate_usd"}
    missing = required_keys - data.keys()
    if missing:
        raise RuntimeError(f"Estimation response missing keys: {missing}")

    return {
        "steps": int(data["steps"]),
        "duration_min": int(data["duration_min"]),
        "duration_max": int(data["duration_max"]),
        "cost_estimate_usd": float(data["cost_estimate_usd"]),
    }
