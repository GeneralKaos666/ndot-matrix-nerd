# NDOT Matrix Nerd

A dot-matrix Nerd Font for Termux. Every glyph — letters, digits, box
drawing, Powerline separators and the full Nerd Font icon set — is drawn from
touching circular dots on a single 80-unit grid, so the whole face has one
coherent "screen door" aesthetic.

```
 A               g               0               ┌
 ###            ####            ###            ####
#   #          #   #          #   #          #
#   #          #   #          # # #          #
#   #          #   #          # # #          #
#####          #   #          #   #          #
#   #          #   #          #   #          #
#   #             #          #   #          #
#   #             #           ###           #
                ###
```

## What it is

| Role | Font | Contribution |
| --- | --- | --- |
| **Base** — letters, digits, box drawing, arrows, Latin/Cyrillic/Greek | [Cozette](https://github.com/the-moonwitch/Cozette) | every pixel redrawn as a touching dot |
| **Merge** — Nerd Font icons (Font Awesome, Devicons, Seti, Material Design, Codicons, Octicons, …) | [FiraCode Nerd Font](https://github.com/ryanoasis/nerd-fonts) | every icon redrawn as a dot |

The result is a single TrueType face, ~15,600 glyphs, monospaced:

* dot pitch **80 units**, radius **40** (touching)
* text advance **480** (6 dots), icons **960** (12 dots)
* Powerline (`U+E0A0–U+E0D8`) stretched to the full cell so separators join
* ligatures stripped — a dot font shows raw dots, not substitutions

## Build

Requirements: `fontforge`, `python3`, `fonttools`, `numpy`.

```bash
./build.sh              # -> ndot-matrix-nerd.ttf
```

The pipeline runs in four steps:

1. **`build_base_dots.py`** — reads `cozette.bdf` and redraws each glyph's
   pixels as touching circles, emitting a TrueType base (`base-dots.ttf`,
   advance 480).
2. **`merge.pe`** (FontForge) — merges `FiraCodeNerdFont-Regular.ttf` onto the
   base, scaling it to the base's units-per-em. The base wins wherever the two
   fonts share a glyph.
3. **`restyle_icons.py`** (fontTools + numpy) — rasterises every glyph the
   merge contributed (icons + rare fills) onto the same 80-unit grid and
   rebuilds it as dots. Powerline glyphs get single width (480, full cell);
   everything else gets double width (960, aspect-fit).
4. **`finalize.py`** — drops the FiraCode GSUB ligature table, pins the
   vertical metrics, re-brands the name table and embeds the OFL notice.

Build outputs (`base-dots.ttf`, `merged.ttf`, `ndot-matrix-nerd.ttf`) are
gitignored.

### Install on Termux

```bash
cp ndot-matrix-nerd.ttf ~/.termux/font.ttf && termux-reload-settings
```

## Source fonts

Both source fonts are bundled in this repo and openly licensed:

| File | Origin | License |
| --- | --- | --- |
| `cozette.bdf` | [Cozette v1.30.0](https://github.com/the-moonwitch/Cozette) by Ines | SIL OFL 1.1 |
| `FiraCodeNerdFont-Regular.ttf` | [Fira Code](https://github.com/tonsky/FiraCode) patched by [Nerd Fonts](https://github.com/ryanoasis/nerd-fonts) | SIL OFL 1.1 (Fira Code) + MIT (Nerd Fonts) |

## License

* Build scripts and docs in this repo: **MIT** (see [`LICENSE`](LICENSE)).
* The built font is derived entirely from OFL-licensed work, so it may be
  used, modified and redistributed under the **SIL Open Font License 1.1**
  (see [`OFL-1.1.txt`](OFL-1.1.txt)). The OFL text and the upstream copyright
  notice are also embedded in the font's `name` table, so the licence travels
  with the `.ttf`.

Upstream copyright:

* Cozette — (c) 2020-2025 Ines <ines@moonwit.ch>
* Fira Code — (c) 2014-2021 The Fira Code Project Authors
* Nerd Fonts — (c) 2014 Ryan L McIntyre and Nerd Fonts contributors
