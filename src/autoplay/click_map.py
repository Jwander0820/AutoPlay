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
    step_capture_url: str | None = None,
    run_url: str | None = None,
    template_url: str | None = None,
    calibration: dict | None = None,
    calibration_guide_command: str | None = None,
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
    step_capture_url_value = json.dumps(step_capture_url)
    run_url_value = json.dumps(run_url)
    template_url_value = json.dumps(template_url)
    calibration_value = json.dumps(calibration or {})
    calibration_guide_command_value = json.dumps(calibration_guide_command)
    allow_device_input_value = json.dumps(allow_device_input)
    profile_value = json.dumps({"adb_path": profile_adb_path, "serial": profile_serial})
    device_input_label = "裝置輸入：已允許" if allow_device_input else "裝置輸入：關閉"
    serial_label = f"serial：{profile_serial}" if profile_serial else "serial：未指定"
    adb_label = f"ADB：{Path(profile_adb_path).name}" if profile_adb_path else "ADB：預設"
    template = """<!doctype html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AutoPlay 錄製工作台 - __TITLE__</title>
  <style>
    :root {
      --bg: #f4f7f8;
      --surface: #ffffff;
      --surface-2: #eef4f2;
      --ink: #172126;
      --muted: #66727a;
      --line: #d8e0e2;
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
      background: rgba(255, 255, 255, 0.96);
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
    .workflow-rail, .context-strip {
      display: grid;
      gap: 8px;
      padding: 10px 18px;
      border-bottom: 1px solid var(--line);
      background: #f9fbfb;
    }
    .workflow-rail {
      grid-template-columns: repeat(4, minmax(0, 1fr));
    }
    .workflow-step {
      display: grid;
      grid-template-columns: auto minmax(0, 1fr);
      gap: 8px;
      align-items: center;
      min-height: 44px;
      padding: 8px 10px;
      border: 1px solid #dce6e4;
      border-radius: 8px;
      background: #ffffff;
    }
    .workflow-step span {
      display: inline-grid;
      place-items: center;
      width: 24px;
      height: 24px;
      border-radius: 999px;
      background: #e5f3ef;
      color: var(--accent-strong);
      font-size: 12px;
      font-weight: 800;
    }
    .workflow-step strong {
      display: block;
      font-size: 13px;
      line-height: 1.3;
    }
    .workflow-step small {
      display: block;
      color: var(--muted);
      font-size: 11px;
      line-height: 1.35;
    }
    .context-strip {
      grid-template-columns: repeat(3, minmax(0, max-content));
      align-items: center;
    }
    .context-chip {
      min-height: 28px;
      padding: 5px 9px;
      border: 1px solid #dce6e4;
      border-radius: 999px;
      background: #ffffff;
      color: #34434a;
      font-size: 12px;
      font-weight: 700;
      overflow-wrap: anywhere;
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
    button.mini {
      min-height: 28px;
      padding: 4px 8px;
      font-size: 12px;
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
    .toolstrip {
      display: grid;
      grid-template-columns: minmax(0, 1.35fr) minmax(220px, 0.9fr) minmax(240px, 1fr);
      gap: 12px;
      margin-bottom: 12px;
    }
    .tool-card {
      border: 1px solid var(--line);
      border-radius: 8px;
      background: rgba(255, 255, 255, 0.86);
      padding: 12px 14px;
    }
    .canvas-meta {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 8px;
      color: var(--muted);
      font-size: 12px;
      line-height: 1.5;
    }
    .calibration-state {
      color: var(--muted);
      font-size: 12px;
      line-height: 1.5;
    }
    .calibration-state strong {
      color: var(--ink);
    }
    .calibration-command {
      margin-top: 8px;
      color: var(--muted);
      font-size: 12px;
      line-height: 1.5;
    }
    .calibration-command-head {
      display: flex;
      justify-content: space-between;
      gap: 8px;
      align-items: center;
    }
    .calibration-command code {
      display: block;
      margin-top: 4px;
      white-space: normal;
      overflow-wrap: anywhere;
      color: var(--ink);
    }
    .next-action {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: center;
      margin-bottom: 12px;
      padding: 12px 14px;
      border: 1px solid #b9d9d0;
      border-radius: 8px;
      background: #eef8f5;
    }
    .next-action[hidden] {
      display: none;
    }
    .next-action strong {
      display: block;
      font-size: 13px;
      line-height: 1.4;
    }
    .next-action p {
      margin: 3px 0 0;
      color: var(--muted);
      font-size: 12px;
      line-height: 1.45;
    }
    .next-action-actions {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      justify-content: flex-end;
    }
    .next-label {
      display: block;
      margin-bottom: 2px;
      color: var(--accent);
      font-size: 11px;
      font-weight: 800;
    }
    .tool-segment {
      grid-template-columns: repeat(5, minmax(0, 1fr));
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
    .crop-selection {
      position: absolute;
      border: 2px solid #72e0ff;
      background: rgba(114, 224, 255, 0.16);
      pointer-events: none;
      box-shadow: 0 0 0 1px rgba(12, 37, 46, 0.34);
    }
    .gesture-line {
      position: absolute;
      height: 4px;
      border-radius: 999px;
      background: linear-gradient(90deg, rgba(255, 207, 90, 0.95), rgba(255, 127, 61, 0.98));
      box-shadow: 0 0 0 1px rgba(12, 24, 28, 0.18), 0 4px 18px rgba(255, 127, 61, 0.22);
      pointer-events: none;
      transform-origin: 0 50%;
    }
    .gesture-line.drag {
      background: linear-gradient(90deg, rgba(89, 191, 245, 0.94), rgba(126, 228, 219, 0.98));
      box-shadow: 0 0 0 1px rgba(9, 29, 39, 0.18), 0 4px 18px rgba(67, 177, 214, 0.2);
    }
    .gesture-line.scroll {
      background: linear-gradient(90deg, rgba(153, 212, 112, 0.92), rgba(60, 161, 115, 0.98));
      box-shadow: 0 0 0 1px rgba(11, 35, 23, 0.18), 0 4px 18px rgba(63, 164, 109, 0.18);
    }
    .gesture-line.preview {
      opacity: 0.7;
      box-shadow: 0 0 0 1px rgba(12, 24, 28, 0.12), 0 0 0 5px rgba(255, 255, 255, 0.15);
    }
    .gesture-handle {
      position: absolute;
      width: 14px;
      height: 14px;
      border: 2px solid #ffffff;
      border-radius: 50%;
      background: #ff9d46;
      box-shadow: 0 3px 12px rgba(14, 21, 24, 0.26);
      pointer-events: none;
      transform: translate(-50%, -50%);
    }
    .gesture-handle.drag {
      background: #2ca7d6;
    }
    .gesture-handle.scroll {
      background: #2b9f68;
    }
    .gesture-handle.start {
      width: 12px;
      height: 12px;
      opacity: 0.92;
    }
    .gesture-badge {
      position: absolute;
      min-height: 24px;
      padding: 3px 8px;
      border-radius: 999px;
      background: rgba(18, 28, 32, 0.92);
      color: #ffffff;
      font-size: 12px;
      line-height: 18px;
      font-weight: 750;
      box-shadow: 0 10px 20px rgba(14, 21, 24, 0.18);
      pointer-events: none;
      white-space: nowrap;
      transform: translate(-50%, calc(-100% - 10px));
    }
    .back-badge {
      position: absolute;
      left: 14px;
      bottom: 14px;
      min-height: 24px;
      padding: 3px 8px;
      border-radius: 999px;
      background: rgba(18, 28, 32, 0.9);
      color: #ffffff;
      font-size: 12px;
      line-height: 18px;
      font-weight: 700;
      box-shadow: 0 10px 20px rgba(14, 21, 24, 0.18);
      pointer-events: none;
    }
    .inspector {
      position: sticky;
      top: 82px;
      max-height: calc(100svh - 100px);
      overflow: auto;
      display: grid;
      gap: 14px;
      padding-right: 2px;
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
      background: #edf2f4;
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
    .direction-pad {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 6px;
      align-items: center;
    }
    .direction-pad button:nth-child(1) {
      grid-column: 2;
    }
    .direction-pad button:nth-child(2) {
      grid-column: 1;
    }
    .direction-pad button:nth-child(3) {
      grid-column: 2;
    }
    .direction-pad button:nth-child(4) {
      grid-column: 3;
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
      .inspector {
        position: static;
        max-height: none;
        overflow: visible;
        padding-right: 0;
      }
      .toolstrip {
        grid-template-columns: 1fr;
      }
      .workflow-rail, .context-strip {
        grid-template-columns: 1fr 1fr;
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
      .workflow-rail, .context-strip {
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
      <p class="subtitle">先選工具，再直接在畫面點一下或拖曳；右側只留等待、驗證與快速補步驟。</p>
    </div>
    <div class="toolbar">
      <button id="captureLatest" type="button">擷取最新畫面</button>
      <button id="saveScript" type="button" class="primary">儲存並驗證</button>
      <button id="runDry" type="button">測試腳本</button>
      <button id="runReal" type="button">真實測試</button>
      <button id="downloadScript" type="button">下載腳本</button>
      <button id="copyYaml" type="button">複製 YAML</button>
      <button id="undoLast" type="button">復原上一筆</button>
      <button id="clear" type="button" class="ghost">清空</button>
    </div>
  </header>
  <section class="workflow-rail" aria-label="錄製流程">
    <div class="workflow-step"><span>1</span><div><strong>連線</strong><small>確認 ADB 與 serial</small></div></div>
    <div class="workflow-step"><span>2</span><div><strong>擷取</strong><small>取得最新模擬器畫面</small></div></div>
    <div class="workflow-step"><span>3</span><div><strong>錄製</strong><small>點擊、手勢、等待</small></div></div>
    <div class="workflow-step"><span>4</span><div><strong>驗證</strong><small>儲存、dry-run、checkpoint</small></div></div>
  </section>
  <section class="context-strip" aria-label="執行環境">
    <span class="context-chip" id="deviceInputState">__DEVICE_INPUT_LABEL__</span>
    <span class="context-chip" id="serialState">__SERIAL_LABEL__</span>
    <span class="context-chip" id="adbState">__ADB_LABEL__</span>
  </section>
  <main class="workspace">
    <section class="stage">
      <div class="stage-head">
        <div>
          <h2 class="stage-title">目前參考畫面</h2>
          <div class="path" id="screenPath">__SCREENSHOT_PATH__</div>
        </div>
        <div class="status" id="status" aria-live="polite">待命中</div>
      </div>
      <div class="next-action" id="nextAction" hidden>
        <div>
          <span class="next-label">下一步</span>
          <strong id="nextActionTitle">建立畫面驗證</strong>
          <p id="nextActionText">框選新畫面上的穩定 UI，儲存成 template checkpoint。</p>
        </div>
        <div class="next-action-actions">
          <button id="nextActionButton" type="button">框選 Template</button>
          <button id="nextActionDismiss" type="button" class="ghost">稍後</button>
        </div>
      </div>
      <div class="toolstrip">
        <div class="tool-card">
          <div class="field-title">互動工具</div>
          <div class="segmented tool-segment" role="group" aria-label="互動工具">
            <button id="toolTap" type="button" class="active">點擊</button>
            <button id="toolSwipe" type="button">滑動</button>
            <button id="toolDrag" type="button">拖曳</button>
            <button id="toolScroll" type="button">捲動</button>
            <button id="toolCrop" type="button">Template</button>
          </div>
        </div>
        <div class="tool-card">
          <div class="field-title">目前操作</div>
          <p class="hint" id="toolHint">點擊工具：在畫面點一下就會新增 tap。</p>
          <div class="canvas-meta">
            <span id="pointerCoords">游標：--</span>
            <span id="toolMeta">腳本模式 / 手動等待</span>
          </div>
        </div>
        <div class="tool-card">
          <div class="field-title">手勢校準</div>
          <div class="calibration-state" id="calibrationState">使用預設手勢參數</div>
          <div class="canvas-meta">
            <span id="calibrationScreen">畫面：1080 x 1920</span>
            <span id="calibrationScroll">捲動：700 / 700</span>
          </div>
          <div class="calibration-command" id="calibrationGuide" hidden>
            <div class="calibration-command-head">
              <span>校準指令</span>
              <button id="copyCalibrationGuide" type="button" class="mini">複製</button>
            </div>
            <code id="calibrationGuideCommand"></code>
          </div>
        </div>
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
            <h2 class="panel-title">驗證與 Template</h2>
            <p class="hint">每次切畫面後都能順手補 checkpoint，讓腳本不只靠座標，也能確認畫面狀態。</p>
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
          <div class="wide">
            <div class="field-title">Template 裁切</div>
            <p class="hint">切到 Template 工具後，在左側拖曳一個穩定 UI 區塊，再儲存為 template。</p>
          </div>
          <button id="startCrop" type="button">切到框選模式</button>
          <button id="saveTemplate" type="button">儲存並加入比對</button>
          <label>X
            <input id="cropX" value="0" inputmode="numeric">
          </label>
          <label>Y
            <input id="cropY" value="0" inputmode="numeric">
          </label>
          <label>寬
            <input id="cropWidth" value="80" inputmode="numeric">
          </label>
          <label>高
            <input id="cropHeight" value="40" inputmode="numeric">
          </label>
        </div>
      </section>
      <section class="panel">
        <div class="panel-head">
          <div>
            <h2 class="panel-title">快速補步驟與手勢微調</h2>
            <p class="hint">滑動、拖曳、捲動現在可直接在左側畫面拖曳；這裡保留返回、方向鍵與座標微調。</p>
          </div>
        </div>
        <div class="grid">
          <label>距離
            <input id="gestureDistance" value="700" inputmode="numeric">
          </label>
          <label>時間 ms
            <input id="gestureDuration" value="400" inputmode="numeric">
          </label>
          <div class="wide">
            <div class="field-title">捲動方向</div>
            <div class="direction-pad" role="group" aria-label="捲動方向">
              <button type="button" data-scroll="up">上</button>
              <button type="button" data-scroll="left">左</button>
              <button type="button" data-scroll="down">下</button>
              <button type="button" data-scroll="right">右</button>
            </div>
          </div>
          <button id="addBack" type="button" class="wide">加入返回</button>
          <label>X1
            <input id="gestureX1" value="500" inputmode="numeric">
          </label>
          <label>Y1
            <input id="gestureY1" value="1400" inputmode="numeric">
          </label>
          <label>X2
            <input id="gestureX2" value="500" inputmode="numeric">
          </label>
          <label>Y2
            <input id="gestureY2" value="500" inputmode="numeric">
          </label>
          <button id="addSwipe" type="button">用座標加入滑動</button>
          <button id="addDrag" type="button">用座標加入拖曳</button>
          <p class="hint wide">拖曳左側畫面時，這些座標與距離會一起更新，方便你再微調一次。</p>
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
    const stepCaptureUrl = __STEP_CAPTURE_URL__;
    const runUrl = __RUN_URL__;
    const templateUrl = __TEMPLATE_URL__;
    const calibration = __CALIBRATION__;
    const calibrationGuideCommand = __CALIBRATION_GUIDE_COMMAND__;
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
    const nextAction = document.getElementById('nextAction');
    const nextActionTitle = document.getElementById('nextActionTitle');
    const nextActionText = document.getElementById('nextActionText');
    const nextActionButton = document.getElementById('nextActionButton');
    const nextActionDismiss = document.getElementById('nextActionDismiss');
    const saveButton = document.getElementById('saveScript');
    const captureButton = document.getElementById('captureLatest');
    const runDryButton = document.getElementById('runDry');
    const runRealButton = document.getElementById('runReal');
    const undoButton = document.getElementById('undoLast');
    const modeScript = document.getElementById('modeScript');
    const modeDevice = document.getElementById('modeDevice');
    const waitManualMode = document.getElementById('waitManualMode');
    const waitAutoMode = document.getElementById('waitAutoMode');
    const clockHint = document.getElementById('clockHint');
    const screenPath = document.getElementById('screenPath');
    const startCropButton = document.getElementById('startCrop');
    const saveTemplateButton = document.getElementById('saveTemplate');
    const toolHint = document.getElementById('toolHint');
    const toolMeta = document.getElementById('toolMeta');
    const pointerCoords = document.getElementById('pointerCoords');
    const calibrationState = document.getElementById('calibrationState');
    const calibrationScreen = document.getElementById('calibrationScreen');
    const calibrationScroll = document.getElementById('calibrationScroll');
    const calibrationGuide = document.getElementById('calibrationGuide');
    const calibrationGuideCommandEl = document.getElementById('calibrationGuideCommand');
    const copyCalibrationGuideButton = document.getElementById('copyCalibrationGuide');
    const toolButtons = {
      tap: document.getElementById('toolTap'),
      swipe: document.getElementById('toolSwipe'),
      drag: document.getElementById('toolDrag'),
      scroll: document.getElementById('toolScroll'),
      crop: document.getElementById('toolCrop')
    };
    let clickMode = 'script';
    let waitMode = 'manual';
    let interactionTool = 'tap';
    let lastRecordedAt = null;
    let cropSelection = null;
    let pointerDraft = null;
    const gestureDefaults = calibrationDefaults();

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
    if (!templateUrl) {
      startCropButton.disabled = true;
      saveTemplateButton.disabled = true;
      startCropButton.title = '離線 HTML 無法直接寫入 template 檔案；請使用 record-ui。';
      saveTemplateButton.title = '離線 HTML 無法直接寫入 template 檔案；請使用 record-ui。';
    }
    if (!allowDeviceInput || !stepCaptureUrl) {
      modeDevice.disabled = true;
      modeDevice.title = '啟動 record-ui 時需要加上 --allow-device-input 才能直接點擊裝置。';
      runRealButton.disabled = true;
      runRealButton.title = '啟動 record-ui 時需要加上 --allow-device-input 才能真實測試。';
    }
    applyCalibrationDefaults();

    modeScript.addEventListener('click', () => setClickMode('script'));
    modeDevice.addEventListener('click', () => setClickMode('device'));
    waitManualMode.addEventListener('click', () => setWaitMode('manual'));
    waitAutoMode.addEventListener('click', () => setWaitMode('auto'));
    Object.entries(toolButtons).forEach(([tool, button]) => {
      button.addEventListener('click', () => setInteractionTool(tool));
    });
    image.addEventListener('load', render);
    image.addEventListener('pointerdown', handleCanvasPointerDown);
    image.addEventListener('pointermove', handleCanvasPointerMove);
    image.addEventListener('pointerup', handleCanvasPointerUp);
    image.addEventListener('pointercancel', cancelCanvasPointer);

    document.getElementById('clear').addEventListener('click', () => {
      steps.length = 0;
      steps.push({ type: 'screenshot', out: initialScreenshotPath });
      lastRecordedAt = null;
      render();
      setStatus('已清空，目前保留初始截圖步驟。', 'warn');
    });
    undoButton.addEventListener('click', () => {
      if (steps.length <= 1) {
        setStatus('目前沒有可復原的步驟。', 'warn');
        return;
      }
      const removed = steps.pop();
      lastRecordedAt = performance.now();
      render();
      setStatus(`已移除上一筆：${typeLabel(removed.type)}。`, 'ok');
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
    startCropButton.addEventListener('click', () => {
      if (!templateUrl) return;
      focusTemplateWorkflow();
    });
    saveTemplateButton.addEventListener('click', async () => {
      if (!templateUrl) return;
      const source = screenPath.textContent.trim() || document.getElementById('checkpointPath').value.trim();
      const template = document.getElementById('templatePath').value.trim();
      const threshold = Number(document.getElementById('threshold').value);
      const x = readNonNegativeInteger('cropX', 'X');
      const y = readNonNegativeInteger('cropY', 'Y');
      const width = readPositiveInteger('cropWidth', '寬');
      const height = readPositiveInteger('cropHeight', '高');
      if (!source || !template) return alert('請填寫來源圖與 template 路徑。');
      if (!Number.isFinite(threshold) || threshold < 0 || threshold > 1) return alert('門檻值必須介於 0 到 1。');
      if ([x, y, width, height].some(value => value === null)) return;
      setStatus('正在儲存 template...');
      try {
        const payload = await postJson(templateUrl, { source, template, x, y, width, height, threshold });
        document.getElementById('checkpointPath').value = payload.source_path || source;
        document.getElementById('templatePath').value = payload.template_path || template;
        recordSteps(payload.steps || [], { autoBefore: false });
        hideNextAction();
        setStatus(payload.messages ? payload.messages.join(' ') : '已儲存 template。', 'ok');
      } catch (error) {
        setStatus(`Template 儲存失敗：${error}`, 'danger');
      }
    });
    nextActionButton.addEventListener('click', () => {
      focusTemplateWorkflow();
    });
    nextActionDismiss.addEventListener('click', () => {
      hideNextAction();
      setStatus('已略過這次 checkpoint 提示。', 'warn');
    });
    copyCalibrationGuideButton.addEventListener('click', async () => {
      if (!calibrationGuideCommand) return;
      await navigator.clipboard.writeText(calibrationGuideCommand);
      setStatus('已複製校準指令。', 'ok');
    });
    document.querySelectorAll('button[data-scroll]').forEach(button => {
      button.addEventListener('click', async () => {
        const distance = readScrollDistance(button.dataset.scroll);
        const duration = readDuration();
        if (distance === null || duration === null) return;
        const step = { type: 'scroll', direction: button.dataset.scroll, distance, duration_ms: duration, label: label.value || `scroll ${button.dataset.scroll}` };
        if (clickMode === 'device' && stepCaptureUrl) {
          await deviceStepCapture(step);
          return;
        }
        recordSteps([step], { autoBefore: true });
      });
    });
    document.getElementById('addBack').addEventListener('click', async () => {
      const step = { type: 'back', label: label.value || 'back' };
      if (clickMode === 'device' && stepCaptureUrl) {
        await deviceStepCapture(step);
        return;
      }
      recordSteps([step], { autoBefore: true });
    });
    document.getElementById('addSwipe').addEventListener('click', () => { void recordSwipeLike('swipe'); });
    document.getElementById('addDrag').addEventListener('click', () => { void recordSwipeLike('drag'); });
    document.getElementById('gestureDuration').addEventListener('input', updateToolMeta);
    image.addEventListener('pointerleave', () => updatePointerCoords(null));

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
      if (!confirm('真實測試會對目前裝置送出 tap 與手勢。請確認畫面安全且不是購買、抽卡、刪除、交易、聊天或登入流程。')) return;
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
      if (mode === 'device' && (!allowDeviceInput || !stepCaptureUrl)) {
        setStatus('目前未允許裝置輸入；請用 --allow-device-input 啟動 record-ui。', 'warn');
        return;
      }
      clickMode = mode;
      modeScript.classList.toggle('active', mode === 'script');
      modeDevice.classList.toggle('active', mode === 'device');
      updateToolMeta();
      setStatus(mode === 'device' ? '裝置模式已啟用：tap 與手勢都會送到裝置，等待後擷取下一張畫面。' : '目前是腳本模式，所有操作都只會寫入 YAML。');
    }

    function setWaitMode(mode) {
      waitMode = mode;
      waitManualMode.classList.toggle('active', mode === 'manual');
      waitAutoMode.classList.toggle('active', mode === 'auto');
      updateToolMeta();
      updateClockHint();
    }

    function calibrationDefaults() {
      return {
        loaded: Boolean(calibration.loaded),
        path: calibration.path || '',
        warnings: Array.isArray(calibration.warnings) ? calibration.warnings : [],
        screenWidth: Number(calibration.screen_width) || 1080,
        screenHeight: Number(calibration.screen_height) || 1920,
        verticalDistance: Number(calibration.scroll_vertical_distance) || 700,
        horizontalDistance: Number(calibration.scroll_horizontal_distance) || 700,
        swipeDuration: Number(calibration.default_swipe_duration_ms) || 400,
        dragDuration: Number(calibration.default_drag_duration_ms) || 700
      };
    }

    function applyCalibrationDefaults() {
      document.getElementById('gestureDistance').value = gestureDefaults.verticalDistance;
      document.getElementById('gestureDuration').value = gestureDefaults.swipeDuration;
      const statusText = gestureDefaults.loaded ? `已套用 ${gestureDefaults.path}` : '使用預設手勢參數';
      const warningText = gestureDefaults.warnings.length ? `；${gestureDefaults.warnings.join('；')}` : '';
      calibrationState.innerHTML = `<strong>${escapeHtml(statusText)}</strong>${escapeHtml(warningText)}`;
      calibrationScreen.textContent = `畫面：${gestureDefaults.screenWidth} x ${gestureDefaults.screenHeight}`;
      calibrationScroll.textContent = `捲動：${gestureDefaults.verticalDistance} / ${gestureDefaults.horizontalDistance}`;
      if (calibrationGuideCommand) {
        calibrationGuide.hidden = false;
        calibrationGuideCommandEl.textContent = calibrationGuideCommand;
      }
      updateToolMeta();
    }

    function setInteractionTool(tool, options = {}) {
      if (tool === 'crop' && !templateUrl) {
        setStatus('離線 HTML 無法直接寫入 template 檔案；請使用 record-ui。', 'warn');
        return;
      }
      interactionTool = tool;
      Object.entries(toolButtons).forEach(([name, button]) => {
        button.classList.toggle('active', name === tool);
      });
      updateToolHint();
      if (options.quiet) return;
      const messages = {
        tap: clickMode === 'device' ? '點擊工具：點一下畫面會直接點裝置並擷取下一張。' : '點擊工具：點一下畫面就會新增 tap。',
        swipe: '滑動工具：在畫面上拖出起點與終點，就會加入 swipe。',
        drag: '拖曳工具：在畫面上拖出拖移路徑，就會加入 drag。',
        scroll: '捲動工具：在畫面上拖一下方向，系統會轉成 scroll step。',
        crop: 'Template 工具：在畫面拖曳框出穩定區域，再按「儲存並加入比對」。'
      };
      setStatus(messages[tool], 'ok');
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

    function readPositiveInteger(id, name) {
      const value = Number(document.getElementById(id).value);
      if (!Number.isInteger(value) || value <= 0) {
        alert(`${name} 必須是正整數。`);
        return null;
      }
      return value;
    }

    function readNonNegativeInteger(id, name) {
      const value = Number(document.getElementById(id).value);
      if (!Number.isInteger(value) || value < 0) {
        alert(`${name} 必須是 0 或正整數。`);
        return null;
      }
      return value;
    }

    function readDuration() {
      const duration = readPositiveInteger('gestureDuration', '時間');
      if (duration === null) return null;
      if (duration < 50 || duration > 5000) {
        alert('時間必須介於 50 到 5000 ms。');
        return null;
      }
      return duration;
    }

    function readScrollDistance(direction) {
      const distanceInput = document.getElementById('gestureDistance');
      const value = Number(distanceInput.value);
      if (!Number.isInteger(value) || value <= 0) {
        alert('距離 必須是正整數。');
        return null;
      }
      const calibrated = direction === 'left' || direction === 'right' ? gestureDefaults.horizontalDistance : gestureDefaults.verticalDistance;
      if (value === gestureDefaults.verticalDistance || value === gestureDefaults.horizontalDistance) {
        distanceInput.value = calibrated;
        return calibrated;
      }
      return value;
    }

    async function recordSwipeLike(type) {
      const x1 = readNonNegativeInteger('gestureX1', 'X1');
      const y1 = readNonNegativeInteger('gestureY1', 'Y1');
      const x2 = readNonNegativeInteger('gestureX2', 'X2');
      const y2 = readNonNegativeInteger('gestureY2', 'Y2');
      const duration = readDuration();
      if ([x1, y1, x2, y2, duration].some(value => value === null)) return;
      const step = { type, x1, y1, x2, y2, duration_ms: duration, label: label.value || type };
      if (clickMode === 'device' && stepCaptureUrl) {
        await deviceStepCapture(step);
        return;
      }
      recordSteps([step], { autoBefore: true });
    }

    function handleCanvasPointerDown(event) {
      if (!image.naturalWidth || !image.naturalHeight) return;
      event.preventDefault();
      image.setPointerCapture(event.pointerId);
      const point = imagePoint(event);
      pointerDraft = { pointerId: event.pointerId, tool: interactionTool, start: point, current: point };
      updatePointerCoords(point);
      if (interactionTool === 'crop') {
        updateCropSelection(point.x, point.y, 1, 1);
        return;
      }
      if (interactionTool === 'swipe' || interactionTool === 'drag' || interactionTool === 'scroll') {
        updateGesturePreview(interactionTool, point, point);
      }
    }

    function handleCanvasPointerMove(event) {
      const point = imagePoint(event);
      updatePointerCoords(point);
      if (!pointerDraft) return;
      event.preventDefault();
      pointerDraft.current = point;
      if (pointerDraft.tool === 'crop') {
        const rect = normalizeRect(pointerDraft.start, point);
        updateCropSelection(rect.x, rect.y, rect.width, rect.height);
        return;
      }
      if (pointerDraft.tool === 'swipe' || pointerDraft.tool === 'drag' || pointerDraft.tool === 'scroll') {
        updateGesturePreview(pointerDraft.tool, pointerDraft.start, point);
      }
    }

    async function handleCanvasPointerUp(event) {
      if (!pointerDraft) return;
      event.preventDefault();
      const point = imagePoint(event);
      const draft = pointerDraft;
      pointerDraft = null;
      clearGesturePreview();
      if (draft.tool === 'tap') {
        if (distanceBetween(draft.start, point) > 16) {
          setStatus('目前是點擊工具；若要拖曳路徑，請切到滑動、拖曳或捲動。', 'warn');
          return;
        }
        if (clickMode === 'device' && stepCaptureUrl) {
          await deviceStepCapture({ type: 'tap', x: point.x, y: point.y, label: label.value || 'tap' });
          return;
        }
        recordSteps([{ type: 'tap', x: point.x, y: point.y, label: label.value || 'tap' }], { autoBefore: true });
        setStatus(`已加入點擊 ${point.x},${point.y}。`, 'ok');
        return;
      }
      if (draft.tool === 'crop') {
        const rect = normalizeRect(draft.start, point);
        updateCropSelection(rect.x, rect.y, rect.width, rect.height);
        setInteractionTool('tap', { quiet: true });
        setStatus(`已框選 template 區域 ${rect.x},${rect.y},${rect.width},${rect.height}，目前切回點擊工具。`, 'ok');
        return;
      }
      const gesture = buildGestureStep(draft.tool, draft.start, point);
      if (!gesture) return;
      if (clickMode === 'device' && stepCaptureUrl) {
        await deviceStepCapture(gesture);
        return;
      }
      recordSteps([gesture], { autoBefore: true });
      setStatus(gestureStatusText(gesture), 'ok');
    }

    function cancelCanvasPointer() {
      pointerDraft = null;
      clearGesturePreview();
      setStatus('已取消目前拖曳操作。', 'warn');
    }

    function imagePoint(event) {
      const rect = image.getBoundingClientRect();
      const x = Math.round((event.clientX - rect.left) * image.naturalWidth / rect.width);
      const y = Math.round((event.clientY - rect.top) * image.naturalHeight / rect.height);
      return {
        x: Math.max(0, Math.min(image.naturalWidth - 1, x)),
        y: Math.max(0, Math.min(image.naturalHeight - 1, y))
      };
    }

    function ensureCropSelection() {
      if (cropSelection) return cropSelection;
      cropSelection = document.createElement('div');
      cropSelection.className = 'crop-selection';
      wrap.appendChild(cropSelection);
      return cropSelection;
    }

    function clearGesturePreview() {
      wrap.querySelectorAll('.gesture-preview').forEach(node => node.remove());
    }

    function updateGesturePreview(tool, start, end) {
      clearGesturePreview();
      drawGestureOverlay(start, end, overlayLabel(tool, start, end), tool, 'gesture-preview');
    }

    function updateCropSelection(x, y, width, height) {
      document.getElementById('cropX').value = x;
      document.getElementById('cropY').value = y;
      document.getElementById('cropWidth').value = width;
      document.getElementById('cropHeight').value = height;
      const selection = ensureCropSelection();
      selection.style.display = 'block';
      selection.style.left = `${image.offsetLeft + x / image.naturalWidth * image.clientWidth}px`;
      selection.style.top = `${image.offsetTop + y / image.naturalHeight * image.clientHeight}px`;
      selection.style.width = `${width / image.naturalWidth * image.clientWidth}px`;
      selection.style.height = `${height / image.naturalHeight * image.clientHeight}px`;
    }

    function updatePointerCoords(point) {
      pointerCoords.textContent = point ? `游標：${point.x}, ${point.y}` : '游標：--';
    }

    function updateToolHint() {
      const hintMap = {
        tap: clickMode === 'device' ? '點擊工具：點一下會對裝置送出 tap，等待後再擷取畫面。' : '點擊工具：點一下畫面就會新增 tap。',
        swipe: '滑動工具：直接在畫面上拖出起點與終點，左下時間線會立刻加入 swipe。',
        drag: '拖曳工具：適合長按拖移的 UI，拖完就會寫入 drag。',
        scroll: '捲動工具：拖一下方向即可，系統會自動判斷上下左右與距離。',
        crop: 'Template 工具：拖曳框選穩定區域，接著用右側按鈕存成 template。'
      };
      toolHint.textContent = hintMap[interactionTool];
      updateToolMeta();
    }

    function updateToolMeta() {
      const waitText = waitMode === 'auto' ? '自動等待' : '手動等待';
      const clickText = clickMode === 'device' ? '裝置模式' : '腳本模式';
      const duration = document.getElementById('gestureDuration').value || '400';
      toolMeta.textContent = `${clickText} / ${waitText} / 手勢 ${duration}ms`;
    }

    function normalizeRect(start, end) {
      return {
        x: Math.min(start.x, end.x),
        y: Math.min(start.y, end.y),
        width: Math.max(1, Math.abs(end.x - start.x)),
        height: Math.max(1, Math.abs(end.y - start.y))
      };
    }

    function distanceBetween(start, end) {
      return Math.hypot(end.x - start.x, end.y - start.y);
    }

    function buildGestureStep(tool, start, end) {
      const distance = Math.round(distanceBetween(start, end));
      if (distance < 18) {
        setStatus('拖曳距離太短，還沒記成手勢。', 'warn');
        return null;
      }
      const duration = readDuration();
      if (duration === null) return null;
      document.getElementById('gestureX1').value = start.x;
      document.getElementById('gestureY1').value = start.y;
      document.getElementById('gestureX2').value = end.x;
      document.getElementById('gestureY2').value = end.y;
      document.getElementById('gestureDistance').value = distance;
      if (tool === 'scroll') {
        const direction = dominantDirection(start, end);
        return { type: 'scroll', direction, distance, duration_ms: duration, label: label.value || `scroll ${direction}` };
      }
      return { type: tool, x1: start.x, y1: start.y, x2: end.x, y2: end.y, duration_ms: duration, label: label.value || tool };
    }

    function dominantDirection(start, end) {
      const dx = end.x - start.x;
      const dy = end.y - start.y;
      if (Math.abs(dx) > Math.abs(dy)) return dx > 0 ? 'right' : 'left';
      return dy > 0 ? 'down' : 'up';
    }

    function overlayLabel(tool, start, end) {
      if (tool === 'scroll') {
        const direction = dominantDirection(start, end);
        return `scroll ${direction} ${Math.round(distanceBetween(start, end))}px`;
      }
      return `${tool} ${start.x},${start.y} -> ${end.x},${end.y}`;
    }

    function gestureStatusText(step) {
      if (step.type === 'scroll') {
        return `已加入捲動 ${step.direction}，距離 ${step.distance}px。`;
      }
      return `已加入${typeLabel(step.type)} ${step.x1},${step.y1} -> ${step.x2},${step.y2}。`;
    }

    function pointToCanvas(point) {
      return {
        x: image.offsetLeft + point.x / image.naturalWidth * image.clientWidth,
        y: image.offsetTop + point.y / image.naturalHeight * image.clientHeight
      };
    }

    function drawGestureOverlay(start, end, text, tool, className = '') {
      const startCanvas = pointToCanvas(start);
      const endCanvas = pointToCanvas(end);
      const deltaX = endCanvas.x - startCanvas.x;
      const deltaY = endCanvas.y - startCanvas.y;
      const length = Math.max(1, Math.hypot(deltaX, deltaY));
      const angle = Math.atan2(deltaY, deltaX) * 180 / Math.PI;
      const line = document.createElement('div');
      line.className = ['gesture-line', tool, className, className ? 'preview' : ''].filter(Boolean).join(' ');
      line.style.left = `${startCanvas.x}px`;
      line.style.top = `${startCanvas.y}px`;
      line.style.width = `${length}px`;
      line.style.transform = `translateY(-50%) rotate(${angle}deg)`;
      wrap.appendChild(line);

      const startHandle = document.createElement('div');
      startHandle.className = ['gesture-handle', tool, 'start', className].filter(Boolean).join(' ');
      startHandle.style.left = `${startCanvas.x}px`;
      startHandle.style.top = `${startCanvas.y}px`;
      wrap.appendChild(startHandle);

      const endHandle = document.createElement('div');
      endHandle.className = ['gesture-handle', tool, className].filter(Boolean).join(' ');
      endHandle.style.left = `${endCanvas.x}px`;
      endHandle.style.top = `${endCanvas.y}px`;
      wrap.appendChild(endHandle);

      const badge = document.createElement('div');
      badge.className = ['gesture-badge', className].filter(Boolean).join(' ');
      badge.textContent = text;
      badge.style.left = `${(startCanvas.x + endCanvas.x) / 2}px`;
      badge.style.top = `${(startCanvas.y + endCanvas.y) / 2}px`;
      wrap.appendChild(badge);
    }

    function scrollOverlayPoints(step) {
      const distance = Math.max(24, Number(step.distance) || 700);
      const half = distance / 2;
      const centerX = image.naturalWidth / 2;
      const centerY = image.naturalHeight / 2;
      const clampX = value => Math.max(0, Math.min(image.naturalWidth - 1, value));
      const clampY = value => Math.max(0, Math.min(image.naturalHeight - 1, value));
      if (step.direction === 'left' || step.direction === 'right') {
        const delta = step.direction === 'left' ? half : -half;
        return {
          start: { x: clampX(centerX + delta), y: clampY(centerY) },
          end: { x: clampX(centerX - delta), y: clampY(centerY) }
        };
      }
      const delta = step.direction === 'up' ? half : -half;
      return {
        start: { x: clampX(centerX), y: clampY(centerY + delta) },
        end: { x: clampX(centerX), y: clampY(centerY - delta) }
      };
    }

    function render() {
      rows.replaceChildren();
      wrap.querySelectorAll('.marker, .gesture-line, .gesture-handle, .gesture-badge, .back-badge').forEach(node => node.remove());
      commands.value = steps.map(stepToCommand).filter(Boolean).join('\\n');
      yaml.value = profileToYaml() + 'steps:\\n' + steps.map(stepToYaml).join('\\n');

      steps.forEach((step, index) => {
        const tr = document.createElement('tr');
        const remove = index === 0 ? '' : `<button class="mini" type="button" data-remove="${index}">移除</button>`;
        tr.innerHTML = `<td>${index + 1}</td><td>${escapeHtml(typeLabel(step.type))}</td><td>${escapeHtml(stepDetail(step))}</td><td>${remove}</td>`;
        rows.appendChild(tr);
        if (step.type === 'tap') {
          const marker = document.createElement('div');
          marker.className = 'marker';
          marker.style.left = `${image.offsetLeft + step.x / image.naturalWidth * image.clientWidth}px`;
          marker.style.top = `${image.offsetTop + step.y / image.naturalHeight * image.clientHeight}px`;
          marker.innerHTML = `<span>${index + 1}</span>`;
          wrap.appendChild(marker);
          return;
        }
        if (step.type === 'swipe' || step.type === 'drag') {
          drawGestureOverlay(
            { x: step.x1, y: step.y1 },
            { x: step.x2, y: step.y2 },
            `${index + 1}. ${typeLabel(step.type)}`,
            step.type
          );
          return;
        }
        if (step.type === 'scroll') {
          const points = scrollOverlayPoints(step);
          drawGestureOverlay(points.start, points.end, `${index + 1}. 捲動 ${step.direction}`, 'scroll');
          return;
        }
        if (step.type === 'back') {
          const badge = document.createElement('div');
          badge.className = 'back-badge';
          badge.textContent = `${index + 1}. 返回`;
          wrap.appendChild(badge);
        }
      });
      if (steps.length === 1) {
        const tr = document.createElement('tr');
        tr.innerHTML = '<td colspan="4" class="empty">尚未加入動作。先選上方工具，再直接在左側畫面點一下或拖曳即可。</td>';
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

    async function deviceStepCapture(step) {
      const manualWait = readSeconds('waitSeconds', 1);
      const minWait = readSeconds('minAutoWait', 1);
      const maxWait = readSeconds('maxAutoWait', 12);
      if (manualWait === null || minWait === null || maxWait === null || minWait > maxWait) {
        setStatus('等待設定不正確，請確認秒數。', 'danger');
        return;
      }
      const actionLabel = typeLabel(step.type);
      setStatus(waitMode === 'auto' ? `正在執行${actionLabel}，並等待畫面變化...` : `正在執行${actionLabel}，等待後擷取畫面...`);
      try {
        const payload = await postJson(stepCaptureUrl || tapCaptureUrl, {
          step,
          wait_seconds: manualWait,
          auto_wait: waitMode === 'auto',
          min_wait_seconds: minWait,
          max_wait_seconds: maxWait,
          poll_seconds: 0.5,
          stable_seconds: 1.2
        });
        applyCapturePayload(payload, false);
      } catch (error) {
        setStatus(`${actionLabel}與擷取失敗：${error}`, 'danger');
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
      const checkpointHint = checkpointHintForCapture(payload, autoBefore);
      setStatus((payload.messages ? payload.messages.join(' ') : payload.status) + waitText + checkpointHint, 'ok');
      if (checkpointHint) {
        showNextAction('建立畫面驗證', '框選新畫面上的穩定 UI，儲存成 template checkpoint。');
        focusTemplateWorkflow({ quiet: true });
      }
      render();
    }

    function checkpointHintForCapture(payload, autoBefore) {
      if (autoBefore || !templateUrl || !Array.isArray(payload.steps)) return '';
      const hasDeviceAction = payload.steps.some(step => ['tap', 'swipe', 'drag', 'scroll', 'back'].includes(step.type));
      return hasDeviceAction ? ' 建議接著框選穩定 UI 區塊，儲存 template checkpoint。' : '';
    }

    function focusTemplateWorkflow(options = {}) {
      if (!templateUrl) return;
      ensureCropSelection();
      cropSelection.style.display = 'none';
      setInteractionTool('crop', options);
    }

    function showNextAction(title, text) {
      nextActionTitle.textContent = title;
      nextActionText.textContent = text;
      nextAction.hidden = false;
    }

    function hideNextAction() {
      nextAction.hidden = true;
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
        swipe: '滑動',
        drag: '拖曳',
        scroll: '捲動',
        back: '返回',
        wait: '等待',
        checkpoint_exists: '檔案檢查',
        checkpoint_match: '圖像比對'
      }[type] || type;
    }

    function stepDetail(step) {
      if (step.type === 'tap') return `${step.x},${step.y} - ${step.label}`;
      if (step.type === 'swipe' || step.type === 'drag') return `${step.x1},${step.y1} -> ${step.x2},${step.y2} / ${step.duration_ms}ms - ${step.label}`;
      if (step.type === 'scroll') return `${step.direction} / ${step.distance || 700}px / ${step.duration_ms || 400}ms - ${step.label}`;
      if (step.type === 'back') return step.label;
      if (step.type === 'wait') return `${step.seconds} 秒`;
      if (step.type === 'screenshot') return step.out;
      if (step.type === 'checkpoint_exists') return step.path;
      if (step.type === 'checkpoint_match') return `${step.source} -> ${step.template} @ ${step.threshold}`;
      return '';
    }

    function stepToCommand(step) {
      if (step.type === 'tap') return `tap ${step.x} ${step.y} ${step.label}`;
      if (step.type === 'swipe' || step.type === 'drag') return `${step.type} ${step.x1} ${step.y1} ${step.x2} ${step.y2} ${step.duration_ms} ${step.label}`;
      if (step.type === 'scroll') return `scroll ${step.direction} ${step.distance || 700} ${step.duration_ms || 400} ${step.label}`;
      if (step.type === 'back') return `back ${step.label}`;
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
      if (step.type === 'swipe' || step.type === 'drag') return [
        `  - type: ${step.type}`,
        `    x1: ${step.x1}`,
        `    y1: ${step.y1}`,
        `    x2: ${step.x2}`,
        `    y2: ${step.y2}`,
        `    duration_ms: ${step.duration_ms}`,
        `    label: ${yamlString(step.label)}`
      ].join('\\n');
      if (step.type === 'scroll') return [
        '  - type: scroll',
        `    direction: ${yamlString(step.direction)}`,
        `    distance: ${step.distance || 700}`,
        `    duration_ms: ${step.duration_ms || 400}`,
        `    label: ${yamlString(step.label)}`
      ].join('\\n');
      if (step.type === 'back') return [
        '  - type: back',
        `    label: ${yamlString(step.label)}`
      ].join('\\n');
      if (step.type === 'wait') return ['  - type: wait', `    seconds: ${step.seconds}`].join('\\n');
      if (step.type === 'screenshot') return ['  - type: screenshot', `    out: ${yamlString(step.out)}`].join('\\n');
      if (step.type === 'checkpoint_exists') return ['  - type: checkpoint_exists', `    path: ${yamlString(step.path)}`].join('\\n');
      if (step.type === 'checkpoint_match') return [
        '  - type: checkpoint_match',
        `    source: ${yamlString(step.source)}`,
        `    template: ${yamlString(step.template)}`,
        `    threshold: ${step.threshold === undefined ? 0.95 : step.threshold}`
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

    window.addEventListener('resize', render);
    updateToolHint();
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
        .replace("__STEP_CAPTURE_URL__", step_capture_url_value)
        .replace("__RUN_URL__", run_url_value)
        .replace("__TEMPLATE_URL__", template_url_value)
        .replace("__CALIBRATION__", calibration_value)
        .replace("__CALIBRATION_GUIDE_COMMAND__", calibration_guide_command_value)
        .replace("__ALLOW_DEVICE_INPUT__", allow_device_input_value)
        .replace("__PROFILE__", profile_value)
        .replace("__DEVICE_INPUT_LABEL__", html.escape(device_input_label))
        .replace("__SERIAL_LABEL__", html.escape(serial_label))
        .replace("__ADB_LABEL__", html.escape(adb_label))
    )
