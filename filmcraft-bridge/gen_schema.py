"""Build fcproj.schema.json from the FilmCraft 0.15 source (schema 15).

Field names, defaults and required-ness follow the serde types in crates/project,
crates/media, crates/time and crates/color. Effect and transition ids are read
from the effect registries. Run: python gen_schema.py
"""
import json, os, re

SRC = os.environ.get(
    "FILMCRAFT_SRC",
    r"C:\Users\wuyou\Downloads\filmcraft-main\filmcraft-main",
)
OUTS = [
    os.path.join(os.path.dirname(os.path.realpath(__file__)), "schema", "fcproj.schema.json"),
    os.path.join(SRC, "docs", "fcproj.schema.json"),
]

def effects():
    root = os.path.join(SRC, "crates", "project", "src")
    found = {}
    call = re.compile(r'\b(?:video|audio|tr)\(\s*"([A-Za-z0-9_]+)"\s*,\s*"([^"]+)"')
    block = re.compile(
        r'id:\s*"([A-Za-z0-9_]+)"\s*,\s*name:\s*"([^"]+)"\s*,\s*kind:\s*EffectKind::(\w+)',
        re.S,
    )
    kind_of = {"video": "Video", "audio": "Audio", "tr": "VideoTransition"}
    for dirpath, _, files in os.walk(root):
        for name in files:
            if not name.endswith(".rs"):
                continue
            text = open(os.path.join(dirpath, name), encoding="utf-8").read()
            for m in call.finditer(text):
                fn = m.group(0).split("(")[0].split()[-1]
                found[m.group(1)] = {"id": m.group(1), "name": m.group(2), "kind": kind_of.get(fn, "Video")}
            for m in block.finditer(text):
                found[m.group(1)] = {"id": m.group(1), "name": m.group(2), "kind": m.group(3)}
    found["graphic_text"] = {"id": "graphic_text", "name": "Text", "kind": "Video"}
    found["graphic_shape"] = {"id": "graphic_shape", "name": "Shape", "kind": "Video"}
    return sorted(found.values(), key=lambda e: (e["kind"], e["id"]))

