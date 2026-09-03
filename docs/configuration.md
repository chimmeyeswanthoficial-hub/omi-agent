# Configuration

Two files matter: **`.env`** (secrets + switches) and
**`configs/providers.yaml`** (routing). Everything else has defaults.

## `.env` (copy from `.env.example`)

| Var | Default | Notes |
|---|---|---|
| `GEMINI_API_KEY` … `GROQ_API_KEY` | — | at least one; names match `api_key_env` in providers.yaml |
| `OMI_HOST` / `OMI_PORT` | `127.0.0.1` / `8000` | bind `0.0.0.0` only behind your own network |
| `OMI_WORKSPACES_DIR` | `~/omi-workspaces` | task repo copies live here |
| `OMI_DATA_DIR` | `~/.omi` | event logs + usage.db |
| `OMI_SANDBOX` | `auto` | `auto` → docker if daemon answers, else local jail; `docker` hard-fails instead |
| `OMI_SANDBOX_IMAGE` | `omiagent/runtime:local` | built from `sandbox/Dockerfile`; falls back to `python:3.12-slim` |
| `OMI_MAX_STEPS` | `80` | loop cap |
| `OMI_STEP_TIMEOUT_S` | `120` | bash/verify timeout |
| `OMI_TASK_BUDGET_USD` | `1.00` | hard stop per task (gateway totals) |
| `OMI_PROVIDERS_FILE` | `configs/providers.yaml` | routing table |
| `OMI_GATEWAY_KEY` | *(empty)* | when set, `/v1/*` requires `Authorization: Bearer <key>` |
| `OMI_PLAN_APPROVAL_TIMEOUT_S` | `25` | plan mode auto-continues after this window (headless safety) |
| `OMI_STATIC_DIR` | `ui/dist` | built UI location |

All are also CLI-independent — any env var beats `.env`, `Settings` reads
`OMI_*` via pydantic-settings.

## `configs/providers.yaml`

```yaml
providers:
  - name: deepseek-chat              # handle used in groups + shown in UI
    model: deepseek/deepseek-chat    # ANY litellm-supported id
    api_key_env: DEEPSEEK_API_KEY    # read from env; empty → provider skipped
    tags: [code, long-context]
    priority: 10                     # lower = tried earlier inside a group
groups:
  code-edit:   [deepseek-chat, gemini-flash]   # ordered fallback chain
  shell-debug: [gemini-flash, groq-llama]
  plan-reason: [openrouter-deepseek-r1, gemini-pro]
  long-context: [deepseek-chat, gemini-flash]
  vision:      [gemini-flash]
  default:     [gemini-flash]
router:
  cooldown_s: 45        # a deployment failing twice is parked this long
  max_retries: 2
  classify: heuristic   # or task-header (trusts X-Omi-Task exclusively)
```

Rules:
- A provider with a missing/empty `api_key_env` value is **skipped**, so
  sharing configs across machines is safe.
- If a group resolves to nothing available, it widens to all providers, then
  the task fails with a clear `gateway failure` event.
- `model` accepts anything litellm speaks: `openai/...`, `anthropic/...`,
  `ollama/...` (offline mode), `groq/...`, `openrouter/vendor/model:free`, …
  Cost accounting uses litellm's price table when known, else $0 with the
  tokens still logged.

## Adding a provider = 4 lines

```yaml
  - name: openai-gpt
    model: openai/gpt-5-mini
    api_key_env: OPENAI_API_KEY
    tags: [code, premium]
    priority: 1
# then put openai-gpt at the head of the groups you want it to serve
```

Restart the server. The UI badges, budget math, and fallback chains pick it up
automatically.
