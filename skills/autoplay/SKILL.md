---
name: autoplay
description: Use when working inside the AutoPlay repository on project setup, automation behavior, architecture choices, implementation conventions, or verification workflows specific to this codebase.
---

# AutoPlay Project Skill

## When to use this skill

Use this skill for AutoPlay-specific work, including repository setup, feature planning, automation flows, agent instructions, and code changes that should follow local project conventions.

## Workflow

1. Inspect the current repository structure before deciding where changes belong.
2. Prefer the smallest useful scaffold over speculative architecture.
3. Record durable project guidance in `AGENT.md` when it will help future agents.
4. For behavior changes, update `docs/specs/` before or alongside code.
5. Add verification steps alongside implementation work.
6. Keep generated files, local secrets, and dependency directories out of git.

## Current conventions

- Project instructions live in `AGENT.md`.
- Project skills live under `skills/`.
- SDD workflow lives in `docs/sdd.md`; concrete behavior specs live in `docs/specs/`.
- User testing notes and manual workflow live in `docs/user-testing.md`.
- Personal script authoring workflow lives in `docs/personal-scripts.md`.
- Maintenance habits live in `docs/maintenance.md`.
- Commits are created only when explicitly requested.
- If a tool or framework is introduced later, follow its standard layout instead of inventing a custom one.

## Verification

For setup-only changes, verify with:

```bash
git status --short
```

For implementation changes, prefer the narrowest relevant test, lint, typecheck, or smoke-test command available in the repository.
