"""Build the .vectorcraft JSON Schema from the VectorCraft source."""
import json
import os
import re

SRC = os.environ.get(
    "VECTORCRAFT_SRC",
    r"C:\Users\wuyou\Downloads\vectorcraft-main\vectorcraft-main",
)
HERE = os.path.dirname(os.path.realpath(__file__))
OUTS = [
    os.path.join(HERE, "schema", "vectorcraft.schema.json"),
    os.path.join(SRC, "docs", "vectorcraft.schema.json"),
]


def node_kinds():
    path = os.path.join(SRC, "crates", "doc", "src", "node", "kind.rs")
    text = open(path, encoding="utf-8").read()
    body = text.split("pub enum NodeKind")[1].split("pub use kind_de")[0]
    names = re.findall(r"^\s{4}([A-Z][A-Za-z0-9]*)\s*(?:\{|\()", body, re.M)
    # serde rename_all = "lowercase" keeps the variant name and lowercases it.
    return [n.lower() for n in names]


def effect_ids():
    root = os.path.join(SRC, "crates", "effects", "src")
    found = []
    if not os.path.isdir(root):
        return found
    for dirpath, _, files in os.walk(root):
        for name in files:
            if not name.endswith(".rs"):
                continue
            text = open(os.path.join(dirpath, name), encoding="utf-8", errors="replace").read()
            found.extend(re.findall(r'"([a-z][a-z0-9]*\.[A-Za-z][A-Za-z0-9]*)"', text))
    return sorted(set(found))


