# Multimedia Grid (Master Thesis, 2007)

Master thesis source files by **Viliam Šimko** (Charles University in Prague, Faculty of Mathematics and Physics, Department of Software Engineering).

* **Supervisor:** RNDr. Leo Galamboš, Ph.D.
* **Topic:** Multimedia Grid & UNIX Videoconferencing using AccessGrid

---

## Overview

This thesis explores the possibilities and challenges of group-to-group communication systems based exclusively on open-source UNIX components. It focuses on AccessGrid technology utilizing multicast packet delivery for multimedia content.

Key topics covered:
- **AccessGrid Architecture:** Designing and deploying a full-featured videoconferencing node (CIANT node).
- **Network Routing & Traversal:** Multicast/Unicast communication, QuickBridge, and NAT/firewall traversal.
- **Protocols & Codecs:** Evaluation of streaming protocols (RTP/RTCP, SIP, H.323) and video/audio codecs (H.261, H.263, H.264, MPEG-4).
- **Recording & Archiving:** Development of the StreamVNC tool, integrating AGVCR, EVIC, and RAT for recording and presentation playback.

---

## Project Structure

```
├── main.tex                 # Master LaTeX document
├── preface.tex              # Preface & acknowledgements
├── abstract.tex             # Abstract & keywords
├── introduction.tex         # Introduction chapter
├── chapter-technology.tex   # Overview of videoconferencing technologies
├── chapter-protocols.tex    # Communication protocols
├── chapter-codecs.tex       # Audio & video codecs
├── chapter-ciantnode.tex    # CIANT AccessGrid node design
├── chapter-nat.tex          # NAT and firewall traversal
├── chapter-nodesetup.tex    # Node setup and hardware configuration
├── chapter-recording.tex    # Recording and archiving (StreamVNC)
├── conclusion.tex           # Conclusion & future work
├── bibfile.bib              # Bibliography references
├── csprimes.tex             # Typography macros
├── images/                  # SVG vector sources and raster images
├── build.sh                 # Build, cleanup, and test script
├── BUILDING.md              # Reproducible local build instructions
├── tests/                   # Build and SVG pipeline tests
└── .github/workflows/       # GitHub Actions CI build workflow
```

---

## Building the Thesis

See [BUILDING.md](BUILDING.md) for the supported toolchain, fresh-checkout setup, dependency requirements, build/test commands, and cleanup behaviour.

Quick start after installing the documented dependencies:

```sh
./build.sh distclean
./build.sh test
./build.sh build
```

The production build uses `latexmk` when installed; otherwise it runs `pdflatex`, `bibtex`, and two further LaTeX passes. In both cases, `-shell-escape` is required so the LaTeX `svg` package can invoke Inkscape.

## Figure source policy

- The 23 maintained vector diagrams in `images/*.svg` are the editable source of truth.
- Reference vector diagrams from LaTeX with `\\includesvg{...}`; Inkscape converts them during the build.
- Photos and screenshots remain raster assets and are included with `\\includegraphics`.
- Do not add ODG files or PDF sidecar exports to `images/`. SVG and raster images are the maintained inputs; generated SVG-to-PDF files belong in the build cache and are removed by `./build.sh clean`.
- Run `./build.sh test` to validate SVG references, required conversion support, and LaTeX references.

## Continuous Integration & Releases (CI/CD)

- **Automatické testovanie a zostavenie:** Pri každom `push` alebo `pull_request` prebehne testovací balíček skriptu a kompilácia `main.tex`. Výsledný `main.pdf` je dostupný ako artefakt daného behu workflowu.
- **Automatické GitHub Releases:** Pri každom zlúčení (merge) pull requestu alebo priamom pushi do vetvy `main` workflow automaticky vytvorí nový GitHub Release (`v<build_number>`) s priloženým `main.pdf` na priame stiahnutie.
