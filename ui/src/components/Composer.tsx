import { useState } from "react";
import { useOmi } from "../state/store";

export default function Composer() {
  const [prompt, setPrompt] = useState("");
  const [repo, setRepo] = useState("");
  const [mode, setMode] = useState<"plan" | "auto">("plan");
  const { submit, sel, detail } = useOmi((s) => ({ submit: s.submit, sel: s.sel, detail: s.detail }));
  const live = Boolean(sel && detail?.live);

  const send = () => {
    if (!prompt.trim() || live) return;
    void submit(prompt, repo, mode);
    setPrompt("");
  };

  return (
    <div className="panel p-2 flex flex-col gap-1.5">
      <textarea
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) send();
        }}
        rows={2}
        placeholder={live ? "agent is working… (queue next task after finish)" : "what should the agent do? e.g. “fix the failing tests and tidy the README”"}
        className="w-full bg-transparent outline-none resize-y text-[13px] placeholder:text-mut/60 disabled:opacity-50"
        disabled={live}
      />
      <div className="flex items-center gap-2">
        <input
          value={repo}
          onChange={(e) => setRepo(e.target.value)}
          placeholder="repo path on server (optional) — e.g. /home/you/projects/app"
          className="flex-1 bg-transparent border border-edge rounded-md px-2 py-1 text-[11px] outline-none focus:border-acc/60 placeholder:text-mut/50"
        />
        <select
          value={mode}
          onChange={(e) => setMode(e.target.value as "plan" | "auto")}
          className="bg-panel2 border border-edge rounded-md px-1.5 py-1 text-[11px] outline-none"
        >
          <option value="plan">plan first</option>
          <option value="auto">auto</option>
        </select>
        <button onClick={send} disabled={live || !prompt.trim()} className="btn btn-acc disabled:opacity-40">
          run ⏎<span className="kbd ml-1">⌃⏎</span>
        </button>
      </div>
    </div>
  );
}
