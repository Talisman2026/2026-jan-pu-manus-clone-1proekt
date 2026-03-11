# Feature Development Lifecycle

## Protocol

Каждая новая фича ОБЯЗАНА следовать 4-фазному lifecycle:

```
/feature [name]
  Phase 1: PLAN      → sparc-prd-manual → docs/features/<n>/sparc/
  Phase 2: VALIDATE  → requirements-validator (swarm, max 3 итерации)
  Phase 3: IMPLEMENT → swarm agents + parallel tasks
  Phase 4: REVIEW    → brutal-honesty-review (swarm)
```

## Rules

### Planning (Phase 1)
- ВСЕ фичи получают SPARC документацию, без исключений
- Документация в `docs/features/<feature-name>/sparc/`
- sparc-prd-manual в MANUAL режиме для сложных, AUTO для простых
- Architecture.md ОБЯЗАН быть consistent с root Architecture.md
- Коммит docs до начала implementation

### Validation (Phase 2)
- Запускать requirements-validator как swarm (параллельные агенты)
- Минимальный score: 70/100 avg, нет BLOCKED (<50)
- Исправлять пробелы в docs, не в коде
- Максимум 3 итерации — если не проходит, эскалировать
- Коммит validation-report.md

### Implementation (Phase 3)
- Читать SPARC docs — не галлюцинировать код
- Модульный дизайн — компоненты переиспользуются
- Task tool для параллельной работы над независимыми модулями
- Коммит после каждого логического изменения
- Тесты запускать параллельно с реализацией
- Format: `feat(<feature-name>): <что>`

### Review (Phase 4)
- brutal-honesty-review с swarm of agents
- Без sugar-coating — находить реальные проблемы
- Исправить все CRITICAL и MAJOR до завершения
- Коммит review-report.md

## Когда пропускать фазы

| Сценарий | Пропустить | Обоснование |
|----------|------------|-------------|
| Hotfix (1-5 строк) | Phase 1-2 | Слишком мало для SPARC |
| Config change | Phase 1-2 | Нет новой функциональности |
| Dependency update | Phase 1-2 | Нет нового дизайна |
| Refactoring | Phase 1 | Validate + implement + review |
| New feature | НИКОГДА | Полный lifecycle всегда |

Phase 4 (review) всегда обязательна, даже для мелких изменений.

## Feature Directory Structure

```
docs/features/
├── task-execution-engine/
│   ├── sparc/
│   │   ├── PRD.md
│   │   ├── Specification.md
│   │   ├── Pseudocode.md
│   │   ├── Architecture.md
│   │   ├── Refinement.md
│   │   ├── Completion.md
│   │   └── validation-report.md
│   └── review-report.md
└── pre-run-estimation/
    └── ...
```
