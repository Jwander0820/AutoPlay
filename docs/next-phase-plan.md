# 下一階段規劃書

## 階段定位

AutoPlay 目前已完成從「人類手動測試工具」走向「本地 AI 可安全調用工具」的基礎：

- LDPlayer / BlueStacks / generic ADB profile 與本機設定分離。
- PyCharm/CMD 友善 launcher 與繁體中文 Recorder UI 已可支援測試。
- AI-facing 工具已集中到 `AgentSession` 安全層。
- JSON bridge、HTTP server、schemas、examples、smoke client、`draft_script` 已完成。
- 真實裝置輸入預設 dry-run，並可用 session-only `device_input_code` 額外保護。

下一階段的目標不是讓 AI 自由點擊，而是完成「本地 AI 對話到可審核腳本」的閉環。

## 下一階段目標

### 1. 本地 AI / MCP 接入薄封裝

目標：讓支援 MCP 或本地工具呼叫的 AI client 可以直接調用 AutoPlay。

工作項目：

- 新增薄 MCP wrapper 或等價 local chat integration spike。
- MCP wrapper 只負責轉換請求，不複製安全邏輯。
- 所有工具仍走 `AiBridge -> AgentSession -> api.py`。
- 將 `ai-schemas` 的工具描述對齊 MCP tool schema。

驗收：

- MCP/local client 可呼叫 `doctor`、`draft_script`、`validate`、dry-run `run_script`。
- 真實輸入仍需 `allow_device_input`、`execute=true`、`device_input_code`。
- `ai-smoke` 或等價 smoke test 能驗證接線。

### 2. 對話式腳本草稿流程

目標：讓 AI 先產出可審核 YAML，而不是直接操作模擬器。

建議流程：

```text
User intent -> AI calls draft_script -> validate -> dry-run run_script -> human review -> guarded real input
```

工作項目：

- 擴充 `draft_script` 範例，涵蓋 checkpoint-first 腳本。
- 新增 AI 可讀的 script authoring guidance。
- 將常用測試流程沉澱為範本：啟動畫面、每日任務入口、等待、截圖、checkpoint。

驗收：

- AI 可以根據使用者意圖產出 `scripts/*.yml`。
- 草稿立即 validate，回傳錯誤/警告。
- dry-run report 可供人類檢查。

### 3. LDPlayer 真機校準與 Recorder 可靠性

目標：確認實際 LDPlayer 畫面、座標、scroll 距離與 checkpoint 工作流穩定。

工作項目：

- 用真實 LDPlayer 執行 `doctor`、`screenshot`、`calibration guide`。
- 對常用解析度建立 serial-aware calibration profile。
- 在 Recorder UI 中驗證 device step capture、template crop、checkpoint nudge。
- 將測試結果寫回 `docs/stage-report.md`。

驗收：

- LDPlayer screenshot 可穩定取得。
- Tap/scroll dry-run command 與實際座標預期一致。
- 至少一個 checkpoint_match 流程可重複驗證。

### 4. 決策迴圈前置能力

目標：為未來 bounded decision loop 準備，但不讓 AI 自主無限制操作。

工作項目：

- 建立 screenshot -> template match -> next scripted step 的設計草案。
- 先限制在 dry-run 或 stop-for-review 模式。
- 定義每輪最大步數、必要 checkpoint、失敗停止條件。

驗收：

- 決策迴圈 spec 完成。
- 第一版只輸出建議/草稿，不送出真實裝置輸入。

## 安全原則

- 私有路徑只放在 `config/autoplay.local.json`，不得提交。
- `artifacts/`、`scripts/`、local config 仍預設不進 git。
- AI 工具不得直接呼叫 raw ADB。
- 真實輸入必須同時符合 local policy、單次 request `execute=true`、必要時提供 `device_input_code`。
- 所有 AI-facing tool call 必須有 audit log 或等價可追蹤紀錄。

## 建議下一個實作切片

優先實作「local chat / MCP spike」：

1. 建立最小 MCP wrapper 或 local chat tool adapter。
2. 只映射 `doctor`、`draft_script`、`validate`、`run_script` dry-run。
3. 用 `ai-smoke` 或新增 smoke test 確認接線。
4. 更新 `AGENT.md` 與 specs。

這會讓 AutoPlay 進入可以和本地 AI 對話測試的狀態，同時維持可審核、可停止、可回滾。
