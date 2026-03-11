# /myinsights [title] — Capture Development Insight

Захват знания после решения нетривиальной проблемы.

## Usage

```
/myinsights "LLM context overflow during long task execution"
/myinsights "VM cold start causing task timeout"
/myinsights "Stripe webhook signature verification failing"
```

## Process

1. Прочитай `docs/insights.md` (если существует) — не дублируй
2. Запроси у пользователя детали (если title неполный):
   - Что наблюдалось? (симптомы)
   - Как диагностировали?
   - В чём была корневая причина?
   - Как решили?
   - Как предотвратить в будущем?

3. Добавь запись в `docs/insights.md`:

```markdown
## [YYYY-MM-DD] [Title]

**Контекст:** AgentFlow, <module/service>

**Symptoms:**
- [что наблюдалось]

**Diagnostic:**
- [как нашли проблему]

**Root Cause:**
- [почему происходило]

**Solution:**
```code
[конкретный fix если есть]
```

**Prevention:**
- [как не допустить в будущем]
- [что добавить в Refinement.md]

**Tags:** `#agent` `#vm` `#api` `#frontend` `#db` `#llm` `#billing`
```

4. Stop hook автоматически закоммитит `docs/insights.md`

## При каких ситуациях обязательно запускать

- Агент зависал в петле → нашли причину
- LLM давал неожиданный output → нашли паттерн
- VM container падал → нашли fix
- Estimation accuracy была сильно off → нашли bias
- Stripe webhook не срабатывал → нашли причину
- WebSocket disconnects → нашли pattern
- Database query медленный → нашли индекс

## Когда Claude предлагает сам

Claude автоматически предложит `/myinsights` если:
- Отладка заняла > 30 минут
- Проблема была неочевидной (не первый google result)
- Решение counter-intuitive
- Проблема могла бы повториться
