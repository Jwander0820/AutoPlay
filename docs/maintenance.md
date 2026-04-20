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
