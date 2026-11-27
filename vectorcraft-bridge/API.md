# VectorCraft 控制埠與 `vc`

VectorCraft 的繪圖功能登記成引擎指令或介面指令。控制埠把指令送到正在跑的程式，改的是目前開著的文件，下一幀就畫出來。`vc` 優先走這條路。控制埠沒開，或加上 `--offline`，才直接寫 `.vectorcraft`。

專案 JSON 的欄位在 `schema/vectorcraft.schema.json`（Draft 2020-12）。同一份在原始碼 `docs/vectorcraft.schema.json`。節點種類取自 `NodeKind`，特效 id 取自 `crates/effects`。`effectCatalog` 只供查閱，不拿來拒絕檔案裡的其他效果。

## 連線

`vectorcraft --control 7979` 只聽 `127.0.0.1`。這個埠沒有 token。`vc` 的預設埠是 `VC_PORT`、`VECTORCRAFT_CONTROL_PORT`，否則 7979。

每一行一個 JSON 物件，回應也是一行。

```json
{"id": 1, "method": "engine.execute", "params": {"command": "shape.rectangle", "params": {"x": 40, "y": 40, "width": 200, "height": 80}}}
```

```json
{"id": 1, "ok": true, "result": {"id": 2}}
```

```json
{"id": 1, "ok": false, "error": "no document is open"}
```

指令若帶了該指令說明裡沒有的參數名稱，會在執行前被拒絕。長時間的存檔和匯出用 `wait: true`，檔案寫完才回應。

已安裝的程式已經能用 `engine.execute` 呼叫全部指令。`engine.batch` 是原始碼裡新增的方法，要重新編譯後才會出現。舊程式回 `unknown method` 時，`vc batch` 改成逐條 `engine.execute`。軟體裡原本就有 `command.batch`：它把多步收成一次復原，失敗會整批還原，而且必須已經開著文件。`engine.batch` 每步各自復原，失敗時保留已經做完的步驟，也可以從 `file.new` 開始。

## 控制埠方法

| 方法 | 參數 | 回傳 |
|---|---|---|
| `engine.execute` | `{command, params}` | 該指令的 result |
| `engine.batch` | `{steps:[{command\|id, params?}], stopOnError?: true}` | `{completed, failed, results}`。外層 `ok` 仍是 true。最多 256 步 |
| `engine.commands` | `{}` | 全部引擎與介面指令 |
| `document.inspect` | `{depth?, childLimit?, ids?, kind?, limit?, offset?}` | 圖層樹、選取、歷史 |
| `ui.inspect` | `{}` | 工具、文件是否改過、`background`（還在背景存檔或匯出的工作）、`opening`、`placing` |
| `app.open` | `{path}` | 開檔。`warnings` 說明沒有完整讀入的部分 |
| `app.save` | `{path?, wait?: true}` | 存檔。`wait: true` 會等寫完 |
| `app.export` | `{path?, format?, artboard?, scale?, wait?: true, …}` | 匯出。格式與選項同 `document.export` |
| `ui.render` | `{path?, artboard?, scale?, data?}` | 把一個畫板畫成 PNG。`artboard` 從 0 起算 |

其餘方法見原始碼 `docs/control-protocol.md`。

## `vc` 指令

全域旗標可以放在指令名稱前面或後面：`-p`、`--port`、`--host`、`--offline`。

`vc` 印一行 `{"ok": true, "result": {...}}`，失敗則 exit code 1 並印 `{"ok": false, "error": "..."}`。`result.via` 是 `control` 或 `file`。

### 文件

`vc new 名稱 --width 1280 --height 720 --units Pixels -p C:\art\poster.vectorcraft`

活的程式送 `file.new`。有 `-p` 時再 `app.save`，並等寫完。寬高單位是點；`Pixels` 時 1 px = 1 pt。預設 612×792 點。

`vc open C:\art\poster.vectorcraft` 送 `app.open`。

`vc save C:\art\poster.vectorcraft` 送 `app.save`，`wait: true`。

### 繪圖

`vc rect --x 40 --y 40 --width 200 --height 80` 送 `shape.rectangle`，回傳 `{id}`。

`vc ellipse` 用同樣的 `--x --y --width --height`，送 `shape.ellipse`。

