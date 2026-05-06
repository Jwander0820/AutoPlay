# 0023 Local AI Client Examples

## Intent

Make the local AI tool interface easier to connect by exposing practical request examples alongside schemas. A local AI client should not need to scrape docs or guess the JSON shape before calling AutoPlay tools.

## Problem

`ai-tool`, `ai-server`, and `ai-schemas` define the callable interface, but early local AI clients still need concrete examples for:

- checking emulator readiness
- capturing screenshots
- dry-run device input
- guarded real device input
- validating and running reviewable scripts

Docs alone are useful for humans, but local AI clients need examples as JSON payloads.

## Decision

Add a small examples surface:

- `src/autoplay/ai_examples.py` contains canonical example requests.
- `python -m autoplay ai-examples` prints a machine-readable example payload.
- `GET /examples` returns the same examples from `ai-server`.
- Examples must avoid private paths, secrets, user email, or local emulator install paths.
- Examples must default to safe dry-run behavior.
- Any real-input example must use placeholder `device_input_code` text, not a real session code.

## Payload Shape

```json
{
  "ok": true,
  "examples": [
    {
      "name": "dry_run_tap",
      "description": "Preview the tap command without touching the device.",
      "safety": "dry_run",
      "request": {
        "tool": "tap",
        "args": {
          "x": 100,
          "y": 200,
          "label": "open daily panel"
        }
      }
    }
  ]
}
```

## Acceptance Criteria

- A user can run `python -m autoplay ai-examples` and receive JSON.
- A local HTTP client can call `GET /examples`.
- Examples include `doctor`, `screenshot`, dry-run `tap`, guarded real `tap`, `scroll`, `validate`, and dry-run `run_script`.
- Examples never include user-specific ADB paths, serials, emails, or local install directories.
- Unit tests cover CLI output and HTTP output.
