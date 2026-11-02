#!/usr/bin/env python3
"""Validate SVG sources, searchable text, and visible label stacking in the final page groups."""
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

chapter_setup = (ROOT / "chapter-nodesetup.tex").read_text(encoding="utf-8")
for diagram in ("arch-quickbridge", "arch-agconnector"):
    if not re.search(
        rf"\\includesvg\\[[^]]*inkscapelatex=false[^]]*\\]\\{{{diagram}\\}}",
        chapter_setup,
    ):
        errors.append(
            f"{diagram}: use direct SVG PDF export (inkscapelatex=false) to preserve multiline labels"
        )

if list(IMAGE_DIR.glob("*.odg")):
    errors.append("ODG source files must not remain in the maintained images directory")

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

    text_nodes = [
        node for node in root.iter()
        if node.tag == f"{svg_ns}text"
    ]

    if svg_path.stem == "mff-logo":
        if text_nodes:
            errors.append("mff-logo.svg: logo should remain vector artwork without text")
        continue

    # These two diagrams are exported directly from patched ODG sources.
    # Their visible text is the artwork; no hidden overlay is needed.
    if svg_path.stem in {"arch-quickbridge", "arch-agconnector"}:
        rendered = [
            (node, " ".join("".join(node.itertext()).split()))
            for node in text_nodes
        ]
        if svg_path.stem == "arch-quickbridge":
            quick = [node for node, label in rendered if label == "QuickBridge"]
            unicast = [node for node, label in rendered if label == "unicast"]
            if len(quick) != 1:
                errors.append(
                    f"arch-quickbridge.svg: expected one QuickBridge label; found {len(quick)}"
                )
            if len(unicast) != 2:
                errors.append(
                    f"arch-quickbridge.svg: expected white unicast text plus its shadow; found {len(unicast)}"
                )
            targets = quick + unicast
        else:
            registry_server = [
                node for node, label in rendered
                if "Registry" in label and "Server" in label
            ]
            if len(registry_server) != 1:
                errors.append(
                    "arch-agconnector.svg: expected one Registry/Server text object; "
                    f"found {len(registry_server)}"
                )
            targets = registry_server

        for node in targets:
            runs = [
                child for child in node.iter()
                if child.tag == f"{svg_ns}tspan"
                and (child.get("font-family") or "font-family:" in child.get("style", ""))
                and "".join(child.itertext()).strip()
            ]
            if not runs or any(
                "DejaVu Sans" not in (child.get("font-family", "") + " " + child.get("style", ""))
                for child in runs
            ):
                errors.append(
                    f"{svg_path.stem}.svg: repaired labels must use DejaVu Sans"
                )
        continue

    layers = [
        node for node in root.iter()
        if node.tag == f"{svg_ns}g"
        and node.get("id") == "searchable-text-layer"
    ]
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
