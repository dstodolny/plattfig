"""Ghosting: the previous build stage drawn pale and desaturated so the
new additions carry the color — the device Platt uses when a circuit
grows across figures.
"""

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from plattfig import Breadboard, WIRE_RED

bb = Breadboard(cols=30)

# everything already built in the previous figure
with bb.ghost():
    bb.ic(13, "555")
    bb.jumper((13, "a"), ("T+", 13), color=WIRE_RED)
    bb.resistor(("T+", 14), (14, "a"), "10k")
    bb.electrolytic((14, "i"), ("B-", 14))

# this figure's additions, in full color
bb.jumper((20, "a"), ("T+", 20), color=WIRE_RED)
bb.resistor((20, "b"), (22, "d"), "2.2k")
bb.pill("2.2K", bb.hole(24, "b")[0], bb.hole(24, "b")[1],
        leader_to=(bb.hole(21, "c")[0] + 6, bb.hole(21, "c")[1]))

out = pathlib.Path(__file__).parent / "output" / "ghost-stage.svg"
print(bb.save(str(out)))
