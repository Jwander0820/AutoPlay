# User Testing Guide

This guide is for the first real BlueStacks test pass.

## Preflight

1. Open BlueStacks 5.
2. Enable Android Debug Bridge in BlueStacks settings.
3. Run from Windows PowerShell:

```powershell
cd D:\SideProject\AutoPlay
py -m pip install -e ".[dev]"
py -m autoplay doctor
```

## No-device agent smoke test

This confirms the AI-facing automation rail can validate, run, write a report, and write an audit log without touching ADB.

```powershell
py -m autoplay agent-run examples\report-only.yml --report-out artifacts\reports\agent-report-only.json --audit-out artifacts\agent\agent-report-only.jsonl
```

Expected:

- Exit code is `0`.
- Output says `Agent run kept tap steps dry-run.`
- `artifacts\reports\agent-report-only.json` exists.
- `artifacts\agent\agent-report-only.jsonl` exists and contains JSONL audit events.

## Safe smoke test

Use a harmless screen before sending a real tap.

```powershell
py -m autoplay screenshot --out artifacts\manual\screen.png
py -m autoplay tap 100 100
py -m autoplay tap 100 100 --yes
```

The first tap command is dry-run. Only the `--yes` command sends input.

## Guided script authoring

Use `record-ui` when you want a small UI to generate and save a script instead of hand-writing coordinates.

```powershell
py -m autoplay record-ui scripts\user-test-daily.yml --screenshot artifacts\manual\user-test-start.png --capture
```

Open the printed localhost URL in your browser. Click on the screenshot to add tap steps, use the side controls to add waits, screenshots, and checkpoints, then press `Save Script`. The server writes `scripts\user-test-daily.yml` and returns validation messages. Stop it with `Ctrl+C`.

For a natural step-by-step flow without real taps, do this:

1. Click the screenshot to add a tap step.
2. Manually perform that action in BlueStacks if needed.
3. Press `Capture Latest` in the browser.
4. Continue recording from the refreshed screenshot.

If you want the browser recorder to execute each click and refresh automatically, start it with explicit device input permission:

```powershell
py -m autoplay record-ui scripts\user-test-daily.yml --screenshot artifacts\manual\user-test-start.png --capture --allow-device-input
```

Then enable `Execute click, wait, and capture next screen` in the browser. Each screenshot click will send a real tap, wait for the configured wait seconds, capture the next screen, and append the tap/wait/screenshot steps. Use this only on safe screens.

If you already have a screenshot, omit `--capture`:

```powershell
py -m autoplay record-ui scripts\user-test-daily.yml --screenshot artifacts\manual\user-test-start.png
```

Use `click-map` when you want an offline HTML builder that does not start a local server.

To capture the current BlueStacks screen and create a local HTML script builder:

```powershell
py -m autoplay click-map artifacts\manual\user-test-start.png --capture --out artifacts\manual\user-test-builder.html --script-out user-test-daily.yml
```

Open `artifacts\manual\user-test-builder.html` in your browser. Click on the screenshot to add tap steps, use the side controls to add waits, screenshots, and checkpoints, then press `Download Script`. Save or move the downloaded YAML to `scripts\user-test-daily.yml`.

If you already have a screenshot, omit `--capture`:

```powershell
py -m autoplay click-map artifacts\manual\user-test-start.png --out artifacts\manual\user-test-builder.html --script-out user-test-daily.yml
```

The older recorder is still available if you want command-line entry:

```powershell
py -m autoplay record scripts\user-test-daily.yml
```

At the `record>` prompt, try:

```text
screenshot artifacts/manual/user-test-start.png
checkpoint_exists artifacts/manual/user-test-start.png
tap 100 100 safe test tap
wait 0.5
done
```

The recorder only writes YAML. It does not send the tap. After each accepted command, it validates the script and prints the result.

## Experimental live click recording

If you want to try direct click recording from the BlueStacks window, run this from Windows Python, not WSL:

```powershell
py -m autoplay screenshot --out artifacts\manual\live-start.png
py -m autoplay record-clicks scripts\live-test.yml --screenshot artifacts\manual\live-start.png --max-clicks 5
```

Then click inside the BlueStacks window. The command appends tap steps to `scripts\live-test.yml`. It does not send taps.

Important: coordinate mapping is experimental. BlueStacks window borders, sidebars, DPI scaling, and renderer layout can shift coordinates. Always validate and dry-run before real execution:

```powershell
py -m autoplay validate scripts\live-test.yml
py -m autoplay agent-run scripts\live-test.yml --report-out artifacts\reports\live-test-agent-dry-run.json --audit-out artifacts\agent\live-test-agent.jsonl --intent "live click recorder dry run"
```

## Script and agent test

```powershell
py -m autoplay run examples\report-only.yml --report-out artifacts\reports\report-only.json
py -m autoplay validate examples\smoke.yml
py -m autoplay run examples\smoke.yml --report-out artifacts\reports\smoke-dry-run.json
py -m autoplay agent-run examples\smoke.yml --report-out artifacts\reports\smoke-agent-dry-run.json --audit-out artifacts\agent\smoke-agent.jsonl
py -m autoplay run examples\smoke.yml --execute-taps --report-out artifacts\reports\smoke-real.json
```

`report-only.yml` does not touch ADB and is useful for confirming that the CLI can write reports. `agent-run` uses the AI-facing safety session and keeps taps dry-run by default. Only run `--execute-taps` on a safe screen.

For agent-controlled real taps, both flags are required:

```powershell
py -m autoplay agent-run examples\smoke.yml --execute-taps --allow-device-input --report-out artifacts\reports\smoke-agent-real.json --audit-out artifacts\agent\smoke-agent-real.jsonl
```

Do not run this until the dry-run report, screenshots, and audit log look correct.

## Template tuning

After capturing a screenshot, crop a small UI element into a template PNG, then test it:

```powershell
py -m autoplay match artifacts\manual\screen.png artifacts\templates\button.png --threshold 0.95
```

Lower the threshold only when the screenshot changes slightly but the template is still visually correct.

## Personal daily-task dry run

For a first real daily-task test, keep it small:

1. Open BlueStacks to the game screen where the daily task starts.
2. Capture `artifacts\manual\start.png`.
3. Crop one stable button or UI element into `artifacts\templates\<name>.png`.
4. Tune `py -m autoplay match`.
5. Create or edit `scripts\my-daily.yml`.
6. Run:

```powershell
py -m autoplay validate scripts\my-daily.yml
py -m autoplay agent-run scripts\my-daily.yml --report-out artifacts\reports\my-daily-agent-dry-run.json --audit-out artifacts\agent\my-daily-agent.jsonl --intent "daily task dry run"
```

Review the report and audit before trying real taps.

## What to collect

- `py -m autoplay doctor` output.
- The script YAML used for the test.
- The screenshot and template files used by checkpoints.
- Any JSON files written with `--report-out`.
- Any JSONL files written with `--audit-out`.
- A short note about what was visible on screen when a failure happened.

## Safety boundaries during user testing

Do not test purchases, gacha/summons, trading, deletion, chat, PvP, verification-code handling, credential entry, anti-cheat bypass, root/hook/memory modification, or anything involving account risk. Keep the first pass to safe navigation, screenshots, waits, checkpoints, and dry-run taps.
