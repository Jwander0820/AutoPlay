# 0015 Checkpoint Authoring Foundation

## Status

Implemented.

## Summary

After mobile gestures, AutoPlay needs better ways to add verification after tap, scroll, swipe, drag, or back actions. This slice keeps the scope small: improve the guided recorder so it can author `checkpoint_match` steps, and clean up gesture helper code so the next template-cropping work has a clearer base.

## Goals

- Let guided recorder users add image checkpoints without hand-editing YAML.
- Keep checkpoint authoring deterministic and reviewable.
- Reduce fresh gesture implementation duplication where it makes the code easier to extend.
- Preserve existing dry-run and validation behavior.

## Recorder Command

Add:

```text
checkpoint_match SOURCE TEMPLATE [THRESHOLD] [TOLERANCE] [REGION_X REGION_Y REGION_WIDTH REGION_HEIGHT]
```

Examples:

```text
checkpoint_match artifacts/manual/after-scroll.png artifacts/templates/quest-row.png
checkpoint_match artifacts/manual/after-scroll.png artifacts/templates/quest-row.png 0.9 8
checkpoint_match artifacts/manual/after-scroll.png artifacts/templates/quest-row.png 0.95 0 100 200 500 300
```

## Validation

- `SOURCE` and `TEMPLATE` are written as YAML strings and resolved by the existing parser.
- `THRESHOLD` must be between `0` and `1`.
- `TOLERANCE` must be an integer from `0` to `255`.
- Region values, when present, must be exactly four integers with non-negative `x/y` and positive `width/height`.
- Existing script validation continues to require an existing template file and either an existing source or earlier screenshot output.

## Implementation Notes

- This does not implement browser template cropping yet.
- This does not add image editing dependencies.
- Gesture helper cleanup should stay internal and not change public CLI/API behavior.

## Acceptance

- Implemented: guided recorder parses and writes `checkpoint_match`.
- Implemented: invalid threshold, tolerance, and region arguments are rejected.
- Implemented: recorder help lists the command.
- Implemented: tests cover new recorder parsing and script validation behavior.
