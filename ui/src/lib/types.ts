export interface Ev {
  kind: string;
  payload: Record<string, unknown>;
  ts: number;
}

export interface TaskMeta {
  id: string;
  prompt: string;
  mode: "plan" | "auto";
  runtime: string;
  status: string;
  created: number;
  finished?: number;
  summary?: string;
  repo?: string | null;
}

export interface TaskDetail extends TaskMeta {
  events: Ev[];
  live: boolean;
  usage?: { tokens_in: number; tokens_out: number; usd: number; calls: number };
}

export interface FileEntry {
  path: string;
  size: number;
}

export interface Cfg {
  version: string;
  sandbox: string;
  task_budget_usd: number;
  max_steps: number;
  providers_available: string[];
  groups: Record<string, string[]>;
}
