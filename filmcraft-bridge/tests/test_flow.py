"""Control-port flow and offline project shape.

The live test speaks the real line protocol to a stand-in server, so it does
not touch a FilmCraft the user already has open.
"""
import json, os, socket, subprocess, sys, tempfile, threading, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
FC = os.path.join(ROOT, "fc")
SRC = os.environ.get("FILMCRAFT_SRC", r"C:\Users\wuyou\Downloads\filmcraft-main\filmcraft-main")
TOKEN = "ab" * 32

def run(args, port, token=TOKEN, offline=False):
    if int(port) == 9877:
        raise AssertionError("refusing port 9877; that is the user's running FilmCraft")
    cmd = [sys.executable, FC, "--port", str(port), "--no-git", "--token", token]
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
        if self.port == 9877:
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
                f = conn.makefile("rwb")
                line = f.readline()
                if not line:
                    continue
                req = json.loads(line.decode("utf-8"))
                self.calls.append(req)
                if req.get("token") != TOKEN:
                    reply = {"id": req.get("id"), "ok": False, "error": "bad token"}
                else:
                    reply = {"id": req.get("id"), "ok": True, "result": answer(req)}
                f.write((json.dumps(reply) + "\n").encode("utf-8"))
                f.flush()
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
        return {"completed": len(params["steps"]), "failed": 0, "results": [{"ok": True, "command": s.get("command"), "result": {}} for s in params["steps"]]}
    if method != "engine.execute":
        return {"method": method}
    command = params.get("command")
    p = params.get("params") or {}
    if command == "file.newProject":
        return {"name": p.get("name")}
    if command == "file.newSequence":
        return {"item": 1}
    if command == "file.save":
        return {"path": p.get("path")}
    if command == "file.import":
        return {"items": [2], "errors": []}
    if command == "timeline.place":
        return {"clips": [10, 11]}
    if command == "sequence.inspect":
        return {
            "id": 1, "settings": {"width": 1920, "height": 1080, "frame_rate": {"num": 24, "den": 1}},
            "video": [{"id": 3, "name": "Video 1", "items": [
                {"clip": 10, "item": 2, "start": 0, "duration": 48 * 10**10, "end": 48 * 10**10, "name": "a"},
                {"clip": 12, "item": 2, "start": 48 * 10**10, "duration": 48 * 10**10, "end": 96 * 10**10, "name": "b"},
            ], "transitions": []}],
            "audio": [{"id": 4, "name": "Audio 1", "items": [{"clip": 11, "start": 0, "end": 1, "name": "a"}], "transitions": []}],
        }
    if command == "sequence.applyVideoTransition":
        return {"transition": 20, "effect": p.get("effect"), "clip": p.get("clip"), "edge": p.get("edge")}
    if command == "graphics.newText":
        return {"clip": 30, "layer": 0}
    if command == "captions.add":
        return {"caption": 40}
    if command == "clip.audioGain":
        return {"clips": p.get("clips"), "db": p.get("db")}
    if command == "effects.setParam":
        return {"keyframes": 1, "param": p.get("param"), "value": p.get("value")}
    if command == "file.exportMedia":
        return {"job": 7, "path": p.get("path"), "warnings": []}
    if command == "jobs.list":
        return [{"id": 7, "label": "Export", "progress": 1, "finished": True, "etaSeconds": 0, "result": {"path": "out.mp4"}}]
    if command == "file.exportFrame":
        return {"path": p.get("path"), "time": p.get("time")}
    if command == "project.inspect":
        return {"name": "Demo"}
    if command == "media.status":
        return {"items": [{"item": 2, "status": "online"}]}
    if command == "media.findMissing":
        return {"missing": []}
    if command == "sequence.settings":
        return p
    if command == "timeline.move":
        return {"moved": [p["moves"][0]["clip"]]}
    if command == "timeline.trim":
        return {"clip": p.get("clip")}
    if command == "timeline.delete":
        return {"clips": p.get("clips")}
    if command == "timeline.razor":
        return {"clips": [13]}
    if command == "effects.apply":
        return {"effect": p.get("effect")}
    return {"command": command}


