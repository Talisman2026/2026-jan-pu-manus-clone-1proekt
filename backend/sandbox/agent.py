"""
AgentFlow MVP — Agent Loop
Runs INSIDE an E2B sandbox microVM.

Reads:
  OPENAI_API_KEY    — user-provided (passed via E2B sandbox env)
  FIRECRAWL_API_KEY — platform key (passed via E2B sandbox env)

Emits JSON events to stdout, one per line. Backend reads them line by line.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from typing import Any

from openai import OpenAI, RateLimitError, APIStatusError, APIConnectionError
from firecrawl import FirecrawlApp


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_STEPS: int = 30
LOOP_DETECTION_THRESHOLD: int = 5  # same tool N times in a row → force stop
BUDGET_WARNING_PERCENT: float = 0.80

# GPT-4o pricing (per token)
INPUT_COST_PER_TOKEN: float = 2.50 / 1_000_000   # $2.50 / 1M tokens
OUTPUT_COST_PER_TOKEN: float = 10.00 / 1_000_000  # $10.00 / 1M tokens

RESULTS_DIR: str = "/home/user/results"

# Rate-limit retry schedule (seconds)
RETRY_BACKOFF: tuple[int, ...] = (10, 20, 40)

# ---------------------------------------------------------------------------
# Log sanitiser — must never let API keys reach stdout
# ---------------------------------------------------------------------------

REDACT_PATTERNS: list[str] = [
    r"sk-[a-zA-Z0-9\-_]{20,}",   # OpenAI key
    r"e2b_[a-zA-Z0-9]{20,}",      # E2B key
    r"fc-[a-zA-Z0-9]{20,}",       # Firecrawl key
]


def sanitize(text: str) -> str:
    """Replace any recognisable API key pattern with [REDACTED]."""
    for pattern in REDACT_PATTERNS:
        text = re.sub(pattern, "[REDACTED]", text)
    return text


# ---------------------------------------------------------------------------
# Event dataclasses
# ---------------------------------------------------------------------------


@dataclass
class StepEvent:
    type: str = "step"
    tool: str = ""
    description: str = ""
    cost_usd: float = 0.0


@dataclass
class BudgetWarningEvent:
    type: str = "budget_warning"
    percent_used: int = 80
    cost_usd: float = 0.0


@dataclass
class BudgetExceededEvent:
    type: str = "budget_exceeded"
    cost_usd: float = 0.0


@dataclass
class CompletedEvent:
    type: str = "completed"
    summary: str = ""
    cost_usd: float = 0.0


@dataclass
class ErrorEvent:
    type: str = "error"
    message: str = ""
    cost_usd: float = 0.0


@dataclass
class StatusEvent:
    type: str = "status"
    message: str = ""


# ---------------------------------------------------------------------------
# Event emitter
# ---------------------------------------------------------------------------


def emit(event: Any) -> None:
    """Serialise a dataclass event to a single JSON line on stdout."""
    raw = json.dumps(asdict(event), ensure_ascii=False)
    print(sanitize(raw), flush=True)


# ---------------------------------------------------------------------------
# Cost calculation
# ---------------------------------------------------------------------------


def calculate_cost(usage: Any) -> float:
    """Return the USD cost for a single OpenAI API call."""
    input_cost = getattr(usage, "prompt_tokens", 0) * INPUT_COST_PER_TOKEN
    output_cost = getattr(usage, "completion_tokens", 0) * OUTPUT_COST_PER_TOKEN
    return input_cost + output_cost


# ---------------------------------------------------------------------------
# Tool definitions (OpenAI function-calling format)
# ---------------------------------------------------------------------------

TOOLS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web and retrieve a list of relevant results with content snippets.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query.",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results to return.",
                        "default": 5,
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scrape_url",
            "description": "Extract full markdown content from a specific URL.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The URL to scrape.",
                    }
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_python",
            "description": "Execute a Python snippet for data processing or computation. Returns stdout + stderr.",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "Valid Python source code to execute.",
                    }
                },
                "required": ["code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": (
                "Save content to a file in /home/user/results/. "
                "Always call this before finish to persist your output."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "Filename, e.g. 'report.md' or 'data.json'.",
                    },
                    "content": {
                        "type": "string",
                        "description": "File contents to write.",
                    },
                },
                "required": ["filename", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "finish",
            "description": "Signal that the task is fully complete. Provide a concise summary of what was accomplished.",
            "parameters": {
                "type": "object",
                "properties": {
                    "summary": {
                        "type": "string",
                        "description": "A brief summary of the completed task and where results were saved.",
                    }
                },
                "required": ["summary"],
            },
        },
    },
]


# ---------------------------------------------------------------------------
# Tool executor
# ---------------------------------------------------------------------------


def get_description(tool_name: str, args: dict) -> str:
    """Return a human-readable description of what the tool is doing."""
    descriptions: dict[str, str] = {
        "web_search": f"Searching: {args.get('query', '')}",
        "scrape_url": f"Reading: {args.get('url', '')}",
        "run_python": "Running Python code...",
        "write_file": f"Saving {args.get('filename', 'file')}",
        "finish": "Finishing task",
    }
    return descriptions.get(tool_name, tool_name)


def execute_web_search(args: dict, firecrawl: FirecrawlApp) -> str:
    """Call Firecrawl search. Returns JSON string of results."""
    query: str = args["query"]
    max_results: int = int(args.get("max_results", 5))
    try:
        result = firecrawl.search(query, limit=max_results)
        return json.dumps(result, ensure_ascii=False)
    except Exception as exc:
        sanitised = sanitize(str(exc))
        return json.dumps({"error": f"web_search failed: {sanitised}"})


def execute_scrape_url(args: dict, firecrawl: FirecrawlApp) -> str:
    """Call Firecrawl scrape. Returns markdown content."""
    url: str = args["url"]
    try:
        result = firecrawl.scrape_url(url, params={"formats": ["markdown"]})
        # firecrawl-py >= 1.0 returns a dict-like object
        if isinstance(result, dict):
            return result.get("markdown", "No content returned")
        # some versions return an object with .markdown attribute
        return getattr(result, "markdown", str(result)) or "No content returned"
    except Exception as exc:
        sanitised = sanitize(str(exc))
        return f"scrape_url failed: {sanitised}"


def execute_run_python(args: dict) -> str:
    """Run a Python snippet in a subprocess. Returns stdout + stderr."""
    code: str = args["code"]
    try:
        proc = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            timeout=30,
        )
        output = proc.stdout + proc.stderr
        return sanitize(output) if output else "(no output)"
    except subprocess.TimeoutExpired:
        return "Error: Python code timed out after 30 seconds"
    except Exception as exc:
        return f"Error running Python: {sanitize(str(exc))}"


def execute_write_file(args: dict) -> str:
    """Write content to a file in the results directory."""
    filename: str = args["filename"]
    content: str = args["content"]
    # Prevent path traversal
    safe_filename = os.path.basename(filename)
    os.makedirs(RESULTS_DIR, exist_ok=True)
    path = os.path.join(RESULTS_DIR, safe_filename)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)
    return f"Saved to {path}"


def execute_tool(tool_name: str, args: dict, firecrawl: FirecrawlApp) -> str:
    """Dispatch to the correct tool implementation."""
    if tool_name == "web_search":
        return execute_web_search(args, firecrawl)
    if tool_name == "scrape_url":
        return execute_scrape_url(args, firecrawl)
    if tool_name == "run_python":
        return execute_run_python(args)
    if tool_name == "write_file":
        return execute_write_file(args)
    return f"Unknown tool: {tool_name}"


# ---------------------------------------------------------------------------
# Loop detector
# ---------------------------------------------------------------------------


@dataclass
class LoopDetector:
    """Detects when the agent calls the same tool too many times in a row."""

    threshold: int = LOOP_DETECTION_THRESHOLD
    _last_tool: str = field(default="", init=False, repr=False)
    _consecutive_count: int = field(default=0, init=False, repr=False)

    def record(self, tool_name: str) -> bool:
        """Record a tool call. Returns True if a loop is detected."""
        if tool_name == self._last_tool:
            self._consecutive_count += 1
        else:
            self._last_tool = tool_name
            self._consecutive_count = 1
        return self._consecutive_count >= self.threshold


# ---------------------------------------------------------------------------
# OpenAI LLM caller with retry
# ---------------------------------------------------------------------------


def call_openai_with_retry(
    client: OpenAI,
    messages: list[dict],
    tools: list[dict],
) -> Any:
    """
    Call the OpenAI Chat Completions API with exponential-backoff retry
    on rate-limit errors (up to 3 attempts: waits 10s, 20s, 40s).
    Raises on all other errors.
    """
    for attempt, backoff in enumerate(RETRY_BACKOFF, start=1):
        try:
            return client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                tools=tools,
                tool_choice="auto",
            )
        except RateLimitError:
            if attempt == len(RETRY_BACKOFF):
                raise
            emit(StatusEvent(message=f"Rate limited by OpenAI, retrying in {backoff}s..."))
            time.sleep(backoff)
        except (APIConnectionError, APIStatusError) as exc:
            # Non-retryable API errors — propagate immediately
            raise exc


# ---------------------------------------------------------------------------
# Partial result save
# ---------------------------------------------------------------------------


def save_partial_results(messages: list[dict], total_cost: float, reason: str) -> None:
    """
    Write a partial-results file when the agent is interrupted before finish.
    Collects all tool results from the message history.
    """
    os.makedirs(RESULTS_DIR, exist_ok=True)
    partial_path = os.path.join(RESULTS_DIR, "partial_results.md")

    lines: list[str] = [
        f"# Partial Results\n",
        f"**Interrupted:** {reason}\n",
        f"**Cost so far:** ${total_cost:.4f}\n\n",
        "---\n\n",
        "## Tool Outputs\n\n",
    ]

    for msg in messages:
        if isinstance(msg, dict) and msg.get("role") == "tool":
            content = msg.get("content", "")
            lines.append(f"### Tool result\n```\n{content[:2000]}\n```\n\n")
        elif hasattr(msg, "role") and msg.role == "assistant" and not getattr(msg, "tool_calls", None):
            # Assistant text message (non-tool-call)
            content = getattr(msg, "content", "") or ""
            if content:
                lines.append(f"### Agent note\n{content}\n\n")

    with open(partial_path, "w", encoding="utf-8") as fh:
        fh.writelines(lines)


# ---------------------------------------------------------------------------
# Main agent loop
# ---------------------------------------------------------------------------


def build_system_prompt(budget_cap: float) -> str:
    return (
        "You are an autonomous research agent. Complete the given task fully and thoroughly.\n"
        f"Budget cap: ${budget_cap:.2f}. You MUST stop if approaching the limit.\n"
        "Always save your final result using write_file before calling finish.\n"
        "Save files to /home/user/results/ directory.\n"
        "Be thorough but efficient. If web_search returns results, use scrape_url on promising "
        "pages for deeper content."
    )


def main(task_description: str, budget_cap: float, task_id: str) -> None:
    # --- Initialise clients ---
    openai_api_key = os.environ.get("OPENAI_API_KEY", "")
    firecrawl_api_key = os.environ.get("FIRECRAWL_API_KEY", "")

    if not openai_api_key:
        emit(ErrorEvent(message="OPENAI_API_KEY is not set", cost_usd=0.0))
        sys.exit(1)
    if not firecrawl_api_key:
        emit(StatusEvent(message="FIRECRAWL_API_KEY is not set — web tools will fail"))

    client = OpenAI(api_key=openai_api_key)
    firecrawl = FirecrawlApp(api_key=firecrawl_api_key)

    # --- Conversation state ---
    messages: list[Any] = [
        {
            "role": "system",
            "content": build_system_prompt(budget_cap),
        },
        {
            "role": "user",
            "content": task_description,
        },
    ]

    total_cost: float = 0.0
    loop_detector = LoopDetector()
    budget_warning_emitted: bool = False

    emit(StatusEvent(message="Agent started, beginning task execution..."))

    # --- Main loop ---
    for step_num in range(MAX_STEPS):
        # Call LLM
        try:
            response = call_openai_with_retry(client, messages, TOOLS)
        except RateLimitError:
            emit(
                ErrorEvent(
                    message="OpenAI API rate limit exceeded after retries",
                    cost_usd=total_cost,
                )
            )
            save_partial_results(messages, total_cost, "OpenAI rate limit exceeded")
            sys.exit(1)
        except Exception as exc:
            safe_msg = sanitize(str(exc))
            emit(ErrorEvent(message=f"OpenAI API error: {safe_msg}", cost_usd=total_cost))
            save_partial_results(messages, total_cost, f"OpenAI error: {safe_msg}")
            sys.exit(1)

        # Accumulate cost
        step_cost = calculate_cost(response.usage)
        total_cost += step_cost

        # Budget checks (before executing tool)
        if not budget_warning_emitted and total_cost >= budget_cap * BUDGET_WARNING_PERCENT:
            emit(
                BudgetWarningEvent(
                    percent_used=80,
                    cost_usd=total_cost,
                )
            )
            budget_warning_emitted = True

        if total_cost >= budget_cap:
            emit(BudgetExceededEvent(cost_usd=total_cost))
            save_partial_results(messages, total_cost, "Budget cap reached")
            sys.exit(0)

        choice = response.choices[0]
        assistant_message = choice.message

        # No tool call → agent gave a final answer without calling finish
        if not assistant_message.tool_calls:
            content = assistant_message.content or "(no content)"
            emit(
                CompletedEvent(
                    summary=sanitize(content),
                    cost_usd=total_cost,
                )
            )
            sys.exit(0)

        # Process first tool call (OpenAI may return multiple; we handle one per step)
        tool_call = assistant_message.tool_calls[0]
        tool_name: str = tool_call.function.name

        # Parse arguments safely
        try:
            tool_args: dict = json.loads(tool_call.function.arguments)
        except json.JSONDecodeError:
            tool_args = {}

        description = get_description(tool_name, tool_args)
        emit(StepEvent(tool=tool_name, description=description, cost_usd=step_cost))

        # Loop detection
        if loop_detector.record(tool_name):
            msg = (
                f"Loop detected: '{tool_name}' called "
                f"{LOOP_DETECTION_THRESHOLD} times in a row. Stopping."
            )
            emit(ErrorEvent(message=msg, cost_usd=total_cost))
            save_partial_results(messages, total_cost, msg)
            sys.exit(1)

        # Handle finish tool
        if tool_name == "finish":
            summary = tool_args.get("summary", "Task completed")
            emit(CompletedEvent(summary=sanitize(summary), cost_usd=total_cost))
            sys.exit(0)

        # Execute tool
        tool_result = execute_tool(tool_name, tool_args, firecrawl)

        # Append assistant turn + tool result to conversation
        messages.append(assistant_message)
        messages.append(
            {
                "role": "tool",
                "content": tool_result,
                "tool_call_id": tool_call.id,
            }
        )

    # Reached MAX_STEPS without finishing
    emit(
        ErrorEvent(
            message=f"Reached maximum step limit ({MAX_STEPS}) without completing the task.",
            cost_usd=total_cost,
        )
    )
    save_partial_results(messages, total_cost, f"MAX_STEPS ({MAX_STEPS}) reached")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="AgentFlow sandbox agent — runs inside E2B microVM"
    )
    parser.add_argument("--task", required=True, help="Task description")
    parser.add_argument("--budget", type=float, required=True, help="Budget cap in USD")
    parser.add_argument("--task-id", required=True, help="Task ID for tracing")
    parsed = parser.parse_args()

    main(
        task_description=parsed.task,
        budget_cap=parsed.budget,
        task_id=parsed.task_id,
    )
