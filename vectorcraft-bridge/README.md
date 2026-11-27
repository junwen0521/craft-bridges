# vc — VectorCraft

`vc` 讓指令走 VectorCraft 的控制埠（預設 `127.0.0.1:7979`，沒有 token）。繪圖、上色、效果和匯出都是軟體裡的指令，開著的文件會立刻更新。

控制埠沒開，或加上 `--offline`，才依 `schema/vectorcraft.schema.json` 改 `.vectorcraft`。指令若被軟體拒絕，不會改去寫檔。每個指令的參數、回傳和範例在 [API.md](API.md)。

```text
vc new Poster -p C:\art\poster.vectorcraft --width 1280 --height 720 --units Pixels
vc rect --x 40 --y 40 --width 200 --height 80
vc text 標題 --x 80 --y 90 --size 36
vc fill 2 --color #112233
vc effect 2 stylize.dropShadow
vc export C:\out\poster.png --format png
vc render C:\out\board.png --artboard 0
vc status
```

`--port`、`--offline` 和 `-p` 可以放在指令名稱前面。

`vc commands` 列出軟體裡的全部指令。`vc exec 指令名 '{...}'` 可直接呼叫還沒有專用子指令的功能。`vc batch steps.json` 一次送多步；已安裝的程式還沒有 `engine.batch` 時，會自動改成逐條執行。
