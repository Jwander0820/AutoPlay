# Personal Script Workflow

This is the current practical path for creating a personalized daily-task script. Full human-demonstration recording is not implemented yet, so the current workflow is semi-manual: capture screenshots, crop templates, write YAML, validate, dry-run, then carefully execute.

## What a script does

An AutoPlay YAML script describes repeatable device actions and checkpoints:

- `screenshot`: capture the current BlueStacks screen.
- `checkpoint_exists`: confirm a screenshot file exists.
- `checkpoint_match`: confirm a screenshot contains a template image.
- `wait`: pause for a fixed number of seconds.
- `tap`: tap a coordinate; it is dry-run unless execution uses `--execute-taps`.

## Folder layout

Use one folder per game or flow under `artifacts/` while testing:

```text
artifacts/
  manual/
    screen.png
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

Create a script file such as `scripts\my-daily.yml`:

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

## Step 5: Validate and dry-run

```powershell
py -m autoplay validate scripts\my-daily.yml
py -m autoplay run scripts\my-daily.yml --report-out artifacts\reports\my-daily-dry-run.json
```

Dry-run mode captures screenshots and checks templates, but tap steps do not touch the device.

## Step 6: Execute carefully

Only run this on a safe screen:

```powershell
py -m autoplay run scripts\my-daily.yml --execute-taps --report-out artifacts\reports\my-daily-real.json
```

If anything fails, keep the report JSON and the screenshots. Those become the input for the next script revision.

## What is not automatic yet

AutoPlay does not yet record your clicks and generate YAML automatically. The planned next stage is a recorder that can help produce scripts from a guided manual run.

AI can help draft and revise YAML from screenshots and reports, but the current runtime is still deterministic: validate, screenshot, checkpoint, wait, and tap. That is intentional for user testing because it keeps each action reviewable.

Until then, the personalization loop is:

1. Screenshot the screen.
2. Crop stable templates.
3. Test templates with `py -m autoplay match`.
4. Write or edit YAML.
5. Validate and dry-run.
6. Execute with `--execute-taps` only when safe.
