import { money } from "../lib/format";
import { useOmi } from "../state/store";

export default function StatusBar() {
  const { events, detail, cfg, cancelTask } = useOmi((s) => ({ events: s.events, detail: s.detail, cfg: s.cfg, cancelTask: s.cancelTask }));
  let usd = 0;
  let tin = 0;
  let tout = 0;
  let steps = 0;
  for (const e of events) {
    if (e.kind === "cost") {
      usd += Number(e.payload.usd ?? 0);
      tin += Number(e.payload.tokens_in ?? 0);
      tout += Number(e.payload.tokens_out ?? 0);
    }
    if (e.kind === "step_started") steps = Math.max(steps, Number(e.payload.step ?? 0));
  }
  const live = Boolean(detail?.live);
  const budget = cfg?.task_budget_usd ?? 0;
  return (
    <footer className="flex items-center gap-3 px-3 py-1 border-t border-edge bg-panel text-[11px]">
      <span className={live ? "text-acc" : "text-mut"}>● {live ? `running step ${steps}/${cfg?.max_steps ?? 80}` : detail ? `idle (${detail.status})` : "idle"}</span>
      <span className="text-mut">🧾 {tin}↑ {tout}↓ tok</span>
      <span className={usd > budget ? "text-err" : "text-mut"}>
        {money(usd)} / {money(budget)} budget
      </span>
      <span className="flex-1" />
      {detail?.runtime && <span className="text-mut">sandbox: {detail.runtime}</span>}
      {live && (
        <button className="btn text-[10px] leading-none border-err/50 text-err" onClick={() => void cancelTask()}>
          ✕ cancel
        </button>
      )}
    </footer>
  );
}
