# FilmCraft 控制埠與 `fc`

FilmCraft 0.15.0 的剪輯功能本來就登記成引擎指令。控制埠把這些指令送到 UI 執行緒，改的是目前開著的專案，下一幀就畫出來，不用重開檔案。`fc` 優先走這條路。控制埠沒開，或明確加上 `--offline`，才直接寫 `.fcproj`。

專案檔的欄位、型別、預設值與特效目錄在 `schema/fcproj.schema.json`（Draft 2020-12）。同一份也放在 FilmCraft 原始碼的 `docs/fcproj.schema.json`。`effectCatalog` 只列出原始碼裡的 293 個效果 id，不拿來拒絕未知 id。

## 連線

只聽 `127.0.0.1`。這台機器上的 FilmCraft 用 `--control 9877`；原始碼文件的預設埠是 9876。`fc` 的預設是 `FC_PORT`、`FILMCRAFT_CONTROL_PORT`，否則 9877。

每一行一個 JSON 物件，回應也是一行。

```json
{"id": 1, "token": "<64 hex>", "method": "engine.execute", "params": {"command": "file.save", "params": {}}}
```

```json
{"id": 1, "ok": true, "result": {"path": "C:\\cut\\demo.fcproj"}}
```

```json
{"id": 1, "ok": false, "error": "no sequence is open"}
```

Token 是 64 個十六進位字元，和啟動 FilmCraft 的 `FILMCRAFT_CONTROL_TOKEN` 相同。`fc` 依序讀 `--token`、該環境變數、`%TEMP%\fc1104.tok`、`filmcraft.tok`、`filmcraft-control.tok`，以及 `%TEMP%` 裡內容剛好是 64 hex 的 `*.tok`。埠開著但找不到 token 時，指令失敗，不會改檔。

連線閒置約兩分鐘會被關掉。長匯出用 `wait: false`，再另開連線查 `jobs.list`。`fc export --wait` 就是這樣輪詢。

`engine.execute` 在已安裝的 0.15.0 就能用。`engine.batch` 是原始碼裡新增的方法，要重新編譯後才會出現在正在跑的程式。舊程式回 `unknown method` 時，`fc batch` 改成逐條 `engine.execute`。

## 時間與軌道

一秒是 `254016000000` tick。指令裡的 `seconds`、`frame`、`timecode` 由引擎換算。兩個例外只收整數 tick：`timeline.move` 的 `time`，以及 `file.exportFrame` 的 `time`。`fc move --at` 和 `fc frame --at` 會先換成 tick。

`timeline.place` 的 `duration` 和 `sourceIn` 可以是 tick，也可以是 `{"seconds": 4}`、`{"frame": 24}` 或 `{"timecode": "00:00:01:00"}`。

檔案裡的軌道名稱是 `Video 1`、`Audio 1`。指令接受 `V1`、`A1`。`graphics.newText` 的 `track` 是從 0 起算的索引，`fc text --track V2` 會送 `1`。

## 控制埠方法

| 方法 | 參數 | 回傳 |
|---|---|---|
| `engine.execute` | `{command, params}` | 該指令的 result |
| `ui.menu.invoke` | `{command\|id, params}` | 同上 |
| `engine.commands` | `{}` | 指令清單（id、參數說明、目前能不能用） |
| `engine.batch` | `{steps:[{command\|id, params?}], stopOnError?: true}` | `{completed, failed, results:[{ok, command, result\|error}]}`。外層 `ok` 仍是 true，好讀到每一步的錯誤。最多 256 步。`stopOnError` 預設 true，也接受 `stop_on_error` |

其餘方法（`ui.inspect`、`ui.click`、`ui.screenshot` 等）見原始碼 `docs/control-protocol.md`。

## 專案與素材

### `file.newProject`

參數 `{"name": str}`。回傳 `{"name", "revision"}`。這會換成一份新專案並清掉復原紀錄。

```json
{"command": "file.newProject", "params": {"name": "Demo"}}
```

`fc new Demo -p C:\cut\demo.fcproj`

### `file.newSequence`

參數 `{"name", "width": 1920, "height": 1080, "fps": 23.976, "sampleRate": 48000, "video": 3, "audio": 3, "mix"?, "trackType"?, "fromItem"?, "fromItems"?}`。`mix` 與 `trackType` 是 `Stereo|Mono|5.1|Adaptive`。回傳含新序列的 id。

