from __future__ import annotations

import base64
import html
import json
from dataclasses import dataclass
from pathlib import Path

from . import api
from .adb import AdbResult


@dataclass(frozen=True)
class ClickMapReport:
    screenshot_path: Path
    html_path: Path
    script_path: Path | None = None
    screenshot_result: AdbResult | None = None


def write_click_map(screenshot_path: str | Path, html_path: str | Path, script_path: str | Path | None = None) -> ClickMapReport:
    screenshot = Path(screenshot_path)
    out = Path(html_path)
    script = Path(script_path) if script_path is not None else None
    image_bytes = screenshot.read_bytes()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_builder_html(screenshot, image_bytes, script), encoding="utf-8")
    return ClickMapReport(screenshot_path=screenshot, html_path=out, script_path=script)


def capture_click_map(
    screenshot_path: str | Path,
    html_path: str | Path,
    script_path: str | Path | None = None,
    adb_path: str | None = None,
    serial: str | None = None,
) -> ClickMapReport:
    screenshot = Path(screenshot_path)
    result = api.screenshot(screenshot, adb_path=adb_path, serial=serial)
    if not result.ok:
        return ClickMapReport(screenshot_path=screenshot, html_path=Path(html_path), script_path=Path(script_path) if script_path else None, screenshot_result=result)
    report = write_click_map(screenshot, html_path, script_path=script_path)
    return ClickMapReport(screenshot_path=report.screenshot_path, html_path=report.html_path, script_path=report.script_path, screenshot_result=result)


