#!/usr/bin/env python3
"""Validate that maintained vector figures use SVG source files in LaTeX."""
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
IMAGE_DIR = ROOT / "images"
TEX_FILES = sorted(ROOT.glob("*.tex"))

def uncomment(source: str) -> str:
    lines = []
    for line in source.splitlines():
        line = re.split(r"(?<!\\)%", line, maxsplit=1)[0]
        lines.append(line)
    return "\n".join(lines)

def asset_path(raw_name: str) -> Path:
    candidate = Path(raw_name)
    if candidate.is_absolute():
        return candidate
    if candidate.parts and candidate.parts[0] == "images":
        return ROOT / candidate
    return IMAGE_DIR / candidate

svg_refs = []
graphics_refs = []
for tex_file in TEX_FILES:
    source = uncomment(tex_file.read_text(encoding="utf-8"))
    svg_refs.extend((tex_file.name, name.strip()) for name in re.findall(
        r"\\includesvg(?:\s*\[[^]]*\])?\s*\{([^}]+)\}", source
    ))
    graphics_refs.extend((tex_file.name, name.strip()) for name in re.findall(
        r"\\includegraphics(?:\s*\[[^]]*\])?\s*\{([^}]+)\}", source
    ))

errors = []
build_script = (ROOT / "build.sh").read_text(encoding="utf-8")
workflow = (ROOT / ".github" / "workflows" / "build.yml").read_text(encoding="utf-8")
if "-shell-escape" not in build_script:
    errors.append("build.sh must pass -shell-escape so LaTeX can invoke Inkscape")
if not re.search(r"apt-get install[^\n]*\binkscape\b", workflow):
    errors.append("GitHub Actions must install Inkscape before building the PDF")

used_svg = set()
for tex_file, raw_name in svg_refs:
    name = raw_name.removesuffix(".svg")
    path = IMAGE_DIR / f"{name}.svg"
    if not path.is_file():
        errors.append(f"{tex_file}: missing SVG source for \\includesvg{{{raw_name}}}")
    else:
        used_svg.add(path.resolve())

all_svg = {p.resolve() for p in IMAGE_DIR.glob("*.svg")}

