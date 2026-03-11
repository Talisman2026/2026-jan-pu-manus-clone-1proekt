# Coding Style Rules

## TypeScript (apps/api/, apps/web/, packages/)

```typescript
// ✅ Явные типы для всего public API
export async function createTask(data: CreateTaskDTO): Promise<Task>

// ✅ Zod для runtime validation
const CreateTaskSchema = z.object({
  description: z.string().min(1).max(5000),
  budget_cap: z.number().min(0.10).max(100),
})

// ❌ Нет any без justification
const data: any = ...  // ЗАПРЕЩЕНО

// ✅ Error handling явный
try {
  const result = await db.tasks.insert(task)
  return result
} catch (error) {
  logger.error('Failed to create task', { error, userId })
  throw new AppError('TASK_CREATE_FAILED', 500)
}

// ✅ Async/await везде (не callbacks)
// ✅ ulid() для всех IDs (не UUID, не auto-increment)
```

## Python (apps/agent/)

```python
# ✅ Type hints везде
async def estimate_task(description: str) -> Estimation:

# ✅ Конкретные исключения (не bare except)
try:
    result = await llm.complete(prompt)
except anthropic.RateLimitError:
    await asyncio.sleep(backoff)
    result = await llm.complete(prompt)  # retry

# ✅ dataclasses или Pydantic для data models
@dataclass
class AgentStep:
    tool: ToolType
    input: dict
    output: str | None = None

# ✅ Logging без PII
logger.info("Task step completed", extra={"task_id": task_id, "tool": tool, "cost": cost})
# ❌ logger.info(f"Task: {task.description}")  # description = PII
```

## React/Next.js (apps/web/)

```typescript
// ✅ Server Components по умолчанию
// ✅ 'use client' только когда нужен state/events
// ✅ Tailwind utility classes (не custom CSS)
// ✅ shadcn/ui компоненты
// ✅ Оптимистичный UI с SWR

// ❌ Нет localStorage (не нужен, state в React)
// ❌ Нет прямых fetch без абстракции (используй api client)
```

## Database (packages/db/)

```typescript
// ✅ Drizzle ORM для всех запросов
// ✅ Явные транзакции для multi-step операций
// ✅ Индексы на все FK и частые query patterns
// ❌ Raw SQL только для сложных аналитических запросов
// ❌ N+1 запросы (используй joins или batch)
```
