# 0024 Local AI Smoke Client

## Intent

Provide a tiny client-side smoke test for local AI integrations. Before wiring a real local chat client or MCP wrapper, the user should be able to verify that `ai-server` exposes health, schemas, examples, and safe tool execution.

## Problem

The server exposes `/health`, `/schemas`, `/examples`, and `/tool`, but a user or local AI client still needs a repeatable way to prove the contract is working end to end.

Manual curl snippets are useful, but they are easy to mistype and awkward from PyCharm.

## Decision

Add a first-party smoke client:

- `src/autoplay/ai_client.py` implements HTTP calls using the Python standard library.
- `python -m autoplay ai-smoke` reads `/health`, `/schemas`, and `/examples`.
- `python -m autoplay ai-smoke --example dry_run_tap` also posts the named example to `/tool`.
- The smoke client refuses guarded real-input examples unless `--allow-real-examples` is passed.
- The output is JSON so PyCharm, scripts, and future local AI setup flows can inspect it.

## Safety

- The default smoke check performs no device input.
- The default executable example should be `dry_run_tap`, which returns the ADB command without touching the emulator.
- Guarded real examples must remain blocked unless explicitly opted in by the human.

## Acceptance Criteria

- A user can run `python -m autoplay ai-smoke --base-url http://127.0.0.1:8787`.
- A user can run `python -m autoplay ai-smoke --example dry_run_tap`.
- The smoke output includes server health, schema count, example count, and optional tool response.
- Guarded real examples are rejected by default.
- Unit tests cover success and guarded-example rejection.

## Implemented Surface

- `src/autoplay/ai_client.py` implements the smoke client.
- `python -m autoplay ai-smoke` checks `/health`, `/schemas`, and `/examples`.
- `python -m autoplay ai-smoke --example dry_run_tap` posts the named example to `/tool`.
- `--allow-real-examples` is required before examples with `args.execute=true` can be posted.
