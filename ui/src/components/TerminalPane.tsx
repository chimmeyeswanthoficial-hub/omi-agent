import { terminalLines } from "../lib/derive";
import { useOmi } from "../state/store";

export default function TerminalPane() {
  const events = useOmi((s) => s.events);
  const lines = terminalLines(events, null);
  return (
    <div className="panel flex-1 min-h-0 flex flex-col">
      <div className="px-2.5 py-1.5 border-b border-edge text-mut text-[11px] uppercase tracking-wider flex items-center gap-2">
        sandbox terminal <span className="text-[10px] normal-case">last bash outputs</span>
      </div>
      <div className="flex-1 min-h-0 overflow-y-auto p-2 text-[11px] leading-relaxed whitespace-pre-wrap text-ink/85">
        {lines.length ? lines.join("\n") : <span className="text-mut">$ waiting for the agent to run something…</span>}
      </div>
    </div>
  );
}
