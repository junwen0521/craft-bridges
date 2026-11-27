# pc API

`pc` 把 PhotoCraft 的控制埠包成指令。預設 `127.0.0.1:7878`。每一條連線的第一行必須是：

```json
{"id": "auth", "method": "auth", "params": {"token": "<64 個十六進位字元>"}}
```

通過之後，一行請求、一行回覆：

```json
{"id": 1, "method": "engine.execute", "params": {"command": "file.new", "params": {}}}
{"id": 1, "ok": true, "result": {}}
```

`pc` 自己印一行：`{"ok": true, "result": ...}` 或 `{"ok": false, "error": "..."}`。結束碼 0 是成功，1 是失敗。

埠開著卻沒有 token 時，`pc` 會失敗，不會改寫 `.pcraft`。連線被拒，或加上 `--offline`，才寫檔。

## 控制埠方法

軟體已經能用 `engine.execute` 呼叫全部引擎指令。`engine.batch` 是原始碼裡新增的方法，要重新編譯後才會出現在正在跑的程式裡。舊程式回 `unknown method` 時，`pc batch` 改成逐條 `engine.execute`。任一步失敗時，回傳會寫出那一步和錯誤訊息，行程結束碼是 1。`--keep-going` 讓後面的步驟繼續，結束碼仍是 1。

| 方法 | 參數 | 回傳 |
|---|---|---|
| `auth` | `{token}` | 空物件。每條連線只認證一次 |
| `engine.execute` | `{command, params?, wait?}` | 該指令的結果。`wait` 預設 true，背景工作做完才回 |
| `engine.batch` | `{steps:[{command\|id, params?}], stopOnError?: true}` | `{completed, failed, results}`。外層 `ok` 仍是 true。最多 256 步 |
| `engine.commands` | `{}` | 指令陣列。每筆有 `id`、`label`、`params`、`enabled`、`disabledReason`、`needsDocument` |
| `app.open` | `{path}` | `{path, name, warnings}`。路徑要在 `--automation-read-root` 底下 |
| `app.save` | `{path?, wait?: true}` | `{path, warnings}`。沒有 `path` 時寫回這份文件自己的 PSD、PSB 或 `.pcraft`。有副檔名時依副檔名匯出。路徑要在 `--automation-write-root` 底下 |
| `app.quit` | `{}` | 關閉視窗。改過的文件會先出現儲存詢問 |
| `jobs.list` | `{}` | 正在跑和剛結束的背景工作 |
| `jobs.cancel` | `{job?}` | `{cancelled}`。省略 `job` 會取消全部 |
| `ui.inspect` | `{}` | 介面狀態。儲存詢問在 `dialogs`，`id` 是 `discard` |
| `ui.dialog.confirm` | `{dialog: "discard", choice: "save"\|"dontSave"\|"cancel"}` | 回答儲存詢問。`choice` 預設 `save` |
| `session.inspect` | `{}` | `{documents:[{index, name, path, dirty, width, height}], active}` |
| `document.inspect` | `{document?: index}` | 圖層、選取、歷史、路徑 |

`file.open`、`file.save`、`file.saveAs` 在控制埠會被拒絕。開檔和存檔用 `app.open`、`app.save`。

## 指令

### 新文件、開檔、存檔

```text
pc new Poster -p C:\art\poster.pcraft --width 1920 --height 1080 --resolution 72 --depth 8 --background white
pc open C:\art\poster.pcraft
pc save
pc save C:\art\poster.png
```

`new` 送 `file.new`，有 `-p` 時再 `app.save`。`background` 是 `white`、`black` 或 `transparent`。`open` 送 `app.open`。`save` 和 `export` 送 `app.save`，並等寫完。

### 圖層、填色、選取、文字、調整

```text
pc layer Ink
pc fill --color #336699
pc select --x 0 --y 0 --width 400 --height 200 --mode replace
pc text 標題 --x 80 --y 120 --size 48 --color #ffffff
pc adjust --brightness 10 --contrast 5
```

| 指令 | 送出 |
|---|---|
| `layer` | `layer.new.layer {name?}` |
| `fill` | `edit.fill {contents: "color", color}` |
| `select` | `select.rect {x, y, width, height, mode}` |
| `text` | `type.create {x, y, text, size, color?}` |
| `adjust` | `image.adjustments.brightnessContrast {brightness, contrast}` |

### 查詢

`pc show` 送 `document.inspect`。圖層在 `layers`，由上到下，每層有 `id`、`name`、`kind`、`bounds`。

`pc links` 從 `document.inspect` 找出 `smartSource.kind` 為 `linked`、而且檔案不在的圖層。

`pc jobs` 送 `jobs.list`。

`pc status` 同時給 `session.inspect`、`document.inspect`、缺少的連結，以及 `jobs.list`。`documents` 裡 `dirty: true` 的文件還沒存。

### 關閉

`pc quit` 先看 `session.inspect`。每一份 `dirty` 且已有路徑的文件會 `document.activate` 再 `app.save`，然後 `app.quit`。若儲存詢問還在，`pc` 送 `ui.dialog.confirm {dialog: "discard", choice: "save"}`。還沒有路徑的文件會取消詢問並回錯誤，接著用 `pc save 路徑`。

`pc quit --discard` 先 `app.quit`，再對每個詢問送 `choice: "dontSave"`。`pc exec app.quit` 和 `pc exec app.quit discard=true` 走同樣的兩條路。

### 其餘指令

```text
pc commands
pc commands --filter type
pc exec layer.setProps '{"name": "Ink", "opacity": 0.5, "blend": "Multiply"}'
pc exec document.pixel x=10 y=20
pc batch steps.json
pc -p C:\art\poster.pcraft validate
```

`steps.json` 是一個陣列：`[{"command": "layer.new.layer", "params": {"name": "Ink"}}]`。某一步失敗時，`error` 是 `指令名: 錯誤訊息`，`result.batch.results` 裡看得到已完成的步驟，行程結束碼是 1。`--keep-going` 讓後面的步驟繼續。

`pc exec` 的 `key=value` 在值能解析成 JSON 時照 JSON 讀。筆刷、濾鏡、路徑、圖層樣式、動作、選取的名稱和參數都在 `pc commands`。

## 什麼時候改檔

| 情況 | 行為 |
|---|---|
| 埠開著，而且有 token | 只送指令。畫面即時更新 |
| 連線被拒，或 `--offline` | 寫 `.pcraft` 資料夾的 `manifest.json`。執行中的 PhotoCraft 要重新開檔才看得到 |
| 指令回 `ok: false` | 失敗，不改檔 |

`open`、`save`、`select`、`adjust`、`export`、`show`、`jobs`、`status`、`quit`、`exec`、`commands`、`batch` 沒有離線編輯。離線的 `new`、`layer`、`text`、`fill`、`links`、`validate` 只動 manifest。選取、調色、筆畫和匯出要等控制埠。

## 專案檔

`.pcraft` 可以是資料夾，或同樣配置的 zip：

```text
manifest.json
tiles/<blake3>.zst
blobs/<blake3>.zst
```

`manifest.json` 要有 `format_version`（目前是 1）、`generator`、`document`。`document` 要有 `id`、`name`、`size`、`resolution_dpi`、`mode`、`depth`、`layers`。圖層由下到上排在 `layers`。像素不在 JSON 裡，而在 `tiles/`。`pc validate` 用 `schema/pcraft.schema.json` 檢查 manifest。