def render_builder_html(
    screenshot_path: Path,
    image_bytes: bytes,
    script_path: Path | None,
    save_url: str | None = None,
    capture_url: str | None = None,
    tap_capture_url: str | None = None,
    allow_device_input: bool = False,
) -> str:
    encoded_image = base64.b64encode(image_bytes).decode("ascii")
    title = html.escape(screenshot_path.name)
    screenshot_value = json.dumps(screenshot_path.as_posix())
    script_filename = json.dumps((script_path.name if script_path is not None else f"{screenshot_path.stem}.yml"))
    save_url_value = json.dumps(save_url)
    capture_url_value = json.dumps(capture_url)
    tap_capture_url_value = json.dumps(tap_capture_url)
    allow_device_input_value = json.dumps(allow_device_input)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AutoPlay Script Builder - {title}</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Arial, sans-serif;
      background: #f6f7f5;
      color: #1e2528;
    }}
    header {{
      padding: 16px 20px;
      border-bottom: 1px solid #d7d9d2;
      background: #ffffff;
      position: sticky;
      top: 0;
      z-index: 2;
    }}
    h1 {{
      font-size: 18px;
      margin: 0 0 8px;
      font-weight: 700;
    }}
    .controls {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
    }}
    label {{
      font-size: 13px;
      color: #455056;
    }}
    input {{
      width: min(360px, 70vw);
      padding: 8px 10px;
      border: 1px solid #b7bcb6;
      border-radius: 4px;
      font: inherit;
    }}
    button {{
      padding: 8px 10px;
      border: 1px solid #7e8c86;
      border-radius: 4px;
      background: #ffffff;
      color: #1e2528;
      font: inherit;
      cursor: pointer;
    }}
    button:hover {{ background: #eef4f1; }}
    main {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(360px, 460px);
      gap: 16px;
      padding: 16px;
    }}
    .image-wrap {{
      position: relative;
      width: 100%;
      overflow: auto;
      border: 1px solid #cfd3cc;
      background: #ffffff;
    }}
    #screen {{
      display: block;
      max-width: 100%;
      height: auto;
      cursor: crosshair;
    }}
    .marker {{
      position: absolute;
      width: 18px;
      height: 18px;
      border: 2px solid #e3262e;
      border-radius: 50%;
      transform: translate(-50%, -50%);
      pointer-events: none;
    }}
    .marker span {{
      position: absolute;
      left: 14px;
      top: -8px;
      min-width: 18px;
      height: 18px;
      padding: 1px 5px;
      background: #e3262e;
      color: #ffffff;
      border-radius: 9px;
      font-size: 12px;
      line-height: 16px;
      font-weight: 700;
    }}
    aside {{
      min-width: 0;
    }}
    textarea {{
      width: 100%;
      min-height: 160px;
      resize: vertical;
      border: 1px solid #b7bcb6;
      border-radius: 4px;
      padding: 10px;
      font: 13px Consolas, monospace;
      background: #ffffff;
    }}
    .panel {{
      margin-bottom: 14px;
    }}
    .panel h2 {{
      font-size: 14px;
      margin: 0 0 8px;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      background: #ffffff;
      border: 1px solid #cfd3cc;
      font-size: 13px;
    }}
    th, td {{
      padding: 6px;
      border-bottom: 1px solid #e4e6e0;
      text-align: left;
      vertical-align: top;
    }}
    th {{ background: #eef1ec; }}
    .step-actions {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
      margin-bottom: 10px;
    }}
    .step-actions input {{
      width: 100%;
    }}
    .wide {{
      grid-column: 1 / -1;
    }}
    .muted {{
      color: #5d686d;
      font-size: 13px;
      margin: 0 0 10px;
    }}
    .danger {{
      color: #8d1c22;
    }}
    @media (max-width: 900px) {{
      main {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>AutoPlay Script Builder: {title}</h1>
    <div class="controls">
      <label for="label">Label</label>
      <input id="label" value="safe test tap" aria-label="Tap label">
      <button id="clear" type="button">Clear</button>
      <button id="saveScript" type="button">Save Script</button>
      <button id="captureLatest" type="button">Capture Latest</button>
      <button id="downloadScript" type="button">Download Script</button>
      <button id="copyYaml" type="button">Copy Script</button>
      <span id="status" aria-live="polite"></span>
    </div>
  </header>
  <main>
    <section class="image-wrap" id="imageWrap">
      <img id="screen" alt="Captured screen" src="data:image/png;base64,{encoded_image}">
    </section>
    <aside>
      <section class="panel">
        <h2>Build Steps</h2>
        <p class="muted">Click the screenshot to add a tap step. Add waits and checkpoints here, then save or download the complete YAML script.</p>
        <div class="step-actions">
          <label class="wide"><input id="executeClicks" type="checkbox"> Execute click, wait, and capture next screen</label>
          <label>Wait seconds <input id="waitSeconds" value="1"></label>
          <button id="addWait" type="button">Add Wait</button>
          <label class="wide">Screenshot path <input id="screenshotPath" value="artifacts/manual/after-step.png"></label>
          <button id="addScreenshot" type="button" class="wide">Add Screenshot Step</button>
          <label class="wide">Checkpoint path <input id="checkpointPath" value="{html.escape(screenshot_path.as_posix())}"></label>
          <button id="addCheckpoint" type="button" class="wide">Add Checkpoint Exists</button>
          <label class="wide">Template path <input id="templatePath" value="artifacts/templates/button.png"></label>
          <label>Threshold <input id="threshold" value="0.95"></label>
          <button id="addMatch" type="button">Add Match</button>
        </div>
      </section>
      <section class="panel">
        <h2>Script Steps</h2>
        <table>
          <thead><tr><th>#</th><th>Type</th><th>Detail</th><th></th></tr></thead>
          <tbody id="stepRows"></tbody>
        </table>
      </section>
      <section class="panel">
        <h2>Recorder Commands</h2>
        <textarea id="commands" readonly></textarea>
      </section>
      <section class="panel">
        <h2>Complete YAML Script</h2>
        <textarea id="yaml" readonly></textarea>
      </section>
    </aside>
  </main>
  <script>
    const initialScreenshotPath = {screenshot_value};
    const scriptFilename = {script_filename};
    const saveUrl = {save_url_value};
    const captureUrl = {capture_url_value};
    const tapCaptureUrl = {tap_capture_url_value};
    const allowDeviceInput = {allow_device_input_value};
    const steps = [{{ type: 'screenshot', out: initialScreenshotPath }}];
    const image = document.getElementById('screen');
    const wrap = document.getElementById('imageWrap');
    const label = document.getElementById('label');
    const rows = document.getElementById('stepRows');
    const commands = document.getElementById('commands');
    const yaml = document.getElementById('yaml');
    const status = document.getElementById('status');
    const saveButton = document.getElementById('saveScript');
    const captureButton = document.getElementById('captureLatest');
    const executeClicks = document.getElementById('executeClicks');

    if (!saveUrl) {{
      saveButton.hidden = true;
    }}
    if (!captureUrl) {{
      captureButton.hidden = true;
    }}
    if (!allowDeviceInput || !tapCaptureUrl) {{
      executeClicks.checked = false;
      executeClicks.disabled = true;
      executeClicks.parentElement.classList.add('muted');
    }}

    image.addEventListener('click', async (event) => {{
      const rect = image.getBoundingClientRect();
      const x = Math.round((event.clientX - rect.left) * image.naturalWidth / rect.width);
      const y = Math.round((event.clientY - rect.top) * image.naturalHeight / rect.height);
      if (executeClicks.checked && tapCaptureUrl) {{
        await tapCapture(x, y);
        return;
      }}
      steps.push({{ type: 'tap', x, y, label: label.value || 'tap' }});
      render();
    }});

    document.getElementById('clear').addEventListener('click', () => {{
      steps.length = 0;
      steps.push({{ type: 'screenshot', out: initialScreenshotPath }});
      render();
    }});

    document.getElementById('addWait').addEventListener('click', () => {{
      const seconds = Number(document.getElementById('waitSeconds').value);
      if (!Number.isFinite(seconds) || seconds < 0) return alert('Wait seconds must be a non-negative number.');
      steps.push({{ type: 'wait', seconds }});
      render();
    }});

    document.getElementById('addScreenshot').addEventListener('click', () => {{
      const out = document.getElementById('screenshotPath').value.trim();
      if (!out) return alert('Screenshot path is required.');
      steps.push({{ type: 'screenshot', out }});
      document.getElementById('checkpointPath').value = out;
      render();
    }});

    document.getElementById('addCheckpoint').addEventListener('click', () => {{
      const path = document.getElementById('checkpointPath').value.trim();
      if (!path) return alert('Checkpoint path is required.');
      steps.push({{ type: 'checkpoint_exists', path }});
      render();
    }});

    document.getElementById('addMatch').addEventListener('click', () => {{
      const source = document.getElementById('checkpointPath').value.trim();
      const template = document.getElementById('templatePath').value.trim();
      const threshold = Number(document.getElementById('threshold').value);
      if (!source || !template) return alert('Source and template paths are required.');
      if (!Number.isFinite(threshold) || threshold < 0 || threshold > 1) return alert('Threshold must be between 0 and 1.');
      steps.push({{ type: 'checkpoint_match', source, template, threshold }});
      render();
    }});

    document.getElementById('copyYaml').addEventListener('click', () => navigator.clipboard.writeText(yaml.value));
    captureButton.addEventListener('click', async () => {{
      if (!captureUrl) return;
      status.textContent = 'Capturing...';
      try {{
        const payload = await postJson(captureUrl, {{}});
        applyCapturePayload(payload, true);
      }} catch (error) {{
        status.textContent = `Capture failed: ${{error}}`;
        status.className = 'danger';
      }}
    }});
    saveButton.addEventListener('click', async () => {{
      if (!saveUrl) return;
      status.textContent = 'Saving...';
      try {{
        const payload = await postJson(saveUrl, {{ yaml: yaml.value }});
        status.textContent = payload.messages ? payload.messages.join(' ') : payload.status;
        status.className = payload.ok ? '' : 'danger';
      }} catch (error) {{
        status.textContent = `Save failed: ${{error}}`;
        status.className = 'danger';
      }}
    }});
    document.getElementById('downloadScript').addEventListener('click', () => {{
      const blob = new Blob([yaml.value], {{ type: 'application/x-yaml' }});
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = scriptFilename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    }});

    function render() {{
      rows.replaceChildren();
      wrap.querySelectorAll('.marker').forEach(marker => marker.remove());
      commands.value = steps.map(stepToCommand).filter(Boolean).join('\\n');
      yaml.value = 'steps:\\n' + steps.map(stepToYaml).join('\\n');

      steps.forEach((step, index) => {{
        const tr = document.createElement('tr');
        const remove = index === 0 ? '' : `<button type="button" data-remove="${{index}}">Remove</button>`;
        tr.innerHTML = `<td>${{index + 1}}</td><td>${{escapeHtml(step.type)}}</td><td>${{escapeHtml(stepDetail(step))}}</td><td>${{remove}}</td>`;
        rows.appendChild(tr);
        if (step.type !== 'tap') return;
        const marker = document.createElement('div');
        marker.className = 'marker';
        marker.style.left = `${{step.x / image.naturalWidth * image.clientWidth}}px`;
        marker.style.top = `${{step.y / image.naturalHeight * image.clientHeight}}px`;
        marker.innerHTML = `<span>${{index + 1}}</span>`;
        wrap.appendChild(marker);
      }});
      rows.querySelectorAll('button[data-remove]').forEach(button => {{
        button.addEventListener('click', () => {{
          steps.splice(Number(button.dataset.remove), 1);
          render();
        }});
      }});
    }}

    async function tapCapture(x, y) {{
      status.textContent = 'Tapping and capturing...';
      try {{
        const payload = await postJson(tapCaptureUrl, {{
          x,
          y,
          label: label.value || 'tap',
          wait_seconds: Number(document.getElementById('waitSeconds').value || 0)
        }});
        applyCapturePayload(payload, false);
      }} catch (error) {{
        status.textContent = `Tap and capture failed: ${{error}}`;
        status.className = 'danger';
      }}
    }}

    async function postJson(url, payload) {{
      const response = await fetch(url, {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify(payload)
      }});
      const data = await response.json();
      if (!response.ok || !data.ok) {{
        throw new Error(data.messages ? data.messages.join(' ') : response.statusText);
      }}
      return data;
    }}

    function applyCapturePayload(payload, appendSteps) {{
      image.src = payload.image_data_url;
      if (appendSteps !== false) {{
        payload.steps.forEach(step => steps.push(step));
      }} else {{
        payload.steps.forEach(step => steps.push(step));
      }}
      if (payload.screenshot_path) {{
        document.getElementById('checkpointPath').value = payload.screenshot_path;
        document.getElementById('screenshotPath').value = nextSuggestedPath(payload.screenshot_path);
      }}
      status.textContent = payload.messages ? payload.messages.join(' ') : payload.status;
      status.className = '';
      render();
    }}

    function nextSuggestedPath(path) {{
      const dot = path.lastIndexOf('.');
      if (dot === -1) return `${{path}}-next.png`;
      return `${{path.slice(0, dot)}}-next${{path.slice(dot)}}`;
    }}

    function stepDetail(step) {{
      if (step.type === 'tap') return `${{step.x}},${{step.y}} - ${{step.label}}`;
      if (step.type === 'wait') return `${{step.seconds}}s`;
      if (step.type === 'screenshot') return step.out;
      if (step.type === 'checkpoint_exists') return step.path;
      if (step.type === 'checkpoint_match') return `${{step.source}} -> ${{step.template}} @ ${{step.threshold}}`;
      return '';
    }}

    function stepToCommand(step) {{
      if (step.type === 'tap') return `tap ${{step.x}} ${{step.y}} ${{step.label}}`;
      if (step.type === 'wait') return `wait ${{step.seconds}}`;
      if (step.type === 'screenshot') return `screenshot ${{step.out}}`;
      if (step.type === 'checkpoint_exists') return `checkpoint_exists ${{step.path}}`;
      if (step.type === 'checkpoint_match') return `# checkpoint_match is included in YAML output`;
      return '';
    }}

    function stepToYaml(step) {{
      if (step.type === 'tap') return [
        '  - type: tap',
        `    x: ${{step.x}}`,
        `    y: ${{step.y}}`,
        `    label: ${{yamlString(step.label)}}`
      ].join('\\n');
      if (step.type === 'wait') return ['  - type: wait', `    seconds: ${{step.seconds}}`].join('\\n');
      if (step.type === 'screenshot') return ['  - type: screenshot', `    out: ${{yamlString(step.out)}}`].join('\\n');
      if (step.type === 'checkpoint_exists') return ['  - type: checkpoint_exists', `    path: ${{yamlString(step.path)}}`].join('\\n');
      if (step.type === 'checkpoint_match') return [
        '  - type: checkpoint_match',
        `    source: ${{yamlString(step.source)}}`,
        `    template: ${{yamlString(step.template)}}`,
        `    threshold: ${{step.threshold}}`
      ].join('\\n');
      return '';
    }}

    function yamlString(value) {{
      return JSON.stringify(String(value));
    }}

    function escapeHtml(value) {{
      return String(value).replace(/[&<>"']/g, char => ({{ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }}[char]));
    }}

    render();
  </script>
</body>
</html>
"""