`vc text 標題 --x 80 --y 90 --size 36 --font Inter` 送 `text.create`。點文字的對齊點是 `(x, y)`。回傳 `{id, bounds}`。

`vc fill 2 --color #112233` 送 `paint.setFill`。`--none` 拿掉填色。

`vc stroke 2 --color #000000 --weight 2` 有顏色就送 `paint.setStroke`，有粗細就送 `stroke.set`。

`vc move 2 --dx 10 --dy 4` 送 `object.move`。

`vc delete 2 3` 送 `edit.clear`。

`vc effect 2 stylize.dropShadow --params "{\"opacity\": 40}"` 送 `effect.apply`。效果 id 用 `vc exec effect.list` 查。

### 匯出與狀態

`vc export C:\out\poster.png --format png --artboard 0 --scale 1` 送 `app.export`，並等待寫完。`format` 可以是 `png`、`jpg`、`svg`、`pdf`、`ai` 等，完整清單是 `document.formats`。

`vc render C:\out\board.png --artboard 0 --scale 1` 送 `ui.render`，畫出該畫板的 PNG。

`vc show` 送 `document.inspect`。圖層在 `layers`，每個物件有 `id`、`name`、`kind`、`bounds`。

`vc links` 送 `links.check`。回傳 `links`，每一筆的 `status` 是 `ok`、`modified` 或 `missing`，另外有 `missing` 和 `modified` 的數量。

`vc status` 同時給文件樹、連結狀態，以及 `ui.inspect`。背景存檔和匯出列在 `ui.background`。

### 其餘指令

```text
vc commands
vc commands --filter text
vc exec shape.star '{"cx": 100, "cy": 100, "radius1": 40, "radius2": 18, "points": 5}'
vc exec object.rotate angle=15 ids="[2]"
vc batch steps.json
```

`steps.json` 是一個陣列：`[{"command": "shape.rectangle", "params": {"x": 0, "y": 0, "width": 10, "height": 10}}]`。`--keep-going` 讓後面的步驟在失敗後繼續。

`vc exec` 的 `key=value` 在值能解析成 JSON 時照 JSON 讀。目錄裡還有筆刷、符號、路徑管理員、混合、封套、文字樣式、變數、列印等指令，名稱和參數都在 `vc commands`。

## 什麼時候改檔

| 情況 | 行為 |
|---|---|
| 埠開著 | 只送指令。畫面即時更新 |
| 連線被拒，或 `--offline` | 依 schema 寫未壓縮的 `.vectorcraft`。執行中的 VectorCraft 要重新開檔才看得到 |
| 指令回 `ok: false` | 失敗，不改檔 |

`open`、`save`、`export`、`render`、`status`、`exec`、`commands`、`batch` 沒有離線編輯。`save` 在離線且檔案已存在時只回報路徑。

## 專案檔

`.vectorcraft` 的 JSON 是：

```json
{"format": "vectorcraft", "version": 4, "generator": "VectorCraft 0.19.0", "document": {}}
```

`version` 是 1 到 4。舊名 `drawcraft` 仍可開啟。從第 3 版起可以用 gzip。第 4 版可以把 8 KiB 以上的圖片、色彩描述檔和 PDF 放在 JSON 後面，標記是換行、NUL、`VCBLOBS`、NUL；JSON 裡用 `"blob": [offset, length]` 指向那段資料。

`document` 必填 `version`、`artboards`、`layers`。畫板有 `id`、`name`、`rect`（`x0`、`y0`、`x1`、`y1`，y 向下）。圖層是節點，`kind.type` 為 `layer`。

節點必填 `id` 和 `kind`。`kind.type` 是 `NodeKind` 的小寫名稱：`layer`、`group`、`path`、`compound`、`text`、`image`、`symbolinstance`、`blend`、`envelope`、`mesh`、`repeat`、`placeddocument`、`intertwine`。路徑的錨點是 `path.subpaths[].anchors[].p`，座標為 `[x, y]`。文字是 `kind.type` `text`，內容在 `runs[].text`。填色和描邊在 `appearance.items`。即時效果在 `appearance.effects`。

`vc validate -p C:\art\poster.vectorcraft` 會先解開 gzip 和 `VCBLOBS`，再對 JSON 檢查 schema。
