import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PC = os.path.join(HERE, "pc")
TOKEN = "ab" * 32
SRC = r"C:\Users\wuyou\Downloads\photocraft-main\photocraft-main"


def run(args, port, offline=False):
    if port == 7878:
        raise AssertionError("refusing the live PhotoCraft port")
    cmd = [sys.executable, PC, "--port", str(port), "--token", TOKEN]
    if offline:
        cmd.append("--offline")
    cmd += args
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    try:
        body = json.loads(proc.stdout)
    except json.JSONDecodeError:
        body = {"ok": False, "error": proc.stdout, "stderr": proc.stderr}
    body["_code"] = proc.returncode
    body["_stderr"] = proc.stderr
    return body


class Server:
    def __init__(self):
        self.sock = socket.socket()
        self.sock.bind(("127.0.0.1", 0))
        self.port = self.sock.getsockname()[1]
        if self.port == 7878:
            self.sock.close()
            self.sock = socket.socket()
            self.sock.bind(("127.0.0.1", 0))
            self.port = self.sock.getsockname()[1]
        self.sock.listen(16)
        self.sock.settimeout(0.5)
        self.calls = []
        self.stop = False
        self.fail_on = {}
        self.no_batch = False
        self.dirty = False
        self.discard_left = 0
        self.thread = threading.Thread(target=self.loop, daemon=True)
        self.thread.start()

    def loop(self):
        while not self.stop:
            try:
                conn, _ = self.sock.accept()
            except socket.timeout:
                continue
            except OSError:
                return
            try:
                fh = conn.makefile("rwb")
                first = fh.readline()
                if not first:
                    continue
                auth = json.loads(first.decode("utf-8"))
                if auth.get("method") != "auth" or (auth.get("params") or {}).get("token") != TOKEN:
                    reply = {"id": auth.get("id"), "ok": False, "error": "authentication failed"}
                    fh.write((json.dumps(reply) + "\n").encode("utf-8"))
                    fh.flush()
                    continue
                fh.write((json.dumps({"id": auth.get("id"), "ok": True, "result": {}}) + "\n").encode("utf-8"))
                fh.flush()
                line = fh.readline()
                if not line:
                    continue
                req = json.loads(line.decode("utf-8"))
                self.calls.append(req)
                reply = self.respond(req)
                fh.write((json.dumps(reply) + "\n").encode("utf-8"))
                fh.flush()
            except Exception:
                continue
            finally:
                conn.close()

    def close(self):
        self.stop = True
        self.sock.close()

    def respond(self, req):
        method = req.get("method")
        params = req.get("params") or {}
        if method == "engine.batch" and self.no_batch:
            return {"id": req.get("id"), "ok": False, "error": "unknown method `engine.batch`"}
        if method == "engine.execute":
            command = params.get("command")
            if command in self.fail_on:
                return {"id": req.get("id"), "ok": False, "error": self.fail_on[command]}
        if method == "ui.dialog.confirm" and params.get("dialog") == "discard":
            self.discard_left = max(0, self.discard_left - 1)
            return {"id": req.get("id"), "ok": True, "result": {"open": self.discard_left > 0}}
        if method == "ui.inspect":
            dialogs = []
            if self.discard_left:
                dialogs.append({"id": "discard", "fields": {"command": "file.exit", "choices": ["save", "dontSave", "cancel"]}})
            return {"id": req.get("id"), "ok": True, "result": {"dialogs": dialogs}}
        return {"id": req.get("id"), "ok": True, "result": answer(self, req)}


def answer(server, req):
    method = req["method"]
    params = req.get("params") or {}
    if method == "engine.batch":
        return {"completed": len(params["steps"]), "failed": 0, "results": [
            {"ok": True, "command": step.get("command"), "result": {}} for step in params["steps"]
        ]}
    if method == "app.save":
        return {"path": params.get("path"), "warnings": []}
    if method == "app.open":
        return {"path": params.get("path"), "name": "Poster"}
    if method == "app.quit":
        return None
    if method == "jobs.list":
        return {"running": [], "finished": []}
    if method != "engine.execute":
        return {"method": method}
    command = params.get("command")
    p = params.get("params") or {}
    if command == "file.new":
        return {"name": p.get("name"), "width": p.get("width"), "height": p.get("height")}
    if command == "session.inspect":
        doc = {"index": 0, "name": "Poster", "path": "C:/art/poster.pcraft" if server.dirty else None, "dirty": server.dirty, "width": 8, "height": 8}
        return {"active": 0, "documents": [doc] if server.dirty or True else []}
    if command == "document.inspect":
        return {"name": "Poster", "width": 1920, "height": 1080, "layers": [{"id": 2, "name": "Ink", "kind": "Raster"}]}
    if command == "document.activate":
        return {"document": p.get("document")}
    if command == "layer.new.layer":
        return {"layer": 2}
    if command == "type.create":
        return {"layer": 3, "bounds": [p.get("x"), p.get("y"), 10, 10]}
    if command == "edit.fill":
        return {"color": p.get("color")}
    if command == "select.rect":
        return {"bounds": [p.get("x"), p.get("y"), p.get("width"), p.get("height")]}
    if command == "image.adjustments.brightnessContrast":
        return {"brightness": p.get("brightness"), "contrast": p.get("contrast")}
    return {"command": command}