```json
{"command": "file.newSequence", "params": {"name": "Demo", "width": 1920, "height": 1080, "fps": 24, "video": 2, "audio": 3}}
```

`fc` 的 `new` 預設 24 fps、2 條視訊、3 條音訊，和引擎預設的 23.976 / 3 / 3 不同。要引擎預設就改 `--fps 23.976 --video 3`。

### `file.open` / `file.save` / `file.saveAs`

`open` 與 `saveAs` 要 `{"path"}`。`save` 的 `path` 可省略，省略時寫回目前檔案。`fc open`、`fc save`、`fc save --save-as`。`fc export --open PATH` 會先打開再匯出。平常的剪輯指令作用在已經開著的專案，不會每次自動開檔。

### `file.import`

參數 `{"paths": [str], "bin"?, "imageSequence"?, "replace"?}`。也接受單一 `path`。回傳 `{"items": [id], "errors": [str]}`，有序列、文件、影像序列或 ingest 時會多出對應欄位。路徑必須是 FilmCraft 這台機器看得到的路徑。全部失敗時整筆指令是 `ok: false`。

```json
{"command": "file.import", "params": {"paths": ["C:\\clips\\a.mp4"]}}
```

`fc import C:\clips\a.mp4`。`--bin` 指定容器。離線時沒有 `--duration` 就用 ffprobe；有 `--duration --width --height --fps` 就直接寫檔，不必有可解碼的媒體。

## 時間軸

### `timeline.place`

參數：

```json
{
  "item": 12,
  "track": "V1",
  "audioTrack": "A1",
  "seconds": 0,
  "duration": {"seconds": 4},
  "sourceIn": {"seconds": 1},
  "insert": false,
  "video": true,
  "audio": true,
  "matchSequence": false
}
```

`item` 與 `items` 二選一。`items` 會依序相接，而且不能同時給 `sourceIn` 或 `duration`。`track` 可寫 `V1`、`A1`、軌道 id 或 `"new"`。時間可寫 `time`（tick）、`frame` 或 `seconds`，省略則用播放頭。回傳 `{"clips": [id]}`；走 `items` 時還有 `placed`。

`fc add-clips 12 13 --at 0 --dur 4 --vtrack V1 --atrack A1`。`--no-audio` 只放畫面。`--clip-db -14` 放完再設音量。

`fc music 12 --in 17 --out 77 --at 0 --track A2 --db -6` 只放聲音，`sourceIn` 與 `duration` 用秒。

### `timeline.move`

```json
{"moves": [{"clip": 10, "track": "V2", "time": 762048000000}], "insert": false, "linked": true}
```

`time` 只能是 tick。`track` 可以是 `"new"`。可加 `copy`、`captions`。回傳 `{"moved": [...]}`。

`fc move 10 --track V2 --at 3`

### `timeline.trim`

```json
{"clip": 10, "edge": "out", "mode": "regular", "deltaFrames": -12, "linked": true}
```

`edge` 是 `in` 或 `out`。`mode` 是 `regular` 或 `ripple`。位移用 `delta`（tick）或 `deltaFrames`。

`fc trim 10 --edge out --frames -12 --mode regular`

### `timeline.delete` / `timeline.razor`

刪除：`{"clips": [10, 11], "ripple": false}`，或單一 `clip`。沒有指名就刪選取。`fc delete 10 11 --ripple`。

剃刀：`{"time": ticks, "track": "V1", "clip": id}`。`time` 是 tick。`fc razor --at 2.5 --track V1`。

## 轉場、特效、音量

### `sequence.applyVideoTransition` / `sequence.applyAudioTransition`

```json
{"clip": 12, "effect": "cross_dissolve", "frames": 12, "edge": "in", "align": "center", "reverse": false}
```

`edge` 是 `in` 或 `out`。`align` 是 `center`、`start`、`end`。可加 `params`。沒有 `clip` 時作用在目前選取的剪接點。聲音轉場的效果 id 是 `constant_power`、`constant_gain`、`exponential_fade`。

`fc transition --dur 0.5 --effect cross_dissolve --align center --track V1` 會先 `sequence.inspect`，對該軌上頭尾相接的剪接點，在後一個片段的 `in` 邊上套轉場。`--frames` 省略時用 `--dur * 24`。

`fc fade in --dur 1 --track V1` 對第一個片段的入點做溶入；`out` 對最後一個片段的出點做溶出。音軌預設 `constant_power`。

### `effects.apply` / `effects.setParam`

