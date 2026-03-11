# AgentFlow MVP

Автономный AI-агент для сложных задач. Пользователь описывает → агент выполняет → результат в файле.

## Quick Start

```bash
# 1. Клонировать и настроить
cp .env.example .env
# Заполни E2B_API_KEY, OPENAI_API_KEY, FIRECRAWL_API_KEY в .env

# 2. Запустить
docker compose up

# 3. Открыть
# http://localhost:3000
```

## Документация
- [PRD](docs/PRD.md) — что строим
- [Architecture](docs/Architecture.md) — стек и структура
- [Pseudocode](docs/Pseudocode.md) — алгоритмы и agent.py
- [Specification](docs/Specification.md) — user stories
- [Development Guide](DEVELOPMENT_GUIDE.md) — порядок разработки

## Стек
- Next.js 15 + FastAPI + PostgreSQL
- E2B Cloud (sandbox для агента)
- OpenAI GPT-4o (BYOK — пользователь вводит свой ключ)
- Firecrawl (web search)