class FlowTest(unittest.TestCase):
    def setUp(self):
        self.server = Server()

    def tearDown(self):
        self.server.close()

    def test_edit_to_export(self):
        port = self.server.port
        steps = [
            ["new", "Demo", "--fps", "24", "--width", "1920", "--height", "1080"],
            ["import", r"C:\clips\a.mp4"],
            ["add-clips", "2", "2", "--at", "0"],
            ["transition", "--dur", "0.5", "--effect", "cross_dissolve", "--track", "V1"],
            ["text", "字幕", "--start", "1", "--dur", "2", "--track", "V2", "--size", "72"],
            ["caption", "你好", "--start", "1", "--dur", "2"],
            ["volume", "--db", "-14", "--track", "A1"],
            ["keyframe", "10", "motion", "scale", "--at", "1", "--value", "120"],
            ["move", "10", "--track", "V2", "--at", "3"],
            ["trim", "10", "--edge", "out", "--frames", "-12"],
            ["effect", "10", "gaussian_blur"],
            ["sequence", "--fps", "24"],
            ["export", r"C:\out\demo.mp4", "--end", "10", "--wait", "--poll", "0.01", "--timeout", "5"],
            ["frame", r"C:\out\frame.png", "--at", "1.5"],
            ["show"],
            ["media-status"],
            ["jobs"],
            ["status"],
        ]
        for args in steps:
            body = run(args, port)
            self.assertTrue(body.get("ok"), (args, body))
            self.assertEqual(body["result"]["via"], "control", args)
        names = [c["params"].get("command") or c["method"] for c in self.server.calls]
        for needed in (
            "file.newProject", "file.newSequence", "file.import", "timeline.place",
            "sequence.applyVideoTransition", "graphics.newText", "captions.add",
            "clip.audioGain", "effects.setParam", "timeline.move", "timeline.trim",
            "effects.apply", "sequence.settings", "file.exportMedia", "jobs.list",
            "file.exportFrame", "sequence.inspect", "project.inspect", "media.status",
            "media.findMissing",
        ):
            self.assertIn(needed, names, needed)
        export = next(c for c in self.server.calls if c["params"].get("command") == "file.exportMedia")
        self.assertEqual(export["params"]["params"]["range"], "custom")
        self.assertEqual(export["params"]["params"]["endSeconds"], 10)
        frame = next(c for c in self.server.calls if c["params"].get("command") == "file.exportFrame")
        self.assertEqual(frame["params"]["params"]["time"], 254016000000 + 127008000000)
        self.assertEqual(frame["params"]["params"]["target"], "program")

    def test_command_error_is_json(self):
        # A failing command must not be reported as a traceback.
        self.server.close()
        sock = socket.socket()
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
        sock.listen(1)

        def once():
            while True:
                conn, _ = sock.accept()
                f = conn.makefile("rwb")
                line = f.readline()
                if not line:
                    conn.close()
                    continue
                req = json.loads(line.decode())
                f.write((json.dumps({"id": req["id"], "ok": False, "error": "no sequence is open"}) + "\n").encode())
                f.flush()
                conn.close()
                sock.close()
                return
        threading.Thread(target=once, daemon=True).start()
        body = run(["show"], port)
        self.assertFalse(body["ok"])
        self.assertEqual(body["error"], "no sequence is open")
        self.assertEqual(body["_code"], 1)

    def test_batch(self):
        path = os.path.join(tempfile.mkdtemp(), "steps.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump([{"command": "playhead.set", "params": {"seconds": 1}}], fh)
        body = run(["batch", path], self.server.port)
        self.assertTrue(body["ok"], body)
        self.assertEqual(self.server.calls[-1]["method"], "engine.batch")


class OfflineTest(unittest.TestCase):
    def test_project_round_trip_matches_schema(self):
        from jsonschema import Draft202012Validator
        folder = tempfile.mkdtemp()
        path = os.path.join(folder, "demo.fcproj")
        media = os.path.join(folder, "clip.mp4")
        open(media, "wb").close()
        port = 1
        made = run(["-p", path, "new", "Demo", "--fps", "24"], port, offline=True)
        self.assertTrue(made["ok"], made)
        imported = run(["-p", path, "media", media, "--duration", "4", "--width", "1280", "--height", "720", "--fps", "24", "--no-audio"], port, offline=True)
        self.assertTrue(imported["ok"], imported)
        item = imported["result"]["items"][0]
        placed = run(["-p", path, "add-clips", str(item), str(item), "--no-audio"], port, offline=True)
        self.assertTrue(placed["ok"], placed)
        clip = placed["result"]["clips"][0]
        for args in (
            ["-p", path, "transition", "--frames", "12", "--effect", "cross_dissolve"],
            ["-p", path, "text", "標題", "--start", "0.5", "--dur", "2", "--track", "V2"],
            ["-p", path, "caption", "你好", "--start", "0.5", "--dur", "2"],
            ["-p", path, "volume", "--db", "-12", "--clip", str(clip), "--track", "A1"],
            ["-p", path, "keyframe", str(clip), "motion", "opacity", "--at", "1", "--value", "80"],
            ["-p", path, "validate"],
        ):
            body = run(args, port, offline=True)
            self.assertTrue(body["ok"], (args, body))
        with open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
        with open(os.path.join(ROOT, "schema", "fcproj.schema.json"), encoding="utf-8") as fh:
            schema = json.load(fh)
        errors = list(Draft202012Validator(schema).iter_errors(doc))
        self.assertEqual(errors, [], [e.message for e in errors[:5]])
        seq = next(it["kind"]["Sequence"] for it in doc["project"]["items"].values() if "Sequence" in it["kind"])
        self.assertTrue(seq["video_tracks"][0]["transitions"])
        self.assertTrue(seq["caption_tracks"][0]["captions"])
        self.assertIn("graphic_text", [e["effect"] for c in seq["video_tracks"][1]["items"] for e in c["effects"]])

    def test_commands_exist_in_source(self):
        blob = []
        root = os.path.join(SRC, "crates", "engine", "src")
        for dirpath, _, files in os.walk(root):
            for name in files:
                if name.endswith(".rs"):
                    with open(os.path.join(dirpath, name), encoding="utf-8", errors="replace") as fh:
                        blob.append(fh.read())
        text = "\n".join(blob)
        for command in (
            "file.newProject", "file.open", "file.save", "file.import", "timeline.place",
            "timeline.move", "timeline.trim", "timeline.delete", "timeline.razor",
            "sequence.applyVideoTransition", "sequence.applyAudioTransition", "effects.apply",
            "effects.setParam", "effects.addKeyframe", "graphics.newText", "captions.add",
            "clip.audioGain", "sequence.settings", "file.exportMedia", "file.exportFrame",
            "sequence.inspect", "project.inspect", "media.status", "media.findMissing", "jobs.list",
        ):
            self.assertIn('"%s"' % command, text, command)


if __name__ == "__main__":
    unittest.main()
