# fc — FilmCraft 0.15.0

`fc` 讓指令走 FilmCraft 的控制埠（預設 `127.0.0.1:9877`）。剪輯、轉場、文字、字幕、音量和匯出都是引擎指令，開著的時間軸會立刻更新。

控制埠沒開，或加上 `--offline`，才依 `schema/fcproj.schema.json` 改 `.fcproj`。指令若被軟體拒絕，不會改去寫檔。每個指令的參數、回傳和範例在 [API.md](API.md)。

```text
fc new Demo -p C:\cut\demo.fcproj --fps 24
fc import C:\clips\a.mp4
fc add-clips 2 3 --at 0
fc transition --dur 0.5 --effect cross_dissolve --track V1
fc text 字幕 --start 1 --dur 2 --track V2
fc caption 你好 --start 1 --dur 2
fc volume --db -14 --track A1
fc export C:\out\demo.mp4 --end 10 --wait
fc frame C:\out\frame.png --at 1.5
fc status
```

Token 用 `FILMCRAFT_CONTROL_TOKEN`，或 `%TEMP%\fc1104.tok` 這類 64 hex 檔。`--port`、`--token`、`--offline`、`--no-git` 和 `-p` 可以放在指令名稱前面。離線寫入會在專案資料夾做 git commit，`--no-git` 可略過。

`fc commands` 列出軟體裡的全部指令。`fc exec COMMAND '{...}'` 可直接呼叫還沒有專用子指令的功能。`fc batch steps.json` 一次送多步；已安裝的 0.15.0 還沒有 `engine.batch` 時，會自動改成逐條執行。
