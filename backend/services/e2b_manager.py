"""E2B sandbox management.

Responsible for:
- Creating an E2B microVM sandbox for a task
- Uploading agent.py + its requirements into the sandbox
- Running the agent and streaming JSON events line by line
- Persisting each event as a TaskStep / Task status update in the DB
- Downloading the result file back to the host
- Killing the sandbox when done (success or failure)

SECURITY:
  user_openai_key is set to None immediately after the sandbox is created,
  so it exists in Python memory for the shortest possible time.
  It is NEVER logged, stored in the DB, or included in error messages.
"""

import json
import logging
import os
import shlex
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import ulid
from e2b import AsyncSandbox
from e2b.exceptions import SandboxException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import AsyncSessionLocal
from models import Task, TaskStep
from security import sanitize

logger = logging.getLogger(__name__)

# Paths inside the sandbox
_SANDBOX_HOME = "/home/user"
_AGENT_SCRIPT = f"{_SANDBOX_HOME}/agent.py"
_AGENT_REQS = f"{_SANDBOX_HOME}/requirements.txt"
_RESULTS_DIR = f"{_SANDBOX_HOME}/results"

# Paths on the host
_HOST_SANDBOX_DIR = Path(__file__).parent.parent / "sandbox"


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


async def run_task_in_sandbox(
    task_id: str,
    description: str,
    budget_cap: float,
    user_openai_key: str,
) -> None:
    """Execute *task_id* inside an E2B sandbox.

    This function is meant to be called as a FastAPI BackgroundTask.
    It creates its OWN DB session (not the request-scoped one which is
    already closed by the time this runs) and updates the Task/TaskStep rows.
    """
    sandbox: Optional[AsyncSandbox] = None

    # Create a fresh DB session for the entire background task lifetime
    async with AsyncSessionLocal() as db:
        try:
            sandbox = await _create_sandbox(user_openai_key)
            # CRITICAL: zero out the key immediately after sandbox creation
            user_openai_key = None  # noqa: F841 — intentional erasure

            await _mark_running(task_id, sandbox.sandbox_id, db)
            await _upload_agent(sandbox)
            await _install_requirements(sandbox)
            await _run_agent(task_id, description, budget_cap, sandbox, db)
            await _download_result(task_id, sandbox, db)

        except SandboxException as exc:
            sanitized = sanitize(str(exc))
            logger.error("Sandbox error for task_id=%s: %s", task_id, sanitized)
            await _mark_failed(task_id, db)

        except Exception as exc:
            sanitized = sanitize(str(exc))
            logger.error("Unexpected error for task_id=%s: %s", task_id, sanitized)
            await _mark_failed(task_id, db)

        finally:
            if sandbox is not None:
                try:
                    await sandbox.kill()
                except Exception as kill_exc:
                    logger.warning(
                        "Failed to kill sandbox for task_id=%s: %s",
                        task_id,
                        sanitize(str(kill_exc)),
                    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _create_sandbox(user_openai_key: str) -> AsyncSandbox:
    """Create an E2B sandbox with the user key injected via env only."""
    envs = {
        "OPENAI_API_KEY": user_openai_key,
        "FIRECRAWL_API_KEY": settings.FIRECRAWL_API_KEY,
    }
    # Attempt once; if it fails, retry once before raising
    for attempt in range(2):
        try:
            sandbox = await AsyncSandbox.create(
                template="base",
                timeout=1800,  # 30 minutes max
                envs=envs,
                api_key=settings.E2B_API_KEY,
            )
            return sandbox
        except SandboxException as exc:
            if attempt == 0:
                logger.warning("Sandbox creation failed, retrying once: %s", sanitize(str(exc)))
                continue
            raise
    # Should be unreachable but keeps type checker happy
    raise SandboxException("Sandbox creation failed after retry")


async def _mark_running(task_id: str, sandbox_id: str, db: AsyncSession) -> None:
    now = datetime.now(timezone.utc)
    await db.execute(
        update(Task)
        .where(Task.id == task_id)
        .values(status="running", sandbox_id=sandbox_id, started_at=now)
    )
    await db.commit()


async def _mark_failed(task_id: str, db: AsyncSession) -> None:
    await db.execute(
        update(Task).where(Task.id == task_id).values(status="failed")
    )
    await db.commit()


async def _upload_agent(sandbox: AsyncSandbox) -> None:
    """Upload agent.py and its requirements.txt into the sandbox."""
    agent_src = (_HOST_SANDBOX_DIR / "agent.py").read_text(encoding="utf-8")
    reqs_src = (_HOST_SANDBOX_DIR / "requirements.txt").read_text(encoding="utf-8")

    await sandbox.files.write(_AGENT_SCRIPT, agent_src)
    await sandbox.files.write(_AGENT_REQS, reqs_src)


async def _install_requirements(sandbox: AsyncSandbox) -> None:
    """Run pip install inside the sandbox (blocking until done)."""
    proc = await sandbox.commands.run(
        f"pip install -r {_AGENT_REQS} -q",
        timeout=120,
    )
    if proc.exit_code != 0:
        raise SandboxException(
            f"pip install failed (exit {proc.exit_code}): {proc.stderr[:500]}"
        )


async def _run_agent(
    task_id: str,
    description: str,
    budget_cap: float,
    sandbox: AsyncSandbox,
    db: AsyncSession,
) -> None:
    """Stream agent stdout and process each JSON event line."""
    # Write the task description to a temp file to avoid shell injection.
    # This is safer than any form of shell-string quoting.
    task_file = f"{_SANDBOX_HOME}/task_description.txt"
    await sandbox.files.write(task_file, description)

    # Use shlex.quote for all other arguments; budget and task_id are safe floats/strings
    cmd = (
        f"python {_AGENT_SCRIPT} "
        f"--task-file {shlex.quote(task_file)} "
        f"--budget {budget_cap} "
        f"--task-id {shlex.quote(task_id)}"
    )

    async for line in sandbox.commands.run_stream(cmd, timeout=1800):
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            # Non-JSON output from agent (e.g. tracebacks); log safely
            logger.debug("Non-JSON agent output for task_id=%s", task_id)
            continue

        await _process_event(task_id, event, db)


async def _process_event(
    task_id: str,
    event: dict,
    db: AsyncSession,
) -> None:
    event_type: str = event.get("type", "")

    if event_type == "step":
        step = TaskStep(
            id=ulid.new().str,
            task_id=task_id,
            tool=event.get("tool", "unknown"),
            description=event.get("description"),
            status="done",
            cost_usd=float(event.get("cost_usd", 0.0)),
        )
        db.add(step)
        # Increment cost_actual
        result = await db.execute(select(Task).where(Task.id == task_id))
        task = result.scalar_one_or_none()
        if task is not None:
            task.cost_actual = (task.cost_actual or 0.0) + step.cost_usd
        await db.commit()

    elif event_type == "budget_warning":
        # Set status so frontend polling can show the warning banner
        await db.execute(
            update(Task).where(Task.id == task_id).values(status="budget_warning")
        )
        await db.commit()
        logger.info("Budget warning for task_id=%s", task_id)

    elif event_type == "completed":
        now = datetime.now(timezone.utc)
        await db.execute(
            update(Task)
            .where(Task.id == task_id)
            .values(
                status="completed",
                result_summary=event.get("summary"),
                completed_at=now,
            )
        )
        await db.commit()

    elif event_type == "error":
        await db.execute(
            update(Task).where(Task.id == task_id).values(status="failed")
        )
        await db.commit()

    elif event_type == "budget_exceeded":
        now = datetime.now(timezone.utc)
        await db.execute(
            update(Task)
            .where(Task.id == task_id)
            .values(status="paused", completed_at=now)
        )
        await db.commit()


async def _download_result(
    task_id: str,
    sandbox: AsyncSandbox,
    db: AsyncSession,
) -> None:
    """Download the first result file from the sandbox if it exists."""
    try:
        files = await sandbox.files.list(_RESULTS_DIR)
    except Exception:
        # No results directory — that's fine
        return

    if not files:
        return

    result_file = files[0]
    content: bytes = await sandbox.files.read_bytes(result_file.path)

    host_results = Path(settings.RESULTS_DIR) / task_id
    host_results.mkdir(parents=True, exist_ok=True)
    dest = host_results / result_file.name
    dest.write_bytes(content)

    await db.execute(
        update(Task)
        .where(Task.id == task_id)
        .values(result_file_path=str(dest))
    )
    await db.commit()
    logger.info("Result file saved for task_id=%s", task_id)


# ---------------------------------------------------------------------------
# Cancel helper (called from route)
# ---------------------------------------------------------------------------


async def cancel_sandbox(sandbox_id: str) -> None:
    """Kill a running sandbox by its ID."""
    try:
        sandbox = await AsyncSandbox.connect(sandbox_id, api_key=settings.E2B_API_KEY)
        await sandbox.kill()
    except SandboxException as exc:
        logger.warning("Failed to cancel sandbox %s: %s", sandbox_id, sanitize(str(exc)))
