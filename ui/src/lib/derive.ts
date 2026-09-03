import type { Ev } from "./types";

/** terminal pane = bash-ish tool results for the step */
export function terminalLines(events: Ev[], step: number | null): string[] {
  const out: string[] = [];
  for (const e of events) {
    if (e.kind !== "tool_result" || e.payload.tool !== "bash") continue;
    if (step !== null && e.payload.step !== step) continue;
    out.push(String(e.payload.text ?? ""));
  }
  return out.slice(-2);
}

/** lines colored as a unified diff inside result text */
export function isDiffLine(line: string): "add" | "del" | "hunk" | null {
  if (line.startsWith("@@")) return "hunk";
  if (line.startsWith("+") && !line.startsWith("+++")) return "add";
  if (line.startsWith("-") && !line.startsWith("---")) return "del";
  return null;
}

export interface StepGroup {
  step: number;
  reasoning: string;
  call?: Ev;
  result?: Ev;
  verify?: Ev;
  checkpoint?: Ev;
  cost?: Ev;
}

export function groupSteps(events: Ev[]): { loose: Ev[]; steps: StepGroup[] } {
  const byStep = new Map<number, StepGroup>();
  const loose: Ev[] = [];
  for (const e of events) {
    const step = typeof e.payload.step === "number" ? e.payload.step : null;
    if (step === null || ["task_started", "task_finished", "plan_proposed", "plan_approved", "error", "status"].includes(e.kind)) {
      loose.push(e);
      continue;
    }
    let g = byStep.get(step);
    if (!g) {
      g = { step, reasoning: "" };
      byStep.set(step, g);
    }
    if (e.kind === "reasoning") g.reasoning = String(e.payload.text ?? "");
    else if (e.kind === "tool_call") g.call = e;
    else if (e.kind === "tool_result") g.result = e;
    else if (e.kind === "verify") g.verify = e;
    else if (e.kind === "checkpoint") g.checkpoint = e;
    else if (e.kind === "cost") g.cost = e;
  }
  return { loose, steps: [...byStep.values()].sort((a, b) => a.step - b.step) };
}
