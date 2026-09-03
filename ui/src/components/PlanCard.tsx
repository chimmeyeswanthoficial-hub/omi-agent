import { useOmi } from "../state/store";

export default function PlanCard({ steps, approved, live }: { steps: string[]; approved: boolean; live: boolean }) {
  const approvePlan = useOmi((s) => s.approvePlan);
  const pending = !approved && live;
  return (
    <div className={`rounded-md border px-3 py-2 ${pending ? "border-warn/60 bg-warn/5" : "border-edge bg-panel"}`}>
      <div className="flex items-center gap-2">
        <span className="text-[11px] uppercase tracking-wider text-warn">🗺 plan</span>
        <span className="flex-1" />
        {pending ? (
          <button onClick={() => void approvePlan()} className="btn btn-acc text-[11px]">
            ▶ approve & run
          </button>
        ) : (
          <span className="text-[10px] text-mut">{approved ? "approved — executing" : "running"}</span>
        )}
      </div>
      <ol className="mt-1.5 ml-4 list-decimal text-[12px] text-ink/90 space-y-0.5">
        {(steps ?? []).map((s, i) => (
          <li key={i}>{s}</li>
        ))}
      </ol>
    </div>
  );
}
