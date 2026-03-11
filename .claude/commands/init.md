# /init — Project Initialization

Первый запуск после unzip/clone.

## Steps

1. Прочитай CLAUDE.md — главный контекст проекта
2. Прочитай DEVELOPMENT_GUIDE.md — порядок разработки
3. Прочитай docs/Architecture.md — стек и структура
4. Прочитай docs/Pseudocode.md — алгоритмы, особенно agent.py
5. Если есть docs/insights.md — прочитай известные проблемы

6. Инициализируй git:
   ```bash
   git init
   git add .
   git commit -m "chore: initial agentflow mvp setup"
   ```

7. Покажи пользователю:
   - Краткое описание проекта
   - Порядок разработки (4 этапа из DEVELOPMENT_GUIDE)
   - Доступные команды: /plan, /test, /deploy, /myinsights

8. Скажи: "С чего начнём? Рекомендую стартовать с backend/sandbox/agent.py"
