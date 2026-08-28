---
name: plattfig
description: Generate Make: Electronics-style breadboard and schematic illustrations as SVG using the plattfig Python library (no dependencies). Use when the user wants a breadboard layout drawing, wiring diagram, circuit schematic, or electronics figure for a course, book, or article — triggers include "breadboard diagram", "draw this circuit", "Platt style", "Make: style", "schematic figure".
---

# plattfig — breadboard and schematic figures

Draw electronics figures in the visual language of Charles Platt's
Make: Electronics illustrations: flat vector breadboards with colored
jumpers and pill callouts, and semi-physical schematics whose DIP
outline mirrors the breadboard. Output is a standalone SVG.

## Setup

Use `plattfig.py` from this skill's directory. If missing, fetch it:

```bash
curl -fsSLO https://raw.githubusercontent.com/dstodolny/plattfig/main/plattfig.py
```

Write one Python spec per figure; run it with `python3` (3.8+, stdlib
only) and it prints the SVG path it wrote.

## Breadboard quick start

```python
from plattfig import Breadboard, WIRE_RED, WIRE_BLUE, WIRE_GREEN
bb = Breadboard(cols=30)                    # half-size board; 63 = full
bb.ic(13, "555")                            # DIP-8 straddles the trench, notch left
bb.jumper((13, "a"), ("T+", 13), color=WIRE_RED)
bb.route([(16, "g"), bb.xy(18.5, "g"), bb.xy(18.5, "T+"), ("T+", 19)], color=WIRE_RED)
bb.resistor(("T+", 14), (14, "a"), "10k")   # bands computed from value
bb.electrolytic((14, "i"), ("B-", 14))      # stripe faces the neg lead
bb.led((15, "h"), (18, "h"))
bb.supply(("T+", 2), "+", label="+5 V", side="left")
bb.pill("10K", x, y, leader_to=(x2, y2))    # px; get px from bb.hole(...)
bb.save("figure.svg")
```

Holes: `(col, row)` with rows `a`-`e` above the trench, `f`-`j` below;
rails are `('T+'|'T-'|'B+'|'B-', col)` (+ row beside the red stripe).
For a DIP at `col`, top pins are 8-7-6-5 on `col..col+3` row `e`,
bottom pins 1-2-3-4 row `f`. Rail holes skip every 6th column
(`bb.rail_skip`) — never land a wire there.

## Rules that make it look right

- Wire color is meaning: red = positive, blue = ground, yellow/green =
  signal. White pill callouts carry component values.
- Wires lie flat: use `route()` with orthogonal segments around
  components. At most ONE curved `jumper(arc=...)` hop over a chip per
  figure, and only when a flat route is impossible.
- Nothing may cross a component or another wire (thin pill leader
  lines excepted). Plan hole rows so verticals and horizontals miss
  each other; `bb.xy()` waypoints may sit between columns.
- Resistor endpoints must be ≥ 2 pitches apart (constant 28px body
  needs room); diagonal placement is period-correct.
- `with bb.ghost():` draws a previous build stage pale; new parts keep
  full color.

## Schematic quick start

```python
from plattfig import Schematic
sc = Schematic(74, 44)                      # canvas in 10px grid units
pins = sc.dip(23.9, 16, "555")              # returns {pin: (x, y)} stub tips
sc.wire([(8, 5), (46, 5), pins["4"]], role="pos")   # 'pos' red, 'neg' blue, 'sig' ink
sc.dot(25, 5, "pos")                        # junction; crossings w/o dot = not connected
sc.resistor(30, 5, orient="v", length=6)
sc.cap(30, 34, polar=True)
sc.led(35, 29); sc.ground(20, 41); sc.supply_plus(8, 5, label="+5 V")
sc.table(51, 8, "Components", [("R1", "Timing, 10K")])
sc.save("schematic.svg")
```

Keep the schematic's layout mirroring the breadboard (same pin order,
supply top, ground bottom) so the pair teaches together.

## Verify before shipping

Always rasterize and LOOK at the result; fix collisions and rerun:

```bash
qlmanage -t -s 1600 -o /tmp figure.svg   # macOS
rsvg-convert -w 1600 figure.svg -o /tmp/figure.png  # if available
```

Check: nothing overlaps, every wire end shows its stripped tip in a
hole, callouts don't cover components, µ/Ω render correctly.
