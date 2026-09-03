import type { Ev } from "./types";

/** Live event stream for a task, auto-reconnecting while open. */
export function connectTaskStream(taskId: string, onEv: (ev: Ev) => void, onDone?: () => void) {
  let ws: WebSocket | null = null;
  let closed = false;
  let retry: ReturnType<typeof setTimeout> | null = null;

  const open = () => {
    if (closed) return;
    const proto = location.protocol === "https:" ? "wss" : "ws";
    ws = new WebSocket(`${proto}://${location.host}/api/ws/tasks/${taskId}`);
    ws.onmessage = (m) => {
      try {
        const ev = JSON.parse(m.data) as Ev;
        if (ev.kind === "task_finished") onDone?.();
        onEv(ev);
      } catch {
        /* ignore malformed frame */
      }
    };
    ws.onclose = () => {
      if (!closed) retry = setTimeout(open, 1500);
    };
  };
  open();

  return {
    send: (msg: Record<string, unknown>) => {
      if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(msg));
    },
    close: () => {
      closed = true;
      if (retry) clearTimeout(retry);
      ws?.close();
    },
  };
}
