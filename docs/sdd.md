# Spec Driven Development

AutoPlay uses SDD so automation behavior stays reviewable before it can touch a device.

## Loop

1. Write or update a spec in `docs/specs/`.
2. Add acceptance criteria that can be tested without a real emulator when possible.
3. Implement the smallest behavior that satisfies the spec.
4. Add or update tests that name the behavior.
5. Run the narrowest useful verification command and record the result when handing work back.

## Spec rules

- Specs describe observable behavior, safety boundaries, CLI shape, and failure modes.
- Specs should not require a specific game unless the feature is game-specific.
- Device-touching behavior must have a dry-run or validation path.
- Any new YAML step type must define parser rules, runner behavior, validation behavior, and tests.
- User-test-facing behavior should produce artifacts or logs that make failures diagnosable.

## Test layers

- Parser tests prove YAML turns into typed steps and rejects invalid input.
- Validation tests prove scripts can be checked without ADB.
- Runner tests use fake ADB clients for success and failure cases.
- Manual tests are reserved for BlueStacks, screenshots, and real taps.
- User-test reports belong under `artifacts/` and should not be committed.

## Next-stage SDD focus

- Core APIs must be specified before exposing them to AI tool callers.
- Recorder behavior must be specified before adding interactive commands.
- AI-facing tool specs must include safety defaults, execution flags, report/audit behavior, and tests for blocked unsafe defaults.
