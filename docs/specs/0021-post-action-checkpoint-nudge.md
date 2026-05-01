# 0021 - Post-Action Checkpoint Nudge

## Status

Implemented as a recorder UI workflow nudge.

## Why

After `record-ui` executes a tap or gesture in device mode, the script usually needs a checkpoint on the resulting screen. Without a prompt, testers can easily record coordinate-only flows that move through screens but do not verify state after the movement.

The goal is not to let AutoPlay infer the correct checkpoint automatically. The goal is to nudge the tester into the existing template-cropping workflow immediately after a real device action and screenshot capture.

## Scope

- Detect device capture payloads that include `tap`, `swipe`, `drag`, `scroll`, or `back`.
- After the captured screenshot is applied, show a short status hint recommending a stable UI template checkpoint.
- When the recorder has a template endpoint, switch the active tool to Template mode so the tester can immediately drag a region.
- Show a visible "next step" strip above the screenshot workspace so the checkpoint prompt is not lost in the status text.
- Let the tester dismiss the next-step strip when a checkpoint is not useful for that screen.
- Keep calibration handoff actionable by offering a copy button for the generated `calibration guide` command.
- Preview the saved template against the source screenshot in the selected region and return the match score.
- Return lightweight quality hints when a template crop is very small, very large, or uses a low threshold.
- Keep the recorder visual style quiet and operational: neutral surfaces, restrained borders, and one action-focused accent.
- Keep desktop controls reachable by making the right-side inspector sticky while the screenshot area scrolls.
- Keep offline `click-map` behavior unchanged when no template endpoint exists.

## Safety

- No automatic template selection.
- No automatic real device input.
- No autonomous decision-making.
- The nudge only changes UI focus after a device action has already been explicitly requested.

## Acceptance

- Implemented: device capture responses with tap/gesture/back actions append a checkpoint hint.
- Implemented: record-ui switches to Template mode only when template saving is available.
- Implemented: record-ui shows a visible next-action strip for the checkpoint workflow.
- Implemented: the next-action strip can be dismissed.
- Implemented: generated calibration guide commands can be copied from the UI.
- Implemented: saved templates include a bounded checkpoint preview and quality messages.
- Implemented: offline click-map remains script-only and does not show a post-action template workflow.
- Implemented: tests verify the rendered UI includes the checkpoint nudge behavior.

## Next

Use real BlueStacks testing to confirm whether this nudge leads testers to create stable `checkpoint_match` steps after movement. If it does, the next slice can add a lightweight checkpoint quality checklist or a dry-run checkpoint preview before saving.
