#!/usr/bin/env python3
"""Patch the original ODG text objects before the one-time SVG export."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import tempfile
import zipfile
import xml.etree.ElementTree as ET

NS = {
    "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
    "style": "urn:oasis:names:tc:opendocument:xmlns:style:1.0",
    "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
    "fo": "urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0",
    "svg": "http://www.w3.org/2000/svg",
}
for prefix, uri in NS.items():
    ET.register_namespace(prefix, uri)

PATCHES = {
    "arch-quickbridge": {
        "QuickBridge": ("ThesisQuickBridge", "8pt", 1),
        "unicast": ("ThesisUnicast", "8pt", 1),
    },
    "arch-agconnector": {
        "Registry": ("ThesisRegistryServer", "8pt", 1),
        "Server": ("ThesisRegistryServer", "8pt", 2),
    },
}


def patch(path: Path) -> None:
    specs = PATCHES.get(path.stem)
    if not specs:
        return
    with zipfile.ZipFile(path, "r") as source:
        entries = [(item, source.read(item.filename)) for item in source.infolist()]
    content = next((data for item, data in entries if item.filename == "content.xml"), None)
    if content is None:
        raise ValueError(f"{path}: content.xml missing")
    root = ET.fromstring(content)
    styles_data = next((data for item, data in entries if item.filename == "styles.xml"), None)
    if styles_data is None:
        raise ValueError(f"{path}: styles.xml missing")
    styles_root = ET.fromstring(styles_data)
    # Legacy ODG exports can nest style containers or omit the declarations.
    automatic = root.find(".//office:automatic-styles", NS)
    automatic_in_styles = False
    if automatic is None:
        automatic = styles_root.find(".//office:automatic-styles", NS)
        automatic_in_styles = automatic is not None
    if automatic is None:
        automatic = ET.SubElement(root, f"{{{NS['office']}}}automatic-styles")



    expected = {label: count for label, (_, _, count) in specs.items()}
    found = {label: 0 for label in specs}
    for paragraph in root.iter(f"{{{NS['text']}}}p"):
        label = "".join(paragraph.itertext()).strip()
        if label not in specs:
            continue
        style_name, font_size, _ = specs[label]
        paragraph.set(f"{{{NS['text']}}}style-name", style_name)
        found[label] += 1

    if found != expected:
        raise ValueError(f"{path}: expected label counts {expected}, found {found}")

    for label, (style_name, font_size, _) in specs.items():
        if any(node.get(f"{{{NS['style']}}}name") == style_name for node in automatic):
            continue
        style = ET.SubElement(automatic, f"{{{NS['style']}}}style", {
            f"{{{NS['style']}}}name": style_name,
            f"{{{NS['style']}}}family": "paragraph",
            f"{{{NS['style']}}}parent-style-name": "P2",
        })
        ET.SubElement(style, f"{{{NS['style']}}}paragraph-properties", {
            f"{{{NS['fo']}}}text-align": "center",
            f"{{{NS['fo']}}}margin-left": "0cm",
            f"{{{NS['fo']}}}margin-right": "0cm",
        })
        ET.SubElement(style, f"{{{NS['style']}}}text-properties", {
            f"{{{NS['fo']}}}font-family": "DejaVu Sans",
            f"{{{NS['fo']}}}font-size": font_size,
        })

    updated = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    updated_styles = ET.tostring(styles_root, encoding="utf-8", xml_declaration=True)
    fd, temporary = tempfile.mkstemp(suffix=".odg", dir=path.parent)
    os.close(fd)
    try:
        with zipfile.ZipFile(temporary, "w", zipfile.ZIP_DEFLATED) as target:
            for item, data in entries:
                if item.filename == "content.xml":
                    data = updated
                elif item.filename == "styles.xml":
                    data = updated_styles
                target.writestr(item, data)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    print(f"{path.name}: patched ODG text objects {found} to DejaVu Sans")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("odg", type=Path)
    args = parser.parse_args()
    patch(args.odg)


if __name__ == "__main__":
    main()
