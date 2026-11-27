import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DG = os.path.join(HERE, "dg")


def find_app():
    env = os.environ.get("DUIGAO_PY")
    if env and os.path.isfile(env):
        return env
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    skip = {"fw-turbo", "stable_whisper", "node_modules", ".git", "__pycache__"}
    found = []
    for dirpath, dirnames, filenames in os.walk(desktop):
        rel = os.path.relpath(dirpath, desktop)
        depth = 0 if rel == "." else rel.count(os.sep) + 1
        if depth > 3:
            dirnames[:] = []
            continue
        dirnames[:] = [name for name in dirnames if name not in skip]
        if "對稿.py" in filenames:
            found.append(os.path.join(dirpath, "對稿.py"))
    for path in found:
        if os.path.isfile(os.path.join(os.path.dirname(path), "fw-turbo", "model.bin")):
            return path
    if found:
        return found[0]
    raise AssertionError("找不到對稿.py")


APP = find_app()


def run(args):
    env = os.environ.copy()
    env["DUIGAO_PY"] = APP
    proc = subprocess.run(
        [sys.executable, DG, *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
    )
    try:
        body = json.loads(proc.stdout)
    except json.JSONDecodeError:
        body = {"ok": False, "error": proc.stdout, "stderr": proc.stderr}
    body["_code"] = proc.returncode
    body["stderr"] = proc.stderr
    return body


class FlowTest(unittest.TestCase):
    def test_edit_export_and_timing(self):
        with tempfile.TemporaryDirectory() as folder:
            video = os.path.join(folder, "clip.mp4")
            with open(video, "wb") as handle:
                handle.write(b"not a real movie")
            source = os.path.join(folder, "clip.txt")
            with open(source, "w", encoding="utf-8", newline="\n") as handle:
                handle.write("[114.0-114.6] 啊\n[114.6-115.5] 欸 終於開了\n補充\n")
            shown = run(["show", video])
            self.assertEqual(shown["_code"], 0, shown)
            self.assertEqual(shown["result"]["lines"][0]["text"], "啊")
            self.assertEqual(shown["result"]["lines"][1]["text"], "欸 終於開了\n補充")
            current = run(["at", video, "114.0"])
            self.assertEqual(current["result"]["index"], 0)
            changed = run(["set", video, "0", "--text", "啊哈", "--start", "114.26", "--end", "114.0"])
            self.assertEqual(changed["_code"], 0, changed)
            self.assertEqual(changed["result"]["line"]["text"], "啊哈")
            self.assertEqual(changed["result"]["line"]["start"], 114.3)
            self.assertEqual(changed["result"]["line"]["end"], 114.4)
            stamped = run(["stamp", video, "1", "start", "--at", "20"])
            self.assertEqual(stamped["_code"], 0, stamped)
            self.assertEqual(stamped["result"]["line"]["start"], 20.0)
            self.assertGreater(stamped["result"]["line"]["end"], 20.0)
            added = run(["add", video, "--index", "0", "--text", "中間"])
            self.assertEqual(added["_code"], 0, added)
            self.assertEqual(added["result"]["line"]["index"], 1)
            removed = run(["delete", video, "1"])
            self.assertEqual(removed["_code"], 0, removed)
            self.assertEqual(removed["result"]["count"], 2)
            srt = run(["srt", video])
            self.assertEqual(srt["_code"], 0, srt)
            with open(srt["result"]["srt"], encoding="utf-8") as handle:
                body = handle.read()
            self.assertIn("00:01:54,300 --> 00:01:54,400", body)
            self.assertIn("啊哈", body)
            checked = run(["validate", video])
            self.assertEqual(checked["_code"], 0, checked)

    def test_convert_portrait_and_refuse_replace(self):
        with tempfile.TemporaryDirectory() as folder:
            video = os.path.join(folder, "talk.mp4")
            with open(video, "wb") as handle:
                handle.write(b"x")
            text = "一二三四五六七八九十甲"
            with open(os.path.splitext(video)[0] + ".txt", "w", encoding="utf-8", newline="\n") as handle:
                handle.write("[0.0-1.0] %s\n" % text)
            converted = run(["convert", video, "直式"])
            self.assertEqual(converted["_code"], 0, converted)
            self.assertEqual(converted["result"]["changed"], 1)
            shown = run(["show", video])
            self.assertEqual(shown["result"]["lines"][0]["text"], "一二三四五六七八九十\n甲")
            flat = run(["convert", video, "landscape"])
            self.assertEqual(flat["result"]["changed"], 1)
            shown = run(["show", video])
            self.assertEqual(shown["result"]["lines"][0]["text"], text)
            refused = run(["transcribe", video])
            self.assertEqual(refused["_code"], 1, refused)
            self.assertIn("--replace", refused["error"])
            self.assertNotIn("正在載入模型", refused.get("stderr", "") + refused["error"])

    def test_commands_exist_in_source(self):
        with open(APP, encoding="utf-8") as handle:
            app = handle.read()
        with open(DG, encoding="utf-8") as handle:
            cli = handle.read()
        for snippet in (
            "word_timestamps=True",
            "suppress_silence=True",
            "suppress_word_ts=True",
            "regroup=True",
            "load_faster_whisper",
        ):
            self.assertIn(snippet, app)
            self.assertIn(snippet, cli)
        for snippet in ("s2twp", "wrap_portrait", "format_srt", "TEXT_CONVERSIONS"):
            self.assertIn(snippet, app)
        for snippet in ("wrap_portrait", "format_srt", "TEXT_CONVERSIONS"):
            self.assertIn(snippet, cli)


if __name__ == "__main__":
    unittest.main()
