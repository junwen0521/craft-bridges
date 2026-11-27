# Craft 控制橋

同一台電腦上，給 bot 操作這三個已安裝的程式。每個資料夾是一支 Python 指令工具：控制埠開著就改畫面上的文件，埠沒開或加上 `--offline` 才改檔案。

| 資料夾 | 指令 | 控制埠 |
|---|---|---|
| `filmcraft-bridge` | `fc` | `127.0.0.1:9877`，需要 64 碼 token |
| `vectorcraft-bridge` | `vc` | `127.0.0.1:7979`，沒有 token |
| `photocraft-bridge` | `pc` | `127.0.0.1:7878`，連線第一行要送 64 碼 token |

各資料夾的 `API.md` 寫指令、參數和回傳。stdout 都是一行 JSON。
