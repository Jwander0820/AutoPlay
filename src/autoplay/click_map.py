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
    run_url: str | None = None,
    allow_device_input: bool = False,
    profile_adb_path: str | None = None,
    profile_serial: str | None = None,
) -> str:
    encoded_image = base64.b64encode(image_bytes).decode("ascii")
    title = html.escape(screenshot_path.name)
    screenshot_value = json.dumps(screenshot_path.as_posix())
    script_filename = json.dumps((script_path.name if script_path is not None else f"{screenshot_path.stem}.yml"))
    save_url_value = json.dumps(save_url)
    capture_url_value = json.dumps(capture_url)
    tap_capture_url_value = json.dumps(tap_capture_url)
    run_url_value = json.dumps(run_url)
    allow_device_input_value = json.dumps(allow_device_input)
    profile_value = json.dumps({"adb_path": profile_adb_path, "serial": profile_serial})
    template = """<!doctype html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AutoPlay 錄製工作台 - __TITLE__</title>
  <style>
    :root {
      --bg: #f6f4ef;
      --surface: #fffdfa;
      --surface-2: #eef5f2;
      --ink: #172126;
      --muted: #66727a;
      --line: #d8ddd7;
      --accent: #0f7b68;
      --accent-strong: #075f50;
      --danger: #a8323a;
      --warn: #9a651a;
      --shadow: 0 14px 40px rgba(20, 31, 35, 0.08);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans TC", sans-serif;
      background: var(--bg);
      color: var(--ink);
    }
    .topbar {
      position: sticky;
      top: 0;
      z-index: 5;
      display: grid;
      grid-template-columns: minmax(260px, 1fr) auto;
      gap: 16px;
      align-items: center;
      padding: 14px 18px;
      border-bottom: 1px solid var(--line);
      background: rgba(255, 253, 250, 0.96);
      backdrop-filter: blur(14px);
    }
    .eyebrow {
      margin: 0 0 3px;
      color: var(--accent);
      font-size: 12px;
      font-weight: 800;
      letter-spacing: 0;
    }
    h1 {
      margin: 0;
      font-size: 21px;
      line-height: 1.2;
    }
    .subtitle {
      margin: 6px 0 0;
      color: var(--muted);
      font-size: 13px;
      line-height: 1.5;
    }
    .toolbar {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
      justify-content: flex-end;
    }
    button, input {
      font: inherit;
    }
    button {
      min-height: 36px;
      padding: 8px 11px;
      border: 1px solid var(--line);
      border-radius: 7px;
      background: var(--surface);
      color: var(--ink);
      cursor: pointer;
      transition: background 140ms ease, border-color 140ms ease, transform 140ms ease;
    }
    button:hover {
      border-color: #abc6bd;
      background: #f2faf7;
    }
    button:active {
      transform: translateY(1px);
    }
    button.primary {
      border-color: var(--accent);
      background: var(--accent);
      color: #ffffff;
    }
    button.primary:hover {
      background: var(--accent-strong);
    }
    button.ghost {
      background: transparent;
    }
    button[disabled] {
      cursor: not-allowed;
      opacity: 0.5;
    }
    label, .field-title {
      font-size: 13px;
      color: #34434a;
      font-weight: 650;
    }
    input {
      width: 100%;
      min-height: 36px;
      padding: 8px 10px;
      border: 1px solid var(--line);
      border-radius: 7px;
      background: #ffffff;
      color: var(--ink);
    }
    input:focus, textarea:focus {
      outline: 2px solid rgba(15, 123, 104, 0.18);
      border-color: var(--accent);
    }
    .workspace {
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(380px, 460px);
      gap: 18px;
      padding: 18px;
      align-items: start;
    }
    .stage, .inspector {
      min-width: 0;
    }
    .stage-head, .panel-head {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: flex-end;
      margin-bottom: 10px;
    }
    .stage-title, .panel-title {
      margin: 0;
      font-size: 15px;
      line-height: 1.3;
    }
    .path {
      color: var(--muted);
      font-size: 12px;
      word-break: break-all;
    }
    .screen-shell {
      position: relative;
      width: 100%;
      overflow: hidden;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #11181b;
      box-shadow: var(--shadow);
    }
    .image-wrap {
      position: relative;
      width: 100%;
      max-height: calc(100svh - 170px);
      overflow: auto;
    }
    #screen {
      display: block;
      max-width: 100%;
      height: auto;
      margin: 0 auto;
      cursor: crosshair;
      user-select: none;
    }
    .marker {
      position: absolute;
      width: 20px;
      height: 20px;
      border: 2px solid #ffcf5a;
      border-radius: 50%;
      transform: translate(-50%, -50%);
      pointer-events: none;
      box-shadow: 0 0 0 4px rgba(255, 207, 90, 0.22);
    }
    .marker span {
      position: absolute;
      left: 15px;
      top: -10px;
      min-width: 20px;
      height: 20px;
      padding: 1px 6px;
      background: #172126;
      color: #ffcf5a;
      border-radius: 999px;
      font-size: 12px;
      line-height: 18px;
      font-weight: 800;
      text-align: center;
    }
    .inspector {
      display: grid;
      gap: 14px;
    }
    .panel {
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--surface);
      padding: 14px;
      box-shadow: 0 8px 24px rgba(20, 31, 35, 0.05);
    }
    .hint {
      margin: 6px 0 0;
      color: var(--muted);
      font-size: 13px;
      line-height: 1.5;
    }
    .grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
      align-items: end;
    }
    .wide {
      grid-column: 1 / -1;
    }
    .segmented {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 4px;
      padding: 4px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #f3f6f3;
    }
    .segmented button {
      min-height: 34px;
      border-color: transparent;
      background: transparent;
    }
    .segmented button.active {
      border-color: var(--accent);
      background: #ffffff;
      color: var(--accent-strong);
      box-shadow: 0 2px 8px rgba(15, 123, 104, 0.12);
    }
    .toggle-line {
      display: flex;
      gap: 8px;
      align-items: flex-start;
      color: #34434a;
      font-size: 13px;
      line-height: 1.45;
    }
    .toggle-line input {
      width: auto;
      min-height: auto;
      margin-top: 3px;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
    }
    th, td {
      padding: 8px 6px;
      border-bottom: 1px solid #e8ece6;
      text-align: left;
      vertical-align: top;
    }
    th {
      color: var(--muted);
      font-size: 12px;
      font-weight: 750;
    }
    td:last-child {
      width: 1%;
      white-space: nowrap;
    }
    .mini {
      min-height: 30px;
      padding: 5px 8px;
      font-size: 12px;
    }
    .empty {
      color: var(--muted);
      padding: 14px 2px;
      font-size: 13px;
    }
    textarea {
      width: 100%;
      min-height: 150px;
      resize: vertical;
      border: 1px solid var(--line);
      border-radius: 7px;
      padding: 10px;
      font: 13px ui-monospace, SFMono-Regular, Consolas, monospace;
      line-height: 1.45;
      background: #ffffff;
      color: #1d292e;
    }
    .status {
      min-height: 20px;
      color: var(--muted);
      font-size: 13px;
    }
    .status.ok { color: var(--accent-strong); }
    .status.danger { color: var(--danger); }
    .status.warn { color: var(--warn); }
    .muted { color: var(--muted); }
    .hide { display: none !important; }
    @media (max-width: 980px) {
      .topbar {
        grid-template-columns: 1fr;
      }
      .toolbar {
        justify-content: flex-start;
      }
      .workspace {
        grid-template-columns: 1fr;
      }
      .image-wrap {
        max-height: 65svh;
      }
    }
    @media (max-width: 560px) {
      .workspace, .topbar {
        padding-left: 12px;
        padding-right: 12px;
      }
      .grid, .segmented {
        grid-template-columns: 1fr;
      }
    }
  </style>
</head>
<body>
  <header class="topbar">
    <div>
      <p class="eyebrow">AutoPlay</p>
      <h1>錄製工作台</h1>
      <p class="subtitle">點畫面、補等待、擷取下一張圖，逐步產生可驗證的 YAML 腳本。</p>
    </div>
    <div class="toolbar">
      <button id="captureLatest" type="button">擷取最新畫面</button>
      <button id="saveScript" type="button" class="primary">儲存並驗證</button>
      <button id="runDry" type="button">測試腳本</button>
      <button id="runReal" type="button">真實測試</button>
      <button id="downloadScript" type="button">下載腳本</button>
      <button id="copyYaml" type="button">複製 YAML</button>
      <button id="clear" type="button" class="ghost">清空</button>
    </div>
  </header>
  <main class="workspace">
    <section class="stage">
      <div class="stage-head">
        <div>
          <h2 class="stage-title">目前參考畫面</h2>
          <div class="path" id="screenPath">__SCREENSHOT_PATH__</div>
        </div>
        <div class="status" id="status" aria-live="polite">待命中</div>
      </div>
      <div class="screen-shell">
        <div class="image-wrap" id="imageWrap">
          <img id="screen" alt="目前擷取畫面" src="data:image/png;base64,__ENCODED_IMAGE__">
        </div>
      </div>
    </section>
    <aside class="inspector">
      <section class="panel">
        <div class="panel-head">
          <div>
            <h2 class="panel-title">錄製設定</h2>
            <p class="hint">一般模式只寫腳本；裝置模式需要啟動時加上允許裝置輸入。</p>
          </div>
        </div>
        <div class="grid">
          <div class="wide">
            <div class="field-title">點擊模式</div>
            <div class="segmented" role="group" aria-label="點擊模式">
              <button id="modeScript" type="button" class="active">只記錄腳本</button>
              <button id="modeDevice" type="button">點擊後擷取</button>
            </div>
          </div>
          <label class="wide">動作名稱
            <input id="label" value="安全測試點擊" aria-label="動作名稱">
          </label>
          <div class="wide">
            <div class="field-title">等待策略</div>
            <div class="segmented" role="group" aria-label="等待策略">
              <button id="waitManualMode" type="button" class="active">手動秒數</button>
              <button id="waitAutoMode" type="button">自動估算</button>
            </div>
            <p class="hint" id="waitHint">手動模式會使用下方秒數；自動估算會依照兩次錄製操作的間隔，或點擊後畫面變化時間，寫入 wait。</p>
          </div>
          <label>手動等待秒數
            <input id="waitSeconds" value="1" inputmode="decimal">
          </label>
          <button id="addWait" type="button">加入等待</button>
          <label>最短等待
            <input id="minAutoWait" value="1" inputmode="decimal">
          </label>
          <label>最長等待
            <input id="maxAutoWait" value="12" inputmode="decimal">
          </label>
        </div>
      </section>
      <section class="panel">
        <div class="panel-head">
          <div>
            <h2 class="panel-title">輔助步驟</h2>
            <p class="hint">擷取畫面後可直接設為 checkpoint，讓腳本不只靠座標，也能確認畫面狀態。</p>
          </div>
        </div>
        <div class="grid">
          <label class="wide">截圖輸出路徑
            <input id="screenshotPath" value="artifacts/manual/after-step.png">
          </label>
          <button id="addScreenshot" type="button" class="wide">加入截圖步驟</button>
          <label class="wide">Checkpoint 路徑
            <input id="checkpointPath" value="__CHECKPOINT_PATH__">
          </label>
          <button id="addCheckpoint" type="button" class="wide">加入檔案存在檢查</button>
          <label class="wide">Template 路徑
            <input id="templatePath" value="artifacts/templates/button.png">
          </label>
          <label>門檻值
            <input id="threshold" value="0.95" inputmode="decimal">
          </label>
          <button id="addMatch" type="button">加入圖像比對</button>
        </div>
      </section>
      <section class="panel">
        <div class="panel-head">
          <div>
            <h2 class="panel-title">腳本時間線</h2>
            <p class="hint" id="clockHint">點擊畫面開始錄製；等待估算會從上一個動作後開始計時。</p>
          </div>
        </div>
        <table>
          <thead><tr><th>#</th><th>類型</th><th>內容</th><th></th></tr></thead>
          <tbody id="stepRows"></tbody>
        </table>
      </section>
      <section class="panel">
        <h2 class="panel-title">Recorder 指令</h2>
        <textarea id="commands" readonly></textarea>
      </section>
      <section class="panel">
        <h2 class="panel-title">完整 YAML 腳本</h2>
        <textarea id="yaml" readonly></textarea>
      </section>
    </aside>
  </main>
  <script>
    const initialScreenshotPath = __SCREENSHOT_VALUE__;
    const scriptFilename = __SCRIPT_FILENAME__;
    const saveUrl = __SAVE_URL__;
    const captureUrl = __CAPTURE_URL__;
    const tapCaptureUrl = __TAP_CAPTURE_URL__;
    const runUrl = __RUN_URL__;
    const allowDeviceInput = __ALLOW_DEVICE_INPUT__;
    const profile = __PROFILE__;
    const steps = [{ type: 'screenshot', out: initialScreenshotPath }];
    const image = document.getElementById('screen');
    const wrap = document.getElementById('imageWrap');
    const label = document.getElementById('label');
    const rows = document.getElementById('stepRows');
    const commands = document.getElementById('commands');
    const yaml = document.getElementById('yaml');
    const status = document.getElementById('status');
    const saveButton = document.getElementById('saveScript');
    const captureButton = document.getElementById('captureLatest');
    const runDryButton = document.getElementById('runDry');
    const runRealButton = document.getElementById('runReal');
    const modeScript = document.getElementById('modeScript');
    const modeDevice = document.getElementById('modeDevice');
    const waitManualMode = document.getElementById('waitManualMode');
    const waitAutoMode = document.getElementById('waitAutoMode');
    const clockHint = document.getElementById('clockHint');
    const screenPath = document.getElementById('screenPath');
    let clickMode = 'script';
    let waitMode = 'manual';
    let lastRecordedAt = null;

    if (!saveUrl) {
      saveButton.hidden = true;
    }
    if (!captureUrl) {
      captureButton.hidden = true;
    }
    if (!runUrl) {
      runDryButton.hidden = true;
      runRealButton.hidden = true;
    }
    if (!allowDeviceInput || !tapCaptureUrl) {
      modeDevice.disabled = true;
      modeDevice.title = '啟動 record-ui 時需要加上 --allow-device-input 才能直接點擊裝置。';
      runRealButton.disabled = true;
      runRealButton.title = '啟動 record-ui 時需要加上 --allow-device-input 才能真實測試。';
    }

    modeScript.addEventListener('click', () => setClickMode('script'));
    modeDevice.addEventListener('click', () => setClickMode('device'));
    waitManualMode.addEventListener('click', () => setWaitMode('manual'));
    waitAutoMode.addEventListener('click', () => setWaitMode('auto'));
    image.addEventListener('load', render);

    image.addEventListener('click', async (event) => {
      const rect = image.getBoundingClientRect();
      const x = Math.round((event.clientX - rect.left) * image.naturalWidth / rect.width);
      const y = Math.round((event.clientY - rect.top) * image.naturalHeight / rect.height);
      if (clickMode === 'device' && tapCaptureUrl) {
        await tapCapture(x, y);
        return;
      }
      recordSteps([{ type: 'tap', x, y, label: label.value || 'tap' }], { autoBefore: true });
    });

    document.getElementById('clear').addEventListener('click', () => {
      steps.length = 0;
      steps.push({ type: 'screenshot', out: initialScreenshotPath });
      lastRecordedAt = null;
      render();
      setStatus('已清空，目前保留初始截圖步驟。', 'warn');
    });

    document.getElementById('addWait').addEventListener('click', () => {
      const seconds = Number(document.getElementById('waitSeconds').value);
      if (!Number.isFinite(seconds) || seconds < 0) return alert('等待秒數必須是 0 或正數。');
      recordSteps([{ type: 'wait', seconds }], { autoBefore: false });
    });

    document.getElementById('addScreenshot').addEventListener('click', () => {
      const out = document.getElementById('screenshotPath').value.trim();
      if (!out) return alert('請填寫截圖輸出路徑。');
      recordSteps([{ type: 'screenshot', out }], { autoBefore: true });
      document.getElementById('checkpointPath').value = out;
    });

    document.getElementById('addCheckpoint').addEventListener('click', () => {
      const path = document.getElementById('checkpointPath').value.trim();
      if (!path) return alert('請填寫 checkpoint 路徑。');
      recordSteps([{ type: 'checkpoint_exists', path }], { autoBefore: false });
    });

    document.getElementById('addMatch').addEventListener('click', () => {
      const source = document.getElementById('checkpointPath').value.trim();
      const template = document.getElementById('templatePath').value.trim();
      const threshold = Number(document.getElementById('threshold').value);
      if (!source || !template) return alert('請填寫來源圖與 template 路徑。');
      if (!Number.isFinite(threshold) || threshold < 0 || threshold > 1) return alert('門檻值必須介於 0 到 1。');
      recordSteps([{ type: 'checkpoint_match', source, template, threshold }], { autoBefore: false });
    });

    document.getElementById('copyYaml').addEventListener('click', async () => {
      await navigator.clipboard.writeText(yaml.value);
      setStatus('已複製 YAML。', 'ok');
    });
    captureButton.addEventListener('click', async () => {
      if (!captureUrl) return;
      setStatus('正在擷取最新畫面...');
      try {
        const payload = await postJson(captureUrl, {});
        applyCapturePayload(payload, true);
      } catch (error) {
        setStatus(`擷取失敗：${error}`, 'danger');
      }
    });
    saveButton.addEventListener('click', async () => {
      if (!saveUrl) return;
      setStatus('正在儲存並驗證...');
      try {
        const payload = await postJson(saveUrl, { yaml: yaml.value });
        setStatus(payload.messages ? payload.messages.join(' ') : payload.status, payload.ok ? 'ok' : 'danger');
      } catch (error) {
        setStatus(`儲存失敗：${error}`, 'danger');
      }
    });
    runDryButton.addEventListener('click', () => runScript(false));
    runRealButton.addEventListener('click', () => {
      if (!allowDeviceInput) {
        setStatus('目前未允許裝置輸入；請用 --allow-device-input 啟動 record-ui。', 'warn');
        return;
      }
      if (!confirm('真實測試會對目前裝置送出 tap。請確認畫面安全且不是購買、抽卡、刪除、交易、聊天或登入流程。')) return;
      runScript(true);
    });
    document.getElementById('downloadScript').addEventListener('click', () => {
      const blob = new Blob([yaml.value], { type: 'application/x-yaml' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = scriptFilename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
      setStatus('已準備下載腳本。', 'ok');
    });

    function setClickMode(mode) {
      if (mode === 'device' && (!allowDeviceInput || !tapCaptureUrl)) {
        setStatus('目前未允許裝置輸入；請用 --allow-device-input 啟動 record-ui。', 'warn');
        return;
      }
      clickMode = mode;
      modeScript.classList.toggle('active', mode === 'script');
      modeDevice.classList.toggle('active', mode === 'device');
      setStatus(mode === 'device' ? '點擊畫面會送出 ADB tap，等待後擷取下一張畫面。' : '點擊畫面只會寫入 YAML，不會操作裝置。');
    }

    function setWaitMode(mode) {
      waitMode = mode;
      waitManualMode.classList.toggle('active', mode === 'manual');
      waitAutoMode.classList.toggle('active', mode === 'auto');
      updateClockHint();
    }

    function recordSteps(newSteps, options = {}) {
      if (options.autoBefore) maybeInsertAutoWait();
      newSteps.forEach(step => steps.push(step));
      lastRecordedAt = performance.now();
      render();
    }

    function maybeInsertAutoWait() {
      if (waitMode !== 'auto' || lastRecordedAt === null) return;
      const minWait = readSeconds('minAutoWait', 1);
      const maxWait = readSeconds('maxAutoWait', 12);
      if (minWait === null || maxWait === null || minWait > maxWait) {
        setStatus('自動等待設定不正確，請確認最短與最長秒數。', 'danger');
        return;
      }
      const elapsed = (performance.now() - lastRecordedAt) / 1000;
      if (elapsed < minWait) return;
      const seconds = Math.round(Math.min(elapsed, maxWait) * 10) / 10;
      steps.push({ type: 'wait', seconds });
      setStatus(`已自動估算等待 ${seconds} 秒。`, 'ok');
    }

    function readSeconds(id, fallback) {
      const value = Number(document.getElementById(id).value || fallback);
      if (!Number.isFinite(value) || value < 0) return null;
      return value;
    }

    function render() {
      rows.replaceChildren();
      wrap.querySelectorAll('.marker').forEach(marker => marker.remove());
      commands.value = steps.map(stepToCommand).filter(Boolean).join('\\n');
      yaml.value = profileToYaml() + 'steps:\\n' + steps.map(stepToYaml).join('\\n');

      steps.forEach((step, index) => {
        const tr = document.createElement('tr');
        const remove = index === 0 ? '' : `<button class="mini" type="button" data-remove="${index}">移除</button>`;
        tr.innerHTML = `<td>${index + 1}</td><td>${escapeHtml(typeLabel(step.type))}</td><td>${escapeHtml(stepDetail(step))}</td><td>${remove}</td>`;
        rows.appendChild(tr);
        if (step.type !== 'tap') return;
        const marker = document.createElement('div');
        marker.className = 'marker';
        marker.style.left = `${image.offsetLeft + step.x / image.naturalWidth * image.clientWidth}px`;
        marker.style.top = `${image.offsetTop + step.y / image.naturalHeight * image.clientHeight}px`;
        marker.innerHTML = `<span>${index + 1}</span>`;
        wrap.appendChild(marker);
      });
      if (steps.length === 1) {
        const tr = document.createElement('tr');
        tr.innerHTML = '<td colspan="4" class="empty">尚未加入點擊。直接點左側畫面即可新增 tap。</td>';
        rows.appendChild(tr);
      }
      rows.querySelectorAll('button[data-remove]').forEach(button => {
        button.addEventListener('click', () => {
          steps.splice(Number(button.dataset.remove), 1);
          lastRecordedAt = performance.now();
          render();
        });
      });
      updateClockHint();
    }

    async function tapCapture(x, y) {
      const manualWait = readSeconds('waitSeconds', 1);
      const minWait = readSeconds('minAutoWait', 1);
      const maxWait = readSeconds('maxAutoWait', 12);
      if (manualWait === null || minWait === null || maxWait === null || minWait > maxWait) {
        setStatus('等待設定不正確，請確認秒數。', 'danger');
        return;
      }
      setStatus(waitMode === 'auto' ? '正在點擊，並等待畫面變化...' : '正在點擊，等待後擷取畫面...');
      try {
        const payload = await postJson(tapCaptureUrl, {
          x,
          y,
          label: label.value || 'tap',
          wait_seconds: manualWait,
          auto_wait: waitMode === 'auto',
          min_wait_seconds: minWait,
          max_wait_seconds: maxWait,
          poll_seconds: 0.5,
          stable_seconds: 1.2
        });
        applyCapturePayload(payload, false);
      } catch (error) {
        setStatus(`點擊與擷取失敗：${error}`, 'danger');
      }
    }

    async function runScript(executeTaps) {
      if (!runUrl) return;
      setStatus(executeTaps ? '正在真實測試目前腳本...' : '正在 dry-run 測試目前腳本...');
      try {
        const payload = await postJson(runUrl, { yaml: yaml.value, execute_taps: executeTaps });
        const executed = payload.executed && payload.executed.length ? ` 執行 ${payload.executed.length} 個步驟。` : '';
        const report = payload.report_path ? ` Report: ${payload.report_path}` : '';
        setStatus(`${payload.messages ? payload.messages.join(' ') : payload.status}${executed}${report}`, payload.ok ? 'ok' : 'danger');
      } catch (error) {
        setStatus(`測試失敗：${error}`, 'danger');
      }
    }

    async function postJson(url, payload) {
      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await response.json();
      if (!response.ok || !data.ok) {
        throw new Error(data.messages ? data.messages.join(' ') : response.statusText);
      }
      return data;
    }

    function applyCapturePayload(payload, autoBefore) {
      image.src = payload.image_data_url;
      if (autoBefore) maybeInsertAutoWait();
      payload.steps.forEach(step => steps.push(step));
      if (payload.screenshot_path) {
        screenPath.textContent = payload.screenshot_path;
        document.getElementById('checkpointPath').value = payload.screenshot_path;
        document.getElementById('screenshotPath').value = nextSuggestedPath(payload.screenshot_path);
      }
      lastRecordedAt = performance.now();
      const waitText = payload.auto_wait && payload.wait_seconds ? ` 自動等待 ${payload.wait_seconds} 秒。` : '';
      setStatus((payload.messages ? payload.messages.join(' ') : payload.status) + waitText, 'ok');
      render();
    }

    function nextSuggestedPath(path) {
      const dot = path.lastIndexOf('.');
      if (dot === -1) return `${path}-next.png`;
      return `${path.slice(0, dot)}-next${path.slice(dot)}`;
    }

    function typeLabel(type) {
      return {
        screenshot: '截圖',
        tap: '點擊',
        wait: '等待',
        checkpoint_exists: '檔案檢查',
        checkpoint_match: '圖像比對'
      }[type] || type;
    }

    function stepDetail(step) {
      if (step.type === 'tap') return `${step.x},${step.y} - ${step.label}`;
      if (step.type === 'wait') return `${step.seconds} 秒`;
      if (step.type === 'screenshot') return step.out;
      if (step.type === 'checkpoint_exists') return step.path;
      if (step.type === 'checkpoint_match') return `${step.source} -> ${step.template} @ ${step.threshold}`;
      return '';
    }

    function stepToCommand(step) {
      if (step.type === 'tap') return `tap ${step.x} ${step.y} ${step.label}`;
      if (step.type === 'wait') return `wait ${step.seconds}`;
      if (step.type === 'screenshot') return `screenshot ${step.out}`;
      if (step.type === 'checkpoint_exists') return `checkpoint_exists ${step.path}`;
      if (step.type === 'checkpoint_match') return `# checkpoint_match is included in YAML output`;
      return '';
    }

    function stepToYaml(step) {
      if (step.type === 'tap') return [
        '  - type: tap',
        `    x: ${step.x}`,
        `    y: ${step.y}`,
        `    label: ${yamlString(step.label)}`
      ].join('\\n');
      if (step.type === 'wait') return ['  - type: wait', `    seconds: ${step.seconds}`].join('\\n');
      if (step.type === 'screenshot') return ['  - type: screenshot', `    out: ${yamlString(step.out)}`].join('\\n');
      if (step.type === 'checkpoint_exists') return ['  - type: checkpoint_exists', `    path: ${yamlString(step.path)}`].join('\\n');
      if (step.type === 'checkpoint_match') return [
        '  - type: checkpoint_match',
        `    source: ${yamlString(step.source)}`,
        `    template: ${yamlString(step.template)}`,
        `    threshold: ${step.threshold}`
      ].join('\\n');
      return '';
    }

    function profileToYaml() {
      const lines = [];
      if (profile.adb_path || profile.serial) {
        lines.push('profile:');
        if (profile.adb_path) lines.push(`  adb_path: ${yamlString(profile.adb_path)}`);
        if (profile.serial) lines.push(`  serial: ${yamlString(profile.serial)}`);
      }
      return lines.length ? `${lines.join('\\n')}\\n` : '';
    }

    function yamlString(value) {
      return JSON.stringify(String(value));
    }

    function updateClockHint() {
      if (waitMode === 'manual') {
        clockHint.textContent = '手動模式：需要等待時按「加入等待」，或在點擊後擷取中使用手動秒數。';
        return;
      }
      if (lastRecordedAt === null) {
        clockHint.textContent = '自動估算：加入第一個動作後開始計時。';
        return;
      }
      const elapsed = Math.max(0, (performance.now() - lastRecordedAt) / 1000);
      clockHint.textContent = `自動估算：距離上一個錄製動作約 ${elapsed.toFixed(1)} 秒。`;
    }

    function setStatus(message, tone = '') {
      status.textContent = message;
      status.className = `status ${tone}`.trim();
    }

    function escapeHtml(value) {
      return String(value).replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char]));
    }

    render();
    setInterval(updateClockHint, 1000);
  </script>
</body>
</html>
"""
    return (
        template.replace("__TITLE__", title)
        .replace("__ENCODED_IMAGE__", encoded_image)
        .replace("__SCREENSHOT_PATH__", html.escape(screenshot_path.as_posix()))
        .replace("__CHECKPOINT_PATH__", html.escape(screenshot_path.as_posix()))
        .replace("__SCREENSHOT_VALUE__", screenshot_value)
        .replace("__SCRIPT_FILENAME__", script_filename)
        .replace("__SAVE_URL__", save_url_value)
        .replace("__CAPTURE_URL__", capture_url_value)
        .replace("__TAP_CAPTURE_URL__", tap_capture_url_value)
        .replace("__RUN_URL__", run_url_value)
        .replace("__ALLOW_DEVICE_INPUT__", allow_device_input_value)
        .replace("__PROFILE__", profile_value)
    )
