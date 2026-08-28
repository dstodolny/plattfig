"""The classic 555 astable on a half-size breadboard.

DIP-8 at columns 13-16, notch left:
  top row (block a-e):  8=13  7=14  6=15  5=16
  bottom row (f-j):     1=13  2=14  3=15  4=16

Routing rules: wires lie flat on the board and go around components
(route() with waypoints). One deliberate hop over the chip is allowed
per figure; here it is the green wire tying pins 6 and 2.
"""

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from plattfig import Breadboard, WIRE_RED, WIRE_BLUE, WIRE_GREEN

bb = Breadboard(cols=30)

bb.ic(13, "555")

# power: pin 8 straight up to T+; pin 4 right along row g, then up
# between columns 18 and 19 to T+; pin 1 down to B-
bb.jumper((13, "a"), ("T+", 13), color=WIRE_RED)
bb.route([(16, "g"), bb.xy(18.5, "g"), bb.xy(18.5, "T+"), ("T+", 19)],
         color=WIRE_RED)
bb.jumper((13, "g"), ("B-", 13), color=WIRE_BLUE)

# timing network
bb.resistor(("T+", 14), (14, "a"), "10k")          # R1: red rail -> pin 7 column
bb.resistor((14, "c"), (15, "a"), "10k")           # R2: pin 7 -> pin 6 column
bb.jumper((15, "d"), (14, "g"), color=WIRE_GREEN, arc=26)  # tie pins 6 and 2
bb.electrolytic((14, "i"), ("B-", 14))             # 10 uF, stripe toward ground

# output indicator: pin 3 -> LED -> 330 R -> blue rail
bb.led((15, "h"), (18, "h"))
bb.resistor((18, "i"), ("B-", 19), "330")

# supply leads and scope probes
bb.supply(("T+", 2), "+", label="+5 V", side="left")
bb.supply(("B-", 2), "-", label="GND", side="left")
bb.probe((14, "h"), "CH2", dx=-46, dy=6)
bb.probe((15, "j"), "CH1", dx=30, dy=22)

# callouts
bb.pill("10K", bb.hole(16, "a")[0] + 26, bb.hole(16, "a")[1] - 34,
        leader_to=(bb.hole(14, "a")[0] + 8, bb.hole(14, "a")[1] - 30))
bb.pill("10K", bb.hole(17, "b")[0] + 6, bb.hole(17, "b")[1] + 2,
        leader_to=(bb.hole(15, "b")[0] - 6, bb.hole(15, "b")[1] - 2))
bb.pill("10µF", bb.hole(11, "j")[0] - 6, bb.hole(11, "j")[1] + 10,
        leader_to=(bb.hole(14, "j")[0] - 12, bb.hole(14, "j")[1] + 8))
bb.pill("330", bb.hole(21, "i")[0] + 8, bb.hole(21, "i")[1] + 14,
        leader_to=(bb.hole(18, "j")[0] + 8, bb.hole(18, "j")[1] + 4))

out = pathlib.Path(__file__).parent / "output" / "astable-breadboard.svg"
print(bb.save(str(out)))
