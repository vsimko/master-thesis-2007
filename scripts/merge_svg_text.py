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
import re
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
    # Keep the numbered red-node correction across automated SVG rebuilds.
    # Apply it to the original XML string so the remaining artwork stays untouched.
    label_offsets = {"localhost-recording": 6, "skype-architecture": 18}
    if output_path.stem in label_offsets:
        labels = [
            node for node in original_root.iter()
            if local_name(node.tag) == "path"
            and node.get("aria-label", "").isdigit()
            and "fill:#ffffff" in node.get("style", "")
        ]
        if len(labels) != label_offsets[output_path.stem]:
            raise ValueError(f"{output_path.name}: unexpected white numbered-label count: {len(labels)}")
        for label in labels:
            label_id = label.get("id")
            marker = f'id="{label_id}"'
            id_pos = original.find(marker)
            path_start = original.rfind("<path", 0, id_pos)
            path_end = original.find(">", id_pos)
            if not label_id or id_pos < 0 or path_start < 0 or path_end < 0:
                raise ValueError(f"{output_path.name}: cannot locate numbered label {label_id}")
            element = original[path_start:path_end + 1]
            updated = element.replace('transform="translate(-30,-30)"', 'transform="translate(-100,-30)"', 1)
            if updated == element:
                raise ValueError(f"{output_path.name}: missing original transform for {label_id}")
            original = original[:path_start] + updated + original[path_end + 1:]


    # Keep the Figure 3.1 red-circle numbers optically centered after SVG rebuild.
    if output_path.stem == "unicast-multicast":
        # The glyphs need separate horizontal offsets; their vertical alignment
        # already matches the circle centers, so do not add the former +60 y shift.
        number_offsets = {"text101": -112, "text110": -120}
        for label_id, x_offset in number_offsets.items():
            marker = f'id="{label_id}"'
            id_pos = original.find(marker)
            path_start = original.rfind("<path", 0, id_pos)
            path_end = original.find(">", id_pos)
            if id_pos < 0 or path_start < 0 or path_end < 0:
                raise ValueError(f"{output_path.name}: cannot locate red-circle number {label_id}")
            element = original[path_start:path_end + 1]
            element = re.sub(r'\s+transform="[^"]*"', "", element)
            element = element.replace("<path", '<path transform="translate(' + str(x_offset) + ',0)"', 1)
            original = original[:path_start] + element + original[path_end + 1:]

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

    # Figure 3.1: center the visible number glyphs in both axes.
    if output_path.stem == "unicast-multicast":
        number_offsets = {"text101": -112, "text110": -120}
        for label_id, x_offset in number_offsets.items():
            pattern = rf'<path(?P<attrs>[^>]*\bid="{label_id}"[^>]*)>'
            def center_number(match: re.Match[str]) -> str:
                attrs = re.sub(r'\s+transform="[^"]*"', "", match.group("attrs"))
                return '<path transform="translate(' + str(x_offset) + ',0)"' + attrs + '>'
            merged, count = re.subn(pattern, center_number, merged, count=1, flags=re.DOTALL)
            if count != 1:
                raise ValueError(f"{output_path.name}: cannot center visible number {label_id}")


    # Repair the two visible labels in figure 7.6 with an installed sans-serif font. The original text outlines
    # wrap the final "e" in QuickBridge and render the rotated unicast label
    # incorrectly. Keep the ODG-derived invisible text overlay unchanged.
    if output_path.stem == "arch-quickbridge":
        fixes = {
            "text60": '<g id="text60" class="SVGTextShape" aria-label="QuickBridge"><rect x="5550" y="2850" width="1870" height="870" fill="#e6e6e6"/><text x="6485" y="3485" text-anchor="middle" dominant-baseline="middle" font-family="DejaVu Sans, sans-serif" font-size="205" fill="#000000" style="font-family:DejaVu Sans, sans-serif;white-space:pre">QuickBridge</text></g>',
            "text80": '<g id="text80" class="SVGTextShape" opacity="0" aria-label="unicast-background"/>',
            "text85": '<g id="text85" class="SVGTextShape" aria-label="unicast"><ellipse cx="4029" cy="3435" rx="205" ry="870" fill="#800000"/><text x="4089" y="3495" text-anchor="middle" dominant-baseline="middle" transform="rotate(-90 4089 3495)" font-family="DejaVu Sans, sans-serif" font-size="205" font-weight="700" fill="#ffffff" style="font-family:DejaVu Sans, sans-serif;white-space:pre">unicast</text></g>',
        }
        for group_id, replacement in fixes.items():
            pattern = rf'<g\s+id="{group_id}"[\s\S]*?</g>'
            merged, count = re.subn(pattern, lambda _match: replacement, merged, count=1)
            if count != 1:
                raise ValueError(f"{output_path.name}: cannot repair visible label group {group_id}")


    # Figure 7.7: render the Registry Server label as two complete sans-serif lines.
    if output_path.stem == "arch-agconnector":
        replacement = (
            '<g id="text78" class="SVGTextShape" aria-label="RegistryServer">'
            '<rect x="13470" y="1400" width="1370" height="870" fill="#e6e6e6"/>'
            '<text x="14155" y="1635" text-anchor="middle" dominant-baseline="middle" '
            'font-family="DejaVu Sans, sans-serif" font-size="230" fill="#000000" style="font-family:DejaVu Sans, sans-serif;white-space:pre">Registry</text>'
            '<text x="14155" y="2045" text-anchor="middle" dominant-baseline="middle" '
            'font-family="DejaVu Sans, sans-serif" font-size="230" fill="#000000" '
            'style="font-family:DejaVu Sans, sans-serif;white-space:pre">Server</text></g>'
        )
        pattern = r'<g\s+id="text78"[\s\S]*?</g>'
        merged, count = re.subn(pattern, lambda _match: replacement, merged, count=1)
        if count != 1:
            raise ValueError(f"{output_path.name}: cannot repair Registry Server label")

    # Keep repaired labels inside LibreOffice's actual Page group. Objects
    # appended at the SVG root are ignored by its slide exporter; labels must
    # be the last children of the Page group to paint over legacy path outlines.
    visible_label_ids = {
        "arch-quickbridge": ("text60", "text85"),
        "arch-agconnector": ("text78",),
    }.get(output_path.stem, ())
    visible_labels: list[str] = []
    for label_id in visible_label_ids:
        pattern = rf'<g\s+id="{label_id}"[^>]*>[\s\S]*?</g>'
        merged, count = re.subn(
            pattern,
            lambda match: (visible_labels.append(match.group(0)) or ""),
            merged,
            count=1,
        )
        if count != 1:
            raise ValueError(f"{output_path.name}: cannot extract visible label {label_id}")

    if visible_labels:
        # Find the Page group and its matching closing tag while respecting
        # nested groups and self-closing LibreOffice metadata groups.
        page_open = re.search(r'<g\b(?=[^>]*\bclass="Page")[^>]*>', merged)
        if page_open is None:
            raise ValueError(f"{output_path.name}: cannot find LibreOffice Page group")
        depth = 1
        page_close = None
        for token in re.finditer(r'<g\b[^>]*>|</g\s*>', merged[page_open.end():]):
            tag = token.group(0)
            if tag.startswith("</g"):
                depth -= 1
                if depth == 0:
                    page_close = page_open.end() + token.start()
                    break
            elif not tag.endswith("/>"):
                depth += 1
        if page_close is None:
            raise ValueError(f"{output_path.name}: cannot find end of Page group")
        merged = (
            merged[:page_close]
            + "\n<!-- Visible replacement labels: last objects inside the LibreOffice Page group. -->\n"
            + "\n".join(visible_labels)
            + "\n"
            + merged[page_close:]
        )

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
