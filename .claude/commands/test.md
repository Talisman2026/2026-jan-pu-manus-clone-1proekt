# /test [scope] — Test Generation & Execution

## Usage

```
/test unit:agent/estimator
/test integration:task-lifecycle
/test e2e:task-creation
/test all
```

## Process

1. Прочитай `docs/test-scenarios.md` — BDD сценарии как основа
2. Прочитай `docs/Refinement.md` — edge cases и testing strategy
3. Сгенерируй тесты для scope:

### Unit Tests (apps/agent/tests/ или apps/api/tests/)
- Тестировать: estimation algorithm, model routing, budget calculation
- Мокировать: LLM API, Docker API, Browser
- Coverage target: ≥80% для core business logic

### Integration Tests
- Тестировать: полный task lifecycle (mocked LLM)
- Фокус: budget cap enforcement, WS events, DB state transitions

### E2E Tests (Playwright, tests/e2e/)
- Основа: BDD сценарии из test-scenarios.md
- Happy paths + critical error scenarios

## Запуск параллельно

```bash
# Все тесты параллельно
npm run test:api & npm run test:agent & npm run test:e2e &
wait

# Конкретный scope
npm run test -- --grep "estimation"
```

## Template: Unit Test (Python)

```python
# tests/unit/test_estimator.py
import pytest
from unittest.mock import AsyncMock, patch
from agent.core.estimator import estimate_task

@pytest.mark.asyncio
async def test_estimation_returns_within_bounds():
    """Estimation accuracy: actual should be within ±30% of estimate"""
    with patch('agent.core.estimator.LLM') as mock_llm:
        mock_llm.classify.return_value = {"intent": "research", "confidence": 0.9}
        mock_llm.plan.return_value = {"steps": [
            {"tool": "browser", "estimated_complexity": "medium"},
            {"tool": "bash", "estimated_complexity": "low"},
        ]}
        
        result = await estimate_task("Research top 5 AI tools")
        
        assert result.steps_min >= 1
        assert result.steps_max <= 20
        assert result.cost_estimate_usd > 0
        assert result.confidence >= 0.5
```
