import { bytes, relTime } from "../lib/format";
import { useOmi } from "../state/store";

const STATUS: Record<string, string> = {
  running: "bg-acc animate-pulse",
  finished: "bg-acc/60",
  error: "bg-err",
  cancelled: "bg-mut",
  budget: "bg-warn",
  "max-steps": "bg-warn",
  queued: "bg-mut",
};

export default function Sidebar() {
  const { tasks, sel, openTask, closeTask, files } = useOmi((s) => ({
    tasks: s.tasks,
    sel: s.sel,
    openTask: s.openTask,
    closeTask: s.closeTask,
    files: s.files,
  }));

  return (
    <aside className="flex flex-col min-h-0 gap-2">
      <div className="panel flex-1 min-h-0 flex flex-col">
        <div className="flex items-center justify-between px-2.5 py-1.5 border-b border-edge">
          <span className="text-mut text-[11px] uppercase tracking-wider">tasks</span>
          {sel && (
            <button className="btn text-[10px] leading-none" onClick={() => closeTask()}>
              new ✕
            </button>
          )}
        </div>
        <ul className="overflow-y-auto flex-1 p-1">
          {tasks.length === 0 && <li className="text-mut text-[11px] px-2 py-3">no tasks yet — describe one →</li>}
          {tasks.map((t) => (
            <li key={t.id}>
              <button
                onClick={() => void openTask(t.id)}
                className={`w-full text-left px-2 py-1.5 rounded-md hover:bg-panel2 cursor-pointer ${sel === t.id ? "bg-panel2 outline outline-1 outline-edge" : ""}`}
              >
                <div className="flex items-center gap-1.5">
                  <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${STATUS[t.status] ?? "bg-mut"}`} />
                  <span className="truncate text-[12px]">{t.prompt}</span>
                </div>
                <div className="text-[10px] text-mut pl-3">
                  {t.mode} · {t.runtime} · {relTime(t.created)}
                </div>
              </button>
            </li>
          ))}
        </ul>
      </div>
      <div className="panel h-2/5 flex flex-col min-h-0">
        <div className="px-2.5 py-1.5 border-b border-edge text-mut text-[11px] uppercase tracking-wider">
          workspace files {sel ? `(${files.length})` : ""}
        </div>
        <ul className="overflow-y-auto flex-1 p-1">
          {files.map((f) => (
            <li key={f.path} className="px-2 py-0.5 text-[11px] flex justify-between gap-2 hover:bg-panel2">
              <span className="truncate">{f.path}</span>
              <span className="text-mut shrink-0">{bytes(f.size)}</span>
            </li>
          ))}
          {sel && files.length === 0 && <li className="text-mut text-[11px] px-2 py-2">empty workspace</li>}
        </ul>
      </div>
    </aside>
  );
}
