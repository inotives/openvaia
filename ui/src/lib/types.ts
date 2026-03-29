export interface Agent {
  name: string;
  status: string;
  last_seen: string | null;
}

export interface AgentHealth {
  name: string;
  status: string;
  last_seen: string | null;
  healthy: boolean | null;
  details: string | null;
  checked_at: string | null;
}

export interface TaskSummaryRow {
  agent: string;
  backlog: number;
  todo: number;
  in_progress: number;
  review: number;
  done: number;
  blocked: number;
}

export interface CronJob {
  id: number;
  agent_name: string | null;
  name: string;
  prompt: string;
  interval_minutes: number;
  enabled: boolean;
  last_run_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface Skill {
  id: number;
  name: string;
  description: string;
  content: string;
  tags: string[];
  global: boolean;
  enabled: boolean;
  status: string;
  created_by: string | null;
  created_at: string;
  updated_at: string;
  // joined fields
  equipped?: boolean;
  priority?: number;
  agent_count?: number;
}

export interface Task {
  key: string;
  title: string;
  description: string | null;
  status: string;
  priority: string;
  assigned_to: string | null;
  created_by: string;
  result: string | null;
  tags: string[];
  parent_task_id: number | null;
  recurrence_minutes: number | null;
  recurrence_count: number;
  last_completed_at: string | null;
  created_at: string;
  updated_at: string;
}
