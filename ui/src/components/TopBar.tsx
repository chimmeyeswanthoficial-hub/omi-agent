import { useOmi } from "../state/store";

export default function TopBar() {
  const cfg = useOmi((s) => s.cfg);
  return (
    <header className="flex items-center gap-3 px-3 py-2 border-b border-edge bg-panel">
      <span className="text-acc font-bold tracking-wide">⚡ omiagent</span>
      <span className="text-mut text-[11px]">v{cfg?.version ?? "…"}</span>
      <span className="flex-1" />
      <div className="flex items-center gap-1.5">
        {(cfg?.providers_available ?? []).map((p) => (
          <span key={p} className="px-1.5 py-0.5 rounded border border-edge text-[10px] text-mut">
            {p}
          </span>
        ))}
        {!cfg?.providers_available.length && (
          <span className="px-1.5 py-0.5 rounded border border-err/50 text-[10px] text-err">no keys — add .env</span>
        )}
      </div>
      <a href="/docs" target="_blank" rel="noreferrer" className="btn text-[11px] no-underline">
        API
      </a>
    </header>
  );
}
