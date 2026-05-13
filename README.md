# AutoPlay

## 2026-05-14 Local AI Provider Chat Stage

This stage makes AutoPlay usable from local and hosted chat models while keeping the existing safety bridge as the only execution path.

Completed AI integration entrypoints:

- `py -m autoplay ai-chat --provider ollama --model <model> --prompt "..."`
- `py -m autoplay ai-chat --provider lmstudio --model <loaded-model> --prompt "..."`
- `py -m autoplay ai-chat --provider openai --model <model> --prompt "..."`
- `py -m autoplay ai-chat-smoke`
- `py -m autoplay ai-mcp-stdio`
- `py -m autoplay ai-mcp-smoke`

Provider defaults:

- Ollama: `http://127.0.0.1:11434/api/chat`
- LM Studio: `http://127.0.0.1:1234/v1/chat/completions`
- OpenAI: `https://api.openai.com/v1/chat/completions`, using `OPENAI_API_KEY` unless `--api-key` is supplied

Safety model:

- Chat model tool calls still route through `AiBridge -> AgentSession -> api.py`.
- Real device input remains blocked unless the session allows it, the tool call sets `execute=true`, and a configured `device_input_code` matches.
- Use repeated `--tool <name>` flags to limit which AutoPlay tools the model can see and call.
- Use `--transcript-out <path>` to write a sanitized debug transcript.
- Sanitized transcripts redact local command paths and absolute local file paths.

Offline smoke test:

```powershell
py -m autoplay ai-chat-smoke --artifact-root artifacts\ai-chat-smoke --out artifacts\ai-chat-smoke\result.json --transcript-out artifacts\ai-chat-smoke\transcript.json
```

Recommended first real-provider tests:

```powershell
py -m autoplay ai-chat --provider ollama --model <ollama-model> --prompt "Draft a wait-only reviewable script." --tool draft_script --transcript-out artifacts\ai-chat\ollama-transcript.json
py -m autoplay ai-chat --provider lmstudio --model <loaded-model> --prompt "Validate scripts\example.yml." --tool validate --transcript-out artifacts\ai-chat\lmstudio-transcript.json
```

AutoPlay 是一個以 BlueStacks / Android Emulator 為起點的本機自動化工具。現在的目標是先讓使用者能用 Web UI 半自動錄製每日任務腳本，再逐步加入畫面判斷、checkpoint 與 AI 輔助決策。

目前已支援：

- 透過 ADB 擷取畫面、點擊、滑動、拖曳、捲動、返回、執行腳本與驗證腳本
- 用 Web UI 點畫面產生 YAML 腳本
- 點擊後自動擷取下一張畫面
- 直接在截圖上拖曳的手機手勢錄製：`swipe`、`drag`、`scroll`，以及快速加入 `back`
- 在 device mode 中，tap 與手勢都能走「執行 -> 等待 -> 擷取下一張畫面」錄製迴圈
- 在 Web UI 框選截圖區域並儲存為 template，再自動加入 `checkpoint_match`
- 手動或自動估算動作之間的等待秒數
- dry-run、安全驗證、執行報告與 AI-facing audit log

## 本階段進度總結

本階段把 AutoPlay 從「可點擊與截圖」推進到「可錄製可驗證的手機操作流程」：

- 手機手勢已成為一等 DSL step：`swipe`、`drag`、`scroll`、`back` 可從 CLI、API、runner、agent tools、guided recorder 與 Web UI 使用。
- Web UI 已能在截圖上直接點擊、拖曳、框選 template，並把 tap、gesture、wait、screenshot、`checkpoint_match` 寫入同一份 YAML。
- device mode 已支援 tap/gesture 的「執行 -> 等待 -> 擷取」迴圈，適合逐步錄製多畫面日常流程。
- device mode 在 tap/gesture 擷取完成後會顯示下一步提示、切到 Template 工具，幫助流程從座標錄製走向畫面驗證。
- recorder 會保留 `profile.serial`，並可載入 serial-aware gesture calibration profile，讓 BlueStacks 多裝置或多開時的操作更可控。
- AI-facing 執行路徑仍維持安全預設：dry-run first、明確 opt-in 真實輸入、step budget、JSON report 與 JSONL audit log。
- `calibration guide` 已提供 CLI-first 的手勢校準流程，能用 dry-run 預覽、測試者回饋與最後確認來產生 profile JSON 與 notes。

