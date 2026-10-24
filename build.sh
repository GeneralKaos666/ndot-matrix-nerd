#!/usr/bin/env bash
# build.sh — build "NDOT Matrix Nerd" for Termux from scratch.
#
#   1. build_base_dots.py   Cozette bitmap -> dot-matrix TrueType base (80-unit
#                           touching dots, advance 480).
#   2. merge.pe             merge FiraCode Nerd Font onto the base (base wins).
#   3. restyle_icons.py     redraw every contributed glyph (icons + rare fills)
#                           as dots at the same 80-unit pitch.
#   4. finalize.py          strip ligatures, pin metrics, brand + embed OFL.
#
# Output: ndot-matrix-nerd.ttf  (in this directory; gitignored)
set -euo pipefail
cd "$(dirname "$0")"

BASE="base-dots.ttf"
MERGE="FiraCodeNerdFont-Regular.ttf"
OUT="merged.ttf"
FINAL="${FINAL:-ndot-matrix-nerd.ttf}"

[[ -f "$MERGE" ]] || { echo "missing $MERGE"; exit 1; }

echo "==> [1/4] building dot base from Cozette"
python3 build_base_dots.py

echo "==> [2/4] merging FiraCode Nerd Font"
fontforge -script merge.pe "$BASE" "$MERGE" "$OUT" "NDOT Matrix Nerd" "NDOTMatrixNerd-Regular" 2>&1 | tail -3

echo "==> [3/4] restyling contributed glyphs as dots"
python3 restyle_icons.py "$OUT"

echo "==> [4/4] finalizing"
python3 finalize.py "$OUT" "$FINAL"

echo "==> done: $FINAL"
