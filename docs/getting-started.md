# Getting started

## TL;DR

```bash
git clone https://github.com/<you>/omiagent.git && cd omiagent
cp .env.example .env        # add at least ONE provider key
uv venv && uv pip install -e .     # or: python3 -m venv .venv && .venv/bin/pip install -e .
omiagent serve              # or: uv run omiagent serve
# → open http://127.0.0.1:8000
```

No keys yet? See the repo work offline first:

```bash
omiagent demo --fake
```

This runs the real agent loop (real tools, real git snapshots) against
`examples/demo_repo` with a scripted model — it fixes the planted `add()` bug
and shows you the whole event stream in your terminal.

## Build the UI (once)

The Python server serves the prebuilt UI. To rebuild it from source:

```bash
cd ui && npm install && npm run build     # outputs ui/dist, picked up automatically
```

During UI development use two terminals: `omiagent serve` (API, :8000) and
`npm run dev` (:5173, proxied) — edit components with hot reload.

## Docker sandbox (recommended, optional)

```bash
docker build -t omiagent/runtime:local sandbox/
OMI_SANDBOX=docker omiagent serve
```

Without Docker (or with `OMI_SANDBOX=auto` and no daemon) everything still
runs in the jailed local runtime — see [security.md](security.md).

## The three ways to drive it

1. **Web workspace** — http://127.0.0.1:8000 : new task, approve plan, watch
   steps/diffs/verify, rewind to any checkpoint.
2. **Task API** — `POST /api/tasks {"prompt", "repo_path", "mode"}` then poll
   `/api/tasks/{id}` or stream `/api/ws/tasks/{id}`.
3. **Model gateway** — point any OpenAI-compatible client at
   `http://127.0.0.1:8000/v1` with `model: "max"`; omirouter classifies the
   request and calls your best provider for it:

```bash
curl -s http://127.0.0.1:8000/v1/chat/completions \
  -H "content-type: application/json" \
  -d '{"model":"max","messages":[{"role":"user","content":"write a haiku about sandboxes"}]}'
```

## Where things live on disk

| Path | What |
|---|---|
| `~/.omi/tasks/<id>/events.jsonl` | the full event log (replayable) |
| `~/.omi/usage.db` | SQLite: tokens/USD/model per call |
| `~/omi-workspaces/<id>/repo` | the git-snapshotted workspace copy |