套用：`{"clips": [10], "effect": "gaussian_blur"}`。省略 `clips` 時用選取。效果可以用 id 或顯示名稱。

設參數：

```json
{"clip": 10, "effect": "motion", "param": "scale", "value": 120, "keyframe": true, "seconds": 1}
```

`value` 依參數型別可以是數字、`[x, y]`、`"#rrggbb"`、布林、路徑，或選項的索引／名稱。`keyframe: true` 在 `time` 或 `seconds` 寫一顆關鍵影格並打開動畫。回傳含 `keyframes`、`param`、`value`。

`fc effect 10 gaussian_blur`。`fc effect 10 motion --param scale --value 120`。`fc keyframe 10 motion scale --at 1 --value 120 --interpolation easeOut` 會再呼叫 `effects.setInterpolation`。

內建畫面效果是 `motion`、`opacity`、`time_remap`。內建聲音效果是 `volume`（`level`，dB）、`channel_volume`、`panner`。片段的 `gain_db` 是另一個值，用下面的音量指令改。

### `clip.audioGain`

```json
{"clips": [11], "mode": "set", "db": -14}
```

`mode` 是 `set`、`adjust`、`normalizeMax`、`normalizeAll`。可加 `relative`。省略 `clips` 時用選取。

`fc volume --db -14 --track A1` 會把該軌每個片段都設成這個 dB。`--clip 11` 只改一個。

## 文字與字幕

### `graphics.newText`

```json
{"text": "字幕", "newClip": true, "time": 254016000000, "seconds": 2, "size": 72, "font": "Microsoft JhengHei", "track": 1}
```

`seconds` 是新片段的長度，預設 5。`time` 是起點 tick。`track` 是索引。`position` 是 `[x, y]`；有 `box` 時那一點是文字框左上角。回傳 `{"clip", "layer"}`。

`fc text 字幕 --start 1 --dur 2 --track V2 --size 72`。`--y` 會依序列寬度把水平放在正中。`--fade 0.3` 才會在頭尾加 `cross_dissolve`，預設不加。

文字圖層的效果 id 是 `graphic_text`，形狀是 `graphic_shape`。完整參數與預設值在 schema 的文字圖層定義。

### `captions.newTrack` / `captions.add`

新軌：`{"format": "Subtitle", "name"?, "language"?}`。格式是 `Subtitle`、`CEA-608`、`CEA-708`、`Teletext`。回傳 `{"track"}`。

加一句：

```json
{"text": "你好", "seconds": 1, "durationSeconds": 2}
```

`durationSeconds` 預設 3。沒有字幕軌時會先建一條。回傳 `{"caption"}`。

`fc caption 你好 --start 1 --dur 2`

## 序列與匯出

### `sequence.settings`

可改 `width`、`height`、`fps`、`name`、`sampleRate`、`mix`、`dropFrame`、`maxRenderQuality`、`workingSpace`（`rec709`、`rec2100-pq`、`rec2100-hlg`）、`wideGamut`、`autoToneMap`。`scaleMotion` 預設 false。

`fc sequence --fps 24 --width 1920 --height 1080 --name Demo`

### `file.exportMedia`

```json
{
  "path": "C:\\out\\demo.mp4",
  "format": "h264",
  "bitrateKbps": 16000,
  "bitrateMode": "vbr1Pass",
  "audioCodec": "aac",
  "range": "custom",
  "startSeconds": 0,
  "endSeconds": 10,
  "wait": false
}
```

`format` 還有 `hevc`、`prores`、`dnxhr`、`wav`、`aac` 等，完整列在引擎的參數說明。`range` 是 `entire`、`inOut`、`workArea`、`custom`。回傳 `{"job", "path", "warnings", "offlineMedia", "poll": "jobs.list"}`。

`fc export C:\out\demo.mp4 --end 10 --kbps 16000 --wait`。`--wait` 用新連線輪詢，直到該 job 的 `finished` 為 true，或超過 `--timeout`（預設 3600 秒）。`result.error` 會讓這筆指令失敗。

### `file.exportFrame`

```json
{"path": "C:\\out\\frame.png", "format": "png", "target": "program", "time": 381024000000}
```

`format` 是 `png`、`jpeg`、`tiff`、`bmp`。`depth` 是 8 或 16（16 只有 PNG 和 TIFF）。`target` 省略等於 `program`。`time` 只能是整數 tick，不能寫秒。`source` 時可加 `item`。`import: true` 會把靜態畫面再匯進專案。

