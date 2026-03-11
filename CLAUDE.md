# CLAUDE.md — AgentFlow MVP

> Автономный AI-агент для сложных задач. Пользователь описывает → агент выполняет → результат в файле.

---

## Что строим

**AgentFlow MVP** — минимальное веб-приложение для проверки гипотезы: пользователи готовы использовать автономного агента для реальных задач (research, analysis, data collection).

**Стек:**
```
Frontend:  Next.js 15 (App Router) + Tailwind + shadcn/ui
Backend:   FastAPI (Python 3.12) + SQLAlchemy + PostgreSQL
Sandbox:   E2B Cloud (microVM per task)
Agent:     Кастомный Python loop + OpenAI GPT-4o tool calling
Search:    Firecrawl MCP (web search + scraping)
Deploy:    Docker Compose → VPS (AdminVPS/HOSTKEY)
```

---

## Структура проекта

```
agentflow/
├── frontend/              # Next.js
├── backend/               # FastAPI
│   └── sandbox/
│       └── agent.py       # код агента (загружается в E2B)
├── docker-compose.yml     # локальная разработка
├── docker-compose.prod.yml # VPS
├── .env.example
└── docs/
```

---

## Ключевые решения

### BYOK — OpenAI API key
```
Пользователь вводит ключ в Settings UI
→ AES-GCM 256-bit encrypt → IndexedDB (браузер)
→ При запуске задачи: decrypt → HTTPS → backend RAM
→ E2B sandbox env: OPENAI_API_KEY
→ После Sandbox.create(): ключ = None

НИКОГДА: не в БД, не в логах, не в .env
```

### Наши ключи (.env)
```
E2B_API_KEY       — создание sandbox'ов
OPENAI_API_KEY    — estimation (GPT-4o-mini, наш расход)
FIRECRAWL_API_KEY — web search внутри sandbox
```

### Agent tools (внутри E2B sandbox)
```
web_search   → Firecrawl search
scrape_url   → Firecrawl scrape
run_python   → subprocess в sandbox
write_file   → сохранить результат
finish       → завершить задачу
```

### Observability
```
Polling каждые 2 сек (не WebSocket — проще для MVP)
Backend читает stdout агента → сохраняет в DB → frontend polling
```

---

## API

```
POST /auth/register
POST /auth/login
POST /auth/logout

GET  /tasks                  список задач
POST /tasks                  создать + estimate
POST /tasks/{id}/run         { budget_cap, openai_key } → запустить
GET  /tasks/{id}             статус + шаги (для polling)
GET  /tasks/{id}/result      скачать файл
POST /tasks/{id}/cancel      остановить
```

---

## База данных

```sql
users(id, email, password_hash, created_at)

tasks(id, user_id, description, status, budget_cap, cost_actual,
      estimation JSONB, result_summary, result_file_path,
      sandbox_id, created_at, started_at, completed_at)

task_steps(id, task_id, tool, description, status, cost_usd, created_at)
```

Task statuses: `created → estimating → estimated → running → completed / failed / paused`

---

## Security (ОБЯЗАТЕЛЬНО)

```python
# Log filter — применять ко всем логам
REDACT_PATTERNS = [r'sk-[a-zA-Z0-9\-_]{20,}', r'e2b_\w+', r'fc-\w+']

# OpenAI ключ пользователя
# ✅ Принять в body POST /tasks/{id}/run
# ✅ Передать в E2B sandbox env
# ✅ Сразу user_openai_key = None после передачи
# ❌ НЕ логировать
# ❌ НЕ писать в БД
# ❌ НЕ включать в сообщения об ошибках
```

---

## Порядок разработки

```
1. backend/sandbox/agent.py     ← СНАЧАЛА, тестируем локально
2. backend/                     ← API + E2B manager
3. frontend/                    ← UI
4. Docker + деплой на VPS
```

---

## Git Discipline

```
Коммит после каждого логического изменения
Format: type(scope): description
Types: feat | fix | refactor | docs | test | chore

Примеры:
feat(agent): add web_search tool
feat(backend): add task estimation endpoint
fix(frontend): fix polling interval cleanup
```

---

## Документация

```
docs/PRD.md           → что строим и зачем
docs/Architecture.md  → структура, стек, схема
docs/Pseudocode.md    → алгоритмы и agent.py код
docs/Specification.md → user stories + API contracts
docs/Refinement.md    → edge cases + security
docs/Completion.md    → DoD + порядок разработки
```
