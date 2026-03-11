# Architecture: AgentFlow MVP

**Версия:** 2.0 MVP | **Дата:** 2026-03-11

---

## 1. Обзор

Простая двухслойная архитектура: Next.js фронтенд + FastAPI бэкенд. Никакого monorepo, никаких очередей, никакого отдельного agent-сервиса.

```
Browser (Next.js)
      │  HTTPS
      ▼
FastAPI (Python)  ──►  PostgreSQL
      │
      │  E2B REST API
      ▼
E2B Cloud (microVM)
  └── agent.py
      ├── OpenAI GPT-4o  (пользовательский ключ)
      └── Firecrawl      (наш ключ)
```

---

## 2. Структура проекта

```
agentflow/
├── frontend/                  # Next.js 15
│   ├── app/
│   │   ├── (auth)/
│   │   │   ├── login/
│   │   │   └── register/
│   │   ├── dashboard/         # список задач
│   │   ├── task/[id]/         # страница задачи + лог
│   │   └── settings/          # ввод API ключа
│   ├── components/
│   └── lib/
│       ├── api.ts             # fetch wrapper
│       └── crypto.ts          # AES-GCM шифрование ключа
│
├── backend/                   # FastAPI (Python 3.12)
│   ├── main.py                # точка входа
│   ├── routes/
│   │   ├── auth.py            # register, login, logout
│   │   ├── tasks.py           # CRUD + estimate + run
│   │   └── users.py           # settings
│   ├── services/
│   │   ├── e2b_manager.py     # создание/управление sandbox
│   │   └── estimator.py       # pre-run estimation
│   ├── models.py              # SQLAlchemy модели
│   ├── database.py            # PostgreSQL подключение
│   └── sandbox/
│       ├── agent.py           # код агента (едет в E2B)
│       └── requirements.txt   # зависимости агента
│
├── docker-compose.yml         # локальная разработка
├── docker-compose.prod.yml    # VPS деплой
├── Dockerfile.frontend
├── Dockerfile.backend
├── .env.example
└── docs/
```

---

## 3. Стек

### Frontend
| Технология | Назначение |
|-----------|-----------|
| Next.js 15 (App Router) | React фреймворк |
| TypeScript | Типизация |
| Tailwind CSS | Стили |
| shadcn/ui | Компоненты |
| Web Crypto API | AES-GCM шифрование ключа |
| IndexedDB | Хранение зашифрованного ключа |

### Backend
| Технология | Назначение |
|-----------|-----------|
| Python 3.12 | Runtime |
| FastAPI | HTTP API |
| SQLAlchemy 2.x | ORM |
| PostgreSQL 16 | База данных |
| python-jose | JWT токены |
| passlib + bcrypt | Хэширование паролей |
| httpx | E2B REST API клиент |
| e2b SDK | Управление sandbox |

### Infrastructure
| Компонент | Технология |
|-----------|-----------|
| Контейнеры | Docker + Docker Compose |
| VPS | AdminVPS/HOSTKEY |
| Reverse proxy | Nginx (только на VPS) |
| TLS | Certbot / Let's Encrypt |

### Внешние сервисы
| Сервис | Назначение | Чей ключ |
|--------|-----------|---------|
| E2B | Sandbox для агента | Наш |
| OpenAI GPT-4o | LLM для задач | Пользователя (BYOK) |
| OpenAI GPT-4o-mini | Pre-run estimation | Наш |
| Firecrawl | Web search + scraping | Наш |

---

## 4. База данных

```sql
CREATE TABLE users (
  id          TEXT PRIMARY KEY,        -- ulid
  email       TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  created_at  TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE tasks (
  id            TEXT PRIMARY KEY,
  user_id       TEXT REFERENCES users(id),
  description   TEXT NOT NULL,
  status        TEXT DEFAULT 'created', -- created|estimating|estimated|running|paused|completed|failed
  budget_cap    NUMERIC(10,4),
  cost_actual   NUMERIC(10,4) DEFAULT 0,
  estimation    JSONB,                  -- {steps, duration_min, duration_max}
  result_summary TEXT,
  result_file_path TEXT,
  sandbox_id    TEXT,                   -- E2B sandbox ID
  created_at    TIMESTAMPTZ DEFAULT now(),
  started_at    TIMESTAMPTZ,
  completed_at  TIMESTAMPTZ
);

CREATE TABLE task_steps (
  id          TEXT PRIMARY KEY,
  task_id     TEXT REFERENCES tasks(id),
  tool        TEXT NOT NULL,           -- web_search|scrape_url|run_python|write_file|finish
  description TEXT,
  status      TEXT DEFAULT 'done',     -- running|done|error
  cost_usd    NUMERIC(10,6) DEFAULT 0,
  created_at  TIMESTAMPTZ DEFAULT now()
);
```

---

## 5. BYOK — OpenAI Key Flow

```
ХРАНЕНИЕ (браузер):
  Пользователь вводит sk-... → AES-GCM 256-bit encrypt → IndexedDB
  Мастер-пароль = пароль пользователя (PBKDF2, 100K итераций)
  Ключ не покидает браузер в зашифрованном виде

ПЕРЕДАЧА при запуске задачи:
  Браузер расшифровывает → POST /api/tasks/{id}/run (HTTPS, body)
  Backend (RAM only) → E2B sandbox env: OPENAI_API_KEY
  После Sandbox.create() → ключ = None в памяти

ГАРАНТИИ:
  ✗ Не пишется в БД
  ✗ Не попадает в логи (log filter на все sk-... паттерны)
  ✗ Не в .env (это наш ключ для estimation, не пользователя)
```

---

## 6. Docker Compose (локальная разработка)

```yaml
version: "3.8"
services:
  frontend:
    build:
      context: .
      dockerfile: Dockerfile.frontend
    ports: ["3000:3000"]
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8000
    depends_on: [backend]

  backend:
    build:
      context: .
      dockerfile: Dockerfile.backend
    ports: ["8000:8000"]
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - JWT_SECRET=${JWT_SECRET}
      - E2B_API_KEY=${E2B_API_KEY}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - FIRECRAWL_API_KEY=${FIRECRAWL_API_KEY}
    depends_on: [postgres]
    volumes:
      - ./backend:/app  # hot reload в dev

  postgres:
    image: postgres:16-alpine
    environment:
      - POSTGRES_DB=agentflow
      - POSTGRES_USER=${POSTGRES_USER}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
    volumes: [pgdata:/var/lib/postgresql/data]
    ports: ["5432:5432"]

volumes:
  pgdata:
```

---

## 7. Деплой на VPS

```
docker-compose.prod.yml добавляет:
- Nginx контейнер (reverse proxy + TLS)
- Certbot для Let's Encrypt
- Убирает volume mount (нет hot reload)
- restart: unless-stopped на все сервисы

Процесс деплоя:
git push → ssh VPS → git pull → docker compose -f docker-compose.prod.yml up -d --build
```
