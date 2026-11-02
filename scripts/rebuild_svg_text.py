#!/usr/bin/env python3
"""Rebuild live, searchable SVG text from the reviewed English text labels."""
from pathlib import Path
import re

FILES = sorted(Path("images").glob("*.svg"))

def attr(source, name):
    match = re.search(r'\\b' + re.escape(name) + r'="([^"]*)"', source)
    return match.group(1) if match else None

def make_text(header, inner, label):
    path_match = re.search(r"<path\\b[^>]*>", inner)
    path = path_match.group(0) if path_match else header
    data = attr(path, "d") or ""
    point = re.match(r"\\s*[mM]\\s*([-+]?(?:\\d*\\.)?\\d+(?:e[-+]?\\d+)?)[,\\s]+([-+]?(?:\\d*\\.)?\\d+)", data, re.I)
    if not point:
        return None
    style = attr(path, "style") or attr(header, "style") or ""
    fill = attr(path, "fill") or attr(header, "fill")
    transform = attr(header, "transform") or attr(path, "transform")
    if not style and fill:
        style = "fill:" + fill
    attributes = f' x="{point.group(1)}" y="{point.group(2)}"'
    if style:
        attributes += ' style="' + style + '"'
    if transform:
        attributes += ' transform="' + transform + '"'
    return "<text" + attributes + ' xml:space="preserve">' + label + "</text>"

def rebuild(path):
    source = path.read_text(encoding="utf-8")
    counts = {"groups": 0, "paths": 0, "unconverted": 0}
    failures = []
    group_re = re.compile(r'<g\\b(?=[^>]*\\bclass="SVGTextShape")(?=[^>]*\\baria-label="([^"]*)")[^>]*>([\\s\\S]*?)</g>')
    def replace_group(match):
        text = make_text(match.group(0), match.group(2), match.group(1))
        if text is None:
            failures.append(match.group(1))
            return match.group(0)
        counts["groups"] += 1
        return text
    path_re = re.compile(r'<path\\b(?=[^>]*\\bclass="SVGTextShape")(?=[^>]*\\baria-label="([^"]*)")[^>]*?/>')
    def replace_path(match):
        text = make_text(match.group(0), "", match.group(1))
        if text is None:
            failures.append(match.group(1))
            return match.group(0)
        counts["paths"] += 1
        return text
    updated = group_re.sub(replace_group, source)
    updated = path_re.sub(replace_path, updated)
    counts["unconverted"] = updated.count('class="SVGTextShape"')
    if failures or counts["unconverted"]:
        raise RuntimeError(f"{path}: failed labels={failures}; remaining outlined text={counts['unconverted']}")
    if counts["groups"] + counts["paths"]:
        path.write_text(updated, encoding="utf-8")
    return counts

total = {"groups": 0, "paths": 0, "files": 0}
for svg in FILES:
    result = rebuild(svg)
    if result["groups"] + result["paths"]:
        total["files"] += 1
        total["groups"] += result["groups"]
        total["paths"] += result["paths"]
        print(f"{svg}: {result['groups']} grouped, {result['paths']} path labels converted")
print(f"TOTAL: {total}")
