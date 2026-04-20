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

## Safe smoke test

Use a harmless screen before sending a real tap.

```powershell
py -m autoplay screenshot --out artifacts\manual\screen.png
py -m autoplay tap 100 100
py -m autoplay tap 100 100 --yes
```

The first tap command is dry-run. Only the `--yes` command sends input.

## Script test

```powershell
py -m autoplay run examples\report-only.yml --report-out artifacts\reports\report-only.json
py -m autoplay validate examples\smoke.yml
py -m autoplay run examples\smoke.yml --report-out artifacts\reports\smoke-dry-run.json
py -m autoplay run examples\smoke.yml --execute-taps --report-out artifacts\reports\smoke-real.json
```

`report-only.yml` does not touch ADB and is useful for confirming that the CLI can write reports. Only run `--execute-taps` on a safe screen.

## Template tuning

After capturing a screenshot, crop a small UI element into a template PNG, then test it:

```powershell
py -m autoplay match artifacts\manual\screen.png artifacts\templates\button.png --threshold 0.95
```

Lower the threshold only when the screenshot changes slightly but the template is still visually correct.

## What to collect

- `py -m autoplay doctor` output.
- The script YAML used for the test.
- The screenshot and template files used by checkpoints.
- Any JSON files written with `--report-out`.
- A short note about what was visible on screen when a failure happened.