def schema(catalog):
    tick = {"type": "integer", "description": "Time in ticks. 254016000000 ticks = 1 second. serde transparent i64."}
    id_ = {"type": "integer", "minimum": 0}
    vec2 = {"type": "object", "required": ["x", "y"], "properties": {
        "x": {"type": ["number", "null"], "description": "null is NaN, meaning auto (frame or source centre) on point parameters only"},
        "y": {"type": ["number", "null"]},
    }, "additionalProperties": False}
    color4 = {"type": "array", "items": {"type": "number"}, "minItems": 4, "maxItems": 4, "description": "straight sRGB RGBA, 0..1"}
    rate = {"type": "object", "required": ["num", "den"], "properties": {"num": {"type": "integer"}, "den": {"type": "integer"}}, "additionalProperties": False,
            "description": "Exact frames per second, num/den. Defaults: 24000/1001."}
    param_value = {"oneOf": [
        {"type": "object", "required": ["Float"], "properties": {"Float": {"type": "number"}}, "additionalProperties": False},
        {"type": "object", "required": ["Vec2"], "properties": {"Vec2": {"$ref": "#/$defs/vec2"}}, "additionalProperties": False},
        {"type": "object", "required": ["Color"], "properties": {"Color": color4}, "additionalProperties": False},
        {"type": "object", "required": ["Bool"], "properties": {"Bool": {"type": "boolean"}}, "additionalProperties": False},
        {"type": "object", "required": ["Choice"], "properties": {"Choice": {"type": "integer", "minimum": 0}}, "additionalProperties": False},
        {"type": "object", "required": ["Text"], "properties": {"Text": {"type": "string"}}, "additionalProperties": False},
        {"type": "object", "required": ["Curve"], "properties": {"Curve": {"type": "array", "items": {"type": "array", "items": {"type": "number"}, "minItems": 2, "maxItems": 2}}}, "additionalProperties": False},
        {"type": "object", "required": ["Path"], "properties": {"Path": {"$ref": "#/$defs/maskPath"}}, "additionalProperties": False},
    ]}
    keyframe = {"type": "object", "required": ["time", "value", "interp"], "properties": {
        "time": tick, "value": param_value,
        "interp": {"enum": ["Linear", "Hold", "Bezier", "AutoBezier", "ContinuousBezier", "EaseIn", "EaseOut"], "default": "Linear"},
        "out_influence": {"type": "number", "default": 0.3333333333333333},
        "in_influence": {"type": "number", "default": 0.3333333333333333},
    }, "additionalProperties": False}
    param = {"type": "object", "required": ["value"], "properties": {
        "value": param_value,
        "keyframes": {"type": "array", "items": keyframe, "description": "Clip-relative ticks. Empty or omitted = static. Default empty."},
    }, "additionalProperties": False}
    label = {"enum": ["Violet", "Iris", "Caribbean", "Lavender", "Cerulean", "Forest", "Rose", "Mango", "Purple", "Blue", "Teal", "Magenta", "Tan", "Green", "Brown", "Yellow"]}
    channels = {"enum": ["Mono", "Stereo", "Surround51", "Adaptive"], "default": "Stereo"}
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://filmcraft.local/schema/fcproj-v15.json",
        "title": "FilmCraft project (.fcproj)",
        "description": "UTF-8 JSON written by filmcraft-format, schema_version 15 (FilmCraft 0.15). Media is referenced by path, never embedded. Files are compact. Ticks: 254016000000 per second. A null coordinate of a point parameter is NaN (auto). This schema lists every field the 0.15 model reads; fields with serde default may be omitted. Unknown future fields are allowed on the envelope and project so a newer optional key does not fail a reader that only checks this file.",
        "type": "object",
        "required": ["format", "schema_version", "project"],
        "properties": {
            "format": {"const": "filmcraft.project"},
            "schema_version": {"type": "integer", "minimum": 1, "maximum": 15, "description": "This build writes 15 and reads 1..15. Newer files are refused."},
            "generator": {"type": "string", "examples": ["FilmCraft 0.15.0"]},
            "project": {"$ref": "#/$defs/project"},
            "view": {"$ref": "#/$defs/projectView", "description": "Optional. Not part of the edit, not an undo step. Omitted when nothing is open."},
        },
        "additionalProperties": True,
        "$defs": {
            "tick": tick,
            "vec2": vec2,
            "frameRate": rate,
            "paramValue": param_value,
            "param": param,
            "keyframe": keyframe,
            "label": label,
            "interpolation": {"enum": ["Linear", "Hold", "Bezier", "AutoBezier", "ContinuousBezier", "EaseIn", "EaseOut"]},
            "project": {
                "type": "object",
                "required": ["name", "settings", "root", "items", "next_id"],
                "properties": {
                    "name": {"type": "string"},
                    "settings": {"$ref": "#/$defs/projectSettings"},
                    "root": {"$ref": "#/$defs/bin"},
                    "items": {"type": "object", "additionalProperties": {"$ref": "#/$defs/projectItem"}, "description": "Map of decimal item id (string key) to item. Ids are u64."},
                    "next_id": {"type": "integer", "minimum": 1, "description": "Next id handed out. Must be greater than every id in use. Default for a new project: 1."},
                    "luts": {"type": "array", "items": {"$ref": "#/$defs/lut"}, "description": "Default empty. Omitted when empty."},
                    "transcripts": {"type": "object", "additionalProperties": {"type": "object"}, "description": "Media item id -> transcript. Default empty, omitted when empty."},
                    "search_bins": {"type": "array", "items": {"type": "object"}, "description": "Schema v11. Default empty, omitted when empty."},
                    "source_graphics": {"type": "object", "additionalProperties": {"type": "object"}, "description": "Schema v12. Default empty, omitted when empty."},
                    "narrations": {"type": "object", "additionalProperties": {"type": "object"}, "description": "Schema v14. Default empty, omitted when empty."},
                    "notes": {"type": "string", "default": "", "description": "Schema v15. Omitted when empty."},
                },
                "additionalProperties": True,
            },
            "projectSettings": {
                "type": "object",
                "required": ["renderer", "video_display", "audio_display_samples", "default_still_duration", "default_transition_duration_frames", "default_audio_transition_duration"],
                "properties": {
                    "renderer": {"type": "string", "default": "FilmCraft GPU Acceleration (wgpu)"},
                    "video_display": {"enum": ["Timecode", "Frames", "Feet16", "Feet35", "AudioSamples", "Seconds"], "default": "Timecode"},
                    "audio_display_samples": {"type": "boolean", "default": True},
                    "default_still_duration": {**tick, "default": 1270080000000, "description": "5 seconds. The editor uses the Timeline preference instead."},
                    "default_transition_duration_frames": {"type": "integer", "default": 24},
                    "default_audio_transition_duration": {**tick, "default": 254016000000},
                    "ingest": {"$ref": "#/$defs/ingest", "description": "Default: enabled false, action createProxies, destination null, preset empty."},
                    "title_safe": {"type": "array", "items": {"type": "number"}, "minItems": 2, "maxItems": 2, "default": [20, 20], "description": "Horizontal, vertical percent."},
                    "action_safe": {"type": "array", "items": {"type": "number"}, "minItems": 2, "maxItems": 2, "default": [10, 10]},
                    "capture_format": {"type": "string", "default": "DV"},
                    "scratch": {"$ref": "#/$defs/scratch"},
                },
                "additionalProperties": False,
            },
            "ingest": {
                "type": "object",
                "properties": {
                    "enabled": {"type": "boolean", "default": False},
                    "action": {"enum": ["copy", "transcode", "createProxies", "copyAndCreateProxies"], "default": "createProxies"},
                    "destination": {"type": ["string", "null"], "default": None},
                    "preset": {"type": "string", "default": ""},
                },
                "additionalProperties": False,
            },
            "scratch": {
                "type": "object",
                "properties": {
                    "captured": {"type": ["string", "null"], "default": None},
                    "videoPreviews": {"type": ["string", "null"], "default": None},
                    "audioPreviews": {"type": ["string", "null"], "default": None},
                    "autoSave": {"type": ["string", "null"], "default": None},
                },
                "additionalProperties": False,
            },
            "bin": {
                "type": "object",
                "required": ["id", "name", "children"],
                "properties": {
                    "id": id_, "name": {"type": "string"},
                    "children": {"type": "array", "items": {"oneOf": [
                        {"type": "object", "required": ["Item"], "properties": {"Item": id_}, "additionalProperties": False},
                        {"type": "object", "required": ["Bin"], "properties": {"Bin": {"$ref": "#/$defs/bin"}}, "additionalProperties": False},
                    ]}},
                },
                "additionalProperties": False,
            },
            "projectItem": {
                "type": "object",
                "required": ["id", "name", "label", "kind"],
                "properties": {
                    "id": id_, "name": {"type": "string"}, "label": {"$ref": "#/$defs/label"},
                    "kind": {"$ref": "#/$defs/itemKind"},
                    "metadata": {"type": "object", "additionalProperties": {"type": "string"}, "default": {}},
                    "created": {"type": "integer", "default": 0, "description": "Import counter, not wall clock."},
                    "split": {"$ref": "#/$defs/splitMarks"},
                },
                "additionalProperties": False,
            },
            "itemKind": {"oneOf": [
                {"type": "object", "required": ["Media"], "properties": {"Media": {"$ref": "#/$defs/mediaClip"}}, "additionalProperties": False},
                {"type": "object", "required": ["Sequence"], "properties": {"Sequence": {"$ref": "#/$defs/sequence"}}, "additionalProperties": False},
                {"type": "object", "required": ["Subclip"], "properties": {"Subclip": {"type": "object", "required": ["parent", "range"], "properties": {
                    "parent": id_, "range": {"$ref": "#/$defs/timeRange"}, "restrict_trims": {"type": "boolean", "default": False}}}}, "additionalProperties": False},
                {"type": "object", "required": ["AdjustmentLayer"], "properties": {"AdjustmentLayer": {"type": "object", "required": ["width", "height", "rate", "duration"], "properties": {
                    "width": {"type": "integer"}, "height": {"type": "integer"}, "rate": rate, "duration": tick}, "additionalProperties": False}}, "additionalProperties": False},
                {"type": "object", "required": ["Graphic"], "properties": {"Graphic": {"type": "object", "required": ["width", "height", "rate"], "properties": {
                    "width": {"type": "integer"}, "height": {"type": "integer"}, "rate": rate}, "additionalProperties": False}}, "additionalProperties": False},
            ]},
            "mediaClip": {
                "type": "object",
                "required": ["media", "info", "interpret", "mark_in", "mark_out", "markers", "offline", "proxy"],
                "properties": {
                    "media": {"$ref": "#/$defs/mediaRef"},
                    "info": {"$ref": "#/$defs/mediaInfo"},
                    "interpret": {"$ref": "#/$defs/interpretation"},
                    "mark_in": {"type": ["integer", "null"]},
                    "mark_out": {"type": ["integer", "null"]},
                    "markers": {"type": "array", "items": {"$ref": "#/$defs/marker"}},
                    "offline": {"type": "boolean", "description": "Made offline on purpose. A missing file is detected at runtime and is not stored."},
                    "proxy": {"anyOf": [{"$ref": "#/$defs/mediaRef"}, {"type": "null"}]},
                    "identity": {"type": "object", "required": ["size", "fingerprint"], "properties": {
                        "size": {"type": "integer"}, "fingerprint": {"type": "string", "pattern": "^[0-9a-fA-F]{16}$"}},
                        "description": "Optional. Omitted for generators and projects from before schema 6. Hex fingerprint of size + first MiB + last MiB."},
                },
                "additionalProperties": False,
            },
            "mediaRef": {"oneOf": [
                {"type": "object", "required": ["File"], "properties": {"File": {"type": "object", "required": ["path"], "properties": {"path": {"type": "string"}}, "additionalProperties": False}}, "additionalProperties": False},
                {"type": "object", "required": ["Generator"], "properties": {"Generator": {"description": "BarsAndTone | BlackVideo | TransparentVideo | CountingLeader | {ColorMatte:{color:[r,g,b,a]}} | {Demo:<scene>} | {Tone:{hz,db}}"}}, "additionalProperties": False},
            ]},
            "mediaInfo": {
                "type": "object",
                "required": ["name", "kind", "duration", "video", "audio_streams", "container", "start_timecode", "file_size"],
                "properties": {
                    "name": {"type": "string"},
                    "kind": {"enum": ["Movie", "AudioOnly", "Still", "ImageSequence", "Synthetic"]},
                    "duration": tick,
                    "video": {"anyOf": [{"$ref": "#/$defs/videoStream"}, {"type": "null"}]},
                    "audio_streams": {"type": "array", "items": {"$ref": "#/$defs/audioStream"}, "description": "Schema v13. Older files used a single `audio` object or null; both load as this array. Stream 0 is the primary stream."},
                    "container": {"type": "string"},
                    "start_timecode": {"type": ["integer", "null"], "description": "First frame, in frames at video.frame_rate."},
                    "file_size": {"type": ["integer", "null"]},
                },
                "additionalProperties": False,
            },
            "videoStream": {
                "type": "object",
                "required": ["width", "height", "frame_rate", "par", "codec", "pixel_format", "color", "has_alpha", "bitrate"],
                "properties": {
                    "width": {"type": "integer"}, "height": {"type": "integer"}, "frame_rate": rate,
                    "par": {"type": "array", "items": {"type": "integer"}, "minItems": 2, "maxItems": 2, "description": "Pixel aspect, numerator then denominator. Square is [1, 1]."},
                    "codec": {"type": "string"}, "pixel_format": {"type": "string"},
                    "color": {"type": "object", "required": ["matrix", "transfer", "primaries", "range"], "properties": {
                        "matrix": {"enum": ["Bt601", "Bt709", "Bt2020Ncl"]},
                        "transfer": {"enum": ["Bt709", "Srgb", "Linear", "Pq", "Hlg"]},
                        "primaries": {"enum": ["Bt709", "Bt601_625", "Bt601_525", "Bt2020", "P3D65"]},
                        "range": {"enum": ["Limited", "Full"]},
                    }, "additionalProperties": False},
                    "has_alpha": {"type": "boolean"},
                    "bitrate": {"type": ["integer", "null"], "description": "Bits per second."},
                    "hdr": {"type": "object", "properties": {
                        "masteringMaxNits": {"type": ["number", "null"]}, "masteringMinNits": {"type": ["number", "null"]},
                        "maxCll": {"type": ["number", "null"]}, "maxFall": {"type": ["number", "null"]},
                    }},
                },
                "additionalProperties": False,
            },
            "audioStream": {
                "type": "object",
                "required": ["sample_rate", "channels", "codec", "bits_per_sample"],
                "properties": {
                    "sample_rate": {"type": "integer"}, "channels": {"type": "integer"}, "codec": {"type": "string"},
                    "bits_per_sample": {"type": ["integer", "null"]},
                },
                "additionalProperties": False,
            },
            "interpretation": {
                "type": "object",
                "required": ["frame_rate", "par", "ignore_alpha", "invert_alpha"],
                "properties": {
                    "frame_rate": {"anyOf": [rate, {"type": "null"}]},
                    "par": {"anyOf": [{"type": "array", "items": {"type": "integer"}, "minItems": 2, "maxItems": 2}, {"type": "null"}]},
                    "ignore_alpha": {"type": "boolean", "default": False},
                    "invert_alpha": {"type": "boolean", "default": False},
                    "color_space": {"enum": ["Rec709", "Srgb", "Rec2020", "P3D65", "Rec2100Pq", "Rec2100Hlg", "SLog3SGamut3Cine", "SLog3SGamut3", "VLogVGamut", "CLog2CinemaGamut", "CLog3CinemaGamut", "LogC3Awg3", "LogC4Awg4", "AppleLog", "DLogDGamut", "FLogFGamut", "FLog2FGamut", "FLog2CFGamutC", "Linear709"], "description": "Optional Interpret Footage override."},
                    "audio_channels": {"type": "object", "properties": {"format": channels, "clips": {"type": "array", "items": {"type": "array", "items": {"type": "integer"}}}}, "description": "Modify > Audio Channels. Optional."},
                },
                "additionalProperties": False,
            },
            "sequence": {
                "type": "object",
                "required": ["settings", "video_tracks", "audio_tracks", "markers", "mark_in", "mark_out", "work_area", "start_timecode"],
                "properties": {
                    "settings": {"$ref": "#/$defs/sequenceSettings"},
                    "video_tracks": {"type": "array", "items": {"$ref": "#/$defs/track"}},
                    "audio_tracks": {"type": "array", "items": {"$ref": "#/$defs/track"}},
                    "markers": {"type": "array", "items": {"$ref": "#/$defs/marker"}},
                    "mark_in": {"type": ["integer", "null"]},
                    "mark_out": {"type": ["integer", "null"]},
                    "work_area": {"anyOf": [{"$ref": "#/$defs/timeRange"}, {"type": "null"}]},
                    "start_timecode": {"type": "integer", "description": "Frames. 0 is the default for a new sequence.", "default": 0},
                    "master_volume_db": {"type": "number", "default": 0},
                    "master_effects": {"type": "array", "items": {"$ref": "#/$defs/effectInstance"}, "default": []},
                    "master_mixer": {"$ref": "#/$defs/mixer"},
                    "submix_tracks": {"type": "array", "items": {"$ref": "#/$defs/track"}, "default": []},
                    "caption_tracks": {"type": "array", "items": {"$ref": "#/$defs/captionTrack"}, "default": []},
                    "multicam": {"type": "object", "description": "Schema v8. Omitted when the sequence is not a multi-camera source."},
                    "merged": {"type": "object", "description": "Schema v8. Omitted unless this sequence is a merged clip."},
                    "split": {"$ref": "#/$defs/splitMarks"},
                },
                "additionalProperties": False,
            },
            "sequenceSettings": {
                "type": "object",
                "required": ["width", "height", "frame_rate", "par", "sample_rate", "drop_frame", "preset", "audio_master", "preview_codec", "max_bit_depth", "max_render_quality", "working_space", "color"],
                "properties": {
                    "width": {"type": "integer", "minimum": 1, "maximum": 32768, "default": 1920},
                    "height": {"type": "integer", "minimum": 1, "maximum": 32768, "default": 1080},
                    "frame_rate": rate,
                    "par": {"type": "array", "items": {"type": "integer", "minimum": 1}, "minItems": 2, "maxItems": 2, "default": [1, 1]},
                    "sample_rate": {"type": "integer", "minimum": 1, "maximum": 384000, "default": 48000},
                    "drop_frame": {"type": "boolean", "default": False},
                    "preset": {"type": "string", "default": "HD 1080p 23.976"},
                    "audio_master": channels,
                    "preview_codec": {"type": "string", "default": "ProRes 422"},
                    "max_bit_depth": {"type": "boolean", "default": False},
                    "max_render_quality": {"type": "boolean", "default": False},
                    "working_space": {"type": "string", "default": "Rec. 709", "description": "Display label. `color` is authoritative."},
                    "color": {"type": "object", "required": ["working", "wide_gamut", "auto_tone_map"], "properties": {
                        "working": {"enum": ["Rec709", "Rec2100Pq", "Rec2100Hlg"], "default": "Rec709"},
                        "wide_gamut": {"type": "boolean", "default": False},
                        "auto_tone_map": {"type": "boolean", "default": True},
                    }, "additionalProperties": False},
                },
                "additionalProperties": False,
            },
            "track": {
                "type": "object",
                "required": ["id", "kind", "name", "items", "transitions", "locked", "sync_lock", "enabled", "muted", "solo", "channels", "volume_db", "pan"],
                "properties": {
                    "id": id_,
                    "kind": {"enum": ["Video", "Audio"], "default": "Video"},
                    "name": {"type": "string", "description": "Engine names are `Video N` and `Audio N`. Commands also accept V1 / A1."},
                    "items": {"type": "array", "items": {"$ref": "#/$defs/trackItem"}},
                    "transitions": {"type": "array", "items": {"$ref": "#/$defs/transition"}},
                    "locked": {"type": "boolean", "default": False},
                    "sync_lock": {"type": "boolean", "default": True},
                    "enabled": {"type": "boolean", "default": True, "description": "Video: eye. Audio: not muted by the eye toggle."},
                    "muted": {"type": "boolean", "default": False},
                    "solo": {"type": "boolean", "default": False},
                    "channels": channels,
                    "volume_db": {"type": "number", "default": 0},
                    "pan": {"type": "number", "default": 0, "description": "-100..100"},
                    "effects": {"type": "array", "items": {"$ref": "#/$defs/effectInstance"}, "default": []},
                    "mixer": {"$ref": "#/$defs/mixer"},
                    "label": {"anyOf": [label, {"type": "null"}], "description": "Optional. Omitted when the track has no colour."},
                },
                "additionalProperties": False,
            },
            "trackItem": {
                "type": "object",
                "required": ["id", "item", "name", "label", "start", "duration", "source_in", "speed", "enabled", "effects"],
                "description": "A clip on a track. start/duration are sequence ticks. source_in is media time. Items on one track do not overlap.",
                "properties": {
                    "id": id_, "item": id_, "name": {"type": "string"}, "label": {"$ref": "#/$defs/label"},
                    "start": tick, "duration": tick, "source_in": tick,
                    "speed": {"type": "number", "description": "1.0 = 100%. Negative means reverse; `reverse` is the flag the editor uses."},
                    "reverse": {"type": "boolean", "default": False},
                    "enabled": {"type": "boolean"},
                    "link": {"type": ["integer", "null"], "default": None, "description": "Shared link id of the video/audio partners."},
                    "group": {"type": ["integer", "null"], "default": None},
                    "effects": {"type": "array", "items": {"$ref": "#/$defs/effectInstance"}},
                    "markers": {"type": "array", "items": {"$ref": "#/$defs/marker"}, "default": []},
                    "gain_db": {"type": "number", "default": 0, "description": "Clip gain, separate from the Volume effect."},
                    "frame_hold": {"type": ["integer", "null"], "default": None},
                    "scale_to_frame": {"type": "boolean", "default": False},
                    "essential": {"type": "object", "description": "Essential Sound. Optional. kind is Dialogue|Music|SFX|Ambience."},
                    "multicam": {"type": "object"},
                    "time_interpolation": {"enum": ["frameSampling", "frameBlending", "opticalFlow"], "default": "frameSampling", "description": "Omitted when frameSampling."},
                    "hold_filters": {"type": "boolean", "default": False, "description": "Omitted when false."},
                    "field_options": {"type": "object", "properties": {
                        "reverseFieldDominance": {"type": "boolean"},
                        "processing": {"enum": ["none", "alwaysDeinterlace", "flickerRemoval"]},
                    }},
                    "source_channels": {"type": "array", "items": {"type": "integer"}, "description": "Audio source channels, 0-based. Omitted when empty (first two channels)."},
                    "audio_stream": {"type": "integer", "minimum": 0, "default": 0, "description": "Schema v13. Omitted when 0."},
                    "graphic": {"$ref": "#/$defs/graphicMeta"},
                },
                "additionalProperties": False,
            },
            "transition": {
                "type": "object",
                "required": ["id", "effect", "start", "duration", "from", "to", "align"],
                "properties": {
                    "id": id_,
                    "effect": {"$ref": "#/$defs/effectInstance"},
                    "start": tick, "duration": tick,
                    "from": {"type": ["integer", "null"], "description": "Outgoing clip. Null = fade in from nothing."},
                    "to": {"type": ["integer", "null"], "description": "Incoming clip. Null = fade out to nothing."},
                    "align": {"enum": ["CenterAtCut", "StartAtCut", "EndAtCut"], "default": "CenterAtCut"},
                    "reverse": {"type": "boolean", "default": False},
                },
                "additionalProperties": False,
            },
            "effectInstance": {
                "type": "object",
                "required": ["effect", "enabled", "params"],
                "properties": {
                    "effect": {"type": "string", "description": "Stable effect id. See effectCatalog. Video clips carry intrinsic motion, opacity and time_remap. Audio clips carry volume, channel_volume and panner. Text is graphic_text. Shapes are graphic_shape."},
                    "enabled": {"type": "boolean", "default": True},
                    "params": {"type": "object", "additionalProperties": {"$ref": "#/$defs/param"}},
                    "masks": {"type": "array", "items": {"$ref": "#/$defs/mask"}, "description": "Schema v7. Omitted when empty."},
                    "post_fader": {"type": "boolean", "default": False, "description": "Track/mix inserts. Omitted when false."},
                    "essential": {"type": "boolean", "default": False, "description": "Omitted when false."},
                    "layer": {"$ref": "#/$defs/layerExtra"},
                },
                "additionalProperties": False,
            },
            "effectCatalog": {
                "description": "Every effect and transition id registered in FilmCraft 0.15. Not a constraint: a project may name an id the renderer does not implement, and the file still opens.",
                "type": "array",
                "items": {"type": "object", "required": ["id", "name", "kind"], "properties": {
                    "id": {"type": "string"}, "name": {"type": "string"},
                    "kind": {"enum": ["Video", "Audio", "VideoTransition", "AudioTransition"]},
                }},
                "const": catalog,
            },
            "textStyle": {
                "description": "graphic_text parameters (Effect Controls). Choice indexes: align Left=0 Center=1 Right=2 Justify=3; caps Normal=0 All Caps=1 Small Caps=2; fill_kind Solid=0 Linear Gradient=1; stroke type Outer=0 Center=1 Inner=2. Defaults in parentheses.",
                "type": "object",
                "properties": {
                    "text": {"type": "string"}, "font": {"default": "Inter"}, "font_style": {"default": "Regular"},
                    "size": {"default": 100}, "align": {"default": 0}, "tracking": {"default": 0},
                    "kerning": {"default": True}, "ligatures": {"default": True}, "leading": {"default": 0},
                    "baseline_shift": {"default": 0}, "faux_bold": {"default": False}, "faux_italic": {"default": False},
                    "caps": {"default": 0}, "underline": {"default": False}, "strikethrough": {"default": False},
                    "box_width": {"default": 0}, "box_height": {"default": 0}, "vertical": {"default": False},
                    "fill": {"default": True}, "fill_color": {"default": [1, 1, 1, 1]}, "fill_kind": {"default": 0},
                    "stroke": {"default": False}, "stroke_width": {"default": 4},
                    "shadow": {"default": False}, "background": {"default": False},
                    "position": {"description": "Layer position. null coordinate = auto."},
                    "anchor": {}, "scale": {"default": 100}, "rotation": {"default": 0}, "opacity": {"default": 100},
                },
            },
            "mask": {
                "type": "object",
                "required": ["name", "path", "feather", "opacity", "expansion"],
                "properties": {
                    "name": {"type": "string"},
                    "path": {"$ref": "#/$defs/param"}, "feather": {"$ref": "#/$defs/param"},
                    "opacity": {"$ref": "#/$defs/param"}, "expansion": {"$ref": "#/$defs/param"},
                    "inverted": {"type": "boolean", "default": False},
                    "mode": {"enum": ["None", "Add", "Subtract", "Intersect", "Lighten", "Darken", "Difference"], "default": "Add"},
                    "track_method": {"enum": ["Position", "PositionRotation", "PositionScaleRotation"], "default": "PositionScaleRotation"},
                },
                "additionalProperties": False,
            },
            "maskPath": {"type": "object", "description": "Closed cubic Bezier in clip pixels. Vertices are {p, t_in, t_out} with Vec2 points.", "additionalProperties": True},
            "marker": {
                "type": "object",
                "required": ["id", "start", "duration", "name", "comment", "kind", "color"],
                "properties": {
                    "id": id_, "start": tick, "duration": tick, "name": {"type": "string"}, "comment": {"type": "string"},
                    "kind": {"enum": ["Comment", "Chapter", "Segmentation", "WebLink", "FlashCue"], "default": "Comment"},
                    "color": {"$ref": "#/$defs/label"},
                },
                "additionalProperties": False,
            },
            "captionTrack": {
                "type": "object",
                "required": ["id", "name", "format", "enabled", "locked", "captions"],
                "properties": {
                    "id": id_, "name": {"type": "string"},
                    "format": {"enum": ["Subtitle", "Cea608", "Cea708", "Teletext"], "default": "Subtitle"},
                    "language": {"type": "string", "default": "en"},
                    "style": {"$ref": "#/$defs/captionStyle"},
                    "enabled": {"type": "boolean", "default": True},
                    "locked": {"type": "boolean", "default": False},
                    "sync_lock": {"type": "boolean", "default": True},
                    "captions": {"type": "array", "items": {"$ref": "#/$defs/caption"}},
                    "vtt_blocks": {"type": "array", "items": {"type": "string"}, "default": []},
                },
                "additionalProperties": False,
            },
            "caption": {
                "type": "object",
                "required": ["id", "start", "duration", "text"],
                "properties": {
                    "id": id_, "start": tick, "duration": tick, "text": {"type": "string", "description": "Lines separated by newline. <i>/<b>/<u> and WebVTT voice spans are kept."},
                    "speaker": {"type": ["string", "null"]},
                    "cue_id": {"type": ["string", "null"]},
                    "settings": {"type": "string", "default": ""},
                },
                "additionalProperties": False,
            },
            "captionStyle": {
                "type": "object",
                "description": "Track style. All fields default: font Inter, size 54, color white, background on, background_color [0,0,0,191], align Center, anchor Bottom, margin 0.08, line_spacing 1.25, outline 0, outline_color black, font_style SemiBold.",
                "properties": {
                    "font": {"type": "string", "default": "Inter"},
                    "size": {"type": "number", "default": 54},
                    "color": {"type": "array", "items": {"type": "integer"}, "minItems": 4, "maxItems": 4, "default": [255, 255, 255, 255]},
                    "background": {"type": "boolean", "default": True},
                    "background_color": {"type": "array", "default": [0, 0, 0, 191]},
                    "align": {"enum": ["Left", "Center", "Right"], "default": "Center"},
                    "anchor": {"enum": ["Top", "Middle", "Bottom"], "default": "Bottom"},
                    "margin": {"type": "number", "default": 0.08},
                    "line_spacing": {"type": "number", "default": 1.25},
                    "outline": {"type": "number", "default": 0},
                    "outline_color": {"type": "array", "default": [0, 0, 0, 255]},
                    "font_style": {"type": "string", "default": "SemiBold"},
                },
                "additionalProperties": False,
            },
            "mixer": {
                "type": "object",
                "description": "Default: mode Read, lanes omitted, sends omitted, output null, record_arm false, solo_safe false, input_map Stereo.",
                "properties": {
                    "mode": {"enum": ["Off", "Read", "Latch", "Touch", "Write"], "default": "Read"},
                    "lanes": {"type": "object", "additionalProperties": {"$ref": "#/$defs/param"}, "description": "Keys: volume, pan, mute, send.<i>.level, pan51.x, pan51.y, pan51.center, pan51.lfe. Keyframe time is sequence time."},
                    "sends": {"type": "array", "items": {"type": "object", "required": ["target", "level_db"], "properties": {
                        "target": id_, "level_db": {"type": "number", "default": 0}, "pan": {"type": "number", "default": 0},
                        "pre_fader": {"type": "boolean", "default": False}, "muted": {"type": "boolean", "default": False},
                    }}},
                    "output": {"type": ["integer", "null"], "default": None},
                    "record_arm": {"type": "boolean", "default": False},
                    "solo_safe": {"type": "boolean", "default": False},
                    "input_map": {"enum": ["Stereo", "Left", "Right", "Swap", "Mono"], "default": "Stereo"},
                },
                "additionalProperties": False,
            },
            "timeRange": {"type": "object", "required": ["start", "duration"], "properties": {"start": tick, "duration": tick}, "additionalProperties": False},
            "splitMarks": {"type": "object", "properties": {
                "videoIn": {"type": ["integer", "null"]}, "videoOut": {"type": ["integer", "null"]},
                "audioIn": {"type": ["integer", "null"]}, "audioOut": {"type": ["integer", "null"]},
            }, "description": "camelCase. Omitted when every side is empty."},
            "graphicMeta": {"type": "object", "properties": {
                "roll": {"type": "object", "properties": {
                    "mode": {"enum": ["Off", "Roll", "CrawlLeft", "CrawlRight"], "default": "Off"},
                    "start_off_screen": {"type": "boolean"}, "end_off_screen": {"type": "boolean"},
                    "preroll": tick, "ease_in": tick, "ease_out": tick, "postroll": tick,
                }},
                "intro": tick, "outro": tick, "design_in": tick, "design_duration": tick,
                "template": {"type": ["object", "null"]},
            }, "description": "Schema v12. Optional on the clip."},
            "layerExtra": {"type": "object", "properties": {
                "uid": {"type": "integer"},
                "runs": {"type": "array", "items": {"type": "object", "description": "start/end character indexes plus camelCase CharStyle overrides (font, fontStyle, size, fill, fauxBold, fauxItalic, underline, strikethrough, tracking, baselineShift, caps)."}},
                "pin": {"type": "object", "properties": {
                    "to": {"description": "Frame, or {Layer: uid}"},
                    "left": {"type": "boolean"}, "top": {"type": "boolean"}, "right": {"type": "boolean"}, "bottom": {"type": "boolean"},
                    "offsets": {"type": "array", "items": {"type": "number"}, "minItems": 4, "maxItems": 4},
                }},
            }, "description": "Schema v12, on graphic layers. Omitted when empty."},
            "lut": {"type": "object", "required": ["id", "name", "format", "text"], "properties": {
                "id": {"type": "string"}, "name": {"type": "string"}, "source_path": {"type": ["string", "null"]},
                "format": {"type": "string", "description": "cube or 3dl"}, "text": {"type": "string"},
            }},
            "projectView": {
                "type": "object",
                "properties": {
                    "open_sequences": {"type": "array", "items": id_, "default": []},
                    "active_sequence": {"type": ["integer", "null"]},
                    "sequences": {"type": "object", "additionalProperties": {"type": "object", "required": ["pps", "scroll", "video_track_h", "audio_track_h"], "properties": {
                        "pps": {"type": "number"}, "scroll": {"type": "number"},
                        "v_scroll": {"type": "number", "default": 0}, "a_scroll": {"type": "number", "default": 0},
                        "video_track_h": {"type": "number"}, "audio_track_h": {"type": "number"},
                    }}},
                    "playheads": {"type": "object", "additionalProperties": tick, "description": "Omitted when empty."},
                },
            },
            "audioTypes": {"enum": ["Dialogue", "Music", "SFX", "Ambience"]},
            "clipKinds": {"description": "Item kinds that can sit on a timeline: Media (movie, audio, still, image sequence, synthetic), Sequence (nest), Subclip, AdjustmentLayer, Graphic (text and shapes live on the clip as effects)."},
        },
    }

def main():
    cat = effects()
    doc = schema(cat)
    text = json.dumps(doc, ensure_ascii=False, indent=1)
    for path in OUTS:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(text + "\n")
        print(path, "effects", len(cat))

if __name__ == "__main__":
    main()
