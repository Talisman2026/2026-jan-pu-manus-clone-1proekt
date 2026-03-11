"""Task management routes."""

import logging
from pathlib import Path
from typing import Annotated

import ulid
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from deps import CurrentUser, DbDep
from models import ACTIVE_STATUSES, Task, TaskStep
from schemas import (
    ErrorResponse,
    EstimationResponse,
    TaskCreate,
    TaskListItem,
    TaskResponse,
    TaskRunRequest,
    TaskStepResponse,
)
from security import sanitize
from services.e2b_manager import cancel_sandbox, run_task_in_sandbox
from services.estimator import estimate_task

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tasks", tags=["tasks"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _get_task_or_404(task_id: str, user_id: str, db: AsyncSession) -> Task:
    result = await db.execute(
        select(Task).where(Task.id == task_id, Task.user_id == user_id)
    )
    task = result.scalar_one_or_none()
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task


async def _load_steps(task: Task, db: AsyncSession) -> list[TaskStep]:
    result = await db.execute(
        select(TaskStep)
        .where(TaskStep.task_id == task.id)
        .order_by(TaskStep.created_at)
    )
    return list(result.scalars().all())


def _task_to_response(task: Task, steps: list[TaskStep]) -> TaskResponse:
    return TaskResponse(
        id=task.id,
        user_id=task.user_id,
        description=task.description,
        status=task.status,
        budget_cap=task.budget_cap,
        cost_actual=task.cost_actual,
        estimation=task.estimation,
        result_summary=task.result_summary,
        has_result=bool(task.result_file_path),
        created_at=task.created_at,
        started_at=task.started_at,
        completed_at=task.completed_at,
        steps=[
            TaskStepResponse(
                id=s.id,
                task_id=s.task_id,
                tool=s.tool,
                description=s.description,
                status=s.status,
                cost_usd=s.cost_usd,
                created_at=s.created_at,
            )
            for s in steps
        ],
    )


def _task_to_list_item(task: Task) -> TaskListItem:
    return TaskListItem(
        id=task.id,
        description=task.description,
        status=task.status,
        budget_cap=task.budget_cap,
        cost_actual=task.cost_actual,
        has_result=bool(task.result_file_path),
        created_at=task.created_at,
        started_at=task.started_at,
        completed_at=task.completed_at,
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get(
    "",
    response_model=list[TaskListItem],
)
async def list_tasks(current_user: CurrentUser, db: DbDep) -> list[TaskListItem]:
    """Return lightweight task summaries for the authenticated user, newest first.

    Uses a single query — no N+1. Steps are omitted (use GET /tasks/{id} for those).
    """
    result = await db.execute(
        select(Task)
        .where(Task.user_id == current_user.id)
        .order_by(Task.created_at.desc())
    )
    tasks = list(result.scalars().all())
    return [_task_to_list_item(task) for task in tasks]


@router.post(
    "",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
    },
)
async def create_task(
    payload: TaskCreate,
    current_user: CurrentUser,
    db: DbDep,
) -> TaskResponse:
    """Create a task and immediately start estimation (async in-process).

    Returns the task with estimation data once estimation completes.
    Estimation uses OUR OpenAI key (GPT-4o-mini) and is fast (< 10 s).
    """
    # Enforce: one active task at a time
    active = await db.execute(
        select(Task).where(
            Task.user_id == current_user.id,
            Task.status.in_(list(ACTIVE_STATUSES)),
        )
    )
    if active.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="У вас уже есть активная задача",
        )

    task = Task(
        id=ulid.new().str,
        user_id=current_user.id,
        description=payload.description,
        status="estimating",
    )
    db.add(task)
    await db.commit()
    logger.info("Task created, task_id=%s, user_id=%s", task.id, current_user.id)

    # Run estimation synchronously (it's fast — GPT-4o-mini)
    try:
        estimation = await estimate_task(payload.description)
        task.estimation = estimation
        task.status = "estimated"
        await db.commit()
    except RuntimeError as exc:
        task.status = "failed"
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=sanitize(str(exc)),
        ) from exc

    steps = await _load_steps(task, db)
    return _task_to_response(task, steps)


@router.post(
    "/{task_id}/run",
    response_model=TaskResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
async def run_task(
    task_id: str,
    payload: TaskRunRequest,
    background_tasks: BackgroundTasks,
    current_user: CurrentUser,
    db: DbDep,
) -> TaskResponse:
    """Start executing a task in an E2B sandbox.

    Accepts budget_cap and the user's OpenAI key.
    The key is passed directly to the sandbox and zeroed out immediately —
    it is never stored in the database or written to any log.
    """
    task = await _get_task_or_404(task_id, current_user.id, db)

    if task.status not in ("estimated", "created"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Task cannot be run from status '{task.status}'",
        )

    # Store budget cap
    task.budget_cap = payload.budget_cap
    task.status = "running"
    await db.commit()

    # Pass key to background task; it creates its own DB session and
    # zeros the key immediately after sandbox creation.
    background_tasks.add_task(
        run_task_in_sandbox,
        task_id=task_id,
        description=task.description,
        budget_cap=payload.budget_cap,
        user_openai_key=payload.openai_key,
    )

    steps = await _load_steps(task, db)
    return _task_to_response(task, steps)


@router.get(
    "/{task_id}",
    response_model=TaskResponse,
    responses={404: {"model": ErrorResponse}},
)
async def get_task(
    task_id: str,
    current_user: CurrentUser,
    db: DbDep,
) -> TaskResponse:
    """Return current task state including all steps (used for polling)."""
    task = await _get_task_or_404(task_id, current_user.id, db)
    steps = await _load_steps(task, db)
    return _task_to_response(task, steps)


@router.get(
    "/{task_id}/result",
    responses={
        404: {"model": ErrorResponse},
        400: {"model": ErrorResponse},
    },
)
async def download_result(
    task_id: str,
    current_user: CurrentUser,
    db: DbDep,
) -> FileResponse:
    """Download the result file produced by the agent."""
    task = await _get_task_or_404(task_id, current_user.id, db)

    if not task.result_file_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No result file available for this task",
        )

    file_path = Path(task.result_file_path)
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Result file not found on server",
        )

    return FileResponse(
        path=str(file_path),
        filename=file_path.name,
        media_type="application/octet-stream",
    )


@router.post(
    "/{task_id}/cancel",
    response_model=TaskResponse,
    responses={404: {"model": ErrorResponse}},
)
async def cancel_task(
    task_id: str,
    current_user: CurrentUser,
    db: DbDep,
) -> TaskResponse:
    """Cancel a running task by killing its E2B sandbox."""
    task = await _get_task_or_404(task_id, current_user.id, db)

    if task.status not in ACTIVE_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Task is not active (status='{task.status}')",
        )

    if task.sandbox_id:
        await cancel_sandbox(task.sandbox_id)

    await db.execute(
        update(Task).where(Task.id == task_id).values(status="paused")
    )
    await db.commit()
    await db.refresh(task)

    logger.info("Task cancelled, task_id=%s", task_id)
    steps = await _load_steps(task, db)
    return _task_to_response(task, steps)
