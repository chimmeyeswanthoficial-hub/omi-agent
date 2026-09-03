# Architecture

```
┌────────────────────────────── one laptop, one process ─────────────────────────────┐
│                                                                                     │
│  ui/ (React+Vite+Tailwind) → build → ui/dist → mounted by the server at /           │
│         │  REST /api/*  ·  WS /api/ws/tasks/{id}                                    │
│         ▼                                                                            │
│  server/app.py ── TaskManager (server/manager.py)                                   │
│       │            • create/cancel/approve/rewind per task                          │
│       │            • event fan-out: jsonl store + ws queues                         │
│       ▼                                                                             │
│  agent/loop.py ── AgentLoop                                                         │
│       │   plan → [reason → act → verify]×N → finish                                 │
│       │   prompts.py (JSON action protocol) · parser.py (tolerant)                  │
│       │   context.py (repo map, verify autodetect) · checkpoint.py (git)            │
│       ▼                                                                             │
│  tools/ — bash · read_file · write_file · edit_file · search · apply_patch · finish │
│       ▼                                                                             │
│  runtime/ — `docker` (per-task container) | `local` (path jail)                     │
│                                                                                     │
│  gateway/router.py — MaxRouter "max" model                                          │
│       • classify() heuristic → group                                                │
│       • configs/providers.yaml → ordered chain, cooldowns, retries                  │
│       • gateway/audit.py → usage.db (tokens/USD) → budget guard + UI cost meter     │
│  server/gateway_routes.py — /v1 OpenAI-compatible surface for outside clients       │
└─────────────────────────────────────────────────────────────────────────────────────┘
            │ litellm.acompletion per request        │ docker exec
            ▼                                         ▼
   Gemini · OpenRouter · DeepSeek · Groq …      sandbox container:
   (add any: one entry in providers.yaml)       /workspace = task repo copy
```

## Design rules (why it looks like this)

- **One process.** The server, agent loop, gateway, and static UI share a
  FastAPI app — a laptop tool, not a microservice estate. The gateway is a
  module (`gateway/`) *and* an HTTP surface (`/v1`) over the same router.
- **Events are the truth.** Every agent decision becomes an `Event`
  (`agent`-side factories in `omiagent/events.py`), appended to JSONL and
  fanned out to WebSocket subscribers from one place (`TaskManager`). The UI
  is a pure reducer over events; refresh mid-task and you're caught up.
- **The sandbox owns execution; the loop owns judgment.** Tools never touch
  the host filesystem directly — `Runtime` (docker or local jail) does reads,
  writes and shell. Swapping runtimes changes one factory call.
- **Git is the undo button.** Checkpoints (`agent/checkpoint.py`) snapshot
  after every mutation; rewind is `git reset --hard <ref>` — no custom VCS.
- **Providers are config, not code.** Model IDs live *only* in
  `configs/providers.yaml`. The agent and UI never name a model; they name a
  task group.

## Failure posture

- Malformed model output → degrades to a conversational answer (`parser.py`),
  never a crash.
- Provider 429/5xx → next in chain + cooldown; all dead → task ends `error`
  with the reason in the event stream.
- Tool exceptions → `ok:false` tool_result fed back to the model; the loop
  keeps control (`max_steps`, USD budget, per-step timeouts).
- Server crash mid-task → workspace + `events.jsonl` survive on disk;
  `~/.omi` is inspectable with plain `cat`/`git log`.
