# ⚡ OmiAgent

**Your own arena.ai/agent — open, self-hosted, and smarter about models.**

OmiAgent is a self-hosted autonomous coding agent with a real workspace UI.
You give it a task; it plans, edits your code, runs bash in a sandbox, watches
its own errors, fixes itself, checkpoints every step to git, and shows you
exactly which model did what and what it cost.

![license](https://img.shields.io/badge/license-MIT-green)
![python](https://img.shields.io/badge/python-3.11%2B-blue)
![node](https://img.shields.io/badge/node-20%2B-brightgreen)
![build](https://img.shields.io/badge/tests-pytest-lightgrey)
> BYOK (bring your own keys): **Gemini · OpenRouter · DeepSeek · Groq** — add
> OpenAI/Anthropic by editing one config file. No model weights, no GPU required.

## Why not just use arena.ai/agent?

| | arena.ai/agent | OmiAgent |
|---|---|---|
| Source | proprietary | MIT, ~2 MB repo |
| Runs on | their cloud | **your** laptop/desktop (Win/macOS/Linux) |
| Models | their pick | yours — task-routed with fallback chains |
| Cost visibility | — | live ₹/$ meter + per-step model badge |
| Rollback | — | git checkpoint every step, rewind |
| Keys leave your machine | n/a | never — local server, direct provider calls |

## Features

- 🧠 **`max` smart routing** — the agent (and anything you point at `POST /v1`)
  uses one virtual model `max`; `omirouter` classifies each request
  (code-edit / shell-debug / plan-reason / long-context / vision) and picks the
  best provider from your key set, with 429 fallback chains + cooldowns.
- 🖥️ **4-pane workspace UI** — event stream (chat/plan/steps), unified diff
  review, sandbox terminal tail, app preview — dark, keyboard-first.
- 🔁 **Self-correction** — failed verify (tests/build) after an edit → auto
  re-plan with the error tail, capped steps + per-task USD budget.
- 📸 **Checkpoints** — every mutation is a git snapshot; rewind the workspace
  to any step from the UI.
- 🐳 **Sandbox or run anywhere** — Docker runtime when present, local jail
  fallback for machines without Docker (path-jailed, denylist, timeouts).
-  **Audit** — SQLite usage ledger: tokens, $, model, group per call.

## 60-second quickstart

```bash
git clone https://github.com/<you>/omiagent && cd omiagent
cp .env.example .env            # paste 1+ provider key
uv run omiagent serve           # or: pip install -e . && omiagent serve
# open http://127.0.0.1:8000
```

Full requirements (per-OS, one-shot command lines, budgets) →
**[REQUIREMENT.md](REQUIREMENT.md)**.

## Architecture

```
 Browser UI (React+Vite+Tailwind)  :8000  (served by the server itself)
        ⇅ REST + WebSocket events
 ┌────────────────────────────────────────────────────────┐
 │ omiagent server (FastAPI)                               │
 │  ├─ AgentLoop   plan → reason → tool → verify → fix     │
 │  ├─ Tools       bash · read · write · edit · search ·   │
 │  │              apply_patch · finish                    │
 │  ├─ omirouter   "max" classifier + fallback chains      │
 │  ├─ Runtime     Docker sandbox  |  local jail (auto)    │
 │  └─ Store       jsonl events · git snapshots · usage.db │
 └───────────────┬───────────────────────┬────────────────┘
        HTTPS (per-request)       docker exec/run
                ▼                         ▼
   Gemini · OpenRouter · DeepSeek ·   sandbox image
   (Groq · OpenAI · Anthropic…)      /workspace = your repo copy
```

Docs: [getting started](docs/getting-started.md) ·
[architecture](docs/architecture.md) ·
[configuration](docs/configuration.md) ·
[routing & providers](docs/routing-and-providers.md) ·
[security](docs/security.md) · [roadmap](docs/roadmap.md)

## Try it without any keys (offline demo)

```bash
uv run omiagent demo --fake     # scripted model, real tools, real git snapshots
```

## Repo at a glance

Single repo, two stacks: `src/omiagent/` (Python server + agent + gateway) and
`ui/` (React). One `Dockerfile`, one `compose.yaml`. Repo size: ~2 MB of text.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). `make check` runs lint + tests + UI
build. CI enforces it.

## Disclaimer

Autonomous agents can run destructive commands inside their sandbox and cost
real money via your keys. Read [docs/security.md](docs/security.md). Not
affiliated with Arena/LMArena.

## License

MIT — see [LICENSE](LICENSE).
