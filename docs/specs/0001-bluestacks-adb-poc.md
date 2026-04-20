# 0001 BlueStacks ADB POC

## Status

Implemented.

## Summary

The first milestone proves AutoPlay can control BlueStacks through ADB from a Python CLI while keeping tap execution explicit and reviewable.

## Behavior

- `py -m autoplay doctor` checks host details, ADB path resolution, and `adb devices -l`.
- `py -m autoplay screenshot --out <path>` writes a PNG from `exec-out screencap -p`.
- `py -m autoplay tap <x> <y>` is dry-run by default and requires `--yes` to send input.
- `py -m autoplay run <script.yml>` executes YAML scripts, with tap steps dry-run unless `--execute-taps` is passed.

## Acceptance

- Unit tests cover command building, serial handling, dry-run taps, path resolution, YAML parsing, and runner failure paths.
- Manual verification on Windows should run `py -m autoplay doctor`, then `py -m autoplay screenshot`, then a safe `py -m autoplay tap ... --yes`.