尚未完成的是自動決策。AutoPlay 目前不會自行理解遊戲畫面並任意點擊；下一階段會先用真實 BlueStacks 驗證校準與 checkpoint 穩定度，再用 checkpoint/template match 建立 bounded decision loop。

## 安裝與環境檢查

請在 Windows PowerShell 執行：

```powershell
cd D:\SideProject\AutoPlay
py -m pip install -e ".[dev]"
py -m autoplay doctor
```

測試 BlueStacks 前，請先確認：

1. BlueStacks 已開啟。
2. BlueStacks 設定中已啟用 Android Debug Bridge。
3. `py -m autoplay doctor` 能找到 ADB 與裝置。

如果看到這種錯誤：

```text
error: more than one device/emulator
```

代表 ADB 同時看到多個目標，例如多開的 BlueStacks、Android Emulator、手機，或殘留的 emulator instance。這時需要指定要操作哪一台。

先查看裝置清單：

```powershell
py -m autoplay doctor
```

在輸出中找到類似這種 serial：

```text
emulator-5554
127.0.0.1:5555
```

然後把 `--serial` 加到指令中，例如：

```powershell
py -m autoplay record-ui scripts\user-test-daily.yml --screenshot artifacts\manual\user-test-start.png --capture --allow-device-input --serial emulator-5554
```

之後需要操作同一台裝置的指令也建議加上同一個 `--serial`，例如：

```powershell
py -m autoplay screenshot --out artifacts\manual\screen.png --serial emulator-5554
py -m autoplay tap 100 100 --yes --serial emulator-5554
py -m autoplay scroll down --distance 700 --yes --serial emulator-5554
py -m autoplay agent-run scripts\user-test-daily.yml --execute-taps --allow-device-input --serial emulator-5554
```

另一個簡單解法是先關掉其他 Android Emulator、手機連線或多開的 BlueStacks，讓 `py -m autoplay doctor` 只看到一台裝置。

## 最推薦的使用方式：Web UI 錄製腳本

如果你想做使用者測試，請優先從 `record-ui` 開始。它會開一個本機 Web UI，讓你用截圖點選位置、加入等待、擷取下一張畫面，並直接儲存 YAML 腳本。

### 只錄製腳本，不操作 BlueStacks

這是最安全的模式，適合第一次測試：

```powershell
py -m autoplay record-ui scripts\user-test-daily.yml --screenshot artifacts\manual\user-test-start.png --capture
```

執行後，終端機會印出一個 localhost 網址。打開後會看到「AutoPlay 錄製工作台」。

建議流程：

1. 先在上方選工具，然後直接在左側畫面點一下或拖曳。
2. 點擊會新增 `tap`；滑動、拖曳、捲動會在畫面上拖出路徑後直接寫成 step。
3. 如果畫面需要等待，使用「等待策略」或按「加入等待」。
4. 如果你手動在 BlueStacks 操作到下一個畫面，按「擷取最新畫面」。
5. 需要驗證時，可切到 Template 工具框選穩定區塊，再儲存成 `checkpoint_match`。
6. 重複操作、等待、擷取。
7. 按「儲存並驗證」。
8. 檢查右側 YAML 與驗證訊息。

這個模式不會送出真實 tap，所以即使點錯也不會操作遊戲。

### 允許 Web UI 直接點擊 BlueStacks

確認畫面安全後，可以啟用裝置輸入：

```powershell
py -m autoplay record-ui scripts\user-test-daily.yml --screenshot artifacts\manual\user-test-start.png --capture --allow-device-input
```

如果 ADB 有多個裝置，請加上 `--serial`：

```powershell
py -m autoplay record-ui scripts\user-test-daily.yml --screenshot artifacts\manual\user-test-start.png --capture --allow-device-input --serial emulator-5554
```

使用 `record-ui --serial ...` 啟動時，Web UI 儲存的 YAML 會自動寫入 `profile.serial`，之後直接跑同一份腳本時，runner 也知道要操作哪一台裝置。

如果有本地校準檔，Web UI 也會依照 serial 載入手勢校準，例如：

```text
artifacts\calibration\bluestacks-emulator-5554.json
```

可以先用 CLI 建立或檢視校準檔：

