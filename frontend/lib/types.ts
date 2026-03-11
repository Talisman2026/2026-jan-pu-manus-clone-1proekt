export type TaskStatus =
  | 'created'
  | 'estimating'
  | 'estimated'
  | 'running'
  | 'paused'
  | 'completed'
  | 'failed'
  | 'budget_warning'

export type ToolType =
  | 'web_search'
  | 'scrape_url'
  | 'run_python'
  | 'write_file'
  | 'finish'

export type StepStatus = 'running' | 'done' | 'error'

export interface TaskStep {
  id: string
  task_id: string
  tool: ToolType
  description: string
  status: StepStatus
  cost_usd: number
  created_at: string
}

export interface Estimation {
  steps: number
  duration_min: number
  duration_max: number
  cost_estimate_usd: number
}

export interface Task {
  id: string
  user_id: string
  description: string
  status: TaskStatus
  budget_cap: number | null
  cost_actual: number
  estimation: Estimation | null
  result_summary: string | null
  /** True when a result file is ready to download. */
  has_result: boolean
  created_at: string
  started_at: string | null
  completed_at: string | null
  steps: TaskStep[]
}

export interface TaskListItem {
  id: string
  description: string
  status: TaskStatus
  budget_cap: number | null
  cost_actual: number
  has_result: boolean
  created_at: string
  started_at: string | null
  completed_at: string | null
}

export interface AuthResponse {
  access_token: string
  token_type: string
}

export interface User {
  id: string
  email: string
  created_at: string
}

export interface ApiError {
  detail: string
}

export interface CreateTaskResponse {
  id: string
  description: string
  status: TaskStatus
  estimation: Estimation | null
}

export interface RunTaskRequest {
  budget_cap: number
  openai_key: string
}
