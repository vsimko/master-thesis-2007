# Reproducible local build

This repository is built and validated in GitHub Actions with the following toolchain:

| Component | Supported version / package set | Purpose |
| --- | --- | --- |
| Operating system | Ubuntu 24.04 GitHub-hosted runner | CI environment |
| TeX distribution | TeX Live 2026 | LaTeX engine and packages |
| TeX Live collections | `collection-latexrecommended`, `collection-latexextra`, `collection-fontsrecommended`, `collection-langczechslovak` | Document class, graphics, fonts, and Czech/Slovak language support |
| Build driver | `latexmk` from TeX Live 2026 (optional locally) | Repeated LaTeX/BibTeX passes |
| SVG renderer | Inkscape (Ubuntu 24.04 package) | SVG-to-PDF conversion invoked by the LaTeX `svg` package |
| Python | Python 3.9 or newer | Static source, SVG, and reference checks |
| Poppler | `poppler-utils` (CI validation) | PDF text extraction and page-layout checks |

The CI workflow is the authoritative tested dependency definition. The TeX Live release and required collections are explicit there; Inkscape and Poppler are installed from the Ubuntu 24.04 repositories. Their package revisions therefore follow the Ubuntu 24.04 security/update stream.

## Fresh checkout

1. Install Git, Python 3.9+, Inkscape, and TeX Live 2026 with the collections listed above. Ensure `pdflatex`, `bibtex`, and `inkscape` are on `PATH`. Install `latexmk` as well to use the same build-driver path as CI.
2. Clone the repository and enter its root directory:
   ```sh
   git clone https://github.com/vsimko/master-thesis-2007.git
   cd master-thesis-2007
   ```
3. Start from a clean generated state and run the checks and production build:
   ```sh
   ./build.sh distclean
   ./build.sh test
   ./build.sh build
   ```
4. Confirm that `main.pdf` exists and that the bibliography was regenerated from `bibfile.bib`. The build script removes the SVG conversion cache during cleanup so SVG exports are recreated from the maintained sources.

## Build behaviour

- `./build.sh build` uses `latexmk -pdf -shell-escape` when `latexmk` is installed. The `-shell-escape` flag is required because the `svg` package invokes Inkscape.
- Without `latexmk`, the script runs `pdflatex`, `bibtex`, and two further `pdflatex` passes.
- `./build.sh test` exercises both build-script paths and runs the SVG and reference audits. The build tests perform real LaTeX builds, so they require the same TeX and Inkscape tools.
- The CI-only PDF diagnostics additionally use `pdftotext` from `poppler-utils`.

## Maintained figure inputs

The 23 vector diagrams are maintained as SVG files in `images/` and referenced with `\includesvg`. Photos and screenshots remain raster images. Do not add ODG source files or PDF sidecar exports to `images/`; the SVG files are the editable vector inputs and Inkscape-generated PDFs are build intermediates only.

## Clean-up

- `./build.sh clean` removes LaTeX auxiliary files and the generated `svg-inkscape/` conversion cache while preserving `main.pdf`.
- `./build.sh distclean` additionally removes `main.pdf`.