`fc frame C:\out\frame.png --at 1.5` 送出的 `time` 是 `381024000000`。

## 狀態

### `project.inspect`

無參數。回傳 `name`、`path`、`dirty`、`revision`、`root`（容器樹，每個項目有 `item`、`name`、`type`）、`activeSequence`、`sourceItem`。

### `sequence.inspect`

參數 `{"item"?}`，省略就是目前序列。軌道在 `video` 和 `audio`，不是檔案裡的 `video_tracks`。片段 id 欄位是 `clip`。每個片段有 `start`、`duration`、`end`、`sourceIn`、`sourceOut`、`gainDb`、`effects`。轉場有 `effect`、`start`、`duration`、`from`、`to`、`align`。`settings.frame_rate` 是 `{"num", "den"}`。

`fc show` 同時回傳專案樹和這份序列。

### `media.status` / `media.findMissing`

`media.status` 的 `{"item"?}` 省略時列出每個媒體。每一筆有 `item`、`name`、`path`、`status`、`identity`、`proxy`。

`media.findMissing` 無參數，回傳 `{"missing": [...]}`。

`fc media-status` 兩筆都查。離線時改看檔案路徑是否存在。

### `jobs.list`

無參數。陣列裡每一筆是：

```json
{"id": 7, "label": "Export", "progress": 0.4, "etaSeconds": 12.5, "done": 40, "total": 100, "status": "", "finished": false, "result": null}
```

完成後 `finished` 為 true。失敗時 `result` 是 `{"error": "..."}`。

`fc jobs` 只列工作。`fc status` 同時給序列、找不到的素材，以及工作進度。

## 一次做多步，以及其餘指令

```json
{"method": "engine.batch", "params": {"steps": [
  {"command": "timeline.place", "params": {"item": 12, "track": "V1", "seconds": 0}},
  {"command": "captions.add", "params": {"text": "你好", "seconds": 0, "durationSeconds": 2}}
], "stopOnError": true}}
```

`fc batch steps.json`。`--keep-going` 讓後面的步驟在失敗後繼續。檔案是一個步驟陣列。

目錄裡還有滑動、速率、遮罩、混音、多機、調色、代理、轉寫等指令。名稱與參數說明用：

```text
fc commands
fc commands --filter caption
fc exec playhead.set '{"seconds": 1}'
fc exec effects.setParam clip=10 effect=opacity param=opacity value=40
```

`fc exec` 的 `key=value` 會在值能解析成 JSON 時照 JSON 讀；點號會變成巢狀欄位。

## `fc` 什麼時候改檔

| 情況 | 行為 |
|---|---|
| 埠開著且 token 正確 | 只送引擎指令。畫面即時更新 |
| 埠開著但沒有 token | 失敗，不改檔 |
| 連線被拒，或 `--offline` | 依 schema 寫 `.fcproj`。stderr 會說明執行中的 FilmCraft 要重新開檔才看得到 |
| 指令回 `ok: false` | 失敗，不改檔 |

離線寫入會在專案資料夾做一次 git commit。`--no-git` 略過。`open`、`export`、`frame`、`jobs`、`status`、`exec`、`commands`、`batch` 沒有離線編輯，埠沒開就失敗。`save` 在離線且檔案已存在時只回報路徑。

`fc` 印一行 `{"ok": true, "result": {...}}` 或以 exit code 1 印 `{"ok": false, "error": "..."}`。`result.via` 是 `control` 或 `file`。

全域旗標可以放在指令名稱前面或後面：`-p`、`--port`、`--host`、`--token`、`--offline`、`--no-git`。

## 專案檔

`.fcproj` 是一個 JSON 物件，`format` 為 `filmcraft.project`，`schema_version` 為 15。媒體以路徑引用。Id 是數字，物件字典的鍵是十進位字串。Tick 是整數。

列舉使用外部標籤，例如 `{"Item": 12}`、`{"Media": {...}}`、`{"File": {"path": "..."}}`、`{"Float": 100}`。序列必填 `settings`、`video_tracks`、`audio_tracks`、`markers`、`mark_in`、`mark_out`、`work_area`、`start_timecode`。片段必填 `id`、`item`、`name`、`label`、`start`、`duration`、`source_in`、`speed`、`enabled`、`effects`。轉場、關鍵影格、字幕樣式、音訊推子與色彩欄位的必填、選填和預設值都在 schema 裡，包含略過預設值才不寫出的欄位。

```text
fc validate -p C:\cut\demo.fcproj
```
