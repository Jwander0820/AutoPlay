# Stage Report

## 2026-05-06 - Local AI Toolchain Foundation

### Summary

This stage established the first safe local AI automation toolchain for AutoPlay. The project now has a JSON bridge, local HTTP server, machine-readable schemas, canonical examples, a smoke client, guarded real-input consent codes, and an AI-facing `draft_script` tool for writing reviewable YAML before any emulator action.

The preferred local AI flow is now:

```text
User intent -> draft_script -> validate -> dry-run run_script -> human review -> guarded real input
```

### Completed

- Added `src/autoplay/ai_bridge.py` and `py -m autoplay ai-tool` for single JSON tool calls through `AgentSession`.
- Added `src/autoplay/ai_server.py` and `py -m autoplay ai-server` for local HTTP calls: `/health`, `/tools`, `/schemas`, `/examples`, and `/tool`.
- Added `src/autoplay/ai_schemas.py` and `py -m autoplay ai-schemas` for machine-readable tool discovery.
- Added `src/autoplay/ai_examples.py` and `py -m autoplay ai-examples` for safe canonical request examples.
- Added `src/autoplay/ai_client.py` and `py -m autoplay ai-smoke` for end-to-end local AI server smoke testing.
- Added session-only `device_input_code` gating for guarded real device input.
- Added `src/autoplay/ai_script_drafts.py` and `draft_script` so AI clients can write reviewable YAML under `scripts/`, validate immediately, and avoid private `profile.adb_path`.
- Updated `AGENT.md`, `docs/ai-local-automation-plan.md`, and specs `0022` through `0025`.

### Implemented Specs

- `docs/specs/0022-local-ai-tool-interface.md`
- `docs/specs/0023-local-ai-client-examples.md`
- `docs/specs/0024-local-ai-smoke-client.md`
- `docs/specs/0025-ai-draft-script-tool.md`

### Verification

Commands run:

```powershell
$env:PYTHONPATH='src;tests'
& 'D:\venv\AutoPlay\Scripts\python.exe' -m unittest discover -s tests
git diff --check
git diff | Select-String -Pattern '<private-path-or-secret-patterns>' -CaseSensitive:$false
git status --short --ignored config artifacts scripts
```

Latest result:

- 170 unit tests passed before final documentation updates in this stage.
- `git diff --check` reported no whitespace errors.
- The private-path / secret scan returned no matches.
- `config/autoplay.local.json` and `artifacts/` remain ignored.

### Safety Notes

- AI tools call `AgentSession`, not raw ADB.
- Device input remains dry-run unless policy and per-call args both opt in.
- Persistent server real input can require the current `device_input_code`.
- `draft_script` writes only under `scripts/`, rejects non-YAML extensions, rejects overwrite unless requested, and refuses `profile.adb_path`.
- User-specific ADB paths remain in ignored local config, not committed files.

### Recommended Next Step

Add a thin MCP wrapper or local chat integration spike that maps MCP/local tool calls onto the existing JSON bridge. Keep the wrapper thin and preserve the current safety chain:

```text
MCP/local chat -> JSON bridge -> AgentSession -> api.py -> ADB
```

## 2026-05-05 - LDPlayer Compatibility Handoff

### Summary

The project has been checked for the emulator switch from BlueStacks to LDPlayer. The core API does not need a rewrite: AutoPlay sends standard ADB commands for screenshots, taps, swipes, drags, scrolls, and back events. The emulator-specific surface is limited to ADB executable discovery, ADB serial selection, gesture calibration profiles, and the experimental Windows live-click recorder window title.

### Completed

- Added common LDPlayer Windows ADB paths to default ADB discovery while preserving `AUTOPLAY_ADB`, `--adb-path`, and profile overrides.
- Updated doctor output to describe Android emulator/device readiness instead of treating BlueStacks as the only supported target.
- Updated CLI and architecture handoff wording to make LDPlayer an explicit compatible emulator profile.

