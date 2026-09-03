# Changelog

All notable changes to OmiAgent are documented here
([Keep a Changelog](https://keepachangelog.com/) format,
[SemVer](https://semver.org/) versioning).

## [0.1.0] - 2026-09-03

Initial public shape — a self-hosted coding agent modeled on arena.ai/agent.

### Added
- **omirouter gateway**: single `max` virtual model, task classification
  (code-edit, plan-reason, shell-debug, long-context, vision), fallback
  chains with 429/5xx cooldowns, provider config via `configs/providers.yaml`,
  OpenAI-compatible `POST /v1/chat/completions` + `GET /v1/models` with
  optional bearer key.
- **Agent engine**: plan → reason → tool → verify → self-correct loop;
  step cap; per-task USD budget; checkpoint (git) after every mutation;
  JSON action protocol.
- **Tools**: `bash`, `read_file`, `write_file`, `edit_file`, `search`,
  `apply_patch`, `finish`.
- **Runtimes**: Docker sandbox (auto-detected) with `local` jail fallback —
  path-jailed, command denylist, timeouts.
- **Server**: FastAPI + WebSocket event streams, task lifecycle REST API,
  plan approval, cancel, rewind-to-checkpoint, task file listing.
- **Persistence**: per-task JSONL event store, SQLite usage ledger
  (tokens/USD/model/group per call).
- **UI** (React + Vite + Tailwind v4): workspace with event stream,
  diff cards, sandbox terminal tail, app preview, files pane, plan approve,
  live cost meter and per-step model badges.
- **UX niceties**: offline demo (`omiagent demo --fake`), usage audit,
  secret redaction in transcripts.
- `omiagent ping` one-shot key/routing smoke; key-gated live provider
  suite (`pytest -m live`, `make live-test`).
- Docs, CI (pytest + ruff + UI build), compose/Dockerfile, MIT license.

[0.1.0]: https://github.com/<you>/omiagent/releases/tag/v0.1.0