def schema():
    kinds = node_kinds()
    effects = effect_ids()
    node = {
        "type": "object",
        "additionalProperties": True,
        "required": ["id", "kind"],
        "properties": {
            "id": {"type": "integer", "minimum": 0},
            "name": {"type": ["string", "null"]},
            "visible": {"type": "boolean", "default": True},
            "locked": {"type": "boolean", "default": False},
            "opacity": {"type": "number", "minimum": 0, "maximum": 1, "default": 1},
            "blend": {},
            "isolate": {"type": "boolean", "default": False},
            "knockout": {},
            "knockout_shape": {"type": "boolean", "default": False},
            "appearance": {"type": "object", "additionalProperties": True},
            "kind": {
                "type": "object",
                "additionalProperties": True,
                "required": ["type"],
                "properties": {"type": {"type": "string", "enum": kinds}},
            },
            "bbox_angle": {"type": "number", "default": 0},
        },
    }
    # Children are nodes. The schema stays acyclic: kind.children is an array of objects.
    node["properties"]["kind"]["properties"]["children"] = {
        "type": "array",
        "items": {"$ref": "#/$defs/node"},
    }
    node["properties"]["kind"]["properties"]["content"] = {
        "type": "array",
        "items": {"$ref": "#/$defs/node"},
    }
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://vectorcraft.local/vectorcraft.schema.json",
        "title": "VectorCraft document (format version 4 JSON)",
        "description": (
            "The JSON object inside a .vectorcraft file. A save may gzip this JSON "
            "(magic 1f 8b, from version 3) or follow it with the VCBLOBS trailer "
            "(newline, NUL, VCBLOBS, NUL) that holds large images, profiles and the PDF. "
            "version 1 and 2 still open. format drawcraft is the name from before the rename. "
            "Node kind tags are serde rename_all lowercase of NodeKind. "
            "effectCatalog lists effect ids found in crates/effects; it does not reject other ids."
        ),
        "type": "object",
        "additionalProperties": True,
        "required": ["format", "version", "document"],
        "properties": {
            "format": {"enum": ["vectorcraft", "drawcraft"]},
            "version": {"type": "integer", "minimum": 1, "maximum": 4},
            "generator": {"type": "string"},
            "preview": {"$ref": "#/$defs/blob"},
            "profiles": {"type": "object", "additionalProperties": {"$ref": "#/$defs/blob"}},
            "pdf": {"$ref": "#/$defs/blob"},
            "images": {"type": "object", "additionalProperties": {"$ref": "#/$defs/blob"}},
            "document": {"$ref": "#/$defs/document"},
        },
        "$defs": {
            "blob": {
                "type": "object",
                "additionalProperties": True,
                "required": ["mime"],
                "properties": {
                    "mime": {"type": "string"},
                    "data": {"type": "string", "description": "base64; omitted when blob is set"},
                    "blob": {
                        "type": "array",
                        "minItems": 2,
                        "maxItems": 2,
                        "items": {"type": "integer", "minimum": 0},
                        "description": "[offset, length] into the VCBLOBS trailer (version 4, at least 8 KiB)",
                    },
                    "proxy": {"type": "boolean"},
                },
            },
            "rect": {
                "type": "object",
                "additionalProperties": True,
                "required": ["x0", "y0", "x1", "y1"],
                "properties": {
                    "x0": {"type": "number"},
                    "y0": {"type": "number"},
                    "x1": {"type": "number"},
                    "y1": {"type": "number"},
                },
            },
            "artboard": {
                "type": "object",
                "additionalProperties": True,
                "required": ["id", "name", "rect"],
                "properties": {
                    "id": {"type": "integer"},
                    "name": {"type": "string"},
                    "rect": {"$ref": "#/$defs/rect"},
                    "locked": {"type": "boolean", "default": False},
                    "show_center_mark": {"type": "boolean", "default": False},
                    "show_cross_hairs": {"type": "boolean", "default": False},
                    "show_video_safe_areas": {"type": "boolean", "default": False},
                    "video_ruler_pixel_aspect_ratio": {"type": "number", "default": 1},
                },
            },
            "node": node,
            "document": {
                "type": "object",
                "additionalProperties": True,
                "required": ["version", "artboards", "layers"],
                "properties": {
                    "version": {"type": "integer"},
                    "title": {"type": "string", "default": ""},
                    "template": {"type": "boolean", "default": False},
                    "units": {
                        "type": "string",
                        "default": "Points",
                        "description": "Points, Picas, Inches, Millimeters, Centimeters, Pixels, Feet & Inches, Meters, Yards, Feet",
                    },
                    "ruler_origin": {"type": "object", "additionalProperties": True},
                    "rulers": {"type": "string", "description": "global or artboard; files from before the choice open as global"},
                    "artboard_ruler_origins": {"type": "object", "additionalProperties": True},
                    "color_mode": {"type": "string", "enum": ["Rgb", "Cmyk"], "default": "Rgb"},
                    "artboards": {"type": "array", "items": {"$ref": "#/$defs/artboard"}},
                    "layers": {"type": "array", "items": {"$ref": "#/$defs/node"}},
                    "swatches": {"type": "array"},
                    "swatch_groups": {"type": "array"},
                    "graphic_styles": {"type": "array"},
                    "char_styles": {"type": "array"},
                    "para_styles": {"type": "array"},
                    "text_threads": {"type": "array"},
                    "symbols": {"type": "array"},
                    "graph_designs": {"type": "array"},
                    "guides": {"type": "array"},
                    "views": {"type": "array"},
                    "saved_selections": {"type": "array"},
                    "variables": {"type": "object", "additionalProperties": True},
                    "grid": {"type": "object", "additionalProperties": True},
                    "raster_effects_ppi": {"type": "number", "default": 72},
                    "images": {"type": "object", "additionalProperties": True},
                    "patterns": {"type": "array"},
                    "next_id": {"type": "integer"},
                    "page_isolate": {"type": "boolean", "default": False},
                    "page_knockout": {"type": "boolean", "default": False},
                    "spot_use_lab": {"type": "boolean", "default": True},
                    "setup": {"type": "object", "additionalProperties": True},
                    "paste_remembers_layers": {"type": "boolean", "default": False},
                    "metadata": {"type": "object", "additionalProperties": True},
                    "raster_effects": {"type": "object", "additionalProperties": True},
                    "last_view": {"type": ["object", "null"], "additionalProperties": True},
                    "transparency_grid": {"type": "boolean", "default": False},
                    "layers_open": {"type": ["array", "null"]},
                    "color_profiles": {"type": "object", "additionalProperties": True},
                    "export_settings": {"type": "object", "additionalProperties": True},
                    "slices": {"type": "array"},
                    "slices_clip_to_artboard": {"type": "boolean", "default": True},
                    "print_setup": {},
                    "assets": {"type": "array"},
                    "svg_scripts": {"type": "array", "items": {"type": "string"}},
                },
            },
            "nodeKind": {"enum": kinds},
            "effectCatalog": {"type": "array", "items": {"const": None}},
        },
    }


def main():
    doc = schema()
    effects = effect_ids()
    doc["$defs"]["effectCatalog"] = {
        "description": "Effect ids named in crates/effects. Informational: a document may use others, including plugin.<id>.",
        "type": "array",
        "const": effects,
    }
    text = json.dumps(doc, ensure_ascii=False, indent=2)
    for path in OUTS:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
        print(path, "kinds", len(doc["$defs"]["nodeKind"]["enum"]), "effects", len(effects))


if __name__ == "__main__":
    main()
