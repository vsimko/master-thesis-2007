#!/usr/bin/env python3
"""Static audit for thesis citations, cross-references, and figure/table assets."""
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
IMAGE_DIR = ROOT / "images"
TEX_FILES = sorted(ROOT.glob("*.tex"))
KNOWN_UNCITED_BIBLIOGRAPHY = {
    "RFC-2429-RTP-Payload-Format-H.263+",
    "RFC-2730-MADCAP-Protocol",
}


def uncomment(source: str) -> str:
    return "\n".join(
        re.split(r"(?<!\\)%", line, maxsplit=1)[0]
        for line in source.splitlines()
    )


sources = {path: uncomment(path.read_text(encoding="utf-8")) for path in TEX_FILES}
combined = "\n".join(sources.values())
errors = []

labels = re.findall(r"\\label\s*\{([^}]+)\}", combined)
references = []
for match in re.finditer(
    r"\\(?:ref|pageref|autoref|eqref|cref|Cref|vref|Vref)\*?\s*\{([^}]+)\}",
    combined,
):
    references.extend(key.strip() for key in match.group(1).split(","))

citation_keys = []
citation_pattern = re.compile(
    r"\\(?:cite[a-zA-Z]*|nocite)\*?(?:\s*\[[^\]]*\]){0,2}\s*\{([^}]+)\}"
)
for match in citation_pattern.finditer(combined):
    citation_keys.extend(key.strip() for key in match.group(1).split(","))

bib_source = uncomment((ROOT / "bibfile.bib").read_text(encoding="utf-8"))
bib_keys = re.findall(r"@\w+\s*\{\s*([^,\s]+)\s*,", bib_source)


def duplicates(items):
    counts = {}
    for item in items:
        counts[item] = counts.get(item, 0) + 1
    return sorted(key for key, count in counts.items() if count > 1)


for label in duplicates(labels):
    errors.append(f"Duplicate LaTeX label: {label}")
for key in duplicates(bib_keys):
    errors.append(f"Duplicate BibTeX key: {key}")

for key in sorted(set(references) - set(labels)):
    errors.append(f"Undefined cross-reference: {key}")
for key in sorted(set(citation_keys) - set(bib_keys)):
    errors.append(f"Undefined citation key: {key}")

unused_bib = set(bib_keys) - set(citation_keys)
for key in sorted(unused_bib - KNOWN_UNCITED_BIBLIOGRAPHY):
    errors.append(f"Unexpected uncited bibliography entry: {key}")
for key in sorted(KNOWN_UNCITED_BIBLIOGRAPHY - unused_bib):
    errors.append(f"Review bibliography allowlist; entry is no longer uncited: {key}")

for tex_file, source in sources.items():
    for name in re.findall(r"\\(?:include|input)\s*\{([^}]+)\}", source):
        included = ROOT / (name if name.endswith(".tex") else f"{name}.tex")
        if not included.is_file():
            errors.append(f"{tex_file.name}: missing included TeX file {name!r}")

graphics_refs = []
svg_refs = []
for tex_file, source in sources.items():
    graphics_refs.extend((tex_file.name, name.strip()) for name in re.findall(
        r"\\includegraphics(?:\s*\[[^]]*\])?\s*\{([^}]+)\}", source
    ))
    svg_refs.extend((tex_file.name, name.strip()) for name in re.findall(
        r"\\includesvg(?:\s*\[[^]]*\])?\s*\{([^}]+)\}", source
    ))

for tex_file, raw_name in graphics_refs:
    candidate = Path(raw_name)
    if not candidate.is_absolute() and (not candidate.parts or candidate.parts[0] != "images"):
        candidate = IMAGE_DIR / candidate
    elif not candidate.is_absolute():
        candidate = ROOT / candidate
    exists = candidate.is_file() if candidate.suffix else any(
        candidate.parent.glob(candidate.name + ".*")
    )
    if not exists:
        errors.append(f"{tex_file}: missing graphics asset {raw_name!r}")

used_svg = set()
for tex_file, raw_name in svg_refs:
    name = raw_name.removesuffix(".svg")
    path = IMAGE_DIR / f"{name}.svg"
    if not path.is_file():
        errors.append(f"{tex_file}: missing SVG source {raw_name!r}")
    else:
        used_svg.add(path.resolve())

all_svg = {path.resolve() for path in IMAGE_DIR.glob("*.svg")}
for path in sorted(all_svg - used_svg):
    errors.append(f"Unreferenced SVG source: {path.relative_to(ROOT)}")

figure_table_labels = []
figure_table_count = {"figure": 0, "table": 0}
for tex_file, source in sources.items():
    for match in re.finditer(
        r"\\begin\{(figure|table)\*?\}([\s\S]*?)\\end\{\1\*?\}", source
    ):
        kind, body = match.group(1), match.group(2)
        figure_table_count[kind] += 1
        captions = re.findall(r"\\caption(?:\[[^]]*\])?\s*\{", body)
        env_labels = re.findall(r"\\label\s*\{([^}]+)\}", body)
        if not captions:
            errors.append(f"{tex_file.name}: {kind} environment has no caption")
        if len(env_labels) != 1:
            errors.append(
                f"{tex_file.name}: {kind} environment must have exactly one label; "
                f"found {len(env_labels)}"
            )
        figure_table_labels.extend(env_labels)

for label in figure_table_labels:
    if label not in references:
        errors.append(f"Figure/table label is not referenced in the text: {label}")

main_source = sources.get(ROOT / "main.tex", "")
for command in (r"\listoftables", r"\listoffigures", r"\bibliography{bibfile}"):
    if command not in main_source:
        errors.append(f"main.tex is missing required list/bibliography command: {command}")

if len(svg_refs) != 23:
    errors.append(f"Expected 23 active SVG references; found {len(svg_refs)}")

if errors:
    print("Reference and bibliography audit failed:")
    for error in errors:
        print(f" - {error}")
    sys.exit(1)

print(
    "Reference audit OK: "
    f"{len(set(labels))} unique labels; {len(references)} cross-references; "
    f"{len(set(citation_keys))} cited bibliography keys / {len(bib_keys)} entries; "
    f"{figure_table_count['figure']} figures; {figure_table_count['table']} tables; "
    f"{len(svg_refs)} SVG and {len(graphics_refs)} raster/vector graphics references."
)
print("Preserved historically uncited entries: " + ", ".join(sorted(unused_bib)))
