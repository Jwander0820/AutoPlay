# Personal Script Workflow

This is the current practical path for creating a personalized daily-task script. The workflow is still intentionally reviewable: capture screenshots, crop templates, use the guided recorder or edit YAML, validate, agent dry-run, then carefully execute.

## What a script does

An AutoPlay YAML script describes repeatable device actions and checkpoints:

- `screenshot`: capture the current BlueStacks screen.
- `checkpoint_exists`: confirm a screenshot file exists.
- `checkpoint_match`: confirm a screenshot contains a template image.
- `wait`: pause for a fixed number of seconds.
- `tap`: tap a coordinate; it is dry-run unless execution uses `--execute-taps`.
- `agent-run`: run a script through the AI-facing safety session, producing both a report and an audit log.

## Folder layout

Use one folder per game or flow under `artifacts/` while testing:

```text
artifacts/
  manual/
    screen.png
    start-builder.html
  templates/
    daily-button.png
  reports/
    my-daily-dry-run.json
scripts/
  my-daily.yml
```

`artifacts/` is ignored by git, so screenshots and reports stay local.

## Step 1: Capture a baseline screenshot

Open BlueStacks to the screen where your daily task starts, then run:

```powershell
py -m autoplay screenshot --out artifacts\manual\start.png
```

Open the image and identify one stable UI element, such as a daily mission button or claim button.

For the most convenient flow, start the local recorder UI. It captures or loads a screenshot, lets you click steps in the browser, and saves directly to your script path:

```powershell
py -m autoplay record-ui scripts\my-daily.yml --screenshot artifacts\manual\start.png --capture
```

Open the printed localhost URL. Click the screenshot to add tap steps, add waits/checkpoints from the side controls, then press `Save Script`. The UI saves `scripts\my-daily.yml` and shows validation messages.

For multi-screen flows, use `Capture Latest` after the game changes screens. The recorder saves numbered screenshots such as `start-001.png` and adds screenshot steps to the script.

If you want the recorder to perform a safe tap and refresh automatically, launch it with:

```powershell
py -m autoplay record-ui scripts\my-daily.yml --screenshot artifacts\manual\start.png --capture --allow-device-input
```

Then enable `Execute click, wait, and capture next screen` in the browser. Each click sends a real tap, waits, captures the next screen, and appends the generated steps. Keep the wait value long enough for animations or loading screens.

If you prefer a standalone HTML file with no local server, generate an offline builder:

```powershell
py -m autoplay click-map artifacts\manual\start.png --capture --out artifacts\manual\start-builder.html --script-out my-daily.yml
```

Open `artifacts\manual\start-builder.html` in your browser. Click the screenshot to add tap steps. Use the side controls to add waits, screenshots, `checkpoint_exists`, or `checkpoint_match`, then press `Download Script`. Save or move the downloaded YAML to `scripts\my-daily.yml`.

There is also an experimental Windows-only live click recorder:

```powershell
py -m autoplay screenshot --out artifacts\manual\live-start.png
py -m autoplay record-clicks scripts\my-daily.yml --screenshot artifacts\manual\live-start.png --max-clicks 10
```

Click inside the BlueStacks window to append tap steps directly. This only writes YAML and never sends taps. Treat the coordinates as approximate until you validate and dry-run, because BlueStacks window chrome and DPI scaling can affect mapping.

## Step 2: Create a template image

Crop a small, stable part of the UI into a PNG file, for example:

```text
artifacts\templates\daily-button.png
```

Good templates are small and unique. Avoid animated areas, countdown numbers, currency values, or notification badges.

## Step 3: Test the template

```powershell
py -m autoplay match artifacts\manual\start.png artifacts\templates\daily-button.png --threshold 0.95
```

Expected success output looks like:

```text
score=1.000 matched=true location=320,540
```

If it fails, crop a more unique template or lower the threshold slightly, for example `--threshold 0.90`.

Full-screen matching on high-resolution screenshots can be slow. Prefer a small template and limit the search area when you roughly know where the button should appear:

```powershell
py -m autoplay match artifacts\manual\start.png artifacts\templates\daily-button.png --threshold 0.95 --region 250 400 500 300
```

The region means `x y width height`. For example, `250 400 500 300` searches a 500x300 rectangle starting at coordinate `(250, 400)`.

The built-in matcher first tries a fast exact match. If no exact match is found and the fuzzy search would be too large, it stops with guidance instead of hanging. For now, AI-driven automation should use screenshots, coordinates, and small template checkpoints rather than full-screen fuzzy matching.

## Step 4: Write the first YAML script

Create a script file such as `scripts\my-daily.yml`, either manually or with:

```powershell
py -m autoplay record scripts\my-daily.yml
```

The recorder appends steps and validates after each append. It never sends tap input.

Example YAML:

```yaml
steps:
  - type: screenshot
    out: artifacts/manual/start.png

  - type: checkpoint_match
    source: artifacts/manual/start.png
    template: artifacts/templates/daily-button.png
    threshold: 0.95

  - type: tap
    x: 320
    y: 540
    label: open daily mission

  - type: wait
    seconds: 1

  - type: screenshot
    out: artifacts/manual/after-open.png
```

The `x` and `y` values are screen coordinates. Use the match location as a clue, then adjust to the center of the button.

The easiest way to generate those coordinates and the surrounding YAML is the recorder UI:

```powershell
py -m autoplay record-ui scripts\my-daily.yml --screenshot artifacts\manual\start.png
```

## Step 5: Validate and dry-run

```powershell
py -m autoplay validate scripts\my-daily.yml
py -m autoplay run scripts\my-daily.yml --report-out artifacts\reports\my-daily-dry-run.json
py -m autoplay agent-run scripts\my-daily.yml --report-out artifacts\reports\my-daily-agent-dry-run.json --audit-out artifacts\agent\my-daily-agent.jsonl --intent "daily task dry run"
```

Dry-run mode captures screenshots and checks templates, but tap steps do not touch the device. `agent-run` also records a JSONL audit trail, which is the path future AI automation will use.

## Step 6: Execute carefully

Only run this on a safe screen:

```powershell
py -m autoplay run scripts\my-daily.yml --execute-taps --report-out artifacts\reports\my-daily-real.json
```

The AI-facing path requires both execution flags:

```powershell
py -m autoplay agent-run scripts\my-daily.yml --execute-taps --allow-device-input --report-out artifacts\reports\my-daily-agent-real.json --audit-out artifacts\agent\my-daily-agent-real.jsonl --intent "daily task reviewed real run"
```

If anything fails, keep the report JSON and the screenshots. Those become the input for the next script revision.

## What is not automatic yet

AutoPlay does not yet make decisions from the game screen by itself. The planned next stage is an agent decision loop that uses screenshots, template matches, and the safety session to choose the next safe step in dry-run/report mode.

AI can help draft and revise YAML from screenshots and reports, but the current runtime is still deterministic: validate, screenshot, checkpoint, wait, and tap. That is intentional for user testing because it keeps each action reviewable.

Until then, the personalization loop is:

1. Screenshot the screen.
2. Crop stable templates.
3. Test templates with `py -m autoplay match`.
4. Write or edit YAML.
5. Validate and dry-run.
6. Execute with `--execute-taps` only when safe.
