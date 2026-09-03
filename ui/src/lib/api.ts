import type { Cfg, FileEntry, TaskDetail, TaskMeta } from "./types";

async function j<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail ?? body);
    } catch {
      /* keep statusText */
    }
    throw new Error(detail);
  }
  return (await res.json()) as T;
}

export const api = {
  config: () => fetch("/api/config").then((r) => j<Cfg>(r)),
  health: () => fetch("/healthz").then((r) => j<Record<string, unknown>>(r)),
  tasks: () => fetch("/api/tasks").then((r) => j<TaskMeta[]>(r)),
  task: (id: string) => fetch(`/api/tasks/${id}`).then((r) => j<TaskDetail>(r)),
  files: (id: string) => fetch(`/api/tasks/${id}/files`).then((r) => j<FileEntry[]>(r)),
  create: (prompt: string, repo_path: string | null, mode: "plan" | "auto") =>
    fetch("/api/tasks", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ prompt, repo_path, mode }),
    }).then((r) => j<{ task_id: string }>(r)),
  approve: (id: string) => fetch(`/api/tasks/${id}/approve-plan`, { method: "POST" }).then((r) => j(r)),
  cancel: (id: string) => fetch(`/api/tasks/${id}/cancel`, { method: "POST" }).then((r) => j(r)),
  rewind: (id: string, ref: string) =>
    fetch(`/api/tasks/${id}/rewind`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ ref }),
    }).then((r) => j(r)),
};
