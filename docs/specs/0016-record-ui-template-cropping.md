# 0016 Record UI Template Cropping

## Status

Implemented.

## Summary

Record UI should let users crop a stable UI element from the current screenshot, save it as a template PNG, and append a `checkpoint_match` step without leaving the browser workflow.

## Goals

- Make visual checkpoint authoring practical after taps and gestures.
- Keep template creation local and deterministic.
- Reuse the current PNG parser/writer path instead of adding image dependencies.
- Preserve dry-run and validation-first behavior.

## Behavior

- `record-ui` exposes a template crop section.
- Users can enter or drag-select crop coordinates on the current screenshot.
- The server saves the crop to a template PNG path.
- On success, the UI updates the template path field and appends:

```yaml
- type: checkpoint_match
  source: <current screenshot path>
  template: <saved template path>
  threshold: <threshold>
```

## Endpoint

`POST /api/template`

Request:

```json
{
  "source": "artifacts/manual/screen.png",
  "template": "artifacts/templates/button.png",
  "x": 100,
  "y": 200,
  "width": 80,
  "height": 40,
  "threshold": 0.95
}
```

Response includes the saved template path and generated steps.

## Validation

- Coordinates must be non-negative integers.
- Width and height must be positive integers.
- Threshold must be between `0` and `1`.
- The source screenshot must be readable as a supported PNG.
- Crop bounds must stay inside the source image.
- Template output should stay under an artifact/template-style path.

## Safety

- Cropping never sends device input.
- Cropping only reads a screenshot and writes a local PNG.
- The generated checkpoint still goes through script validation before execution.

## Acceptance

- Implemented: PNG crop helper writes a valid RGBA PNG.
- Implemented: record-ui serves and handles `/api/template`.
- Implemented: UI can drag-select a crop rectangle and save it as a template.
- Implemented: successful template save appends a `checkpoint_match` step.
- Implemented: tests cover endpoint success and invalid crop handling.
