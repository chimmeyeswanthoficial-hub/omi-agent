import { useEffect, useRef } from "react";
import { groupSteps } from "../lib/derive";
import { useOmi } from "../state/store";
import EmptyState from "./EmptyState";
import PlanCard from "./PlanCard";
import StepCard from "./StepCard";

export default function EventStream() {
  const events = useOmi((s) => s.events);
  const detail = useOmi((s) => s.detail);
  const error = useOmi((s) => s.error);
  const { loose, steps } = groupSteps(events);
  const scroller = useRef<HTMLDivElement>(null);
  useEffect(() => {
    scroller.current?.scrollTo({ top: scroller.current.scrollHeight, behavior: "smooth" });
  }, [events.length]);

  const planEv = loose.find((e) => e.kind === "plan_proposed");
  const approved = loose.some((e) => e.kind === "plan_approved");
  const started = loose.find((e) => e.kind === "task_started");
  const ended = loose.find((e) => e.kind === "task_finished");

  if (events.length === 0) return <EmptyState />;

  return (
    <div ref={scroller} className="panel flex-1 min-h-0 overflow-y-auto p-2 flex flex-col gap-2">
      {started && (
        <div className="text-[12px] px-2 py-1.5 rounded-md bg-panel2">
          <span className="text-acc">task › </span>
          {String(started.payload.prompt ?? "")}
          <span className="text-mut"> · {String(started.payload.runtime)} sandbox</span>
        </div>
      )}
      {planEv && <PlanCard steps={planEv.payload.steps as string[]} approved={approved} live={detail?.live ?? false} />}
      {steps.map((g) => (
        <StepCard key={g.step} g={g} />
      ))}
      {loose
        .filter((e) => e.kind === "error" || e.kind === "status")
        .map((e, i) => (
          <div key={i} className={`text-[11px] px-2 py-1 rounded ${e.kind === "error" ? "text-err bg-err/10" : "text-mut"}`}>
            {String(e.payload.message ?? "")}
          </div>
        ))}
      {ended && (
        <div className="text-[12px] px-2 py-2 rounded-md border border-acc/40 bg-acc/5">
          <span className="text-acc font-bold">■ {String(ended.payload.status)}</span>{" "}
          <span className="whitespace-pre-wrap">{String(ended.payload.summary ?? "")}</span>
          <div className="text-[10px] text-mut mt-1">
            {String(ended.payload.steps)} steps · ${Number(ended.payload.usd ?? 0).toFixed(4)}
          </div>
        </div>
      )}
      {error && <div className="text-err text-[11px] px-2">⚠ {error}</div>}
    </div>
  );
}
