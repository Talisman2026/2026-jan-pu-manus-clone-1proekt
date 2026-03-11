# Testing Rules

## Coverage Requirements

| Module | Min Coverage | Rationale |
|--------|:-----------:|-----------|
| agent/core/estimator.py | 90% | Accuracy is core metric |
| agent/core/executor.py | 80% | Main business logic |
| agent/core/router.py | 85% | Cost control |
| api/services/task.service.ts | 80% | Core service |
| api/services/billing.service.ts | 85% | Money involved |
| Overall | ≥75% | Quality baseline |

## Test Pyramid

```
         /\
        /E2E\       ← 20% (Playwright, critical paths only)
       /──────\
      /  Integ. \   ← 30% (full lifecycle, mocked LLM)
     /────────────\
    /   Unit Tests  \ ← 50% (estimator, router, budget, auth)
   /──────────────────\
```

## Required Test Scenarios (from test-scenarios.md)

Все BDD сценарии в `docs/test-scenarios.md` ДОЛЖНЫ быть покрыты тестами.

### Критически важные (обязательны для любого деплоя):
- [ ] Budget cap hard stop (деньги)
- [ ] JWT expiry + refresh flow (безопасность)
- [ ] Task state machine transitions (корректность)
- [ ] Estimation returns within 10 seconds (SLA)
- [ ] Partial results saved on interruption (data safety)

## Mocking Rules

```python
# ✅ Всегда мокировать внешние сервисы в unit tests
@patch('agent.core.estimator.anthropic_client')
@patch('agent.vm.manager.docker_client')

# ✅ Использовать fixtures для test data
@pytest.fixture
def sample_task():
    return Task(description="Test task", budget_cap=5.0, user_id="test-user")

# ❌ Никогда не использовать реальный OpenAI API в unit/integration tests
# ❌ Никогда не использовать реальную БД в unit tests
```

## Running Tests

```bash
# Параллельно (предпочтительно)
npm run test:api & npm run test:agent & wait

# С coverage
pytest apps/agent --cov=agent --cov-report=html
npm run test:api --coverage

# Конкретный сценарий
pytest -k "test_budget_cap"
npm run test -- --grep "Budget Cap"
```
