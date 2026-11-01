#!/usr/bin/env python3
"""Fail CI when the final LaTeX/BibTeX pass contains unresolved references or errors."""
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
log_path = ROOT / "main.log"
blg_path = ROOT / "main.blg"
errors = []

for path in (log_path, blg_path):
    if not path.is_file():
        errors.append(f"Expected build diagnostic file was not produced: {path.name}")

if log_path.is_file():
    log = log_path.read_text(encoding="utf-8", errors="replace")
    checks = {
        "undefined citation": r"LaTeX Warning: Citation [\x60'][^\x60']+[\x60'] .*undefined",
        "undefined reference": r"LaTeX Warning: Reference [\x60'][^\x60']+[\x60'] .*undefined",
        "duplicate label": r"Label [\x60'][^\x60']+[\x60'] multiply defined",
        "duplicate PDF destination": r"destination with the same identifier",
        "missing asset": r"(?:LaTeX|Package .* Error): .*?(?:not found|File .* not found)",
        "unresolved references summary": r"There were undefined references",
    }
    for description, pattern in checks.items():
        if re.search(pattern, log, re.IGNORECASE):
            errors.append(f"Final main.log contains {description} warning/error")
    if "Output written on main.pdf" not in log:
        errors.append("Final main.log does not confirm that main.pdf was written")

if blg_path.is_file():
    blg = blg_path.read_text(encoding="utf-8", errors="replace")
    for line in blg.splitlines():
        if re.search(r"^(?:Warning--|I was expecting|Sorry|error)", line, re.IGNORECASE):
            errors.append(f"BibTeX diagnostic: {line.strip()}")

if errors:
    print("LaTeX/BibTeX log audit failed:")
    for error in errors:
        print(f" - {error}")
    sys.exit(1)

print("LaTeX/BibTeX log audit OK: no unresolved citations/references, duplicate labels/destinations, missing assets, or BibTeX warnings.")