```powershell
py -m autoplay calibration write --serial emulator-5554 --from-screenshot artifacts\manual\user-test-start.png --scroll-vertical-distance 760 --scroll-horizontal-distance 520
py -m autoplay calibration show --serial emulator-5554
py -m autoplay scroll down --calibrated --serial emulator-5554
```

目前校準狀態會顯示在左側畫面上方的「手勢校準」區塊。第一次測試時請注意它是「使用預設手勢參數」還是「已套用」某個檔案，並確認顯示的畫面尺寸與捲動距離符合你的 BlueStacks。

也可以用 guided flow 產生同一種 profile，避免手動猜距離與編輯 JSON：

```powershell
py -m autoplay calibration guide --serial emulator-5554 --from-screenshot artifacts\manual\user-test-start.png
```

預設只會印出 dry-run 預覽指令，不會送出真實手勢。如果要在流程中允許單次真實 scroll 測試，需加上 `--yes`，而且每次真實 scroll 前仍要在 prompt 輸入 `yes`。
每個方向最多會進行 6 輪回饋，可用 `--max-rounds` 調整。

使用 `record-ui --serial ...` 時，手勢校準區塊也會顯示對應目前 serial 與 screenshot 的 `calibration guide` 指令，方便直接從錄製工作台接續校準。
這個指令可以在 UI 中直接複製到剪貼簿。
如果目前截圖尺寸和已載入的校準 profile 尺寸不同，這裡也會顯示警告，請先重新校準或確認 BlueStacks 解析度。

打開 Web UI 後，將「點擊模式」切到「點擊後擷取」。

這時點左側畫面或用手勢工具拖曳會執行：

1. 送出真實 ADB tap 或手勢。
2. 等待畫面穩定。
3. 擷取下一張畫面。
4. 自動把原始 step、`wait`、`screenshot` 寫進 YAML。
5. 提示你框選穩定 UI 區塊，並切到 Template 工具以建立 `checkpoint_match`。

儲存 template 時，server 會在你框選的區域做一次 checkpoint preview，並回傳簡單品質提示，例如 template 太小、太大或門檻值偏低。這只是協助檢查，不會自動選圖或自動判斷下一步。

請只在安全畫面使用這個模式，不要測試購買、抽卡、交易、刪除、聊天、PvP、驗證碼、帳號密碼或任何有帳號風險的操作。

### 在 Web UI 直接測試目前腳本

Web UI 右上方有兩個測試按鈕：

- 「測試腳本」：執行目前 YAML 的 dry-run，不會送出真實 tap 或手勢。
- 「真實測試」：只有用 `--allow-device-input` 啟動時可用，會對裝置送出真實 tap 與手勢。

建議流程：

1. 先按「儲存並驗證」。
2. 再按「測試腳本」確認流程與 report 正常。
3. 確認畫面安全後，才按「真實測試」。

Web UI 測試會產生 report 與 audit log，路徑會顯示在狀態列。

## 等待策略怎麼用

Web UI 目前有兩種等待策略。

### 手動秒數

適合畫面變化時間很固定的操作，例如點擊後大約固定等 1 秒。

使用方式：

1. 選「手動秒數」。
2. 在「手動等待秒數」填入秒數，例如 `1` 或 `1.5`。
3. 按「加入等待」，或在「點擊後擷取」模式下讓 UI 自動把這個等待寫進 YAML。

### 自動估算

適合畫面載入時間不固定的操作。

在「只記錄腳本」模式下，自動估算會用兩次錄製操作之間的實際時間來插入 `wait`。

在「點擊後擷取」模式下，自動估算會在 tap 後持續擷取畫面，直到畫面已經變化並維持穩定一小段時間，或達到「最長等待」為止。UI 會把實際等待秒數寫回 YAML。

建議設定：

- 最短等待：`1`
- 最長等待：`12`

如果遊戲載入較慢，可以把最長等待調高，例如 `12`。

## 產生的腳本放在哪裡

建議把個人測試腳本放在：

```text
scripts\
```

例如：

```text
scripts\user-test-daily.yml
scripts\my-daily.yml
```

`scripts/` 屬於本機個人腳本，預設不應提交到 GitHub。

截圖、報告與測試產物建議放在：

```text
artifacts\
```

例如：

```text
artifacts\manual\user-test-start.png
artifacts\reports\my-daily-agent-dry-run.json
artifacts\agent\my-daily-agent.jsonl
```

