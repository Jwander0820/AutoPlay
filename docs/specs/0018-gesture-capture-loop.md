# 0018 - Gesture Capture Loop

## Why

After direct screenshot gesture authoring landed, `record-ui` still had an uneven device-mode experience:

- `tap` could execute on the device, wait, capture the next screen, and append the resulting steps.
- `swipe`, `drag`, `scroll`, and `back` could be authored in the UI, but not run through the same recorder loop.

That mismatch made gesture-heavy flows feel half-automated. This slice extends the existing recorder safety model so gestures can use the same execute-and-capture loop as taps.

## Scope

- Add a recorder endpoint for executing a bounded device step, then capturing the next screenshot.
- Support `tap`, `swipe`, `drag`, `scroll`, and `back`.
- Reuse the existing manual wait and auto-wait-until-stable behavior.
- Update the shared browser builder UI so device mode applies to gestures as well as taps.
- Keep script mode unchanged.

## Safety

- This endpoint is only available when `record-ui` is launched with `--allow-device-input`.
- Real device input remains opt-in and bounded to one explicit step per UI action.
- The endpoint only accepts the existing safe step types. No free-form shelling out or arbitrary actions are added.

## UX expectations

- In script mode, clicks and drags only author YAML.
- In device mode, clicks and supported gestures execute immediately, wait, capture the next screen, and append:
  - the original step
  - an optional `wait`
  - a follow-up `screenshot`
- The same wait controls should work for both tap and gesture actions.

## Notes

- This does not yet calibrate gesture distances against real BlueStacks devices.
- This does not add multi-step autonomous loops; it remains one user-confirmed step at a time.

## Implementation status

- Implemented: `/api/device-step-capture` for `tap`, `swipe`, `drag`, `scroll`, and `back`.
- Implemented: shared recorder wait/capture handling for tap and gesture device input.
- Implemented: `record-ui` device mode now applies to direct canvas gestures and quick gesture buttons.
