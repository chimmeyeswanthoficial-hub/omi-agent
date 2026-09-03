# OmiAgent — project plan (v2 · API-first)
**Goal:** build our own arena.ai/agent — same experience, better looks, better loop, smarter model use — running 100% on API providers through **omirouter**, our personal gateway where one virtual model `max` auto-picks the right model group per task.
**Owner:** Omi · **Machine:** Windows 10/11 + WSL2 · **Status:** planning done → M0 next · **Updated:** 2026-09-03 (v2: user confirmed API-only; providers = Gemini, OpenRouter, DeepSeek, Groq now; OpenAI/Anthropic later)

---

## 1. Locked decisions

| Decision | Value |
|---|---|
| Model source | **100% APIs** — no local inference (Ollama deferred to Appendix A) |
| Providers now | Google Gemini · OpenRouter · DeepSeek · Groq |
| Providers later | OpenAI, Anthropic (design slots ready — §4 config marked `LATER`) |
| Gateway | `omirouter` = LiteLLM Proxy + our `max_router` middleware (NOT Tencent omi-router — wrong project, it's a frontend router) |
| Engine | custom agent loop, borrow SWE-agent ACI tools + OpenHands event-stream patterns |
| UI | custom React+Vite+Tailwind 4-pane workspace — the visual differentiator |
| Sandbox | Docker (WSL2 backend), never mounts docker.sock |
| Leaderboard/FastChat clone | parked → Appendix B (phase 2 idea) |

## 2. "Better than arena.ai/agent" — our feature bar

1. **`max` auto-routing:** one model name → task-classified → best/cheapest model per step. UI shows *which real model ran which step* (badge). Nobody else has this at home.
2. **4-pane workspace:** chat/plan stream + file tree + diff-review editor + terminal tail + live preview iframe.
3. **Plan mode:** agent drafts plan → you edit/approve → then it executes.
4. **Checkpoints:** every step = git snapshot in the sandbox branch; rewind button.
5. **Cost meter:** tokens + ₹/$ per task, read from LiteLLM logs; `max_budget` kill-switch at gateway.
6. **Rate-limit-native:** free tiers = tiny RPMs; our fallback chains are first-class, not an afterthought (§4).
7. **Parallel subtasks** (M6): independent files → 2–3 sandbox workers → merged PR-style diff.

## 3. Architecture (v2 — cloud-brained, local-hands)

```
 Windows laptop / WSL2 ──────────────────────────────────────────────┐
 │  C. UI (React, :3000) ⇄ WebSocket ⇄  B. AGENT SERVER (Python)     │
 │                                    tools: bash·read·edit·search·   │
 │                                    patch·web_fetch·screenshot→LLM  │
 │                                        │ docker run/exec          │
 │                                        ▼                           │
 │                              SANDBOX container (python+node+git    │
 │                              +ripgrep; mounted repo; no docker.sock)│
 │                                        │ OpenAI-compat requests    │
 │                                        ▼  (model always = "max")   │
 │                              A. OMIROUTER (LiteLLM :4000)          │
 │                              max_router middleware: classify task   │
 │                              → group → provider w/ fallback chains  │
 │                              logs tokens/$ → UI cost meter          │
 └────────────────────────────────────┬───────────────────────────────┘
                                      │ HTTPS (100% API — nothing local)
        ┌───────────────┬─────────────┴──────────┬───────────────┐
        ▼               ▼                        ▼               ▼
   Gemini API       OpenRouter              DeepSeek API      Groq Cloud
   flash free       28+ :free + paid        V4 (cheap/1M)     llama-3.3-70b
   (1.5K RPD)       (20 RPM free)                               (30 RPM free)
```

## 4. omirouter — the `max` model design

### 4.1 Task groups (what "max" fans out to) — pinned Sept 2026 reality
| Group (task) | Primary | Fallback chain | Why |
|---|---|---|---|
| `code-edit` (diffs, refactors) | DeepSeek V4-Pro (`deepseek-chat`→V4 per console) | OpenRouter `Qwen3 Coder 480B :free` → Gemini 3 Flash → **CLAUDE (LATER)** | paid-but-cheap primary avoids free-tier 429 walls mid-task |
| `shell-debug` (stdout triage, commands) | Gemini 2.5 Flash (free 1,500 RPD) | Groq llama-3.3-70b-versatile → Gemini Flash-Lite | speed + volume, $0 |
| `plan-reason` (planning, root-cause) | DeepSeek V4 thinking / R1 via OpenRouter :free | Gemini Pro (50 RPD free — rare & precious) | reasoning only for step 0 & failures |
| `long-context` (repo maps >128K) | DeepSeek V4 (1M ctx) or Gemini Flash (1M) | OpenRouter long-ctx models | two free 1M paths |
| `summarize-misc` | Groq (fast) | Gemini Flash-Lite | free filler |
| `vision` (screenshot→bug, preview QA) | Gemini 2.5 Flash (multimodal, free) | OpenRouter vision :free | **only our free providers that take images** — Groq can't |

Rules: classification happens in `max_router` (heuristic v0: fenced-code ratio + keywords + step-kind label the agent server sends in an `X-Omi-Task` header; v2: embedding smart-router). Gateway rewrites `model:"max"` → group member, retries 429 by walking the fallback chain, logs everything.

### 4.2 config.yaml (working skeleton — swap exact IDs from each console)
```yaml
model_list:
  # ---- code-edit ----
  - model_name: "max"
    litellm_params: { model: deepseek/deepseek-chat, api_key: os.environ/DEEPSEEK_API_KEY, tags: ["code-edit"] }
  - model_name: "max"
    litellm_params: { model: openrouter/qwen/qwen3-coder:free, api_key: os.environ/OPENROUTER_API_KEY, tags: ["code-edit","fallback"] }
  - model_name: "max"
    litellm_params: { model: gemini/gemini-3-flash-preview, api_key: os.environ/GEMINI_API_KEY, tags: ["code-edit","fallback"] }
  # LATER: - { model: anthropic/claude-*, tags: ["code-edit","premium"] }  # top-priority when key exists
  # ---- shell-debug / fast ----
  - model_name: "max"
    litellm_params: { model: gemini/gemini-2.5-flash, api_key: os.environ/GEMINI_API_KEY, tags: ["shell-debug"] }
  - model_name: "max"
    litellm_params: { model: groq/llama-3.3-70b-versatile, api_key: os.environ/GROQ_API_KEY, tags: ["shell-debug","fallback"] }
  # ---- long-context ----
  - model_name: "max"
    litellm_params: { model: gemini/gemini-2.5-flash, api_key: os.environ/GEMINI_API_KEY, tags: ["long-context"] }
  # ---- vision ----
  - model_name: "max"
    litellm_params: { model: gemini/gemini-2.5-flash, api_key: os.environ/GEMINI_API_KEY, tags: ["vision"] }

router_settings:
  enable_tag_filtering: true
  allowed_fails: 3          # cool down a deployment after 3 429s/5xx
  cooldown_time: 60
  retry_policy: { BadRequestErrorRetries: 1, TimeoutErrorRetries: 2 }
litellm_settings:
  master_key: os.environ/OMIROUTER_KEY
  max_budget: 500           # ₹ per month hard stop, kill-switch
  budget_duration: 30d
general_settings: { store_model_in_db: true }   # spend logs → UI cost meter
```
Agent server always sends: `{"model": "max", ...}` + `X-Omi-Task: code-edit|shell-debug|...` header. That's the entire protocol.

### 4.3 Free-tier stacking strategy (the money math, Sept 2026)
- **Gemini free:** ~1,500 req/day Flash + 1M TPM (no card needed); Pro free essentially gone (50 RPD / paid) — so Flash IS our volume workhorse.
- **OpenRouter:** 28+ `:free` models at 20 RPM & 50 req/day — **one-time $10 top-up lifts :free to 1,000 req/day, credits never expire** → do this early; the $10 also becomes our OpenAI/Anthropic-onramp later.
- **Groq free:** 30 RPM, ~6K TPM (small!) — good for bursty shell triage, not long files.
- **DeepSeek:** pay-as-you-go, V4-Flash from ~$0.14/M in — this is our only real spend; ₹1,000/month ≈ enormous agent-hours.
- ⇒ Realistic daily free capacity ≈ 1.5K (Gem) + 1K (OR after $10) + bursty (Groq) + paid overflow (DeepSeek) → **~2,500+ calls/day at ≤₹50/day.** An agent task ≈ 20–60 calls. Comfortable for nightly dev.

## 5. Agent engine (`omiagent`) — the loop that must feel smarter than Arena's

- Loop: `task → PLAN (editable) → [reason → tool → observe → verify]×N → diff summary`. Every step: event on WS + git snapshot + gateway call tagged.
- Tools (SWE-agent ACI, token-frugal): `bash(timeout 120s)`, `read_file(offset,limit)`, `edit(find,replace)` exact-match w/ retry-on-fail, `search(regex,glob)`, `apply_patch`, `web_fetch`, `finish(summary)`.
- Self-correction: 2 failed verifies on same file → auto re-plan (inject full error tail, switch to `plan-reason` group). This is the "feels intelligent" bit.
- Context: rolling step-summary; repo map (tree+signatures) rebuilt per snapshot; files >300 lines never sent whole.
- Hard rules: everything executes in sandbox; max 80 steps/task; spend cap per task (ask gateway balance diff before each step).

## 6. UI (`omied` — Omi's agent canvas)

Dark, one accent, mono everywhere. Layout:
```
┌───────┬─────────────────────────────────┬───────────────┐
│ FILES │  EVENTS: plan → steps → results │ PREVIEW (app) │
│ tree  │  [model badge] [tokens] [$]     ├───────────────┤
│       │  inline diff cards: ✔ approve ✖ │  TAIL: stdout │
├───────┴─────────────────────────────────┴───────────────┤
│ input ⏎ · status: ● running step 12/80 · 41.2k tok · ₹9.1│
└──────────────────────────────────────────────────────────┘
```
v0 = plain chat+events over REST. v1 = WS streaming + diffs. v2 = preview + cost + badges.

## 7. Milestones

| M | Deliverable | Done-when (test I can verify) | Time |
|---|---|---|---|
| **M0** | WSL2+Docker+uv+Node env; keys in `.env` | `docker run hello-world` ✓; curl each provider `models` endpoint → 4× 200 | ½ day |
| **M1** | omirouter live: LiteLLM + §4.2 config | curl `model:"max"` with code-task vs chat-task → log shows DeepSeek vs Gemini chosen; force 429 → fallback works; `GET /spend/logs` populated | 1 day |
| **M2** | `max_router` middleware: classifier + `X-Omi-Task` | 20-prompt eval sheet: ≥90% grouped correctly | 1 day |
| **M3** | omiagent CLI core: loop + 7 tools + sandbox + snapshots | `omi "make tests pass" ./demo_repo` runs unattended → clean commit + summary | 2–4 days |
| **M4** | WS event stream + resume (jsonl) | kill server mid-task → restart → resumes | 1 day |
| **M5** | UI v1: chat+events+diff approve | fix a real repo of yours entirely in browser | 3–5 days |
| **M6** | Plan mode · preview pane · cost meter · rewind · embeddings router · parallel subtasks · **then add OpenAI/Anthropic keys into `code-edit` premium slot** | demo reel "better than arena.ai/agent" | 1–2 wks |

## 8. M0 commands

```powershell
# PowerShell (admin)
wsl --install -d Ubuntu-24.04
winget install Docker.DockerDesktop        # then: Settings → Resources → WSL integration → Ubuntu ON
```
```bash
# Ubuntu (WSL2)
curl -LsSf https://astral.sh/uv/install.sh | sh
sudo apt update && sudo apt install -y git ripgrep nodejs npm
mkdir -p ~/omi/{omirouter,omiagent,omied,sandbox,demo_repo} && cd ~/omi
# keys — get them at: AI Studio (GEMINI_API_KEY) · openrouter.ai/keys · platform.deepseek.com · console.groq.com/keys
cat > ~/omi/omirouter/.env <<'EOF'
GEMINI_API_KEY=***
OPENROUTER_API_KEY=***
DEEPSEEK_API_KEY=***
GROQ_API_KEY=***
OMIROUTER_KEY=sk-om…-key
EOF
# M1 run:  uvx --from 'litellm[proxy]' litellm --config config.yaml --port 4000
# smoke:   curl -s localhost:4000/v1/chat/completions -H "Authorization: Bearer $OMIROUTER_KEY" \
#          -H "X-Omi-Task: shell-debug" -d '{"model":"max","messages":[{"role":"user","content":"ping"}]}'
```

## 9. Risks & house rules

1. **Model-ID drift** — providers rename/retire fast (Gemini free tier just tightened April 2026; OR free list rotates). Rule: pins live only in `omirouter/config.yaml`; quarterly update = edit one file. Never hardcode a model name in agent/UI code.
2. **Free-tier 429 walls** — 15–30 RPM is low for an agent loop; mitigated by fallback chains + step budgeting + DeepSeek overflow. Don't babysit quotas with the primary model; keep the priciest-per-quality model for code-edit only.
3. **Privacy:** Gemini **free tier may train on your data**. Don't feed personal/secret files on free keys; move sensitive repos to paid keys only (note in README).
4. **API keys:** stay in gateway `.env` only — never in sandbox, never in prompts, never in git (`.gitignore` from M0).
5. **Security:** sandbox container = agent's blast radius; no docker.sock, no host mounts except the repo, CPU/mem caps (`--cpus 2 --memory 4g`).
6. **Don't** fork whole LiteLLM or whole OpenHands — thin middleware + own loop keeps you in control and keeps "I made this" honest.
7. OpenAI/Anthropic later = add 3 lines to `model_list`, tag `premium`; classifier auto-uses them. Zero other changes.

## 10. Disk & file budget — MEASURED 2026-09-03 (real installs run in my sandbox)

| Piece | Size | Files | Basis |
|---|---|---|---|
| Our repo code (all of omirouter mw + omiagent + UI src, M0–M5) | ~1.5–2.5 MB | ~120–150 | estimate (text code) |
| Gateway venv `litellm[proxy]` | **671 MB** | **20,847** | measured (top eaters: polars 211M, litellm 111M, numpy 42M, botocore 27M, granian 21M, openai 20M) |
| ↳ slim alternative `litellm`+fastapi+uvicorn | **257 MB** | **14,325** | measured (−414 MB; loses proxy admin/DB-spend extras) |
| Agent-server venv (fastapi/uvicorn/ws/httpx/docker) | **59 MB** | **2,419** | measured |
| UI `node_modules` (vite+react+tailwind v4) | **121 MB** | **765** | measured (npm dedupe works: only 31 top pkgs) |
| UI production `dist/` | 264 KB | 8 | measured |
| Sandbox Docker image (py3.12-slim+node+git+rg) | ~350–400 MB | — | est. (no Docker here to run) |
| Model weights | **0 MB** | **0** | 100% API — decided |
| One-time pip+npm caches | ~415 MB | — | measured 176M+239M — purgeable (`pip cache purge`, `npm cache clean --force`) |

**Totals for a complete working setup (excluding OS prereqs & caches):**
- Full-gateway build: ≈ **1.3 GB · ~24,000 files**
- Slim-gateway build: ≈ **0.9 GB · ~18,000 files**
- The repo itself on GitHub: ≈ 2 MB · ~150 files.

OS prereqs on your laptop (not repo): WSL2 Ubuntu ~2 GB + Docker Desktop ~1.5–2 GB. Note: WSL vhdx grows over time; compact with `wsl --manage <distro> --set-sparse true` (or the 25H1 auto-sparse default) if it bloats.
Runtime growth: git snapshots + task jsonl logs ≈ few MB/task (self-pruned per §5 rules).

For scale: the FastChat/leaderboard route Google quoted = 130 MB code + 2–4 GB ML deps + 14–30 GB weights. Ours: same-day agent platform at 0 GB weights.

## Appendix A — deferred: local/offline mode (Ollama)
If laptop later gets ≥12 GB VRAM: add `ollama_chat/qwen3-coder` deployments tagged `offline` + one env flip in agent server. Architecture already supports it (gateway speaks OpenAI-compat to anything).

## Appendix B — parked: the leaderboard clone (FastChat / arena-hard-auto)
Your Google chat's first answer track. Phase 2 idea: run `lmarena/arena-hard-auto` + arena-rank-style Bradley-Terry on *your own* battle logs to leaderboard-test routing strategies ("max v1 vs max v2"). Verifies the "even better" claim with numbers.

## Sources for §4.3 numbers (checked 2026-09-03)
- Gemini free tier 1,500 RPD Flash / Pro cut Apr-2026: tokenmix.ai, findskill.ai, geotoolbox.ai writeups of Google AI Studio limits.
- OpenRouter :free — 28+ models, 20 RPM, 50→1,000 RPD after $10: pricepertoken.com/endpoints/openrouter/free.
- Groq free 30 RPM/6K TPM; DeepSeek V4 pricing; stacking strategy: klymentiev.com free-LLM-API comparisons (Jun 2026).
- (re-verify each before M0 — these move.)
