# /feature [name] — Full Feature Lifecycle

Запускает 4-фазный lifecycle для новой фичи AgentFlow.

## Usage

```
/feature task-execution-engine
/feature pre-run-estimation
/feature budget-caps
/feature [any-feature-name]
```

## Phase 1: PLAN (SPARC Documentation)

```
Read skill: .claude/skills/sparc-prd-manual/SKILL.md
```

Создать SPARC документацию в `docs/features/<name>/sparc/`:
- PRD.md (scope этой фичи)
- Specification.md (user stories + AC в Gherkin)
- Pseudocode.md (алгоритмы + data flow)
- Architecture.md (как вписывается в текущую архитектуру)
- Refinement.md (edge cases + testing)
- Completion.md (deploy + monitoring)

**Передать в sparc-prd-manual:**
```
Architecture Constraints:
- Distributed Monolith, Docker Compose, VPS
- Primary LLM: OpenAI (GPT-4o)
- Multi-model routing: Haiku для estimation, Sonnet для execution

Project Context:
- AgentFlow = autonomous AI agent + flat-rate billing
- Main differentiator: pre-run estimation + budget caps
- Existing services: api (Fastify), web (Next.js), agent (Python)
```

Режим: MANUAL (с checkpoint на каждой фазе)

Коммит: `docs(feature): add SPARC docs for <name>`

⏸️ **Checkpoint 1:** Подтверди документацию

## Phase 2: VALIDATE (Requirements Validation)

```
Read skill: .claude/skills/requirements-validator/SKILL.md
```

Запустить Swarm Validation (параллельно):
```
Task A: validator-stories  → INVEST score на user stories
Task B: validator-ac       → SMART score на acceptance criteria  
Task C: validator-arch     → соответствие архитектуре проекта
Task D: validator-coherence → кросс-документ consistency
```

Exit criteria: среднее ≥ 70/100, нет BLOCKED (< 50)
Max 3 итерации. Если не проходит → вернуться к Phase 1.

Коммит: `docs(feature): validation report for <name>`

⏸️ **Checkpoint 2:** Подтверди validation results

## Phase 3: IMPLEMENT

Читать SPARC docs — НЕ галлюцинировать код.

Запустить параллельные Tasks для независимых модулей:
```
Task A: backend logic (api/ или agent/)
Task B: database migrations (packages/db/)    ← parallel
Task C: frontend UI (web/)                    ← parallel
Task D: tests                                 ← parallel с B и C
```

Правила:
- Коммит после каждого логического изменения
- Format: `feat(<name>): <что>`
- Использовать @planner для разбивки на tasks
- Использовать @architect для architectural decisions

⏸️ **Checkpoint 3:** Покажи implementation summary

## Phase 4: REVIEW (Brutal Honesty)

```
Read skill: .claude/skills/brutal-honesty-review/SKILL.md
```

Swarm review:
```
Task A: code-quality    → clean code, patterns, naming
Task B: architecture    → consistency с Architecture.md
Task C: security        → vulnerabilities, input validation
Task D: performance     → bottlenecks, complexity
Task E: testing         → coverage, edge cases
```

Fix all CRITICAL и MAJOR issues.
Сохранить: `docs/features/<name>/review-report.md`
Коммит: `docs(feature): review complete for <name>`

## Completion

```
✅ Feature: <name>

📁 docs/features/<name>/
├── sparc/validation-report.md  (score: XX/100)
└── review-report.md            (X issues → X fixed)

💡 Если столкнулся с нетривиальной проблемой → /myinsights
```
