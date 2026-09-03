import { useState } from "react";

export default function PreviewPane() {
  const [url, setUrl] = useState("");
  const [shown, setShown] = useState("");
  return (
    <div className="panel flex-1 min-h-0 flex flex-col">
      <div className="px-2 py-1.5 border-b border-edge flex items-center gap-1.5">
        <span className="text-mut text-[11px] uppercase tracking-wider pl-0.5">app preview</span>
        <input
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && setShown(url.trim())}
          placeholder="http://localhost:3000 → Enter"
          className="flex-1 bg-transparent outline-none border border-edge rounded px-1.5 py-0.5 text-[11px] focus:border-acc/60 placeholder:text-mut/50"
        />
        <button className="btn text-[10px] leading-none" onClick={() => setShown(url.trim())}>
          go
        </button>
      </div>
      <div className="flex-1 min-h-0 bg-black/30">
        {shown ? (
          <iframe title="preview" src={shown} className="w-full h-full border-0 bg-white" sandbox="allow-scripts allow-same-origin allow-forms allow-popups" />
        ) : (
          <div className="h-full grid place-items-center text-mut text-[11px] px-6 text-center">
            point the agent at “run the dev server” then paste its URL here to watch the app live.
          </div>
        )}
      </div>
    </div>
  );
}
