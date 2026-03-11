# Secrets Management

## Ключи в .env (серверные)
| Ключ | Назначение |
|------|-----------|
| `E2B_API_KEY` | Создание sandbox'ов |
| `OPENAI_API_KEY` | Estimation (GPT-4o-mini, наш расход) |
| `FIRECRAWL_API_KEY` | Web search внутри sandbox |

## BYOK — OpenAI ключ пользователя

**Жизненный цикл:**
```
UI Settings → AES-GCM encrypt → IndexedDB
При запуске задачи → decrypt в браузере
→ POST /tasks/{id}/run body (HTTPS)
→ backend RAM → E2B sandbox env
→ user_key = None (сразу после передачи)
```

**Правила:**
```python
# ✅ Правильно
sandbox = await e2b.Sandbox.create(envs={"OPENAI_API_KEY": user_key})
user_key = None  # сразу

# ❌ Запрещено
logger.info(f"key: {user_key}")      # логировать
db.execute("UPDATE ... SET key=...", user_key)  # в БД
raise Exception(f"Failed: {user_key}")  # в ошибках
```

**Log filter (обязательно):**
```python
import re
def sanitize(text):
    for p in [r'sk-\S{20,}', r'e2b_\S+', r'fc-\S+']:
        text = re.sub(p, '[REDACTED]', text)
    return text
```

**UI disclosure:**
> "Ваш ключ хранится только в вашем браузере. При запуске задачи передаётся на сервер по зашифрованному соединению и не сохраняется."
