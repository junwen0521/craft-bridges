"""Control-port flow and offline document shape.

The live test speaks the line protocol to a stand-in server. It does not
connect to a VectorCraft that is already open.
"""
import gzip
import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
VC = os.path.join(ROOT, "vc")
SRC = os.environ.get("VECTORCRAFT_SRC", r"C:\Users\wuyou\Downloads\vectorcraft-main\vectorcraft-main")
REAL = [
    r"C:\Users\wuyou\Desktop\VectorCraft\yt-1103\yt-1103-cover.vectorcraft",
    r"C:\Users\wuyou\Desktop\VectorCraft\ballet\ballet-cover.vectorcraft",
]


def load_vc(path):
    with open(path, "rb") as fh:
        raw = fh.read()
    if raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    cut = raw.find(b"\n\0VCBLOBS\0")
    if cut >= 0:
        raw = raw[:cut]
    return json.loads(raw.decode("utf-8"))


def run(args, port, offline=False):
    if int(port) == 7979:
        raise AssertionError("refusing port 7979; that is a running VectorCraft")
    cmd = [sys.executable, VC, "--port", str(port)]
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
        if self.port == 7979:
            self.sock.close()
            self.sock = socket.socket()
            self.sock.bind(("127.0.0.1", 0))
            self.port = self.sock.getsockname()[1]
        self.sock.listen(16)
        self.sock.settimeout(0.5)
        self.calls = []
        self.stop = False
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
                line = fh.readline()
                if not line:
                    continue
                req = json.loads(line.decode("utf-8"))
                self.calls.append(req)
                reply = {"id": req.get("id"), "ok": True, "result": answer(req)}
                fh.write((json.dumps(reply) + "\n").encode("utf-8"))
                fh.flush()
            except Exception:
                continue
            finally:
                conn.close()

    def close(self):
        self.stop = True
        self.sock.close()


def answer(req):
    method = req["method"]
    params = req.get("params") or {}
    if method == "engine.batch":
        return {"completed": len(params["steps"]), "failed": 0, "results": [
            {"ok": True, "command": step.get("command"), "result": {}} for step in params["steps"]
        ]}
    if method == "app.save":
        return {"path": params.get("path")}
    if method == "app.open":
        return {"index": 0, "title": "Demo"}
    if method == "app.export":
        return {"path": params.get("path"), "format": params.get("format"), "bytes": 8}
    if method == "ui.render":
        return {"path": params.get("path"), "width": 10, "height": 10}
    if method == "ui.inspect":
        return {"background": [], "documents": [{"title": "Demo", "dirty": False}]}
    if method != "engine.execute":
        return {"method": method}
    command = params.get("command")
    p = params.get("params") or {}
    if command == "file.new":
        return {"index": 0}
    if command == "shape.rectangle":
        return {"id": 2}
    if command == "text.create":
        return {"id": 3, "bounds": {"x": p.get("x"), "y": p.get("y"), "width": 10, "height": 10}}
    if command == "paint.setFill":
        return {"objects": 1}
    if command == "object.move":
        return {"ids": p.get("ids")}
    if command == "effect.apply":
        return {"ids": p.get("ids"), "index": 0}
    if command == "document.inspect":
        return {"layers": [{"id": 1, "name": "Layer 1", "kind": "Layer"}], "artboards": [{"id": 1}], "selection": [2]}
    if command == "links.check":
        return {"links": [], "missing": 0, "modified": 0}
    return {"command": command}


