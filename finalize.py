#!/usr/bin/env python3
"""
finalize.py — clean up and brand the merged dot-matrix font for Termux.

  1. Drop the FiraCode GSUB table (ligatures / stylistic sets / spacing
     features) — a dot-matrix font should show raw dots, not substitute
     smooth ligature glyphs, and terminals don't apply ligatures anyway.
  2. Pin the vertical metrics so line height is tight and correct.
  3. Re-brand the name table and embed the OFL licence so the terms travel
     with the .ttf.
"""
from __future__ import annotations

import os
import sys

from fontTools.ttLib import TTFont

FAMILY = "NDOT Matrix Nerd"
PSNAME = "NDOTMatrixNerd-Regular"
VERSION = "Version 1.000"

ASCENT = 800
DESCENT = -240


def finalize(path, out):
    font = TTFont(path)

    # 1. strip ligature / layout tables
    for tag in ("GSUB",):
        if tag in font:
            del font[tag]
            print("dropped", tag)

    # 2. vertical metrics
    font["hhea"].ascent = ASCENT
    font["hhea"].descent = DESCENT
    font["hhea"].lineGap = 0

    os2 = font["OS/2"]
    os2.sTypoAscender = ASCENT
    os2.sTypoDescender = DESCENT
    os2.sTypoLineGap = 0
    os2.usWinAscent = ASCENT
    os2.usWinDescent = -DESCENT
    os2.fsType = 0  # installable / editable
    os2.fsSelection = 0b01000000  # REGULAR

    # 3. name table
    name = font["name"]
    name.setName(FAMILY, 1, 3, 1, 0x409)          # family
    name.setName("Regular", 2, 3, 1, 0x409)       # subfamily
    name.setName(PSNAME + "-1.000", 3, 3, 1, 0x409)
    name.setName(FAMILY + " Regular", 4, 3, 1, 0x409)
    name.setName(VERSION, 5, 3, 1, 0x409)
    name.setName(PSNAME, 6, 3, 1, 0x409)
    name.setName(
        "Copyright (c) 2020-2025 Ines <ines@moonwit.ch> (Cozette, SIL OFL 1.1); "
        "Copyright (c) 2014-2021 The Fira Code Project Authors (SIL OFL 1.1); "
        "Copyright (c) 2014 Ryan L McIntyre and Nerd Fonts contributors (MIT). "
        "NDOT Matrix Nerd merges Cozette (as dots) with FiraCode Nerd Font icons "
        "(also redrawn as dots).",
        0, 3, 1, 0x409)

    here = os.path.dirname(os.path.abspath(__file__))
    ofl = os.path.join(here, "OFL-1.1.txt")
    if os.path.exists(ofl):
        with open(ofl, encoding="utf-8") as fh:
            text = fh.read().strip()
        name.setName(text, 13, 3, 1, 0x409)        # license description
        name.setName("https://openfontlicense.org", 14, 3, 1, 0x409)

    font.save(out)
    font.close()
    print("wrote", out)


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else "merged.ttf"
    dst = sys.argv[2] if len(sys.argv) > 2 else "ndot-matrix-nerd.ttf"
    finalize(src, dst)
