# Completion: AgentFlow MVP

**Версия:** 2.0 MVP | **Дата:** 2026-03-11

---

## 1. Definition of Done

MVP готов когда:

- [ ] Пользователь может зарегистрироваться и залогиниться
- [ ] Пользователь может ввести OpenAI ключ (шифруется в браузере)
- [ ] Пользователь может создать задачу и получить estimation
- [ ] Агент выполняет задачу в E2B sandbox
- [ ] Лог шагов обновляется в реальном времени (polling)
- [ ] Budget cap работает — агент останавливается при достижении лимита
- [ ] Файл результата скачивается
- [ ] История задач отображается на dashboard
- [ ] Приложение запускается через `docker compose up`
- [ ] Приложение деплоится на VPS и доступно по HTTPS

---

## 2. Порядок разработки

### Этап 1: Agent core (начни отсюда)
```
backend/sandbox/agent.py  ← пишем и тестируем первым
backend/sandbox/requirements.txt

Тест: python agent.py --task "find top 5 AI tools" --budget 1.0 --task-id test1
Ожидаем: JSON события в stdout, файл в /home/user/results/
```

### Этап 2: Backend API
```
backend/main.py
backend/models.py
backend/database.py
backend/routes/auth.py
backend/routes/tasks.py    ← e2b_manager внутри
backend/services/e2b_manager.py
backend/services/estimator.py
```

### Этап 3: Frontend
```
frontend/app/(auth)/login
frontend/app/(auth)/register
frontend/app/settings       ← ввод API ключа
frontend/app/dashboard      ← список задач
frontend/app/task/[id]      ← лог выполнения + результат
frontend/lib/crypto.ts      ← AES-GCM шифрование
```

### Этап 4: Docker + деплой
```
Dockerfile.frontend
Dockerfile.backend
docker-compose.yml          ← локально
docker-compose.prod.yml     ← VPS
```

---

## 3. .env.example

```bash
# Database
DATABASE_URL=postgresql://agentflow:password@postgres:5432/agentflow
POSTGRES_USER=agentflow
POSTGRES_PASSWORD=change_me

# Auth
JWT_SECRET=change_me_to_32_byte_random_string

# E2B
E2B_API_KEY=e2b_your_key_here

# OpenAI (НАШ ключ — только для estimation)
# Ключ пользователя вводится в UI и НЕ хранится здесь
OPENAI_API_KEY=sk-your_key_here

# Firecrawl
FIRECRAWL_API_KEY=fc-your_key_here
```

---

## 4. Runbooks

### Агент не завершает задачу
```
1. Проверь логи backend: docker compose logs backend
2. Проверь активные E2B sandboxes в dashboard e2b.dev
3. Если sandbox завис — он auto-kill через 30 мин
4. Если проблема в промпте агента — правь agent.py и rebuild
```

### Backend не стартует
```
docker compose logs backend
# Чаще всего: DATABASE_URL неверный или postgres ещё не готов
# Решение: depends_on + healthcheck в docker-compose.yml
```

### VPS деплой
```bash
ssh user@your-vps
cd /app/agentflow
git pull
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml ps  # проверить статус
```

---

## 5. Известные ограничения MVP

| Ограничение | Когда решать |
|-------------|-------------|
| Одна задача за раз | v1.1 — очередь задач |
| Нет WebSocket (polling) | v1.1 — реальный стриминг |
| Нет email уведомлений | v1.1 |
| Нет оплаты | v1.1 — Stripe |
| Результаты хранятся на диске сервера | v1.1 — S3/Minio |
| Нет retry для упавших задач | v1.1 |
