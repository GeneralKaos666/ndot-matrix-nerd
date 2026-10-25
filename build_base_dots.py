#!/usr/bin/env python3
"""
build_base_dots.py — build a TrueType "NDOT matrix" base font from Cozette's
bitmap (BDF) data.

Every Cozette glyph is a 6px-wide monospace bitmap. This script reads the BDF,
and for every glyph redraws each "on" pixel as a touching circle on a dot grid,
so the whole face takes on the NDOT / dot-matrix look (circular dots, touching,
screen-door aesthetic) instead of Cozette's pixel squares.

Coordinate model (font units, y up, baseline = 0):
  * units-per-em    = 1024
  * dot pitch       = 80   (square cells)
  * dot radius      = 40   (0.5 * pitch  -> dots touch, NDOT style)
  * advance         = 480  (6 cells, Cozette's 6px width)
  * ascent  = 10 cells = 800
  * descent =  3 cells = 240  (Cozette: 10 ascent / 3 descent)

The result is `base-dots.ttf`, a TrueType face that FontForge can merge with a
Nerd Font (FiraCode) to fill in every icon the base is missing.
"""
from __future__ import annotations

import math
import os

from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen

UPM = 1024
CELL = 80
RADIUS = CELL // 2          # 40 -> touching dots
ADVANCE = 6 * CELL          # 480
ASCENT = 10 * CELL          # 800
DESCENT = -3 * CELL         # -240

BDF = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cozette.bdf")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "base-dots.ttf")

FAMILY = "NDOT Matrix Nerd"
PSNAME = "NDOTMatrixNerd-Regular"


def draw_dot(pen, cx, cy, r):
    """One dot = 8 quadratic segments (circle), matching NDOT's round dots."""
    c = r / math.cos(math.radians(22.5))
    pts = []
    for k in range(8):
        a = math.radians(k * 45)
        pts.append((round(cx + r * math.cos(a)), round(cy + r * math.sin(a))))
    pen.moveTo(pts[0])
    for k in range(8):
        a_mid = math.radians(k * 45 + 22.5)
        ctrl = (round(cx + c * math.cos(a_mid)), round(cy + c * math.sin(a_mid)))
        pen.qCurveTo(ctrl, pts[(k + 1) % 8])
    pen.closePath()


def parse_bdf(path):
    """Return {codepoint: (name, advance_cells, xoff, yoff, rows)}.

    rows is a list of bit-strings (each exactly `width` chars, '1' = on).
    """
    glyphs = {}
    with open(path) as f:
        lines = f.read().splitlines()

    i = 0
    n = len(lines)
    while i < n:
        if lines[i].startswith("STARTCHAR"):
            name = lines[i].split(None, 1)[1]
            enc = None
            dw = 6
            bbx = None
            rows = []
            i += 1
            while i < n and not lines[i].startswith("ENDCHAR"):
                line = lines[i]
                if line.startswith("ENCODING"):
                    enc = int(line.split()[1])
                elif line.startswith("DWIDTH"):
                    dw = int(line.split()[1])
                elif line.startswith("BBX"):
                    parts = line.split()
                    w, h, xo, yo = (int(parts[1]), int(parts[2]),
                                    int(parts[3]), int(parts[4]))
                    bbx = (w, h, xo, yo)
                elif line.startswith("BITMAP"):
                    # subsequent non-keyword lines are hex rows
                    i += 1
                    while i < n and not lines[i].startswith("ENDCHAR"):
                        hexrow = lines[i].strip()
                        if hexrow:
                            val = int(hexrow, 16)
                            bits = format(val, "0%db" % (len(hexrow) * 4))
                            rows.append(bits)
                        i += 1
                    break
                i += 1
            if enc is not None and bbx is not None:
                w, h, xo, yo = bbx
                # BDF rows are left-aligned, MSB-first: the glyph's pixels are
                # the first `w` bits of each row, not the last.
                clipped = [r[:w].ljust(w, "0") for r in rows]
                glyphs[enc] = (name, dw, xo, yo, clipped)
        i += 1
    return glyphs


