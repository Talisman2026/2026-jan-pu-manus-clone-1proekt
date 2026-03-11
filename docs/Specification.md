# Specification: AgentFlow MVP

**Версия:** 2.0 MVP | **Дата:** 2026-03-11

---

## 1. User Stories

### Auth

**US-001: Регистрация**
```gherkin
Scenario: Новый пользователь регистрируется
  Given я на странице /register
  When я ввожу email и пароль (мин. 8 символов)
  And нажимаю "Зарегистрироваться"
  Then меня редиректит на /settings
  And я вижу подсказку "Введите ваш OpenAI API key для начала работы"
```

**US-002: Логин**
```gherkin
Scenario: Пользователь логинится
  Given я на странице /login
  When я ввожу корректные email и пароль
  Then меня редиректит на /dashboard
  And я вижу список своих задач (пустой если новый)
```

---

### API Key Setup

**US-003: Ввод OpenAI ключа**
```gherkin
Scenario: Пользователь вводит API ключ
  Given я на странице /settings
  When я ввожу свой OpenAI API key (sk-...)
  And нажимаю "Сохранить"
  Then ключ шифруется и сохраняется в браузере
  And я вижу "Ключ сохранён ✓" (показываем только последние 4 символа)
  And ключ НЕ отправляется на сервер в этот момент

Scenario: Пользователь пытается запустить задачу без ключа
  Given у меня нет сохранённого API ключа
  When я нажимаю "Запустить задачу"
  Then вижу сообщение "Сначала добавьте OpenAI API key в Settings"
  And кнопку "Перейти в Settings"
```

---

### Task Execution

**US-004: Создание и запуск задачи**
```gherkin
Scenario: Пользователь запускает задачу
  Given я залогинен и у меня есть API ключ
  When я ввожу описание задачи
  And нажимаю "Оценить"
  Then через ≤ 10 сек вижу estimation:
    | Поле | Пример |
    | Примерных шагов | 8-12 |
    | Примерное время | 5-10 мин |
    | Оценка стоимости | ~$0.15 |
  And могу установить budget cap (по умолчанию = estimate * 1.5)
  When нажимаю "Запустить"
  Then задача начинает выполняться
  And меня редиректит на /task/{id}

Scenario: Одна задача за раз
  Given у меня уже есть задача со статусом "running"
  When я пытаюсь запустить новую задачу
  Then вижу "У вас уже есть активная задача"
  And кнопку "Посмотреть активную задачу"
```

**US-005: Наблюдение за выполнением**
```gherkin
Scenario: Пользователь видит лог в реальном времени
  Given задача выполняется
  When я на странице /task/{id}
  Then вижу лог шагов обновляющийся каждые 2 секунды
  And каждый шаг показывает: иконку инструмента + описание + статус
  And вижу прогресс-бар бюджета

Scenario: Budget warning
  Given задача использовала 80% бюджета
  Then вижу предупреждение "Использовано 80% бюджета"
  And кнопки "Продолжить" и "Остановить"
```

**US-006: Получение результата**
```gherkin
Scenario: Задача завершена успешно
  Given задача завершена
  Then вижу summary результата в UI
  And кнопку "Скачать результат"
  When нажимаю "Скачать результат"
  Then скачивается файл (.md, .xlsx, .csv или .html)

Scenario: Задача завершена с ошибкой
  Given задача завершена с ошибкой
  Then вижу сообщение об ошибке
  And кнопку "Попробовать снова"
```

---

## 2. Non-functional Requirements

- Task start (sandbox ready): ≤ 5 сек после нажатия "Запустить"
- Polling latency: ≤ 2 сек до появления нового шага в UI
- API response time p95: ≤ 500ms
- Один пользователь = одна задача одновременно

---

## 3. Tech Constraints

| Constraint | Значение |
|-----------|---------|
| Architecture | Monolith (frontend + backend) |
| Sandbox | E2B Cloud (microVM) |
| Agent LLM | OpenAI GPT-4o (BYOK) |
| Estimation LLM | OpenAI GPT-4o-mini (наш ключ) |
| Web search | Firecrawl (наш ключ) |
| Deploy | Docker Compose на VPS |
| Observability | Polling каждые 2 сек (не WebSocket) |
