# Refinement: AgentFlow MVP

**Версия:** 2.0 MVP | **Дата:** 2026-03-11

---

## 1. Edge Cases

### Task Execution

| Сценарий | Поведение |
|----------|-----------|
| E2B sandbox не создался | Retry 1x, затем task → failed, показать ошибку пользователю |
| OpenAI API вернул 429 (rate limit) | Retry с backoff 10s, затем task → failed |
| OpenAI API недоступен | task → failed, сообщение "OpenAI API unavailable" |
| Sandbox timeout (30 мин) | E2B auto-kill, сохраняем partial steps, task → paused |
| Агент в цикле (один tool 5+ раз подряд) | Force stop, save partial, task → paused |
| Firecrawl недоступен | Агент получает ошибку и пробует другой подход или завершает |
| Пользователь закрыл вкладку | Задача продолжает в фоне, при возврате polling подхватывает |
| Budget exceeded без ответа | После 60s → task → paused, partial results доступны |

### Auth

| Сценарий | Поведение |
|----------|-----------|
| Истёкший JWT | 401 → фронтенд редирект на /login |
| Неверный пароль | 401 + "Неверный email или пароль" (не указываем что именно) |
| Email уже занят | 400 + "Этот email уже зарегистрирован" |

### API Key

| Сценарий | Поведение |
|----------|-----------|
| Неверный OpenAI ключ | E2B sandbox создаётся, агент сразу падает с auth error → task failed + "Invalid OpenAI API key" |
| Ключ удалён из браузера | При запуске задачи → "API key not found, please add it in Settings" |

---

## 2. Security

### Log Filter (обязательно в backend)
```python
import re

REDACT_PATTERNS = [
    r'sk-[a-zA-Z0-9\-_]{20,}',   # OpenAI key
    r'e2b_[a-zA-Z0-9]{20,}',      # E2B key
    r'fc-[a-zA-Z0-9]{20,}',       # Firecrawl key
]

def sanitize(text: str) -> str:
    for pattern in REDACT_PATTERNS:
        text = re.sub(pattern, '[REDACTED]', text)
    return text

# Применять ко всем log сообщениям и сообщениям об ошибках
```

### Input Validation
- Task description: max 2000 символов
- Budget cap: min $0.10, max $20.00
- Email: стандартная валидация
- Password: min 8 символов

---

## 3. Performance

- **E2B cold start** (~1-3 сек): показываем "Preparing sandbox..." в UI
- **pip install в sandbox** (~10-20 сек): показываем "Installing dependencies..."
- **Итого до первого шага агента**: ≤ 30 сек — нормально для MVP
- **Polling**: каждые 2 сек пока задача активна, каждые 10 сек если completed/failed

---

## 4. Testing

### Ручное тестирование (MVP)
Список задач для проверки агента:
1. "Find top 5 competitors of Notion and create a comparison table"
2. "Research the latest news about OpenAI from the past week"
3. "Find the pricing pages of 10 SaaS tools in the project management space"
4. "Analyze the website example.com and write an SEO audit"
5. "Create a list of 20 AI startups founded in 2024 with their funding"

### Автотесты (минимум для MVP)
```
tests/
├── test_auth.py          # register, login, JWT
├── test_tasks.py         # create, estimate, run flow
├── test_e2b.py           # sandbox create/kill (с mock)
└── test_agent.py         # agent loop с mock OpenAI
```
