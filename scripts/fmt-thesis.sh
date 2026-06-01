set -e
root=$(git rev-parse --show-toplevel)
latex_dir="$root/tcc2-latex"

echo "[fmt] Formatting refs.bib with bibtex-tidy..."
tmp=$(mktemp)
bibtex-tidy \
  --space=2 --align=14 --sort-fields --trailing-commas --no-escape \
  < "$latex_dir/refs.bib" > "$tmp"
mv "$tmp" "$latex_dir/refs.bib"

echo "[fmt] Formatting .tex files with tex-fmt..."
find "$latex_dir" -name "*.tex" -print0 \
  | xargs -0 tex-fmt --nowrap

echo "[fmt] Done."
