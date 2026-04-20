# Maintenance Loop

AutoPlay should evolve through small, observable increments.

## Each change

1. Update or create a spec in `docs/specs/`.
2. Add tests for parser, validation, runner, or CLI behavior as appropriate.
3. Keep ADB-touching behavior behind dry-run, validation, or explicit flags.
4. Run `PYTHONPATH=src python3 -m unittest discover -s tests`.
5. Update `docs/architecture.md` or `docs/user-testing.md` when the workflow changes.

## After user tests

- Convert repeated manual notes into a new spec.
- Prefer one durable feature per iteration.
- Add fixtures or fake adapters before relying on real BlueStacks for regression coverage.
- Keep report artifacts under `artifacts/` so they stay out of git.

## Before publishing or pushing

Run a tracked-file scan:

```bash
git ls-files
rg -n -i "token|secret|password|api[_-]?key|private|credential|cookie|bearer" $(git ls-files)
git ls-files | rg -n "(^|/)(artifacts|\\.idea|__pycache__|.*\\.pyc|.*\\.png|.*\\.json|\\.codex|.*egg-info)($|/)"
```

Expected result: no tracked artifacts, images, IDE files, caches, credentials, or local-only tool files.
