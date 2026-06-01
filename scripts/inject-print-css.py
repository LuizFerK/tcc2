import sys
import re
import os

src = open(sys.argv[1], encoding="utf-8").read()

# Convert relative image paths to absolute file:// URLs so Chromium can load
# them from the temp directory where the patched HTML lives.
input_dir = os.path.dirname(os.path.abspath(sys.argv[1]))


def abs_src(m):
    rel = m.group(1)
    abs_path = os.path.normpath(os.path.join(input_dir, rel))
    return f'src="file://{abs_path}"'


src = re.sub(r'src="(\.\.[^"]+)"', abs_src, src)

# Slides are designed for a 1280×720 viewport (100vw × 100vh viewed at 200%
# zoom on a 2.5K monitor). PDF page matches that size exactly.
inject = """<style id="slides-print-override">
@page { size: 1280px 720px; margin: 0; }
@media print {
  *, *::before, *::after {
    -webkit-print-color-adjust: exact !important;
    print-color-adjust: exact !important;
    color-adjust: exact !important;
    transition: none !important;
    animation: none !important;
  }
  html, body {
    overflow: visible !important;
    width: 1280px !important;
    height: auto !important;
    margin: 0 !important;
    padding: 0 !important;
  }
  script, style { display: none !important; }
  #slides-container, .slides-container,
  [class*="slide-container"], [class*="slides-wrapper"] {
    overflow: visible !important;
    height: auto !important;
    position: static !important;
    display: block !important;
  }
  .slide {
    display: flex !important;
    visibility: visible !important;
    opacity: 1 !important;
    position: relative !important;
    inset: auto !important;
    width: 1280px !important;
    height: 720px !important;
    overflow: hidden !important;
    transform: none !important;
    flex-shrink: 0 !important;
    box-sizing: border-box !important;
  }
  .slide ~ .slide {
    break-before: page !important;
    page-break-before: always !important;
  }
  .nav-btn, .nav, nav, button,
  .progress-bar, .slide-counter,
  [class*="counter"], [class*="progress"],
  [class*="nav-btn"] { display: none !important; }
}
</style>"""

out = re.sub(r"(</head>)", inject + "\n\\1", src, count=1, flags=re.IGNORECASE)
open(sys.argv[2], "w", encoding="utf-8").write(out)
