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

    for attribute in ("width", "height", "viewBox"):
        if original_root.get(attribute) != exported_root.get(attribute):
            raise ValueError(
                f"{attribute} differs: original={original_root.get(attribute)!r}, "
                f"exported={exported_root.get(attribute)!r}"
            )

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
        },
    )
    for node in text_nodes:
        cloned = copy.deepcopy(node)
        # Avoid collisions with IDs in the original, path-based artwork.
        for element in cloned.iter():
            element.attrib.pop("id", None)
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
