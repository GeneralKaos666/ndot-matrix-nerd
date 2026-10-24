#!/usr/bin/env python3
"""
restyle_icons.py — redraw every non-base glyph of a merged dot-matrix font as
dots, at the SAME pitch as the text (80 units), so the whole face is one
coherent dot grid.

The base (Cozette -> dots) already covers ASCII, Latin, Cyrillic, Greek, box
drawing, arrows, ... at advance 480. Everything FiraCode contributed is either
a Nerd Font icon (Private Use Area) or a rare letter/symbol. This script turns
all of them into touching circles and pins each to a monospace advance.

Modes (per glyph):
  * powerline  U+E0A0..U+E0D8  -> single 480, stretched to the full cell so
                                   separators connect edge-to-edge
  * PUA icon   (other PUA)     -> double 960, aspect-fit + centered
  * text fill  (non-PUA)       -> single 480, aspect-fit + centered
Combining marks (U+0300..U+036F) and zero-width glyphs are left untouched.
"""
from __future__ import annotations

import math
import sys

import numpy as np
from fontTools.pens.basePen import BasePen
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont

CELL = 80
RADIUS = CELL // 2          # 40 -> touching dots
SINGLE = 6 * CELL           # 480
DOUBLE = 12 * CELL          # 960
ASCENT = 10 * CELL          # 800
DESCENT = -3 * CELL         # -240
PAD = CELL                  # 80

POWERLINE_LO, POWERLINE_HI = 0xE0A0, 0xE0D8
PUA_RANGES = ((0xE000, 0xF8FF), (0xF0000, 0xFFFFD), (0x100000, 0x10FFFD))


def is_pua(cp):
    return any(lo <= cp <= hi for lo, hi in PUA_RANGES)


def is_powerline(cp):
    return POWERLINE_LO <= cp <= POWERLINE_HI


def is_combining(cp):
    return 0x0300 <= cp <= 0x036F


# --------------------------------------------------------------------------- #
# Outline -> flattened contours
# --------------------------------------------------------------------------- #
def _quad(p0, p1, p2, t):
    mt = 1.0 - t
    return (mt * mt * p0[0] + 2 * mt * t * p1[0] + t * t * p2[0],
            mt * mt * p0[1] + 2 * mt * t * p1[1] + t * t * p2[1])


def _cube(p0, p1, p2, p3, t):
    mt = 1.0 - t
    return (mt**3 * p0[0] + 3 * mt * mt * t * p1[0] + 3 * mt * t * t * p2[0] + t**3 * p3[0],
            mt**3 * p0[1] + 3 * mt * mt * t * p1[1] + 3 * mt * t * t * p2[1] + t**3 * p3[1])


class ContoursPen(BasePen):
    def __init__(self, glyphSet, steps=4):
        super().__init__(glyphSet)
        self.steps = steps
        self.contours = []
        self._cur = []

    def _moveTo(self, pt):
        self._closePath()
        self._cur = [pt]

    def _lineTo(self, pt):
        self._cur.append(pt)

    def _curveToOne(self, p1, p2, p3):
        p0 = self._cur[-1]
        for i in range(1, self.steps + 1):
            self._cur.append(_cube(p0, p1, p2, p3, i / self.steps))

    def _qCurveToOne(self, p1, p2):
        p0 = self._cur[-1]
        for i in range(1, self.steps + 1):
            self._cur.append(_quad(p0, p1, p2, i / self.steps))

    def _closePath(self):
        if self._cur and len(self._cur) >= 2:
            self.contours.append(np.asarray(self._cur, dtype=float))
        self._cur = []

    def _endPath(self):
        self._closePath()

    def result(self):
        self._closePath()
        return self.contours


def winding(contours, qx, qy):
    qx = np.asarray(qx, float)
    qy = np.asarray(qy, float)
    wn = np.zeros(qx.shape, np.int32)
    for poly in contours:
        x, y = poly[:, 0], poly[:, 1]
        x1, y1 = np.roll(x, -1), np.roll(y, -1)
        left = (x1 - x)[:, None] * (qy[None, :] - y[:, None]) - \
               (y1 - y)[:, None] * (qx[None, :] - x[:, None])
        up = (y[:, None] <= qy[None, :]) & (y1[:, None] > qy[None, :])
        down = (y[:, None] > qy[None, :]) & (y1[:, None] <= qy[None, :])
        wn += (up & (left > 0)).sum(axis=0)
        wn -= (down & (left < 0)).sum(axis=0)
    return wn


