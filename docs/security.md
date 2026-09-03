# Security

An agent that edits code and runs commands is a dangerous object. Threat model
and mitigations, honestly:

## Isolation levels

| Runtime | Isolation | Use when |
|---|---|---|
| `docker` (default `auto`) | container: own fs view (only `/workspace` bind-mounted), capped 2 CPU/1 GB, no docker.sock, no host paths | any real work |
| `local` jail | same-user subprocess with path-jailed file tools (`PermissionError` outside workspace), stripped env (`PATH/HOME/LANG/TERM/TMPDIR/USER` only — **your API keys are NOT in the child env**), per-command timeout, process-group kill on timeout | no Docker available / throwaway repos only |

`OMI_SANDBOX=docker` fails loudly instead of silently downgrading.

## Command policy (`safety/policy.py`)

A small, readable denylist runs on *every* `bash` call before the runtime
sees it: recursive deletes at `/` or `~`, `sudo`, docker/podman CLI (escape
tooling), `mkfs`/`dd` to raw disks, fork bombs, pipe-to-shell, systemctl,
mount, kernel modules, iptables. It is **defense-in-depth, not the wall** —
the wall is the container. The denylist exists so the local jail and careless
moments stay survivable.

## Secrets

- Provider keys live in `.env` and are read **only by the gateway process**.
  The sandbox environment never receives them (see stripped env above).
- `safety/redact.py` scrubs key-shaped strings from every transcript echo,
  event payload, and gateway message pass-through.
- `~/.omi` contains task prompts + outputs — treat it like browser history.

## Network

The server binds `127.0.0.1` by default. If you set `OMI_HOST=0.0.0.0`:
1. set `OMI_GATEWAY_KEY` (protects `/v1`), and
2. know that `/api/tasks` can run commands on this machine — put it behind a
   reverse proxy with auth, or don't. CORS is limited to the vite dev origin.

## Prompt injection (yes, really)

Code, READMEs, and web pages the agent reads *can* try to instruct it. The
system prompt pins the JSON-only action protocol and the denylist blocks the
worst outcomes, but a determined poisoned repo is an attack surface — run
untrusted repos inside Docker only, on a scratch workspace copy (which the
manager already makes — your original repo is never the execution target).

## Cost attacks

A runaway loop burns your keys. Mitigations: per-task USD budget
(`OMI_TASK_BUDGET_USD`, checked before every step), step cap, provider
cooldowns on 429 storms, and `usage.db` you can audit. Set a hard monthly cap
at each provider console too — that's the only true kill-switch.

## Provider fine print (Sept 2026)

Google's **free** Gemini tier may use your prompts for training. Send
sensitive repos through paid lanes only, or run Ollama behind the same
providers.yaml interface locally.

## Reporting

See SECURITY.md at the repo root.
