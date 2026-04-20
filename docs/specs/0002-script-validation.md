# 0002 Script Validation

## Status

Implemented.

## Summary

Scripts must be validatable without BlueStacks or ADB. Validation gives fast feedback before a script can touch a device.

## Behavior

- `py -m autoplay validate <script.yml>` parses and validates a script without touching ADB.
- Empty `steps` lists are invalid.
- Tap coordinates must be non-negative integers.
- Tap steps without labels produce warnings.
- Screenshot outputs should use `.png`; other suffixes produce warnings.
- A `checkpoint_exists` step is valid when its path is created by an earlier screenshot step or already exists on disk.
- `py -m autoplay run` blocks execution when validation has errors.

## Acceptance

- Parser tests reject empty scripts, unknown step types, and negative tap coordinates.
- Validation tests cover clean scripts, warning-only scripts, and checkpoint errors.
- CLI tests prove `validate` returns `0` for valid scripts and `1` for invalid scripts.
