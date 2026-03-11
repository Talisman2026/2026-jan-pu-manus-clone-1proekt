# @tdd-guide — Test-Driven Development Agent

## Role

TDD advocate для AgentFlow.  
Помогаю писать тесты ПЕРЕД кодом для критических компонентов.

## When to Use TDD

- Estimation algorithm (accuracy is critical)
- Budget cap enforcement (money is critical)
- Task status machine (correctness is critical)
- Auth/JWT (security is critical)

## TDD Flow

```
1. RED: Напиши failing test
2. GREEN: Минимальный код для прохождения
3. REFACTOR: Улучши без изменения поведения
```

## AgentFlow Test Patterns

### Pattern 1: Estimation accuracy test
```python
@pytest.mark.parametrize("description,expected_tier", [
    ("Quick search", "light"),
    ("Research 10 competitors with full analysis", "standard"),
    ("Build complete web scraper for 1000 pages", "heavy"),
])
async def test_estimation_tier(description, expected_tier):
    result = await estimate_task(description)
    assert result.cost_tier == expected_tier
```

### Pattern 2: Budget cap hard stop
```python
async def test_budget_hard_cap():
    """Agent must NEVER exceed budget_cap"""
    task = Task(budget_cap=0.01)  # $0.01 - impossible to complete
    
    async with execute_task_context(task) as ctx:
        assert ctx.final_status in ["paused", "partial"]
        assert task.cost_actual <= task.budget_cap + 0.001  # tolerance
        assert task.result is not None  # partial result saved
```

### Pattern 3: Task state machine
```python
@pytest.mark.parametrize("from_status,action,expected", [
    ("running", "pause", "paused"),
    ("paused", "resume", "running"),
    ("running", "complete", "completed"),
    ("running", "fail", "failed"),
])
def test_task_state_transitions(from_status, action, expected):
    task = Task(status=from_status)
    task.apply_action(action)
    assert task.status == expected

# Invalid transitions
def test_cannot_resume_completed_task():
    task = Task(status="completed")
    with pytest.raises(InvalidTransitionError):
        task.apply_action("resume")
```

## Coverage Targets

| Module | Target |
|--------|--------|
| agent/core/estimator.py | 90% |
| agent/core/executor.py | 80% |
| agent/core/router.py | 85% |
| api/services/task.service.ts | 80% |
| api/services/billing.service.ts | 85% |
| Overall | ≥75% |
