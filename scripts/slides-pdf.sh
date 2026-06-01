# INJECT_CSS_SCRIPT is exported by the flake wrapper before this script runs.
: "${INJECT_CSS_SCRIPT:?INJECT_CSS_SCRIPT must be set}"

set -e
root=$(git rev-parse --show-toplevel)
htmls_dir="$root/presentation/htmls"
pdfs_dir="$root/presentation/pdfs"

mkdir -p "$pdfs_dir"

tmpdir=$(mktemp -d)
trap 'rm -rf "$tmpdir"' EXIT

patch_and_render() {
  local input="$1"
  local name
  name=$(basename "$input" .html)
  local output="$pdfs_dir/$name.pdf"
  local tmphtml="$tmpdir/$name.html"

  echo "[slides-pdf] $name ..."
  python3 "$INJECT_CSS_SCRIPT" "$input" "$tmphtml"

  # --window-size matches the 1280×720 viewport the slides were designed for
  # (100vw × 100vh at 200% zoom on a 2.5K monitor), keeping the @page size in
  # sync and preventing content clipping.
  # --allow-file-access-from-files lets the temp HTML load images via file://.
  HOME="$tmpdir" chromium \
    --headless=new \
    --disable-gpu \
    --no-sandbox \
    --no-pdf-header-footer \
    --disable-dev-shm-usage \
    --run-all-compositor-stages-before-draw \
    --virtual-time-budget=10000 \
    --window-size=1280,720 \
    --allow-file-access-from-files \
    --print-to-pdf="$output" \
    "file://$tmphtml"

  echo "[slides-pdf] → $output"
}

for html in "$htmls_dir"/*.html; do
  patch_and_render "$html"
done

echo "[slides-pdf] Done. PDFs written to $pdfs_dir/"
