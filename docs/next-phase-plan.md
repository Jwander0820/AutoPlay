# 下一階段規劃書

## 階段目標

下一階段要把 AutoPlay 從「可測的自動化工具」推進到「人和本地 AI 都能安全操作的本機自動化工作台」。

核心方向有三個：

1. 讓人類測試更順：少打指令、少猜狀態、少碰私有路徑。
2. 讓模擬器相容更清楚：LDPlayer、BlueStacks、Generic ADB 都透過 profile 隔離差異。
3. 讓本地 AI 有可呼叫工具邊界：Skill 負責說明規則，MCP 或本機 JSON bridge 負責真正執行工具。

## 目前基礎

- `run_autoplay.cmd` / `run_autoplay.py` 可開啟繁體中文開發測試工具。
- Launcher 支援 emulator profile、ADB path、serial、connect targets、本機預設儲存、截圖、dry-run tap/scroll、真實 tap/scroll 確認與 Recorder UI 啟動。
- 使用者私有設定放在 `config/autoplay.local.json`，並由 `.gitignore` 排除。
- 可追蹤範本放在 `config/autoplay.example.json`。
- `record-ui` 已顯示四段工作流：連線、擷取、錄製、驗證。
- `record-ui` 已顯示執行環境狀態：裝置輸入、serial、ADB 來源。
- `src/autoplay/api.py` 是核心 Python API。
- `src/autoplay/agent_tools.py` 是 AI-facing 安全層，具備 dry-run 預設、step budget、audit log 與 unsafe intent blocking。
- `docs/ai-local-automation-plan.md` 已記錄本地 AI 對話整體方向。
- `docs/specs/0022-local-ai-tool-interface.md` 已草擬本地 AI tool bridge / MCP 映射規格。

## 產品化優先順序

### 1. 測試入口產品化

目標：使用者打開 launcher 後，可以用少數按鈕確認環境可用。

下一步：

- 在 launcher 加上狀態燈：ADB path 是否存在、serial 是否可用、截圖是否成功、Recorder server 是否執行中。
- 在 launcher 加上截圖預覽縮圖，讓使用者不用開資料夾也知道是否抓到正確畫面。
- 把「一鍵煙霧測試」結果整理成清楚摘要，而不是只看 log。
- 加上「開啟 artifacts/manual」與「開啟目前腳本」按鈕。

驗收：

- 使用者開 launcher 後，不需要 CMD 就能確認 LDPlayer 是否可控。
- smoke test 不送真實輸入，並能明確指出失敗卡在哪一步。

### 2. Recorder UI 易用性

目標：錄製腳本時，使用者能清楚知道目前是在「只寫腳本」還是「會送真實輸入」。

下一步：

- 將「裝置模式 / 腳本模式」改成更明顯的狀態區。
- 每次 device action 後，強化 template checkpoint 的引導與預覽品質提示。
- 增加「目前 YAML 是否已儲存」提示。
- 增加「最近一次截圖時間 / 截圖來源」顯示。

驗收：

- 使用者完成一次 tap 或 scroll 後，能自然接著建立 checkpoint。
- 使用者不會誤以為 dry-run 已經送出真實點擊。

### 3. 模擬器相容性

目標：不同模擬器差異集中在 profile 與 calibration，不擴散到核心 API。

下一步：

- 將 emulator profile 擴充為可由 local config 覆寫常見 port、ADB candidates、window title hints。
- 針對 LDPlayer 實測 serial、截圖尺寸、scroll 距離，寫入 local calibration notes。
- 保留 BlueStacks profile，但避免新功能綁死 BlueStacks 名稱。

驗收：

- LDPlayer 測試通過時，不需要改核心 `api.py`。
- BlueStacks 使用者仍可透過 profile 或手動 ADB path 使用既有流程。

### 4. 本地 AI Tool Bridge

目標：先建立本機 JSON tool bridge，再包成 MCP。

設計判斷：

- Skill 不適合直接執行操作，它是給 AI 讀的操作手冊與安全規則。
- MCP 或本機 tool server 才適合讓 AI 呼叫 `doctor`、`screenshot`、`match`、`tap`、`run_script` 等工具。
- 第一版可以先做 JSON bridge，之後薄薄包成 MCP。

下一步：

- 新增 `src/autoplay/ai_bridge.py`，輸入 `{ "tool": "...", "args": {...} }`，輸出 `{ "ok": true/false, ... }`。
- bridge 只呼叫 `AgentSession`，不得直接繞過安全層。
- 新增 CLI，例如 `python -m autoplay ai-tool request.json`，方便本地 AI 或外部程式測試。
- 定義 MCP server 時，讓 MCP tool schema 對齊 JSON bridge schema。

驗收：

- AI bridge 可呼叫 `doctor`、`screenshot`、dry-run `tap`、dry-run `scroll`。
- 未授權時，real tap/scroll 一律被擋。
- 所有 AI tool call 都寫 audit log。

### 5. 安全與隱私

目標：自動化能力變強，但不犧牲本機隱私與安全邊界。

下一步：

- 繼續保證 `config/*.local.json`、`artifacts/`、`scripts/` 不進 git。
- commit 前掃描 staged diff 是否有私人路徑、token、credential。
- AI tool 預設只能寫 `artifacts/`。
- 真實裝置輸入必須同時滿足 local policy、tool args、step budget、audit log。

驗收：

- git diff 不包含使用者私有 ADB path。
- AI 不可在未授權狀態下送真實 device input。

## 建議下一個實作切片

優先做 `0022` 的第一個可測版本：

1. `ai_bridge.py`
2. `ai-tool` CLI
3. `doctor` / `screenshot` / dry-run `tap` / dry-run `scroll`
4. audit log
5. 單元測試

這個切片能直接支撐未來 MCP，也能先讓本地 AI 用 JSON 呼叫 AutoPlay，而不需要先綁定某個 AI 客戶端。
