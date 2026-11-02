#!/usr/bin/env python3
"""Keep the original ODG-exported artwork and add an invisible searchable text layer.

LibreOffice's current SVG export can substitute fonts and alter the visual
appearance of the diagrams. The SVGs already committed before the searchable
text migration contain the original text as vector outlines. Those outlines
are kept untouched; text from a fresh ODG export is added as an invisible
overlay so that PDF text extraction and search still work.
"""
from __future__ import annotations

import argparse
import copy
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG_NS)


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def merge(original_path: Path, exported_path: Path, output_path: Path) -> None:
    original = original_path.read_text(encoding="utf-8")
    exported = exported_path.read_text(encoding="utf-8")
    original_root = ET.fromstring(original)
    exported_root = ET.fromstring(exported)

    def parse_viewbox(root: ET.Element, label: str) -> tuple[float, float, float, float]:
        raw = root.get("viewBox", "")
        values = raw.replace(",", " ").split()
        if len(values) != 4:
            raise ValueError(f"{label}: invalid or missing viewBox {raw!r}")
        x, y, width, height = (float(value) for value in values)
        if width <= 0 or height <= 0:
            raise ValueError(f"{label}: viewBox dimensions must be positive")
        return x, y, width, height

    ox, oy, ow, oh = parse_viewbox(original_root, str(original_path))
    gx, gy, gw, gh = parse_viewbox(exported_root, str(exported_path))
    # Some legacy SVGs use a cropped or differently scaled viewBox. Map the
    # invisible full-page text into the original canvas; visible artwork stays
    # byte-for-byte unchanged, and searchable text remains inside the PDF page.
    sx, sy = ow / gw, oh / gh
    tx, ty = ox - gx * sx, oy - gy * sy
    transform = f"matrix({sx:.12g} 0 0 {sy:.12g} {tx:.12g} {ty:.12g})"

    text_nodes = [
        node for node in exported_root.iter()
        if local_name(node.tag) == "text"
    ]
    if not text_nodes:
        if output_path.stem == "mff-logo":
            output_path.write_text(original, encoding="utf-8")
            print(f"{output_path.name}: logo is vector artwork; no text overlay")
            return
        raise ValueError(f"{exported_path}: no SVG text elements found")

    if 'id="searchable-text-layer"' in original:
        raise ValueError(f"{original_path}: searchable text layer already exists")

    layer = ET.Element(
        f"{{{SVG_NS}}}g",
        {
            "id": "searchable-text-layer",
            "data-purpose": "invisible-searchable-text",
            "opacity": "0",
            "pointer-events": "none",
            "style": "opacity:0 !important; fill-opacity:0 !important",
            "transform": transform,
        },
    )
    for node in text_nodes:
        cloned = copy.deepcopy(node)
        # Avoid collisions with IDs in the original, path-based artwork.
        for element in cloned.iter():
            element.attrib.pop("id", None)
            if local_name(element.tag) in {"text", "tspan"}:
                # Inkscape may ignore opacity on the containing group when
                # importing nested text; force transparency on each text node.
                element.set("opacity", "0")
                element.set("fill-opacity", "0")
                style = element.get("style", "").strip().rstrip(";")
                element.set(
                    "style",
                    (style + ";" if style else "")
                    + "opacity:0 !important;fill-opacity:0 !important",
                )
        layer.append(cloned)

    fragment = ET.tostring(layer, encoding="unicode")
    closing_tag = original.rfind("</svg>")
    if closing_tag < 0:
        raise ValueError(f"{original_path}: missing closing SVG tag")

    merged = original[:closing_tag] + "\n" + fragment + "\n" + original[closing_tag:]
    output_path.write_text(merged, encoding="utf-8")
    print(
        f"{output_path.name}: preserved original artwork; "
        f"added {len(text_nodes)} invisible searchable text elements"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original", type=Path, required=True)
    parser.add_argument("--exported", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        merge(args.original, args.exported, args.output)
    except (OSError, ET.ParseError, ValueError) as exc:
        print(f"SVG merge failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
