# Roadmap

v0.1.0 ships the loop: plan → act → verify → checkpoint, 4-pane UI, `max`
routing, budget meter, rewind, offline demo. Everything below is ordered by
pain-to-value, not hype.

## v0.2 — sharper loop
- [ ] Streaming actions (tool args render while the model writes them)
- [ ] Diff-hunk approval (approve per file, not per step)
- [ ] `test --auto-detect` for more ecosystems (cargo, go, make)
- [ ] Task resume after server restart (rebuild from events.jsonl)
- [ ] Embedding-based `classify` behind a config flag

## v0.3 — workspace muscle
- [ ] Lint/typecheck as first-class verify layers
- [ ] Multi-repo tasks (two workspaces, shared plan)
- [ ] Screenshot→vision loop wired into `vision` group (preview pane → model)
- [ ] Rewind to step from UI keyboard (`R`)

## v0.4 — parallel & social
- [ ] Parallel subtasks: disjoint file sets → N sandboxes → merged diffs
- [ ] Exportable session tapes (events.jsonl → markdown/HTML report)
- [ ] Shared read-only link to a task (static event replay)

## later, maybe
- [ ] Ollama-only preset (airplane mode) + auto model discovery
- [ ] Leaderboard mode: run `max` v1 vs v2 routings on your own task corpus
  (this is where the arena-hard-auto / arena-rank world becomes a phase 2 toy)
- [ ] Plugin API for custom tools (python entry-points)

**Non-goals:** being a general chat client; owning GPUs; anything that makes
`docker.sock` reachability a feature.
