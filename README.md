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
├── images/                  # Diagrams (.odg, .pdf) and screenshots (.png)
├── build.sh                 # Build, cleanup, and test script
├── tests/                   # Test suite for build script
└── .github/workflows/       # GitHub Actions CI build workflow
```

---

## Prerequisites

To build the thesis document locally, you need a LaTeX distribution (such as TeX Live):

- `pdflatex`
- `bibtex`
- `latexmk` *(optional, recommended for automated build passes)*

On Debian/Ubuntu:
```sh
sudo apt-get install texlive-latex-base texlive-latex-extra texlive-fonts-recommended texlive-lang-czechslovak latexmk
```

---

## Building the Thesis

### Using the build script

The provided `build.sh` script automates the compilation and cleanup process:

```sh
# Build main.pdf (uses latexmk if installed, otherwise pdflatex + bibtex)
./build.sh build

# Clean auxiliary build files (*.aux, *.log, *.toc, etc.)
./build.sh clean

# Clean auxiliary files and generated main.pdf
./build.sh distclean

# Run tests for build script
./build.sh test
```

### Using latexmk directly

```sh
latexmk -pdf main.tex
```

---

## Continuous Integration & Releases (CI/CD)

- **Automatické testovanie a zostavenie:** Pri každom `push` alebo `pull_request` prebehne testovací balíček skriptu a kompilácia `main.tex`. Výsledný `main.pdf` je dostupný ako artefakt daného behu workflowu.
- **Automatické GitHub Releases:** Pri každom zlúčení (merge) pull requestu alebo priamom pushi do vetvy `main` workflow automaticky vytvorí nový GitHub Release (`v<build_number>`) s priloženým `main.pdf` na priame stiahnutie.
