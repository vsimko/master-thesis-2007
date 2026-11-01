#!/bin/sh
set -eu

cd "$(dirname "$0")"

clean_aux() {
  rm -f ./*.aux main.bbl main.blg main.dvi main.idx main.ilg \
    main.ind main.lof main.log main.lot main.nav main.out \
    main.snm main.synctex.gz main.toc main.fls main.fdb_latexmk
}

case "${1:-build}" in
  build)
    if command -v latexmk >/dev/null 2>&1; then
      echo "Building using latexmk..."
      latexmk -pdf -shell-escape -interaction=nonstopmode -halt-on-error main.tex
    else
      echo "Building using pdflatex and bibtex..."
      pdflatex -shell-escape -interaction=nonstopmode -halt-on-error main.tex
      bibtex main
      pdflatex -interaction=nonstopmode -halt-on-error main.tex
      pdflatex -interaction=nonstopmode -halt-on-error main.tex
    fi
    ;;
  clean)
    clean_aux
    ;;
  distclean|clean-all)
    clean_aux
    rm -f main.pdf
    ;;
  test)
    sh ./tests/test_build.sh
    python3 ./tests/test_svg_pipeline.py
    ;;
  *)
    printf 'Použitie: sh build.sh [build|clean|distclean|test]\n' >&2
    exit 1
    ;;
esac
