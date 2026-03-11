# Pseudocode: AgentFlow MVP

**Версия:** 2.0 MVP | **Дата:** 2026-03-11

---

## 1. Core Data Models

```typescript
enum TaskStatus {
  CREATED | ESTIMATING | ESTIMATED | RUNNING | PAUSED | COMPLETED | FAILED
}

interface Task {
  id: string
  user_id: string
  description: string
  status: TaskStatus
  budget_cap: number
  cost_actual: number
  estimation: { steps: number, duration_min: number, duration_max: number } | null
  result_summary: string | null
  result_file_path: string | null
  sandbox_id: string | null
  steps: TaskStep[]
}

interface TaskStep {
  id: string
  task_id: string
  tool: "web_search" | "scrape_url" | "run_python" | "write_file" | "finish"
  description: string
  status: "running" | "done" | "error"
  cost_usd: number
  created_at: Date
}
```

---

## 2. Pre-Run Estimation

```python
async def estimate_task(description: str) -> Estimation:
    # Используем наш GPT-4o-mini ключ — дёшево и достаточно
    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{
            "role": "user",
            "content": f"""Estimate this task execution plan:
            Task: {description}
            
            Return JSON only:
            {{
              "steps": <number of tool calls expected>,
              "duration_min": <optimistic seconds>,
              "duration_max": <conservative seconds>,
              "cost_estimate_usd": <rough upper bound>
            }}"""
        }]
    )
    return parse_json(response)
```

---

## 3. Task Execution (backend/services/e2b_manager.py)

```python
async def run_task(task: Task, user_openai_key: str):
    # 1. Создаём E2B sandbox
    sandbox = await e2b.Sandbox.create(
        template="base",
        timeout=1800,
        envs={
            "OPENAI_API_KEY": user_openai_key,   # пользовательский, только RAM
            "FIRECRAWL_API_KEY": FIRECRAWL_API_KEY
        }
    )
    user_openai_key = None  # сразу затираем

    # 2. Загружаем agent.py в sandbox
    await sandbox.files.write("/home/user/agent.py", open("sandbox/agent.py").read())
    await sandbox.files.write("/home/user/requirements.txt", open("sandbox/requirements.txt").read())
    await sandbox.commands.run("pip install -r /home/user/requirements.txt -q")

    # Сохраняем sandbox_id в БД
    await db.tasks.update(task.id, {
        "status": "running",
        "sandbox_id": sandbox.sandbox_id,
        "started_at": now()
    })

    # 3. Запускаем агента, читаем JSON events из stdout
    async for line in sandbox.commands.run_stream(
        f"python /home/user/agent.py --task '{escape(task.description)}' "
        f"--budget {task.budget_cap} --task-id {task.id}"
    ):
        event = json.loads(line)
        await process_event(task.id, event)

    # 4. Забираем файл результата
    files = await sandbox.files.list("/home/user/results/")
    if files:
        content = await sandbox.files.read(files[0].path)
        save_result_file(task.id, files[0].name, content)

    await sandbox.kill()


async def process_event(task_id: str, event: dict):
    if event["type"] == "step":
        await db.task_steps.insert({
            "task_id": task_id,
            "tool": event["tool"],
            "description": event["description"],
            "status": "done",
            "cost_usd": event["cost_usd"]
        })
        await db.tasks.increment_cost(task_id, event["cost_usd"])

    elif event["type"] == "budget_warning":
        # Пишем в БД, фронтенд увидит при следующем polling
        await db.tasks.update(task_id, {"status": "budget_warning"})

    elif event["type"] == "completed":
        await db.tasks.update(task_id, {
            "status": "completed",
            "result_summary": event["summary"],
            "completed_at": now()
        })

    elif event["type"] == "error":
        await db.tasks.update(task_id, {"status": "failed"})
```

---

## 4. Agent Loop (backend/sandbox/agent.py)

