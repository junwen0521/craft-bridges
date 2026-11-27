# pc — PhotoCraft

`pc` 讓指令走 PhotoCraft 的控制埠（預設 `127.0.0.1:7878`）。每次連線要先送 64 個十六進位字元的 token。繪圖、圖層、調整和匯出都是軟體裡的指令，開著的文件會立刻更新。

先另開視窗啟動軟體，再在這個資料夾執行 `python pc`：

```text
photocraft --control 7878 --control-token-file %TEMP%\photocraft.tok --automation-read-root C:\art --automation-write-root C:\art
python pc new Poster -p C:\art\poster.pcraft --width 1920 --height 1080
```

token 用 `--token`、`--token-file`，或環境變數 `PHOTOCRAFT_CONTROL_TOKEN`、`PHOTOCRAFT_CONTROL_TOKEN_FILE`。沒有指定時，`pc` 會讀 `%TEMP%\photocraft-control.token` 或 `%TEMP%\photocraft.tok`。

控制埠沒開，或加上 `--offline`，才依 `schema/pcraft.schema.json` 寫 `.pcraft` 資料夾裡的 `manifest.json`。像素在旁邊的 `tiles/`，離線模式只建立新文件、文字圖層和純色填充圖層。指令若被軟體拒絕，不會改去寫檔。每個指令的參數、回傳和範例在 [API.md](API.md)。

```text
pc --token-file C:\private\photocraft-control.token new Poster -p C:\art\poster.pcraft --width 1920 --height 1080
pc layer Ink
pc fill --color #336699
pc text 標題 --x 80 --y 120 --size 48 --color #ffffff
pc adjust --brightness 10 --contrast 5
pc export C:\art\poster.png
pc status
pc quit
```

`--port`、`--offline`、`-p` 和 `--token` 可以放在指令名稱前面。

`pc commands` 列出軟體裡的全部指令。`pc exec 指令名 '{...}'` 可直接呼叫還沒有專用子指令的功能。`pc batch steps.json` 一次送多步；已安裝的程式還沒有 `engine.batch` 時，會自動改成逐條執行。某一步失敗會印出那一步並以結束碼 1 停下，`--keep-going` 才會繼續後面的步驟。

`pc quit` 先存改過的文件再關閉。存檔詢問若還是出現，會替你按儲存。還沒有路徑的文件會取消詢問並回錯誤。`pc quit --discard` 對每個詢問按不儲存，然後關閉。
