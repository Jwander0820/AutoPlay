# 0011 Live Click Recorder

## Status

Experimental.

## Summary

AutoPlay includes an experimental Windows-only live click recorder. It listens for mouse clicks inside a BlueStacks window and appends tap steps to a YAML script.

## Behavior

- `py -m autoplay record-clicks <script.yml>` installs a low-level Windows mouse hook.
- The command only records clicks from a window whose title contains `BlueStacks` by default.
- `--window-title TEXT` changes the target title filter.
- `--screenshot PATH` uses a screenshot's dimensions to scale window client coordinates into ADB tap coordinates.
- `--label-prefix TEXT` controls generated tap labels.
- `--max-clicks N` stops automatically after N recorded clicks; otherwise use `Ctrl+C`.
- Each click appends a YAML tap step immediately.

## Safety

- `record-clicks` only writes YAML.
- It never sends tap input.
- It is Windows-only and must be run from Windows Python, not WSL/Linux Python.
- Coordinates are experimental because BlueStacks chrome, sidebars, DPI scaling, and renderer layout can affect the mapping between window coordinates and Android screenshot coordinates.

## Acceptance

- Tests cover coordinate scaling, outside-click filtering, YAML append behavior, non-Windows rejection, and CLI wiring.