# Searchable labels must not replace the original ODG-exported glyph artwork.
# The visible paths stay byte-for-byte sourced from the pre-migration SVG;
# extracted text is kept in a transparent overlay.
svg_ns = "{http://www.w3.org/2000/svg}"
for svg_path in sorted(all_svg):
    try:
        root = ET.parse(svg_path).getroot()
    except ET.ParseError as exc:
        errors.append(f"{svg_path.relative_to(ROOT)}: invalid SVG XML: {exc}")
        continue

    layers = [
        node for node in root.iter()
        if node.tag == f"{svg_ns}g"
        and node.get("id") == "searchable-text-layer"
    ]
    text_nodes = [
        node for node in root.iter()
        if node.tag == f"{svg_ns}text"
    ]

    if svg_path.stem == "mff-logo":
        if layers or text_nodes:
            errors.append("mff-logo.svg: logo should remain vector artwork without text")
        continue

    if len(layers) != 1:
        errors.append(
            f"{svg_path.relative_to(ROOT)}: expected one searchable-text-layer; found {len(layers)}"
        )
        continue

    layer = layers[0]
    if layer.get("opacity") != "0":
        errors.append(f"{svg_path.relative_to(ROOT)}: searchable text layer must be invisible")
    layer_text = [
        node for node in layer.iter()
        if node.tag == f"{svg_ns}text"
    ]
    if not layer_text:
        errors.append(f"{svg_path.relative_to(ROOT)}: searchable text layer is empty")
    for text_node in layer.iter():
        if text_node.tag in {f"{svg_ns}text", f"{svg_ns}tspan"}:
            if text_node.get("opacity") != "0" or text_node.get("fill-opacity") != "0":
                errors.append(
                    f"{svg_path.relative_to(ROOT)}: searchable text glyphs must be fully transparent"
                )
                break
    visible_text = [node for node in text_nodes if node not in layer_text]
    if svg_path.stem == "arch-quickbridge":
        visible_labels = ["".join(node.itertext()).strip() for node in visible_text]
        if sorted(visible_labels) != ["QuickBridge", "unicast"]:
            errors.append(
                "arch-quickbridge.svg: expected only the repaired visible labels "
                f"QuickBridge and unicast; found {visible_labels}"
            )
        else:
            by_label = {label: node for label, node in zip(visible_labels, visible_text)}
            quickbridge = by_label["QuickBridge"]
            unicast = by_label["unicast"]
            if quickbridge.get("x") != "6485" or quickbridge.get("y") != "3485" or quickbridge.get("font-size") != "205":
                errors.append("arch-quickbridge.svg: QuickBridge label is not centered in its box")
            if unicast.get("transform") != "rotate(-90 4089 3495)" or unicast.get("font-size") != "205":
                errors.append("arch-quickbridge.svg: unicast label must remain vertically centered")
            for node in (quickbridge, unicast):
                if node.get("font-family") != "DejaVu Sans, sans-serif":
                    errors.append("arch-quickbridge.svg: QuickBridge and unicast must use DejaVu Sans")
    elif svg_path.stem == "arch-agconnector":
        visible_labels = ["".join(node.itertext()).strip() for node in visible_text]
        if visible_labels != ["Registry", "Server"]:
            errors.append(
                "arch-agconnector.svg: Registry Server must be two separate visible lines; "
                f"found {visible_labels}"
            )
        else:
            for node in visible_text:
                if node.get("font-family") != "DejaVu Sans, sans-serif":
                    errors.append("arch-agconnector.svg: Registry Server must use DejaVu Sans")
    elif visible_text:
        errors.append(
            f"{svg_path.relative_to(ROOT)}: visible text elements found outside the hidden layer"
        )
    if svg_path.stem == "unicast-multicast":
        numbered = {
            node.get("id"): node
            for node in root.iter()
            if node.tag == f"{svg_ns}path" and node.get("id") in {"text101", "text110"}
        }
        expected_offsets = {"text101": "translate(-112,0)", "text110": "translate(-120,0)"}
        if set(numbered) != set(expected_offsets) or any(
            node.get("transform") != expected_offsets[label_id]
            for label_id, node in numbered.items()
        ):
            errors.append("unicast-multicast.svg: red-circle numbers must be centered horizontally and vertically")
    if not any("".join(node.itertext()).strip() for node in layer_text):
        errors.append(f"{svg_path.relative_to(ROOT)}: searchable text contains no labels")
for path in sorted(all_svg - used_svg):
    errors.append(f"Unreferenced maintained SVG source: {path.relative_to(ROOT)}")
for path in sorted(used_svg - all_svg):
    errors.append(f"Unknown SVG source: {path}")

svg_stems = {p.stem for p in all_svg}
for tex_file, raw_name in graphics_refs:
    candidate = Path(raw_name)
    stem = candidate.stem if candidate.suffix else candidate.name
    if stem in svg_stems and (not candidate.suffix or candidate.suffix.lower() == ".pdf"):
        errors.append(
            f"{tex_file}: vector figure {raw_name!r} must use \\includesvg, not \\includegraphics"
        )

for tex_file, raw_name in graphics_refs:
    candidate = asset_path(raw_name)
    if candidate.suffix:
        exists = candidate.is_file()
    else:
        exists = any(p.is_file() for p in candidate.parent.glob(candidate.name + ".*"))
    if not exists:
        errors.append(f"{tex_file}: missing \\includegraphics asset {raw_name!r}")

if len(svg_refs) != 23:
    errors.append(f"Expected 23 active SVG references; found {len(svg_refs)}")

if errors:
    print("SVG pipeline validation failed:")
    for error in errors:
        print(f" - {error}")
    sys.exit(1)

print(f"SVG pipeline OK: {len(svg_refs)} SVG sources referenced; "
      f"{len(graphics_refs)} graphics references checked.")
