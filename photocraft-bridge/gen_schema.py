#!/usr/bin/env python3
"""Build the .pcraft manifest schema from the PhotoCraft source."""
import json
import os
import re

SRC = os.environ.get("PHOTOCRAFT_SRC", r"C:\Users\wuyou\Downloads\photocraft-main\photocraft-main")
HERE = os.path.dirname(os.path.realpath(__file__))
OUTS = [
    os.path.join(HERE, "schema", "pcraft.schema.json"),
    os.path.join(SRC, "docs", "pcraft.schema.json"),
]


def enum_variants(path, name):
    text = open(path, encoding="utf-8").read()
    match = re.search(r"enum %s \{(?P<body>.*?)\n\}" % name, text, re.S)
    if not match:
        raise SystemExit("missing enum %s in %s" % (name, path))
    body = match.group("body")
    return re.findall(r"^\s*(?:#\[default\]\s*)?([A-Z][A-Za-z0-9]*)\b", body, re.M)


def content_kinds(path):
    lines = open(path, encoding="utf-8").read().splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith("pub enum ContentM"))
    names = []
    depth = 0
    for line in lines[start:]:
        if depth == 1:
            match = re.match(r"    ([A-Z][A-Za-z0-9]*) \{", line)
            if match:
                names.append(match.group(1))
        depth += line.count("{") - line.count("}")
        if depth == 0 and names:
            break
    if not names:
        raise SystemExit("missing ContentM variants")

    def snake(name):
        return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name).lower()

    return [snake(name) for name in names]


def main():
    color = os.path.join(SRC, "crates", "color", "src", "lib.rs")
    blend = os.path.join(SRC, "crates", "color", "src", "blend.rs")
    doc = os.path.join(SRC, "crates", "doc", "src", "lib.rs")
    manifest = os.path.join(SRC, "crates", "format", "src", "manifest.rs")
    modes = enum_variants(color, "ColorMode")
    samples = enum_variants(color, "SampleType")
    blends = enum_variants(blend, "BlendMode")
    labels = enum_variants(doc, "LabelColor")
    kinds = content_kinds(manifest)
    layer = {
        "type": "object",
        "additionalProperties": True,
        "required": ["id", "name", "visible", "locks", "blend", "opacity", "fill_opacity", "clipped", "mask", "effects", "label", "content", "psd_blocks", "psd_id", "fill_cache"],
        "properties": {
            "id": {"type": "integer", "minimum": 0},
            "name": {"type": "string"},
            "visible": {"type": "boolean"},
            "locks": {"type": "object", "additionalProperties": True},
            "blend": {"enum": blends},
            "opacity": {"type": "number"},
            "fill_opacity": {"type": "number"},
            "clipped": {"type": "boolean"},
            "mask": {"type": ["object", "null"], "additionalProperties": True},
            "effects": {"type": "object", "additionalProperties": True},
            "label": {"enum": labels},
            "content": {"$ref": "#/$defs/content"},
            "psd_blocks": {"type": "array"},
            "psd_id": {"type": ["integer", "null"]},
            "fill_cache": {"type": ["object", "null"], "additionalProperties": True},
        },
    }
    content = {
        "type": "object",
        "additionalProperties": True,
        "required": ["kind"],
        "properties": {
            "kind": {"enum": kinds},
            "surface": {"$ref": "#/$defs/surface"},
            "children": {"type": "array", "items": {"$ref": "#/$defs/layer"}},
            "text": {"type": "string"},
            "font_family": {"type": "string"},
            "size_pt": {"type": "number"},
        },
    }
    surface = {
        "type": "object",
        "additionalProperties": True,
        "required": ["format", "default", "tiles"],
        "properties": {
            "format": {
                "type": "object",
                "additionalProperties": True,
                "required": ["mode", "sample", "alpha"],
                "properties": {
                    "mode": {"enum": modes},
                    "sample": {"enum": samples},
                    "alpha": {"type": "boolean"},
                },
            },
            "default": {"type": "string"},
            "tiles": {"type": "array"},
        },
    }
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://photocraft.dev/schema/pcraft-manifest.json",
        "title": "PhotoCraft manifest.json",
        "description": "The JSON manifest inside a .pcraft directory or zip. Pixels live in tiles/<blake3>.zst, not in this file. format_version 1.",
        "type": "object",
        "additionalProperties": True,
        "required": ["format_version", "generator", "document"],
        "properties": {
            "format_version": {"const": 1},
            "generator": {"type": "string"},
            "thumbnail": {"type": ["string", "null"]},
            "composite": {"type": ["string", "null"]},
            "document": {"$ref": "#/$defs/document"},
        },
        "$defs": {
            "layer": layer,
            "content": content,
            "surface": surface,
            "document": {
                "type": "object",
                "additionalProperties": True,
                "required": ["id", "name", "size", "resolution_dpi", "mode", "depth", "icc_profile", "layers", "channels", "guides", "metadata", "global_light"],
                "properties": {
                    "id": {"type": "integer", "minimum": 0},
                    "name": {"type": "string"},
                    "size": {
                        "type": "object",
                        "additionalProperties": True,
                        "required": ["width", "height"],
                        "properties": {"width": {"type": "integer", "minimum": 1}, "height": {"type": "integer", "minimum": 1}},
                    },
                    "resolution_dpi": {"type": "number", "exclusiveMinimum": 0},
                    "mode": {"enum": modes},
                    "depth": {"enum": samples},
                    "icc_profile": {"type": ["string", "null"]},
                    "layers": {"type": "array", "items": {"$ref": "#/$defs/layer"}},
                    "channels": {"type": "array"},
                    "guides": {"type": "object", "additionalProperties": True},
                    "metadata": {"type": "object", "additionalProperties": True},
                    "global_light": {"type": "object", "additionalProperties": True},
                },
            },
        },
    }
    text = json.dumps(schema, ensure_ascii=False, indent=2) + "\n"
    for path in OUTS:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        print(path)
    print("kinds", len(kinds), "blends", len(blends), "modes", len(modes))


if __name__ == "__main__":
    main()
