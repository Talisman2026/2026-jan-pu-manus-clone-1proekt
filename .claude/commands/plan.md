# /plan [feature] — Implementation Planning

Создать детальный план реализации фичи на основе SPARC документации.

## Usage

```
/plan task-execution-engine
/plan pre-run-estimation
/plan "add Slack integration"
```

## Process

1. Прочитай `docs/features/<n>/sparc/Pseudocode.md` (если есть)
2. Прочитай `docs/Architecture.md` — учти существующую структуру
3. Разбей на параллельные Tasks:

```
IMPLEMENTATION PLAN: <feature>

Backend tasks (apps/api/ или apps/agent/):
├── Task 1: <конкретный модуль> (~X мин)
├── Task 2: <конкретный модуль> (~X мин) ← parallel с Task 1
└── Task 3: DB migration (packages/db/) ← parallel

Frontend tasks (apps/web/):
├── Task 4: <page/component> (~X мин) ← parallel с Task 1-3
└── Task 5: <component> (~X мин)

Tests:
└── Task 6: <test scope> (~X мин) ← parallel с Task 4-5

Estimated total: ~X мин (с параллельным выполнением)
```

4. Используй @architect для architectural questions
5. Начни с самого рискованного/блокирующего Task'а

## Swarm Agents

| Агент | Когда использовать |
|-------|-------------------|
| @planner | Разбивка сложной задачи на Tasks |
| @architect | Architectural decisions, consistency |
| @code-reviewer | Code quality перед коммитом |
| @tdd-guide | Test-first подход для критических путей |