```python
# Этот файл загружается в E2B sandbox и выполняется там
import os, json, subprocess, argparse
from openai import OpenAI
from firecrawl import FirecrawlApp

def main(task_description: str, budget_cap: float, task_id: str):
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    firecrawl = FirecrawlApp(api_key=os.environ["FIRECRAWL_API_KEY"])

    tools = [
        {
            "type": "function",
            "function": {
                "name": "web_search",
                "description": "Search the web and get results with content",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "max_results": {"type": "integer", "default": 5}
                    },
                    "required": ["query"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "scrape_url",
                "description": "Extract full content from a specific URL",
                "parameters": {
                    "type": "object",
                    "properties": {"url": {"type": "string"}},
                    "required": ["url"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "run_python",
                "description": "Execute Python code for data processing",
                "parameters": {
                    "type": "object",
                    "properties": {"code": {"type": "string"}},
                    "required": ["code"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "write_file",
                "description": "Save final result to file",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "filename": {"type": "string"},  # e.g. "report.md"
                        "content": {"type": "string"}
                    },
                    "required": ["filename", "content"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "finish",
                "description": "Task is complete, provide summary",
                "parameters": {
                    "type": "object",
                    "properties": {"summary": {"type": "string"}},
                    "required": ["summary"]
                }
            }
        }
    ]

    messages = [
        {
            "role": "system",
            "content": f"""You are an autonomous agent. Complete the given task fully.
            Budget cap: ${budget_cap}. Stop and save partial results if approaching limit.
            Always save your final result using write_file tool before calling finish.
            Save files to /home/user/results/ directory."""
        },
        {"role": "user", "content": task_description}
    ]

    total_cost = 0.0
    MAX_STEPS = 30

    for step_num in range(MAX_STEPS):
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            tools=tools
        )

        step_cost = calculate_cost(response.usage)
        total_cost += step_cost

        tool_call = response.choices[0].message.tool_calls[0] \
                    if response.choices[0].message.tool_calls else None

        if not tool_call:
            # Нет tool call — агент завершил без finish
            emit_event("completed", summary=response.choices[0].message.content,
                      cost_usd=step_cost)
            break

        tool_name = tool_call.function.name
        tool_args = json.loads(tool_call.function.arguments)

        emit_event("step", tool=tool_name,
                  description=get_description(tool_name, tool_args),
                  cost_usd=step_cost)

        # Budget checks
        if total_cost >= budget_cap * 0.8:
            emit_event("budget_warning", percent_used=80)
        if total_cost >= budget_cap:
            emit_event("budget_exceeded")
            break

        if tool_name == "finish":
            emit_event("completed", summary=tool_args["summary"], cost_usd=step_cost)
            break

        # Выполняем инструмент
        result = execute_tool(tool_name, tool_args, firecrawl)

        messages.append(response.choices[0].message)
        messages.append({
            "role": "tool",
            "content": str(result),
            "tool_call_id": tool_call.id
        })


def execute_tool(name: str, args: dict, firecrawl) -> str:
    if name == "web_search":
        result = firecrawl.search(args["query"], limit=args.get("max_results", 5))
        return json.dumps(result, ensure_ascii=False)

    elif name == "scrape_url":
        result = firecrawl.scrape_url(args["url"], params={"formats": ["markdown"]})
        return result.get("markdown", "No content")

    elif name == "run_python":
        out = subprocess.run(
            ["python", "-c", args["code"]],
            capture_output=True, text=True, timeout=30
        )
        return out.stdout + out.stderr

    elif name == "write_file":
        import os
        os.makedirs("/home/user/results", exist_ok=True)
        path = f"/home/user/results/{args['filename']}"
        with open(path, "w") as f:
            f.write(args["content"])
        return f"Saved to {path}"


def emit_event(type: str, **kwargs):
    # Печатаем JSON в stdout — backend читает построчно
    print(json.dumps({"type": type, **kwargs}), flush=True)


def calculate_cost(usage) -> float:
    # GPT-4o pricing (приблизительно)
    input_cost = usage.prompt_tokens * 0.0025 / 1000
    output_cost = usage.completion_tokens * 0.01 / 1000
    return input_cost + output_cost


def get_description(tool_name: str, args: dict) -> str:
    descriptions = {
        "web_search": f"Searching: {args.get('query', '')}",
        "scrape_url": f"Reading: {args.get('url', '')}",
        "run_python": "Running Python code...",
        "write_file": f"Saving {args.get('filename', 'file')}",
        "finish": "Finishing task"
    }
    return descriptions.get(tool_name, tool_name)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", required=True)
    parser.add_argument("--budget", type=float, required=True)
    parser.add_argument("--task-id", required=True)
    args = parser.parse_args()
    main(args.task, args.budget, args.task_id)
```

---

## 5. Frontend Polling (вместо WebSocket)

```typescript
// Polling каждые 2 секунды пока задача активна
async function pollTaskStatus(taskId: string) {
  const interval = setInterval(async () => {
    const task = await api.get(`/tasks/${taskId}`)
    
    setTaskState(task)
    
    if (["completed", "failed", "paused"].includes(task.status)) {
      clearInterval(interval)
    }
  }, 2000)
  
  return () => clearInterval(interval)
}
```

---

## 6. API Endpoints

```
POST /auth/register          { email, password }
POST /auth/login             { email, password } → { access_token }
POST /auth/logout

GET  /tasks                  → список задач пользователя
POST /tasks                  { description } → { task_id, estimation }
POST /tasks/{id}/run         { budget_cap, openai_key } → { status: "running" }
GET  /tasks/{id}             → task + steps (для polling)
GET  /tasks/{id}/result      → скачать файл результата
POST /tasks/{id}/cancel      → остановить задачу
```
