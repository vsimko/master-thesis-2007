#!/usr/bin/env python3
"""Validate that maintained vector figures use SVG source files in LaTeX."""
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
IMAGE_DIR = ROOT / "images"
TEX_FILES = sorted(ROOT.glob("*.tex"))

def uncomment(source: str) -> str:
    lines = []
    for line in source.splitlines():
        line = re.split(r"(?<!\\)%", line, maxsplit=1)[0]
        lines.append(line)
    return "\n".join(lines)

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
used_svg = set()
for tex_file, raw_name in svg_refs:
    name = raw_name.removesuffix(".svg")
    path = IMAGE_DIR / f"{name}.svg"
    if not path.is_file():
        errors.append(f"{tex_file}: missing SVG source for \\includesvg{{{raw_name}}}")
    else:
        used_svg.add(path.resolve())

all_svg = {p.resolve() for p in IMAGE_DIR.glob("*.svg")}
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
    candidate = IMAGE_DIR / raw_name
    if candidate.suffix:
        exists = candidate.is_file()
    else:
        exists = any(p.is_file() for p in IMAGE_DIR.glob(candidate.name + ".*"))
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
