set -e
origdir=$(pwd)

build_one() {
  local lang="$1"
  local main="$2"
  local out="$3"

  echo "[thesis] Building $lang version ($main)..."
  tmpdir=$(mktemp -d)
  cp -r "$origdir/tcc2-latex/." "$tmpdir/"
  cd "$tmpdir"
  HOME=$(mktemp -d) latexmk -pdf -bibtex -interaction=nonstopmode "$main"
  cp "${main%.tex}.pdf" "$origdir/$out"
  echo "[thesis] $lang PDF written to $origdir/$out"
  rm -rf "$tmpdir"
  cd "$origdir"
}

build_one "English"    "main-en-us.tex" "thesis-en-us.pdf"
build_one "Portuguese" "main-pt-br.tex" "thesis-pt-br.pdf"

echo "[thesis] Done. Outputs: thesis-en-us.pdf  thesis-pt-br.pdf"
