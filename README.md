# Craft 控制橋

同一台電腦上，給 bot 操作已安裝的 FilmCraft、VectorCraft、PhotoCraft，以及對稿。前三支先把軟體的控制埠打開，再執行 `python fc`、`python vc` 或 `python pc`。對稿沒有控制埠，`python dg` 改的是影片旁邊的 txt。成功時終端機印一行 JSON，`"ok": true` 就是做成了。

埠沒開，或指令加上 `--offline`，才會改檔案，畫面上不會動。參數和回傳寫在各資料夾的 `API.md`。

## FilmCraft

另開一個視窗啟動，埠 `9877`，token 存成 64 個十六進位字元：

```text
filmcraft --control 9877 --control-token-file %TEMP%\filmcraft.tok
```

```text
cd filmcraft-bridge
python fc new Demo -p C:\cut\demo.fcproj --fps 24
python fc import C:\clips\a.mp4
python fc text 字幕 --start 1 --dur 2 --track V2
python fc export C:\out\demo.mp4 --end 10 --wait
```

`fc` 會讀 `%TEMP%\filmcraft.tok`。也可以設環境變數 `FILMCRAFT_CONTROL_TOKEN`，或在指令上加 `--token`。

## VectorCraft

沒有 token，埠 `7979`：

```text
vectorcraft --control 7979
```

```text
cd vectorcraft-bridge
python vc new Poster -p C:\art\poster.vectorcraft --width 1280 --height 720 --units Pixels
python vc rect --x 40 --y 40 --width 200 --height 80
python vc text 標題 --x 80 --y 90 --size 36
python vc export C:\out\poster.png --format png
```

## PhotoCraft

埠 `7878`。token 在啟動時指定，讀寫的資料夾要放進允許範圍：

```text
photocraft --control 7878 --control-token-file %TEMP%\photocraft.tok --automation-read-root C:\art --automation-write-root C:\art
```

```text
cd photocraft-bridge
python pc new Poster -p C:\art\poster.pcraft --width 1920 --height 1080
python pc text 標題 --x 80 --y 120 --size 48 --color #ffffff
python pc export C:\art\poster.png
python pc quit
```

`pc` 會讀 `%TEMP%\photocraft.tok`。`pc quit` 先存檔再關閉。

## 對稿

對稿用視窗看影片、改字幕。`dg` 改同一份 txt，不負責播放。先讓桌面上的 `對稿.py` 旁邊有 `fw-turbo` 模型，或設定 `DUIGAO_PY`。

```text
cd duigao-bridge
python dg show C:\art\clip.mp4
python dg transcribe C:\art\clip.mp4
python dg set C:\art\clip.mp4 0 --text 啊哈
python dg srt C:\art\clip.mp4
```

旁邊已經有字幕時，`transcribe` 不會蓋掉，要重轉才加 `--replace`。對稿視窗若正開著，要重新匯入才看得到 `dg` 改過的字。匯出的 SRT 可交給 FilmCraft 的 `captions.import`。

## 查其餘功能

沒有專用子指令的功能，先列出名稱再用 `exec`：

```text
python fc commands
python vc commands
python pc commands
python vc exec object.move "{\"ids\":[2],\"dx\":10,\"dy\":0}"
```
