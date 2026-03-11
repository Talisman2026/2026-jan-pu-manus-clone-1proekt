# Development Guide: AgentFlow MVP

---

## Быстрый старт

```bash
cp .env.example .env
# Заполни E2B_API_KEY, OPENAI_API_KEY, FIRECRAWL_API_KEY

docker compose up
# Frontend: http://localhost:3000
# Backend:  http://localhost:8000
# API docs: http://localhost:8000/docs
```

---

## Этапы разработки

### 🧠 Этап 1: Agent (начни отсюда)

Сначала проверь что агент работает без всего остального:

```bash
cd backend/sandbox
pip install openai firecrawl-py
python agent.py --task "Find top 5 Notion competitors" --budget 1.0 --task-id test1
```

Ожидаемый вывод: JSON строки в stdout, файл в `/home/user/results/`

Когда агент стабильно выполняет 3-5 разных задач — переходи дальше.

### 🔧 Этап 2: Backend API

```bash
cd backend
pip install fastapi sqlalchemy psycopg2 python-jose passlib e2b httpx
uvicorn main:app --reload
# Проверь: http://localhost:8000/docs
```

Порядок файлов:
1. `models.py` + `database.py`
2. `routes/auth.py`
3. `services/estimator.py`
4. `services/e2b_manager.py`
5. `routes/tasks.py`

### 🎨 Этап 3: Frontend

```bash
cd frontend
npm install
npm run dev
# http://localhost:3000
```

Порядок страниц:
1. `/login` + `/register`
2. `/settings` (ввод ключа + crypto.ts)
3. `/dashboard` (список задач)
4. `/task/[id]` (лог + результат)

### 🐳 Этап 4: Docker

```bash
docker compose up --build
# Проверь что всё работает в контейнерах
```

### 🚀 Этап 5: Деплой на VPS

```bash
# На VPS:
git clone your-repo /app/agentflow
cd /app/agentflow
cp .env.example .env && nano .env  # заполни переменные
docker compose -f docker-compose.prod.yml up -d
```

---

## Команды Claude Code

| Команда | Действие |
|---------|---------|
| `/init` | Первый запуск — читает документацию, показывает план |
| `/plan [feature]` | Планирование новой фичи |
| `/test [scope]` | Запуск тестов |
| `/deploy` | Деплой на VPS |
| `/myinsights [title]` | Захват решения нетривиальной проблемы |

---

## Агенты

| Агент | Когда использовать |
|-------|-------------------|
| `@planner` | Планирование новой фичи или сложного изменения |
| `@architect` | Архитектурные решения |
| `@code-reviewer` | Перед мержем |

---

## Тестирование агента вручную

Задачи для проверки:
```
1. "Find top 5 competitors of Notion and compare their pricing"
2. "Research latest news about OpenAI from this week"
3. "Find 10 SaaS tools for project management with their prices"
4. "Analyze agentflow.app and write a brief SEO audit"
5. "List 20 AI startups founded in 2024 with funding amounts"
```

---

## Структура коммитов

```
feat(agent): add web_search tool
feat(backend): add /tasks/{id}/run endpoint
feat(frontend): add task log polling
fix(agent): handle firecrawl timeout
fix(backend): sanitize openai key from logs
chore: update docker compose for prod
```

---

## Известные ограничения MVP

| Ограничение | Когда решать |
|-------------|-------------|
| Одна задача за раз | v1.1 |
| Polling вместо WebSocket | v1.1 |
| Нет email уведомлений | v1.1 |
| Нет Stripe / оплаты | v1.1 |
| Файлы хранятся на диске | v1.1 → S3 |
