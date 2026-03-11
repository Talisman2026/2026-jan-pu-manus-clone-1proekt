# Git Workflow Rules

## Commit Rules

**Commit после каждого логического изменения** — не в конце сессии.

### Format
```
type(scope): description (max 50 chars)
```

### Types
| Type | When |
|------|------|
| `feat` | Новая функциональность |
| `fix` | Исправление бага |
| `refactor` | Рефакторинг без изменения поведения |
| `docs` | Документация |
| `test` | Тесты |
| `chore` | Конфиг, зависимости, CI |

### Scopes (AgentFlow specific)
```
agent     → apps/agent/
api       → apps/api/
web       → apps/web/
db        → packages/db/
infra     → infra/, docker-compose.yml
feature   → feature lifecycle (docs)
insights  → docs/insights.md
```

### Examples
```
feat(agent): add pre-run estimation engine
feat(api): add POST /api/tasks/confirm endpoint
fix(agent): handle LLM timeout with exponential backoff
fix(api): enforce budget cap hard stop correctly
test(agent): add unit tests for model router
docs(feature): add SPARC docs for budget-caps
chore(infra): update nginx config for websocket proxy
```

## Branch Strategy

```
main          → production (protected)
feat/<name>   → new features
fix/<name>    → bug fixes
```

**Для MVP:** прямые коммиты в main допустимы для solo dev.

## Never Commit

```
.env files (только .env.example)
API keys, secrets, passwords
node_modules/, __pycache__/
*.log файлы
```
