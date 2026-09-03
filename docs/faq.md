# FAQ

**Is this a copy of arena.ai/agent's code?** No — that's proprietary. This is a
functional re-creation of the *experience* (agent + sandbox + workspace UI)
built from public pieces (litellm, FastAPI, git), so you can read every line.

**Why is it "even better"?** Four things the hosted version can't do for you:
your keys (`max` routing picks *your* cheapest good model per step), per-step
cost badges, rewind-to-checkpoint, and offline demo. Plus it's 2 MB of Python
you can actually change.

**Does my code leave my machine?** Only to the model providers you configure —
exactly like any coding assistant. The server itself is localhost by default
and phones home nowhere. There's no telemetry.

**Do I need a GPU?** No — 100% API. A GPU + Ollama is an optional extra lane
for the same config.

**Why not just run OpenDevin/OpenHands?** Great project; it's also 100k+ LOC
with its own runtime estate. OmiAgent is a deliberately small engine — you can
hold the whole loop in your head, which is the point of a *personal* agent.

**Free-tier limits?** ~1,500 req/day Gemini Flash + OpenRouter `:free` (20 RPM,
50 req/day → 1,000/day after a one-time $10 top-up). The router's cooldown
chains mean free tiers degrade gracefully; DeepSeek-class paid is the calm
lane (~$0.1x/M tokens territory). Numbers move — verify before relying.

**Why is a step missing a model badge?** Calls that fail routing before any
provider answered, or the offline `--fake` demo, have no real provider — that's
by design, no fake numbers.

**The UI says "no keys — add .env" but I did?** `.env` is read from the process
CWD (`omiagent serve` from the repo root, or set `OMI_PROVIDERS_FILE`/export
env vars). Keys must be `export`ed or in that file — not in another shell's
history.

**Can the agent rm my home dir?** It tries → blocked by policy + it never sees
your home anyway (file tools are jailed; sandbox mounts only the task copy).
Running *without* Docker on a folder of yours is the only sharp edge — see
security.md.

**Windows?** WSL2 Ubuntu, everything identical. Docker Desktop optional.

**Why is it `omirouter` inside the app?** It *is* the gateway: same code path
serves the agent (in-process) and `/v1` (for anything external speaking
OpenAI). One brain, two doors.
