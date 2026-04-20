# 0003 Template Checkpoint

## Status

Implemented.

## Summary

AutoPlay can verify that a screenshot contains a template image before continuing a script. This gives the runner its first screen-state checkpoint without requiring a real emulator during unit tests.

## Behavior

- YAML supports `checkpoint_match` steps.
- CLI supports `py -m autoplay match <source.png> <template.png>` for tuning templates without ADB.
- Required fields: `source` and `template`.
- Optional fields: `threshold` from `0` to `1`, default `0.95`; `tolerance` from `0` to `255`, default `0`; `region` as `[x, y, width, height]`.
- The source path must either exist on disk or be created by an earlier `screenshot` step.
- The template path must exist before validation passes.
- Runner stops when the best match score is below threshold.
- The current matcher supports non-interlaced 8-bit grayscale, RGB, and RGBA PNG files using the Python standard library.
- The matcher tries an exact row-based search before fuzzy scoring.
- If no exact match is found and the fuzzy search is too large, the matcher stops with guidance instead of running an impractical full-screen search.

## Acceptance

- Parser tests cover defaults, region parsing, and invalid threshold.
- Validation tests cover earlier screenshot source handling and missing template errors.
- Image matching tests cover exact matches, region limits, threshold failure, and invalid PNG files.
- Image matching tests cover large-search fast failure and region-limited fallback.
- CLI tests cover `py -m autoplay match` success and failure exit codes.
- Runner tests cover successful template checkpoints and mismatch failures.
