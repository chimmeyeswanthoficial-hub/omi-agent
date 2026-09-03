# NEXT → Antigravity 🚀
> The bridge file: everything between "repo built in the sandbox" and "omiagent on
> GitHub with my keys proven." Follow top to bottom; check boxes off as you go.

Prereq: you downloaded the repo (e.g. `omiagent.zip` from the workspace — includes
`.git` with the 2 commits, excludes `.venv`/`node_modules`).

---

## 1 · Open & sanity (2 min)

- [ ] Unzip somewhere you'll keep it, e.g. `~/projects/omiagent`
- [ ] Open that folder in **Antigravity**
- [ ] In Antigravity's terminal:

```bash
cd ~/projects/omiagent
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"   # or: uv venv && uv pip install -e ".[dev]"
.venv/bin/python -m pytest -q          # expect: 49 passed, 3 skipped (live suite = key-gated)
.venv/bin/ruff check src tests         # expect: All checks passed!
cp .env.example .env                   # keep the file empty for now — next step proves offline first
.venv/bin/omiagent demo --fake         # expect: 🏁 finished + 3-commit git log (offline demo, no keys)
```

If those four pass, the machine is ready. (Full requirements: [REQUIREMENT.md](REQUIREMENT.md).)

## 2 · Make it yours (1 min)

Repo files carry `<you>` placeholders — replace with your GitHub username:

```bash
grep -rl '<you>' --include='*.md' --include='*.toml' . | xargs sed -i "s/<you>/YOUR-USERNAME/g"
git commit -am "point repo links at my GitHub"
```

- [ ] Decide the name: keep **`omiagent`** (public) — or rename the folder too if you prefer `agent-omi`.

## 3 · Push via Antigravity (3 min)

GitHub side first:
1. github.com → **New repository** → name `omiagent` → **public** → do **not**
   tick "add README/license/gitignore" (we ship all three). → Create.
2. Copy the URL: `https://github.com/YOUR-USERNAME/omiagent.git`

Antigravity terminal:

```bash
git remote add origin https://github.com/YOUR-USERNAME/omiagent.git
git branch -M main
git push -u origin main        # sign-in prompt: use GitHub's browser flow or a PAT (repo scope)
git log --oneline origin/main  # you should see your commits
```

- [ ] push clean · [ ] repo loads in browser with README hero

> Using Antigravity's agent/commit UI instead of raw git? Any path that ends in
> `git push -u origin main` is fine. Never let the tool "initialize a new repo
> with a starter README" — we already have real history.

## 4 · GitHub cosmetics (2 min)

**About / description line** (repo → ⚙️ settings → Description), paste:

```
⚡ Your own arena.ai/agent — self-hosted coding agent with a workspace UI, sandboxed bash + git checkpoints, and BYOK smart model routing ("max" over Gemini/OpenRouter/DeepSeek/Groq). 100% local, MIT.
```

**Topics:**

```
ai-agent coding-agent self-hosted llm fastapi react openai-compatible llm-router
byok agent-mode dev-tools python
```

Other settings worth it:
- [ ] Features: tick **Issues** (and Discussions if you want a feedback zone); untick Wiki
- [ ] Social preview: skip, or export `assets/logo.svg` to a 1280×640 PNG
- [ ] Default branch `main` ✅

## 5 · Draft the v0.1.0 release (copy-paste ready)

GitHub → **Releases → Draft a new release** → tag `v0.1.0` → target `main` →
title:

```
omiagent v0.1.0 — your own arena.ai/agent, self-hosted
```

notes body — paste as-is:

```md
## What this is
A self-hosted autonomous coding agent + workspace UI, modeled on arena.ai/agent — and yours: your keys, your machine, your code. MIT, one process, ~1 MB of source you can actually read.

## Highlights
- 🧠 **`max` smart routing (omirouter)** — one virtual model; each request classified into task groups (code-edit / plan-reason / shell-debug / long-context / vision) with ordered fallback chains, 429 cooldowns, and per-call usage ledger. BYOK: Gemini, OpenRouter, DeepSeek, Groq — add OpenAI/Anthropic with 4 config lines.
- 🖥️ **Workspace UI** — event stream, unified-diff steps, sandbox terminal tail, app preview, plan approve; every step wears a **model badge + token/$ meter**.
- 🔄 **Real agent loop** — plan → act → verify → self-correct; per-task USD budget + step caps.
- 📸 **Checkpoints** — every mutation is a git snapshot; rewind from the UI.
- 🐳 **Sandbox or not** — per-task Docker container when present, path-jailed local runtime when not. Same laptop, any machine.
- 🔌 **OpenAI-compatible gateway** — point anything at `POST /v1` with `model:"max"`.
- 🧪 **Provable** — `omiagent ping` proves keys+routing in 5 s; `pytest -m live` is the key-gated live suite; offline `demo --fake` needs nothing.

## Quickstart
    cp .env.example .env   # one key is enough
    uv pip install -e .    # or pip install -e .
    omiagent ping          # → group → provider → tokens → $
    omiagent serve         # → http://127.0.0.1:8000

## Quality
49 offline tests + 3 live tests, ruff-clean, CI (py 3.11 & 3.13 + UI build + docker smoke), UI ships ~53 kB gz.

## Read first
REQUIREMENT.md (what to install) · docs/getting-started.md · docs/security.md (threat model — yes, the agent runs code)

## Credits
litellm (routing), FastAPI/uvicorn, React/Vite/Tailwind, SWE-agent + OpenHands for design inspiration. Not affiliated with Arena/LMArena.
```

