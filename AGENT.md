# AutoPlay Agent Guide

## Project intent

AutoPlay is a new project. Treat this repository as the source of truth for future implementation details, product decisions, and local automation behavior.

## Working rules

- Read the existing files before making changes.
- Keep changes small, focused, and consistent with the current structure.
- Prefer clear names and simple modules over early abstractions.
- Do not overwrite user-created files or generated assets without checking their purpose.
- When adding behavior, include a practical way to verify it.
- Use SDD: update the relevant spec before or alongside behavior changes, then add tests that prove the spec.

## Skill entrypoint

Use the project skill at `skills/autoplay/SKILL.md` when work involves AutoPlay-specific planning, architecture, automation behavior, or project conventions.

## Engineering documents

- SDD workflow: `docs/sdd.md`
- Current architecture: `docs/architecture.md`
- Maintenance loop: `docs/maintenance.md`
- User testing guide: `docs/user-testing.md`
- Personal script workflow: `docs/personal-scripts.md`
- Next-stage handoff: `docs/next-stage.md`
- Implemented specs: `docs/specs/`

## Autonomous maintenance loop

- Treat every user test failure as input for the next spec.
- Prefer adding diagnostics before adding more automation surface.
- Keep the project runnable without BlueStacks for unit tests.
- Preserve safety defaults: validation first, dry-run taps by default, explicit flags for device input.

## Next stage direction

- Build a small guided tool for users to create scripts without hand-writing YAML.
- API-ize core actions so agents can call typed functions such as `tap(x, y)`, `screenshot(path)`, `wait(seconds)`, `validate(script)`, and `run(script)`.
- Keep AI-facing APIs behind the same safety model: dry-run by default, explicit execution flags, validation before device input, and JSON reports for every run.
- Do not give AI an unrestricted loop that freely clicks the device. Prefer bounded tool calls, step budgets, and reviewable plans/scripts.

## Git workflow

- Keep generated caches, dependency folders, logs, and local environment files out of git.
- Make commits only when asked.
- Before handing work back, run the smallest relevant verification command and report anything that could not be checked.
