# Insights Capture Protocol

## When to Capture

Claude ДОЛЖЕН предложить `/myinsights` если:

- Отладка заняла > 30 минут
- Проблема была неочевидной (не в первых результатах поиска)
- Решение оказалось counter-intuitive
- Ошибка могла повториться
- Найден workaround для известного бага библиотеки
- Обнаружено неожиданное поведение LLM API или Docker

## Format (docs/insights.md)

```markdown
## [YYYY-MM-DD] [Краткий заголовок проблемы]

**Контекст:** AgentFlow, <service/module>

**Symptoms:**
- <что наблюдалось пользователем/системой>

**Diagnostic:**
- <шаги которые привели к обнаружению>

**Root Cause:**
- <настоящая причина>

**Solution:**
```code or steps```

**Prevention:**
- <правило или паттерн для предотвращения>
- <что добавить в Refinement.md если нужно>

**Tags:** #agent #vm #api #web #db #llm #billing #docker #playwright
```

## Before Debugging

**Всегда** проверь `docs/insights.md` ПЕРЕД началом отладки.  
Возможно, проблема уже была решена.

## Auto-commit

Stop hook автоматически коммитит `docs/insights.md` при завершении сессии.  
Не нужно помнить про `git add`.