def rasterize(contours, i0, i1, j0, j1):
    """One center sample per 80-unit cell: cell is 'on' if its center is inside
    the (already target-fitted) outline. Coarse grid -> center sampling is
    enough and keeps the pass fast."""
    qx, qy = [], []
    for j in range(j0, j1 + 1):
        for i in range(i0, i1 + 1):
            qx.append((i + 0.5) * CELL)
            qy.append((j + 0.5) * CELL)
    if not qx:
        return set()
    wn = winding(contours, qx, qy)
    cells = set()
    ncols = i1 - i0 + 1
    for k in np.nonzero(wn != 0)[0].tolist():
        cells.add((i0 + k % ncols, j0 + k // ncols))
    return cells


def draw_dot(pen, cx, cy):
    c = RADIUS / math.cos(math.radians(22.5))
    pts = [(round(cx + RADIUS * math.cos(math.radians(k * 45))),
            round(cy + RADIUS * math.sin(math.radians(k * 45)))) for k in range(8)]
    pen.moveTo(pts[0])
    for k in range(8):
        a_mid = math.radians(k * 45 + 22.5)
        ctrl = (round(cx + c * math.cos(a_mid)), round(cy + c * math.sin(a_mid)))
        pen.qCurveTo(ctrl, pts[(k + 1) % 8])
    pen.closePath()


def restyle(path):
    font = TTFont(path)
    glyph_set = font.getGlyphSet()
    glyf = font["glyf"]
    hmtx = font["hmtx"]
    order = font.getGlyphOrder()

    name2cp = {}
    for table in font["cmap"].tables:
        if table.isUnicode():
            for k, v in table.cmap.items():
                name2cp.setdefault(v, k)

    changed = 0
    emptied = 0
    total = len(order)
    for idx, name in enumerate(order):
        if idx % 2000 == 0:
            print("  ... %d/%d (%d changed)" % (idx, total, changed))
        if name not in glyf:
            continue
        advance = hmtx[name][0]
        cp = name2cp.get(name)

        # unmapped glyphs (FiraCode ligature / alternate / spacer glyphs) are
        # only reachable via GSUB, which we strip later — leave them untouched.
        if cp is None:
            continue
        # base glyphs (advance already 480) and combining marks are skipped
        if advance == SINGLE and not is_pua(cp):
            continue
        if is_combining(cp) or advance == 0:
            continue

        # decide mode + target transform
        if cp is not None and is_powerline(cp):
            mode = "powerline"
        elif cp is not None and is_pua(cp):
            mode = "icon"
        else:
            mode = "text"

        glyph = glyf[name]
        pen = ContoursPen(glyph_set)
        glyph.draw(pen, glyph_set)
        contours = pen.result()
        if not contours:
            continue
        # exact (un-flattened) bounds for the fit, so the aspect-fit can't
        # under-estimate and overflow the cell
        bp = BoundsPen(glyph_set)
        glyph.draw(bp, glyph_set)
        x0, y0, x1, y1 = bp.bounds
        w = x1 - x0
        h = y1 - y0
        if w < 1 or h < 1:
            continue

        if mode == "powerline":
            tadv = SINGLE
            sx, sy = SINGLE / w, (ASCENT - DESCENT) / h
        else:
            tadv = DOUBLE if mode == "icon" else SINGLE
            box_w = tadv - 2 * PAD
            box_h = (ASCENT - DESCENT) - 2 * PAD
            s = min(box_w / w, box_h / h)
            sx = sy = s

        cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
        tcx = tadv / 2.0
        tcy = (ASCENT + DESCENT) / 2.0

        def tx(p):
            return (p - cx) * sx + tcx

        def ty(p):
            return (p - cy) * sy + tcy

        tcontours = []
        for poly in contours:
            tcontours.append(np.stack([tx(poly[:, 0]), ty(poly[:, 1])], axis=1))

        tx0, tx1 = tx(x0), tx(x1)
        ty0, ty1 = ty(y0), ty(y1)
        i0 = math.floor(min(tx0, tx1) / CELL)
        i1 = math.floor(max(tx0, tx1) / CELL)
        j0 = math.floor(min(ty0, ty1) / CELL)
        j1 = math.floor(max(ty0, ty1) / CELL)

        cells = rasterize(tcontours, i0, i1, j0, j1)
        if not cells:
            emptied += 1
            hmtx[name] = (tadv, hmtx[name][1])
            continue

        out_pen = TTGlyphPen(glyph_set)
        for i, j in sorted(cells):
            draw_dot(out_pen, (i + 0.5) * CELL, (j + 0.5) * CELL)
        g = out_pen.glyph()
        g.recalcBounds(glyf)
        glyf[name] = g
        hmtx[name] = (tadv, g.xMin)
        changed += 1

    print("restyled %d glyphs (%d kept original, empty raster)" % (changed, emptied))
    font.save(path)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: restyle_icons.py MERGED.ttf")
        sys.exit(1)
    restyle(sys.argv[1])