class FlowTest(unittest.TestCase):
    def setUp(self):
        self.server = Server()

    def tearDown(self):
        self.server.close()

    def test_draw_to_export(self):
        port = self.server.port
        steps = [
            ["new", "Poster", "--width", "1280", "--height", "720", "--units", "Pixels"],
            ["rect", "--x", "40", "--y", "40", "--width", "200", "--height", "80"],
            ["text", "標題", "--x", "80", "--y", "90", "--size", "36"],
            ["fill", "2", "--color", "#112233"],
            ["move", "2", "--dx", "10", "--dy", "4"],
            ["effect", "2", "stylize.dropShadow"],
            ["export", r"C:\out\poster.png", "--format", "png", "--artboard", "0"],
            ["render", r"C:\out\board.png", "--artboard", "0", "--scale", "1"],
            ["show"],
            ["links"],
            ["status"],
        ]
        for args in steps:
            body = run(args, port)
            self.assertTrue(body.get("ok"), (args, body))
            self.assertEqual(body["result"]["via"], "control", args)
        names = []
        for call in self.server.calls:
            if call["method"] == "engine.execute":
                names.append(call["params"].get("command"))
            else:
                names.append(call["method"])
        for needed in (
            "file.new", "shape.rectangle", "text.create", "paint.setFill", "object.move",
            "effect.apply", "app.export", "ui.render", "document.inspect", "links.check", "ui.inspect",
        ):
            self.assertIn(needed, names, needed)
        exported = next(c for c in self.server.calls if c["method"] == "app.export")
        self.assertEqual(exported["params"]["format"], "png")
        self.assertTrue(exported["params"]["wait"])

    def test_command_error_is_json(self):
        self.server.close()
        sock = socket.socket()
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
        if port == 7979:
            self.fail("refusing port 7979")
        sock.listen(1)

        def once():
            while True:
                conn, _ = sock.accept()
                fh = conn.makefile("rwb")
                line = fh.readline()
                if not line:
                    conn.close()
                    continue
                req = json.loads(line.decode())
                fh.write((json.dumps({"id": req.get("id"), "ok": False, "error": "no document is open"}) + "\n").encode())
                fh.flush()
                conn.close()
                sock.close()
                return

        threading.Thread(target=once, daemon=True).start()
        body = run(["show"], port)
        self.assertFalse(body["ok"])
        self.assertEqual(body["error"], "no document is open")
        self.assertEqual(body["_code"], 1)

    def test_batch(self):
        folder = tempfile.mkdtemp()
        path = os.path.join(folder, "steps.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump([{"command": "shape.rectangle", "params": {"x": 0, "y": 0, "width": 10, "height": 10}}], fh)
        body = run(["batch", path], self.server.port)
        self.assertTrue(body["ok"], body)
        self.assertEqual(self.server.calls[-1]["method"], "engine.batch")


class OfflineTest(unittest.TestCase):
    def test_document_round_trip_matches_schema(self):
        from jsonschema import Draft202012Validator
        folder = tempfile.mkdtemp()
        path = os.path.join(folder, "poster.vectorcraft")
        port = 1
        made = run(["-p", path, "new", "Poster", "--width", "1280", "--height", "720", "--units", "Pixels"], port, offline=True)
        self.assertTrue(made["ok"], made)
        drawn = run(["-p", path, "rect", "--x", "10", "--y", "20", "--width", "100", "--height", "40", "--fill", "#336699"], port, offline=True)
        self.assertTrue(drawn["ok"], drawn)
        nid = drawn["result"]["id"]
        for args in (
            ["-p", path, "text", "你好", "--x", "30", "--y", "40", "--size", "18"],
            ["-p", path, "fill", str(nid), "--color", "#abcdef"],
            ["-p", path, "move", str(nid), "--dx", "5", "--dy", "-2"],
            ["-p", path, "effect", str(nid), "stylize.dropShadow", "--params", "{\"opacity\": 40}"],
            ["-p", path, "validate"],
        ):
            body = run(args, port, offline=True)
            self.assertTrue(body["ok"], (args, body))
        with open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
        with open(os.path.join(ROOT, "schema", "vectorcraft.schema.json"), encoding="utf-8") as fh:
            schema = json.load(fh)
        errors = list(Draft202012Validator(schema).iter_errors(doc))
        self.assertEqual(errors, [], [e.message for e in errors[:8]])
        child = doc["document"]["layers"][0]["kind"]["children"][0]
        self.assertEqual(child["kind"]["type"], "path")
        self.assertEqual(child["kind"]["path"]["subpaths"][0]["anchors"][0]["p"], [15.0, 18.0])
        self.assertTrue(any(c["kind"]["type"] == "text" for c in doc["document"]["layers"][0]["kind"]["children"]))

    def test_real_files_match_schema(self):
        from jsonschema import Draft202012Validator
        with open(os.path.join(ROOT, "schema", "vectorcraft.schema.json"), encoding="utf-8") as fh:
            schema = json.load(fh)
        validator = Draft202012Validator(schema)
        for path in REAL:
            if not os.path.isfile(path):
                self.skipTest(path)
            doc = load_vc(path)
            errors = list(validator.iter_errors(doc))
            self.assertEqual(errors, [], (path, [e.message for e in errors[:5]]))

    def test_commands_exist_in_source(self):
        blob = []
        roots = [
            os.path.join(SRC, "crates", "engine", "src"),
            os.path.join(SRC, "crates", "ui-egui", "src"),
        ]
        for root in roots:
            for dirpath, _, files in os.walk(root):
                for name in files:
                    if name.endswith(".rs"):
                        with open(os.path.join(dirpath, name), encoding="utf-8", errors="replace") as fh:
                            blob.append(fh.read())
        text = "\n".join(blob)
        for command in (
            "file.new", "file.open", "file.save", "shape.rectangle", "shape.ellipse",
            "text.create", "paint.setFill", "paint.setStroke", "stroke.set", "object.move",
            "edit.clear", "effect.apply", "document.export", "document.inspect", "links.check",
            "engine.batch", "command.batch",
        ):
            self.assertIn('"%s"' % command, text, command)


if __name__ == "__main__":
    unittest.main()