`artifacts/` 也不應提交到 GitHub。

## 驗證腳本

錄完腳本後先跑驗證：

```powershell
py -m autoplay validate scripts\user-test-daily.yml
```

如果驗證通過，再做 dry-run：

```powershell
py -m autoplay agent-run scripts\user-test-daily.yml --report-out artifacts\reports\user-test-agent-dry-run.json --audit-out artifacts\agent\user-test-agent.jsonl --intent "user test dry run" --serial emulator-5554
```

如果腳本裡已經有 `profile.serial`，可以省略指令列上的 `--serial`。

`agent-run` 預設不會真的點擊或操作手勢。它會產生：

- JSON report
- JSONL audit log

請先確認 report 與 audit log 合理，再考慮真實裝置輸入。

## 真實執行腳本

只有在你確認腳本安全、畫面正確、dry-run 報告正常後，才使用真實裝置輸入：

```powershell
py -m autoplay agent-run scripts\user-test-daily.yml --execute-taps --allow-device-input --report-out artifacts\reports\user-test-agent-real.json --audit-out artifacts\agent\user-test-agent-real.jsonl --intent "safe user test real run" --serial emulator-5554
```

真實執行前請再次確認：

1. BlueStacks 畫面停在腳本預期的起始畫面。
2. 腳本不包含高風險操作。
3. dry-run 報告中的步驟順序正確。
4. 你可以隨時停止流程。

## 離線座標工具：click-map

如果你只想用一張截圖產生腳本，不需要啟動本機 server，可以用：

```powershell
py -m autoplay click-map artifacts\manual\user-test-start.png --capture --out artifacts\manual\user-test-builder.html --script-out user-test-daily.yml
```

打開產生的 HTML 後，可以點截圖產生 tap、加入手勢、wait/checkpoint，最後下載 YAML。

這個模式不會直接儲存到 `scripts\`，也不會操作 BlueStacks。

## 實驗功能：BlueStacks live click 錄製

如果想直接監聽你在 BlueStacks 視窗上的點擊，可以試：

```powershell
py -m autoplay screenshot --out artifacts\manual\live-start.png
py -m autoplay record-clicks scripts\live-test.yml --screenshot artifacts\manual\live-start.png --max-clicks 5
```

這個功能目前是實驗性質。BlueStacks 視窗邊框、側邊欄、DPI scaling 或 renderer 設定都可能讓座標偏移。錄完後一定要先：

```powershell
py -m autoplay validate scripts\live-test.yml
py -m autoplay agent-run scripts\live-test.yml --report-out artifacts\reports\live-test-agent-dry-run.json --audit-out artifacts\agent\live-test-agent.jsonl --intent "live click recorder dry run"
```

## 使用者測試時請回報

測試時請記錄：

- `py -m autoplay doctor` 的結果
- 使用的指令
- Web UI 選擇的點擊模式、手勢設定與等待策略
- 產生的 YAML 腳本
- 截圖檔案
- dry-run report
- audit log
- 哪一步和預期不同

如果畫面等待時間不穩定，請特別記錄：

- 手動秒數是否太短或太長
- 自動估算是否有等到畫面變化
- 是否達到最長等待才繼續

## 安全邊界

使用者測試階段請不要測：

- 購買
- 抽卡或召喚
- 交易
- 刪除
- 聊天
- PvP
- 驗證碼
- 帳號密碼輸入
- 反作弊繞過
- root、hook、memory 修改

目前請把測試範圍限制在安全導航、截圖、等待、checkpoint、dry-run tap/gesture，以及你可以明確回復的日常流程。

## 下一階段

請從 `docs/stage-report.md`、`docs/next-stage.md` 與 `docs/specs/0020-guided-gesture-calibration.md` 接續：

1. 用真實 BlueStacks 測試 `py -m autoplay calibration guide` 產生的 scroll distance、screen dimensions 與 notes 是否足夠好用。
2. 用真實 BlueStacks 測試 record-ui 顯示的 `calibration guide` 指令是否能順利承接目前 serial/screenshot。
3. 用真實 BlueStacks 測試 tap/gesture 後的 template checkpoint 穩定度。
4. 在 checkpoint 足夠可靠後，再設計第一個 bounded decision loop：讀 screenshot、跑 template match、選下一個安全 scripted step，並在真實裝置輸入前停下給使用者確認。
