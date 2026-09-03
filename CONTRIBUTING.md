# Contributing

Small core, big ideas — welcome.

## Ground rules
1. **One process, no microservices.** New capability = new module, not a new daemon.
2. **Model names never appear outside `configs/providers.yaml`.** Code speaks task groups.
3. Every loop/tool behavior change ships with a pytest (offline, no keys).
4. Keep the local runtime fully functional — Docker is a nicety, not a dependency.
5. Python ≥ 3.11, `ruff` clean (line 100). UI: strict TS, no new deps without a one-line reason in the PR.

## Dev loop

```bash
git clone https://github.com/<you>/omiagent && cd omiagent
uv venv && uv pip install -e ".[dev]"          # or python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
make check                                      # ruff + pytest
make ui-dev                                     # optional: hot-reload UI against the API
```

Useful commands:

```bash
omiagent demo --fake     # end-to-end sanity without keys
uv run pytest -k loop    # the heart of it
uv run ruff check --fix src tests
```

## PR shape
- Describe the *user-visible* change first, mechanism second.
- For UI changes, attach a GIF (the panes make great ones).
- Breaking config changes update `.env.example` **and** docs/configuration.md in the same commit.

## Ideas label
`good-first-issue`s include: more `classify` test rows, provider preset YAMLs,
per-hunk diff approval, terminal colorizer, docker-compose profile for Ollama.

By contributing you agree your contribution is MIT-licensed like the repo.
