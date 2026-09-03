# sandbox/

Docker image in which the agent's `bash`, file edits, searches and verify
commands actually execute. Your repo is bind-mounted at `/workspace` —
nothing else of the host is visible. It intentionally has **no**
`docker.sock`, no secrets, and no network aliases beyond the internet.

```bash
docker build -t omiagent/runtime:local sandbox/
```

`OMI_SANDBOX=auto` uses this image when Docker is present; otherwise the
runtime falls back to the local jail (`src/omiagent/runtime/local.py`).

Want extra tooling (Go, Rust, …)? Add it to your own derivative image and
point `OMI_SANDBOX_IMAGE` at it.
