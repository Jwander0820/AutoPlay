# 0017 - Record UI Direct Gesture Authoring

## Why

User testing showed that tap authoring in `record-ui` felt immediate because it happened directly on the screenshot, while `swipe`, `drag`, and part of the gesture flow still depended on filling coordinate fields in the side panel. That made gesture recording slower, less legible, and harder to trust.

This slice makes the screenshot canvas the primary authoring surface for gesture work and smooths a few workflow rough edges in the browser UI.

## Scope

Add direct-manipulation gesture authoring to the shared `click-map` / `record-ui` builder UI:

- Introduce a visible tool mode selector on the stage.
- Support screenshot drag authoring for:
  - `swipe`
  - `drag`
  - `scroll`
  - template crop selection
- Keep tap as direct click authoring.
- Render existing tap and gesture steps back onto the screenshot as visual overlays.
- Add a small workflow polish pass so common actions are easier to discover and undo.

## UX expectations

- The screenshot is the primary recording surface.
- Users pick one tool, then act directly on the screenshot.
- `swipe` and `drag` should be authored by dragging from start to end.
- `scroll` should be authored by dragging in a direction; the UI derives direction and distance.
- Template cropping should be discoverable from the same interaction model instead of feeling like a separate subsystem.
- Side-panel coordinate fields remain available as fallback and for fine-tuning, but they are no longer the main path.
- The timeline and canvas should stay in sync so users can see what was recorded.

## Safety

- Direct gesture authoring still only writes YAML unless the existing explicit device-input mode is enabled.
- Real execution still requires the existing test/run controls and opt-in safety checks.
- No new real-device automation surface is added in this slice.

## Notes

- This does not yet add a gesture + capture loop similar to tap capture.
- This does not calibrate gesture distances against real BlueStacks screens; that remains a follow-up.

## Implementation status

- Implemented: stage tool selector for tap, swipe, drag, scroll, and template crop.
- Implemented: drag-to-author gesture steps directly on the screenshot.
- Implemented: canvas overlays for recorded taps, swipes, drags, scrolls, and back steps.
- Implemented: one-click undo for the last recorded step.
