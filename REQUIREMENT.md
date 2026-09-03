# REQUIREMENT.md — what OmiAgent needs to run from the command line

This file answers one question only: **what must exist on the machine, and what
must you type, to start OmiAgent from a terminal?** Nothing else.

---

## 1. Hardware floor (any laptop or desktop)

| | Minimum | Comfortable |
|---|---|---|
| CPU | x86-64 or ARM64, 2 cores | 4 cores |
| RAM | 8 GB total system | 16 GB |
| Free disk | **2 GB** (repo 4 MB + deps) | 8 GB |
| GPU | none (100% API) | none |
| Network | HTTPS to model providers | — |

Measured footprint (2026-09): Python venv ≈ 316 MB (litellm+fastapi stack),
UI `node_modules` ≈ 121 MB (**dev-only**, not needed to run), built UI `dist`
≈ 0.3 MB, sandbox Docker image ≈ 350–400 MB (optional). Model weights: 0.

## 2. Software you must have installed

| Tool | Version | Needed for | Already on most dev machines |
|---|---|---|---|
| Python | ≥ 3.11 (3.12/3.13 best) | server + agent | — |
| [uv](https://docs.astral.sh/uv/) *(or pip ≥ 24)* | any | install/run | optional |
| Node.js + npm | ≥ 20 | **only if you edit the UI** (dev) | — |
| Docker | 24+ (Desktop on Win/macOS, Engine on Linux) | **optional** sandbox runtime; auto-falls back to local jail | — |
| git | ≥ 2.30 | checkpoints/snapshots | usually yes |

Windows note: run everything inside **WSL2 (Ubuntu)** or PowerShell; Docker
Desktop must have WSL integration enabled. macOS/Linux need no special setup.

## 3. What you must type (one path — copy/paste)

```bash
# 1) get the repo (≈4 MB with history)
git clone https://github.com/<you>/omiagent.git && cd omiagent

# 2) install + configure (~350 MB download, one time)
uv venv && uv pip install -e .          # or: python3 -m venv .venv && .venv/bin/pip install -e .
cp .env.example .env
nano .env                               # paste AT LEAST ONE key:
                                        #   GEMINI_API_KEY / OPENROUTER_API_KEY /
                                        #   DEEPSEEK_API_KEY / GROQ_API_KEY
# 3) start
uv run omiagent serve                   # or: .venv/bin/omiagent serve
```

Then open **http://127.0.0.1:8000** in any browser. That's the whole startup.

## 4. Command-line switches you may want

| Command | Effect |
|---|---|
| `omiagent serve --port 8080` | serve on another port |
| `omiagent demo --fake` | offline demo: scripted model, real tools/snapshots (no keys, no network) |
| `omiagent demo` | live demo on `examples/demo_repo` using your keys |
| `OMI_SANDBOX=docker omiagent serve` | force Docker sandbox (needs `docker build -t omiagent/runtime:local sandbox/`) |
| `OMI_SANDBOX=local` | force no-Docker mode |

## 5. Environment (all optional except ≥1 key)

See `.env.example`. Defaults already work: `OMI_HOST=127.0.0.1`,
`OMI_PORT=8000`, `OMI_SANDBOX=auto`, `OMI_MAX_STEPS=80`,
`OMI_TASK_BUDGET_USD=1.00`, `OMI_WORKSPACES_DIR=~/omi-workspaces`.

## 6. Where the keys come from (one-minute list)

| Var | Console | Free tier (verify today's numbers) |
|---|---|---|
| `GEMINI_API_KEY` | aistudio.google.com | ~1,500 req/day on Flash |
| `OPENROUTER_API_KEY` | openrouter.ai/keys | 28+ `:free` models, 20 RPM |
| `DEEPSEEK_API_KEY` | platform.deepseek.com | pay-as-you-go, very cheap |
| `GROQ_API_KEY` | console.groq.com/keys | fast Llama/Qwen, rate-limited |

## 7. If Docker is absent

Nothing to do. Runtime auto-detection falls back to the **local jail**
(path-jailed subprocess + denylist + timeouts) and the UI shows a warning
badge. Functionality is identical; isolation is weaker — see docs/security.md.

## 8. UI development (only if you change the interface)

```bash
cd ui && npm install && npm run dev    # vite dev server :5173 → proxies /api and /ws to :8000
```
