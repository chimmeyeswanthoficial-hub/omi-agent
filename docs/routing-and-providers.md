# Routing & the `max` model

**The claim:** one model name should be enough for everyone. You configure
*capability groups*; `omirouter` decides per request.

## How a request gets routed

```
client/agent says model="max"
        │
        ▼
classify(messages, hint)          ← heuristic v0, deterministic
   hint wins if present (agent tags each call; external clients send
   X-Omi-Task: code-edit | shell-debug | plan-reason | long-context | vision)
   else:  image parts → vision · >60k chars → long-context
          plan/why/design → plan-reason · code fences / fix/refactor words → code-edit
          anything else → shell-debug (cheapest fast lane)
        │
        ▼
groups[group] → ordered provider names
   filter: provider needs its api_key_env non-empty (or unset)
   filter: skip providers in cooldown (2 consecutive failures)
        │
        ▼
litellm.acompletion(model, …)
   429/5xx/timeout → next entry in the chain (walk) , failure counts, cooldown
   success → tokens + cost → usage.db  →  budget guard + UI meter
```

Every response carries `omi: {provider, model, group, usd}` so the UI can show
*why* a model was chosen — the badge next to each step.

## Group tuning notes (Sept 2026 reality)

| group | good primaries | watch out |
|---|---|---|
| `code-edit` | DeepSeek V3/V4 class (`deepseek/deepseek-chat`), Qwen3-Coder via OpenRouter, Claude-class when you add it | free `:free` OpenRouter ids rotate — keep 2+ entries per group |
| `shell-debug` | Gemini Flash (1.5k RPD free), Groq Llama-3.3 (very fast, small TPM) | agent steps are chatty: prefer the free volume lane here |
| `plan-reason` | R1-class reasoners, Pro/GPT-5-class when paid | 1 call per task + re-plans only |
| `long-context` | 1M-context lanes: DeepSeek, Gemini Flash | repo map already avoids this group; it's for big single files |
| `vision` | Gemini Flash (the free image lane) | screenshot→bug flows land here |

## Extending `classify`

v0 is a transparent keyword heuristic you can outgrow in an afternoon:
swap `classify` in `gateway/router.py` for an embedding call (e.g. a small
Ollama model) or an LLM-tagging pass with caching. Same return value: a group
name string. Nothing else knows about classification.

## Budgeting

`MaxRouter` records every call via `UsageLog`. The agent loop checks
`totals_for(task)` before each step and stops at `OMI_TASK_BUDGET_USD`.
`GET /api/usage` returns lifetime totals; the footer shows
`spent / budget` live.
