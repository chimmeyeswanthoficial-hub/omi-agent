import { create } from "zustand";
import { api } from "../lib/api";
import { connectTaskStream } from "../lib/ws";
import type { Cfg, Ev, FileEntry, TaskDetail, TaskMeta } from "../lib/types";

interface OmiState {
  cfg: Cfg | null;
  tasks: TaskMeta[];
  sel: string | null;
  detail: TaskDetail | null;
  events: Ev[];
  files: FileEntry[];
  error: string | null;
  openTask: (id: string) => Promise<void>;
  closeTask: () => void;
  submit: (prompt: string, repo: string, mode: "plan" | "auto") => Promise<void>;
  approvePlan: () => Promise<void>;
  cancelTask: () => Promise<void>;
  refreshTasks: () => Promise<void>;
  _push: (ev: Ev) => void;
}

let stream: ReturnType<typeof connectTaskStream> | null = null;

export const useOmi = create<OmiState>((set, get) => ({
  cfg: null,
  tasks: [],
  sel: null,
  detail: null,
  events: [],
  files: [],
  error: null,

  async refreshTasks() {
    try {
      const tasks = await api.tasks();
      const cfg = get().cfg ?? (await api.config().catch(() => null));
      set({ tasks, cfg: cfg ?? get().cfg });
    } catch (e) {
      set({ error: String(e) });
    }
  },

  async openTask(id) {
    stream?.close();
    try {
      const detail = await api.task(id);
      const files = await api.files(id).catch(() => []);
      set({ sel: id, detail, events: detail.events, files, error: null });
      if (detail.live) {
        stream = connectTaskStream(
          id,
          (ev) => get()._push(ev),
          () => {
            void get().refreshTasks();
          },
        );
      }
    } catch (e) {
      set({ error: String(e) });
    }
  },

  closeTask() {
    stream?.close();
    stream = null;
    set({ sel: null, detail: null, events: [], files: [] });
  },

  _push(ev) {
    const st = get();
    const events = [...st.events, ev];
    const patch: Partial<OmiState> = { events };
    if (ev.kind === "task_finished") {
      void api.files(st.sel ?? "").then((files) => set({ files })).catch(() => undefined);
      void get().refreshTasks();
    }
    if (ev.kind === "step_started") {
      void api.files(st.sel ?? "").then((files) => set({ files })).catch(() => undefined);
    }
    set(patch);
  },

  async submit(prompt, repo, mode) {
    try {
      set({ error: null });
      const { task_id } = await api.create(prompt, repo.trim() || null, mode);
      await get().openTask(task_id);
      await get().refreshTasks();
    } catch (e) {
      set({ error: String(e) });
    }
  },

  async approvePlan() {
    const id = get().sel;
    if (!id) return;
    try {
      await api.approve(id);
    } catch (e) {
      set({ error: String(e) });
    }
  },

  async cancelTask() {
    const id = get().sel;
    if (!id) return;
    try {
      await api.cancel(id);
    } catch (e) {
      set({ error: String(e) });
    }
  },
}));
