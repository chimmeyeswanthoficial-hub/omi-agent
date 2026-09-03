export default function EmptyState() {
  return (
    <div className="panel flex-1 grid place-items-center">
      <div className="text-center max-w-md px-6 py-10">
        <div className="text-3xl mb-3">⚡</div>
        <h2 className="text-[15px] font-bold mb-1">omiagent workspace</h2>
        <p className="text-mut text-[12px] leading-relaxed">
          Type a task below — optionally point it at a repo path on this machine. The agent plans, edits, runs
          commands in the sandbox, verifies, and checkpoints every step to git.
        </p>
        <p className="text-mut text-[11px] mt-4">
          no keys yet? run{" "}
          <code className="bg-panel2 px-1.5 py-0.5 rounded text-acc">omiagent demo --fake</code> in a terminal.
        </p>
      </div>
    </div>
  );
}
