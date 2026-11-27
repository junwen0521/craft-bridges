# dg — 對稿

對稿是看影片、改字幕的視窗。`dg` 讓 bot 改同一份字幕，不用去點視窗。

對稿沒有控制埠。每一支影片旁邊有一份 txt，視窗存的也是這個檔：

```text
[114.0-114.6] 啊
[114.6-115.5] 欸 終於開了
```

播放、暫停、跳到某一句，仍用對稿視窗。`dg` 改字、改秒數、轉文字、匯出 SRT。終端機成功時印一行 JSON，`"ok": true` 就是做成了。句號從 0 開始。

視窗如果正開著，不會自動重讀。`dg` 改完後，在對稿裡重新匯入那支影片才看得到新字。

參數和回傳寫在 [API.md](API.md)。

## 開對稿視窗

雙擊對稿資料夾裡的「開啟對稿.bat」，或把影片拖到這個 bat 上。有同名 txt 會直接出現；沒有就按「轉成文字」。

`dg` 會在桌面上找 `對稿.py`，而且它旁邊要有 `fw-turbo` 模型。模型不在這個倉庫裡。若對稿不在桌面，先設：

```text
set DUIGAO_PY=C:\Users\wuyou\Desktop\對稿\對稿\對稿.py
```

## 用指令改字幕

在這個資料夾執行：

```text
python dg show C:\art\clip.mp4
python dg transcribe C:\art\clip.mp4
python dg set C:\art\clip.mp4 0 --text 啊哈
python dg stamp C:\art\clip.mp4 0 end --at 115.0
python dg srt C:\art\clip.mp4
```

`show` 讀出每一句的開始、結束和文字。`transcribe` 用對稿同一個模型把影片轉成旁邊的 txt。旁邊已經有字幕時不會蓋掉，要重轉才加 `--replace`。`set` 改某一句。`stamp` 把開始或結束改成指定的秒數，對應視窗的「開頭改成現在」「結尾改成現在」。`srt` 匯出給 FilmCraft 用的字幕檔。

轉完、改完之後，FilmCraft 要把字放上時間軸：

```text
python fc exec captions.import "{\"path\":\"C:\\art\\clip.srt\"}"
```

FilmCraft 預覽看得到字。要字出現在輸出的影片裡，輸出選項要選「把字幕燒進影片」。

## 其他指令

```text
python dg tracks C:\art\clip.mp4
python dg transcribe C:\art\clip.mp4 --track 2
python dg add C:\art\clip.mp4 --index 0 --text 中間
python dg delete C:\art\clip.mp4 1
python dg convert C:\art\clip.mp4 直式
python dg at C:\art\clip.mp4 114.0
python dg validate C:\art\clip.mp4
python dg commands
```

`tracks` 的號碼從 1 開始，和視窗音軌選單一樣。`convert` 可以是 `台灣繁體`、`繁體`、`香港繁體`、`簡體`、`直式`、`橫式`。
