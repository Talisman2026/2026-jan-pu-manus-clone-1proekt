"""Tests for backend/sandbox/agent.py logic (no E2B, no real OpenAI calls)."""
import os
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

import pytest

# ---------------------------------------------------------------------------
# Add the sandbox directory to sys.path so we can import agent.py directly.
# ---------------------------------------------------------------------------
_SANDBOX_DIR = str(Path(__file__).parent.parent.parent / "backend" / "sandbox")
if _SANDBOX_DIR not in sys.path:
    sys.path.insert(0, _SANDBOX_DIR)

# agent.py imports openai and firecrawl at module level; stub them out before
# the real import so the tests do not require those packages to be installed
# in the test environment.
import unittest.mock as mock

# Provide minimal stubs only if the packages are absent.
for _mod in ("openai", "firecrawl"):
    if _mod not in sys.modules:
        sys.modules[_mod] = mock.MagicMock()

# Sub-modules / classes referenced at import time
for _submod in (
    "openai.OpenAI",
    "openai.RateLimitError",
    "openai.APIStatusError",
    "openai.APIConnectionError",
    "firecrawl.FirecrawlApp",
):
    parts = _submod.split(".")
    parent = sys.modules.get(parts[0])
    if parent is not None and not hasattr(parent, parts[1]):
        setattr(parent, parts[1], mock.MagicMock())

from agent import (  # noqa: E402  (import after path/stub setup)
    LoopDetector,
    calculate_cost,
    execute_write_file,
    get_description,
    sanitize,
    RESULTS_DIR,
)


# ---------------------------------------------------------------------------
# sanitize()
# ---------------------------------------------------------------------------


def test_sanitize_in_agent():
    """sanitize() in agent.py redacts OpenAI/E2B/Firecrawl keys."""
    text = "key=sk-abcdefghijklmnopqrstuvwxyz0000 end"
    result = sanitize(text)
    assert "[REDACTED]" in result
    assert "sk-" not in result


# ---------------------------------------------------------------------------
# LoopDetector
# ---------------------------------------------------------------------------


def test_loop_detector_no_loop():
    """Alternating tools do not trigger loop detection."""
    detector = LoopDetector(threshold=5)
    tools = ["web_search", "scrape_url", "run_python", "write_file", "web_search"]
    results = [detector.record(t) for t in tools]
    assert not any(results), "No loop should be detected when tools vary"


def test_loop_detector_detects_loop():
    """Calling the same tool threshold times in a row triggers detection."""
    detector = LoopDetector(threshold=5)
    # First 4 calls should not trigger
    for i in range(4):
        assert detector.record("web_search") is False, f"Should not trigger on call {i + 1}"
    # 5th consecutive call must trigger
    assert detector.record("web_search") is True


# ---------------------------------------------------------------------------
# calculate_cost()
# ---------------------------------------------------------------------------


def test_calculate_cost():
    """calculate_cost returns the correct USD amount for known token counts."""
    # GPT-4o pricing: $2.50/1M input, $10.00/1M output
    usage = SimpleNamespace(prompt_tokens=1_000_000, completion_tokens=1_000_000)
    cost = calculate_cost(usage)
    expected = 2.50 + 10.00  # $12.50
    assert abs(cost - expected) < 1e-9


# ---------------------------------------------------------------------------
# get_description()
# ---------------------------------------------------------------------------


def test_get_description_web_search():
    result = get_description("web_search", {"query": "python async"})
    assert "python async" in result


def test_get_description_scrape_url():
    result = get_description("scrape_url", {"url": "https://example.com"})
    assert "https://example.com" in result


def test_get_description_run_python():
    result = get_description("run_python", {"code": "print(1)"})
    assert "Python" in result


def test_get_description_write_file():
    result = get_description("write_file", {"filename": "report.md"})
    assert "report.md" in result


def test_get_description_finish():
    result = get_description("finish", {})
    assert result  # non-empty string


# ---------------------------------------------------------------------------
# execute_write_file()
# ---------------------------------------------------------------------------


def test_execute_write_file(tmp_path, monkeypatch):
    """execute_write_file writes content to RESULTS_DIR and returns the path."""
    # Redirect RESULTS_DIR to a temp directory so tests don't touch the VM path.
    import agent as agent_module

    monkeypatch.setattr(agent_module, "RESULTS_DIR", str(tmp_path))

    result = execute_write_file({"filename": "test_output.txt", "content": "hello world"})

    written = tmp_path / "test_output.txt"
    assert written.exists(), "File should have been created"
    assert written.read_text(encoding="utf-8") == "hello world"
    assert "test_output.txt" in result


def test_execute_write_file_prevents_path_traversal(tmp_path, monkeypatch):
    """Filenames with directory components are sanitised to basename only."""
    import agent as agent_module

    monkeypatch.setattr(agent_module, "RESULTS_DIR", str(tmp_path))

    execute_write_file({"filename": "../../etc/passwd", "content": "malicious"})

    # Should land inside tmp_path as "passwd", not escape it
    assert (tmp_path / "passwd").exists()
    assert not (Path("/etc/passwd_test")).exists()