class FlowTest(unittest.TestCase):
    def setUp(self):
        self.server = Server()

    def tearDown(self):
        self.server.close()

    def test_edit_to_export(self):
        steps = [
            ["new", "Poster", "--width", "1280", "--height", "720"],
            ["layer", "Ink"],
            ["fill", "--color", "#336699"],
            ["text", "你好", "--x", "40", "--y", "80", "--size", "32"],
            ["select", "--x", "0", "--y", "0", "--width", "100", "--height", "40"],
            ["adjust", "--brightness", "10", "--contrast", "-5"],
            ["export", r"C:\out\poster.png"],
            ["show"],
            ["status"],
            ["jobs"],
        ]
        for args in steps:
            body = run(args, self.server.port)
            self.assertTrue(body.get("ok"), (args, body))
            self.assertEqual(body["result"]["via"], "control", args)
        names = []
        for call in self.server.calls:
            if call["method"] == "engine.execute":
                names.append(call["params"].get("command"))
            else:
                names.append(call["method"])
        for needed in (
            "file.new", "layer.new.layer", "edit.fill", "type.create", "select.rect",
            "image.adjustments.brightnessContrast", "app.save", "document.inspect", "session.inspect", "jobs.list",
        ):
            self.assertIn(needed, names, needed)
        exported = next(c for c in self.server.calls if c["method"] == "app.save")
        self.assertTrue(exported["params"]["wait"])
        self.assertTrue(exported["params"]["path"].endswith(".png"))

    def test_batch_names_the_failed_step(self):
        self.server.no_batch = True
        self.server.fail_on["edit.fill"] = "no document is open"
        folder = tempfile.mkdtemp()
        path = os.path.join(folder, "steps.json")
        steps = [
            {"command": "layer.new.layer", "params": {"name": "Ink"}},
            {"command": "edit.fill", "params": {"color": "#ffffff"}},
            {"command": "type.create", "params": {"text": "next", "x": 0, "y": 0}},
        ]
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(steps, fh)
        stopped = run(["batch", path], self.server.port)
        self.assertFalse(stopped["ok"], stopped)
        self.assertEqual(stopped["_code"], 1)
        self.assertIn("edit.fill", stopped["error"])
        self.assertIn("no document is open", stopped["error"])
        sent = [c["params"]["command"] for c in self.server.calls if c["method"] == "engine.execute"]
        self.assertEqual(sent, ["layer.new.layer", "edit.fill"])
        self.server.calls.clear()
        kept = run(["batch", path, "--keep-going"], self.server.port)
        self.assertFalse(kept["ok"], kept)
        self.assertEqual(kept["result"]["batch"]["completed"], 2)
        sent = [c["params"]["command"] for c in self.server.calls if c["method"] == "engine.execute"]
        self.assertEqual(sent, ["layer.new.layer", "edit.fill", "type.create"])

    def test_quit_saves_dirty_documents_before_closing(self):
        self.server.dirty = True
        body = run(["quit"], self.server.port)
        self.assertTrue(body["ok"], body)
        methods = []
        for call in self.server.calls:
            if call["method"] == "engine.execute":
                methods.append(call["params"]["command"])
            else:
                methods.append(call["method"])
        self.assertEqual(methods, ["session.inspect", "document.activate", "app.save", "app.quit", "ui.inspect"])
        saved = next(c for c in self.server.calls if c["method"] == "app.save")
        self.assertEqual(saved["params"]["path"], "C:/art/poster.pcraft")
        self.assertTrue(saved["params"]["wait"])

    def test_quit_discard_answers_dont_save(self):
        self.server.discard_left = 1
        body = run(["quit", "--discard"], self.server.port)
        self.assertTrue(body["ok"], body)
        confirm = next(c for c in self.server.calls if c["method"] == "ui.dialog.confirm")
        self.assertEqual(confirm["params"], {"dialog": "discard", "choice": "dontSave"})
        self.assertEqual(self.server.calls[0]["method"], "app.quit")


class OfflineTest(unittest.TestCase):
    def test_commands_exist_in_source(self):
        with open(os.path.join(SRC, "crates", "ui-egui", "src", "control", "dispatch.rs"), encoding="utf-8") as fh:
            dispatch = fh.read()
        with open(os.path.join(SRC, "crates", "ui-egui", "src", "control.rs"), encoding="utf-8") as fh:
            control = fh.read()
        self.assertIn('"engine.batch"', dispatch)
        self.assertIn('"engine.execute"', dispatch)
        self.assertIn('"app.quit"', control)

    def test_manifest_round_trip_matches_schema(self):
        folder = tempfile.mkdtemp()
        path = os.path.join(folder, "poster.pcraft")
        made = run(["-p", path, "new", "Poster", "--width", "1280", "--height", "720", "--background", "white"], 1, offline=True)
        self.assertTrue(made["ok"], made)
        drawn = run(["-p", path, "text", "你好", "--x", "30", "--y", "40", "--size", "18", "--color", "#112233"], 1, offline=True)
        self.assertTrue(drawn["ok"], drawn)
        filled = run(["-p", path, "fill", "--color", "#abcdef"], 1, offline=True)
        self.assertTrue(filled["ok"], filled)
        checked = run(["-p", path, "validate"], 1, offline=True)
        self.assertTrue(checked["ok"], checked)
        with open(os.path.join(path, "manifest.json"), encoding="utf-8") as fh:
            doc = json.load(fh)
        kinds = [layer["content"]["kind"] for layer in doc["document"]["layers"]]
        self.assertEqual(kinds, ["raster", "text", "fill"])


if __name__ == "__main__":
    unittest.main()