def build_glyph(xoff, yoff, rows):
    """Draw one glyph's dots. `rows` rows[0] is the TOP bitmap row."""
    pen = TTGlyphPen(None)
    h = len(rows)
    for r, row in enumerate(rows):
        for c, bit in enumerate(row):
            if bit == "1":
                x_cell = xoff + c
                # BDF: baseline at y=0; descent cells sit below. yoff is the
                # distance from baseline to the *bottom* of the bitmap.
                y_from_bottom = yoff + (h - 1 - r) + 3  # +3 = descent cells
                # font y of the cell's bottom edge
                cell_bottom = (y_from_bottom - 3) * CELL
                cx = (x_cell + 0.5) * CELL
                cy = cell_bottom + 0.5 * CELL
                draw_dot(pen, cx, cy, RADIUS)
    return pen


def main():
    glyphs = parse_bdf(BDF)
    print("parsed %d glyphs from %s" % (len(glyphs), os.path.basename(BDF)))

    order = [".notdef"]
    cmap = {}
    glyf = {}

    # .notdef — a simple box (solid, so missing glyphs are obvious)
    nd = TTGlyphPen(None)
    nd.moveTo((40, ASCENT - 120))
    nd.lineTo((ADVANCE - 40, ASCENT - 120))
    nd.lineTo((ADVANCE - 40, 120 - DESCENT))
    nd.lineTo((40, 120 - DESCENT))
    nd.closePath()
    g = nd.glyph()
    g.width = ADVANCE
    glyf[".notdef"] = g

    for cp in sorted(glyphs):
        name, dw, xo, yo, rows = glyphs[cp]
        # keep only single-width text glyphs in the base (double-width CJK and
        # the like are supplied by the merge font)
        if dw != 6:
            continue
        # Skip Private Use Area codepoints. Cozette ships its own low-res dot
        # glyphs for these (503 of them, including U+F07B "folder"), and they
        # would override FiraCode's proper Nerd Font icons on merge. Let the
        # merge font own the icon planes instead.
        if (0xE000 <= cp <= 0xF8FF) or (0xF0000 <= cp <= 0xFFFFD) or \
           (0x100000 <= cp <= 0x10FFFD):
            continue
        glyph_name = name
        if glyph_name in order:
            glyph_name = "uni%04X" % cp if cp < 0x10000 else "u%05X" % cp
        order.append(glyph_name)
        cmap[cp] = glyph_name
        pen = build_glyph(xo, yo, rows)
        g = pen.glyph()
        g.width = ADVANCE
        glyf[glyph_name] = g

    fb = FontBuilder(UPM, isTTF=True)
    fb.setupGlyphOrder(order)
    fb.setupCharacterMap(cmap)
    fb.setupGlyf(glyf)

    # Correct left side bearing per glyph. Glyphs with a left offset (xoff>0)
    # have their ink shifted right of the origin; a wrong lsb=0 makes the merge
    # re-anchor them and corrupt box drawing. lsb must equal the ink's xMin.
    metrics = {}
    for name in order:
        g = glyf[name]
        g.recalcBounds(None)
        lsb = g.xMin if g.numberOfContours > 0 else 0
        metrics[name] = (ADVANCE, lsb)
    fb.setupHorizontalMetrics(metrics)

    fb.setupHorizontalHeader(ascent=ASCENT, descent=DESCENT)
    fb.setupNameTable({
        "familyName": FAMILY,
        "styleName": "Regular",
        "uniqueFontIdentifier": "NDOTMatrixNerd-Regular-1.000",
        "fullName": FAMILY + " Regular",
        "psName": PSNAME,
        "version": "Version 1.000",
        "copyright": "Based on Cozette (c) 2020-2025 Ines <ines@moonwit.ch>, SIL OFL 1.1",
    })
    fb.setupOS2(sTypoAscender=ASCENT, sTypoDescender=DESCENT,
                sTypoLineGap=0, usWinAscent=ASCENT, usWinDescent=-DESCENT)
    fb.setupPost()
    fb.save(OUT)
    print("saved %s (%d glyphs)" % (OUT, len(order)))


if __name__ == "__main__":
    main()
