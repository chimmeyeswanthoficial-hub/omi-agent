import type { StepGroup } from "../lib/derive";
import { api } from "../lib/api";
import { useOmi } from "../state/store";
import CostMeter from "./CostMeter";
import DiffText from "./DiffText";
import ModelBadge from "./ModelBadge";

export default function StepCard({ g }: { g: StepGroup }) {
  const sel = useOmi((s) => s.sel);
  const tool = g.call?.payload.tool as string | undefined;
  const args = (g.call?.payload.args ?? {}) as Record<string, unknown>;
  const ok = g.result ? Boolean(g.result.payload.ok) : undefined;
  const text = g.result ? String(g.result.payload.text ?? "") : "";

  return (
    <div className="rounded-md border border-edge bg-panel px-2.5 py-2">
      <div className="flex items-center gap-2 text-[11px]">
        <span className="text-mut font-bold">#{g.step}</span>
        {tool && (
          <span className={`px-1.5 rounded ${ok ? "bg-acc/15 text-acc" : "bg-err/15 text-err"}`}>
            {tool}
            {ok === false ? " ✗" : ""}
          </span>
        )}
        {g.cost && <ModelBadge group={String(g.cost.payload.group)} provider={String(g.cost.payload.provider)} />}
        {g.cost && <CostMeter tokensIn={Number(g.cost.payload.tokens_in)} tokensOut={Number(g.cost.payload.tokens_out)} usd={Number(g.cost.payload.usd)} />}
        <span className="flex-1" />
        {g.checkpoint &&
          (() => {
            const commit = String(g.checkpoint!.payload.commit);
            return (
              <button
                className="btn text-[10px] leading-none"
                title={`rewind workspace to ${commit}`}
                onClick={() => sel && void api.rewind(sel, commit).then(() => useOmi.getState().openTask(sel))}
              >
                ↺ {commit}
              </button>
            );
          })()}
      </div>
      {g.reasoning && <p className="text-[12px] text-ink/90 mt-1 whitespace-pre-wrap">{g.reasoning}</p>}
      {tool && (
        <pre className="text-[10px] text-mut mt-1 whitespace-pre-wrap bg-panel2 rounded p-1.5 max-h-24 overflow-y-auto">
          {JSON.stringify(args, null, 1).slice(0, 500)}
        </pre>
      )}
      {text && (
        <pre className="text-[11px] mt-1 whitespace-pre-wrap max-h-72 overflow-y-auto rounded p-1.5 bg-[#0d1017]">
          <DiffText text={text} />
        </pre>
      )}
      {g.verify && (
        <div className={`text-[11px] mt-1 px-1.5 py-0.5 rounded ${g.verify.payload.ok ? "text-acc bg-acc/10" : "text-err bg-err/10"}`}>
          {g.verify.payload.ok ? "🧪 verify passed" : "🧪 verify FAILED"}
        </div>
      )}
    </div>
  );
}