### LDPlayer Follow-Up

Use a real LDPlayer session to run:

```powershell
py -m autoplay doctor --adb-path <LDPlayer adb.exe path>
py -m autoplay screenshot --out artifacts\manual\ldplayer-start.png --adb-path <LDPlayer adb.exe path> --serial <serial>
py -m autoplay calibration guide --serial <serial> --from-screenshot artifacts\manual\ldplayer-start.png --adb-path <LDPlayer adb.exe path>
```

If LDPlayer is installed somewhere else, set `AUTOPLAY_ADB` to its `adb.exe` path or pass `--adb-path` per command.

## 2026-05-01 - Guided Gesture Calibration

### Summary

This stage moved AutoPlay from manual gesture calibration profiles to a bounded guided calibration workflow. The project can now derive scroll distances from tester feedback, save a reviewable profile, write local calibration notes, and surface the correct guide command inside the recorder UI when serial context is available.

### Completed

- Added `py -m autoplay calibration guide` as a CLI-first calibration workflow.
- Added non-interactive calibration helpers for profile drafting, scroll-distance adjustment, note rendering, and note writing.
- Kept calibration safe by default: dry-run previews only unless `--yes` is passed, and each real scroll still requires an explicit `yes` prompt.
- Added `--max-rounds` to keep each axis bounded during calibration.
- Kept invalid feedback inside the bounded prompt loop instead of aborting calibration.
- Saved calibration notes separately from the executable JSON profile under `artifacts/calibration/`.
- Updated `record-ui` to show the matching `calibration guide` command when launched with `--serial`.
- Added recorder UI warnings when the current screenshot dimensions differ from the loaded calibration profile dimensions.
- Added a post-action checkpoint nudge so device-mode tap/gesture captures switch testers toward Template mode.
- Refined the recorder workspace visual hierarchy with a neutral work-focused palette and a visible next-step strip for checkpoint authoring.
- Added front-end affordances for copying the calibration guide command, dismissing checkpoint prompts, and keeping the inspector reachable on desktop.
- Added template checkpoint preview and quality hints for saved crops.
- Updated user-facing and handoff documentation for the implemented 0020 workflow.

### Verification

Commands run:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
PYTHONPATH=src python3 -m autoplay calibration guide --help
git diff --check
```

Latest result:

- 132 unit tests passed.
- `calibration guide --help` prints the expected CLI options.
- `git diff --check` reports no whitespace errors.

### Safety Notes

- `calibration guide` does not send device input unless launched with `--yes`.
- Even with `--yes`, the guide sends at most one real scroll per confirmation prompt.
- Each axis is capped by `--max-rounds`, defaulting to 6.
- Invalid feedback consumes a bounded round and never triggers device input.
- The profile JSON is written only after final save confirmation.
- Generated calibration JSON and notes remain local under ignored `artifacts/` paths.

### Current Limits

- The guided workflow still needs real BlueStacks validation on Windows PowerShell.
- The record-ui guide command needs manual confirmation with normal paths and space-containing paths.
- Calibration is still serial-based; app orientation or BlueStacks layout-specific profiles are not modeled yet.
- Post-gesture checkpoints still depend on tester-authored templates, but the UI now nudges testers into that workflow with a visible next-step prompt that can be dismissed when inappropriate.
- Template preview currently verifies the selected source region, not future screenshots; real BlueStacks testing still needs to confirm template stability across repeated captures.

### Recommended Next Step

Use a real BlueStacks session to run:

```powershell
py -m autoplay calibration guide --serial emulator-5554 --from-screenshot artifacts\manual\user-test-start.png
py -m autoplay calibration show --serial emulator-5554
py -m autoplay scroll down --calibrated --serial emulator-5554
```

Then record whether the generated profile produces predictable scroll movement in `record-ui` device mode, and whether the template preview warnings catch unstable or overly broad crops. If movement and checkpoints are stable, the next implementation slice should focus on a bounded screenshot/template decision loop.
