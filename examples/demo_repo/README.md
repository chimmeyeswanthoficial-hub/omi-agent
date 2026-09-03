# demo_repo

A deliberately broken mini-project so you can watch an agent fix it.

- `calculator.py` contains **one planted bug** in `add()`.
- `tests/test_calculator.py` has 4 tests; `test_add` fails.

Try:

```bash
omiagent demo --fake     # scripted model, real tools (offline)
omiagent demo            # real model via your keys
```

Or point the web UI at this folder as the workspace.