- [ ] Publish release (tick *Set as the latest*)

## 6 · Prove YOUR keys from the terminal (the "first real provider call" — now wired)

```bash
cd ~/projects/omiagent
nano .env            # paste ONE real key: GEMINI_API_KEY / OPENROUTER_API_KEY / DEEPSEEK_API_KEY / GROQ_API_KEY
.venv/bin/omiagent ping
```

You should see, e.g.:

```
⚡ omiagent ping — providers ready: gemini-flash
   ✓ group=shell-debug → provider=gemini-flash (gemini/gemini-2.5-flash)  18↑ 6↓ tok  $0.0000  1240 ms
   reply: 'OMI-OK'
   keys + routing + usage ledger all alive — you're cleared for tasks 🫡
```

Then the full key-gated suite (3 tests, a few hundred tokens — coffee money):

```bash
.venv/bin/python -m pytest -m live -v      # or: make live-test
```

- [ ] `ping` ✓ · [ ] `pytest -m live` → **3 passed**

**Reading the output** (fast debugging map):

| Symptom | Meaning / fix |
|---|---|
| `providers ready: NONE` | `.env` not found (run from repo root) or no var named exactly as in providers.yaml |
| `✗ gateway failure: no providers configured` | key exists but that provider's entry needs it — check `api_key_env` spelling |
| `401/403` from provider | wrong/quota-less key — test at the provider console |
| `live` shows `skipped` | env not exported into the test run: `set -a && . ./.env && set +a` |
| big `elapsed_ms` first call | cold DNS/TLS — second call is your real latency |

## 7 · First real task, end-to-end

```bash
.venv/bin/omiagent serve        # → http://127.0.0.1:8000
```

- [ ] UI loads (dark, 4 panes) → type: **`Fix the failing test in calculator.py and explain the bug`**
- [ ] set repo path (optional box) to `examples/demo_repo`, mode **plan** → run
- [ ] watch: 🗺 plan → ✅ (approve) → 🔧 bash pytest → edit → 🧪 verify PASSED → 🏁 finished
- [ ] hit `↺` on a checkpoint and confirm the file reverts (that's the undo button)
- [ ] `GET http://127.0.0.1:8000/docs` → try `/v1/models` → should list `max`

## 8 · Post-launch (optional, 10 min)

- [ ] CI badge works: Actions tab green on your push → paste badges into README when they show
- [ ] Add a **screenshot/GIF** to the README hero (UI open on your laptop beats any ASCII art):
      `![workspace](docs/assets/screenshot.png)` — drop the file in `docs/assets/`
- [ ] Star your own repo, share: X/Reddit r/LocalLLaMA post draft idea:
      *"Built my own open-source arena.ai/agent over a weekend — your keys, your sandbox, per-step model badges + cost. `omiagent ping` proves it in 5s."*
- [ ] Roadmap issues: lift the v0.2 bullets from docs/roadmap.md into GitHub issues (Antigravity can batch this)
- [ ] When you add a new provider key (OpenAI/Anthropic): 4 lines in `configs/providers.yaml` + env var — nothing else changes (docs/routing-and-providers.md)

## 9 · House rules I already enforced (don't regress them)

- `.env` never enters git (`.gitignore`); no provider key appears in code/prompts (redaction + stripped sandbox env)
- Model names live **only** in `configs/providers.yaml` — PRs that hardcode a model id in code get rejected
- `make check` (ruff + pytest) before every commit; live suite stays key-gated so CI never spends money
- If you push from Windows line-endings get weird: `.gitattributes` is present — leave it alone

---

### Status line (fill it in as you go)
```
[2] rename <you>     ─ ☐
[3] push origin main ─ ☐
[4] about + topics   ─ ☐
[5] release v0.1.0   ─ ☐
[6] ping + live ✓    ─ ☐
[7] first task ✓     ─ ☐
[8] polish           ─ ☐
```

**Blocked?** The whole story of every run is on disk: `~/.omi/tasks/<id>/events.jsonl`
(the event stream, replayable) + `usage.db` (spend) + `git log` inside the task
workspace. `cat` them and you know exactly what the agent did. 🫡
