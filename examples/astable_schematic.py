"""The same 555 astable as a semi-physical schematic.

The DIP keeps its physical pin order (notch left, 8-7-6-5 across the
top, 1-2-3-4 across the bottom) so the schematic mirrors the breadboard
drawing. Coordinates are 10px grid units.
"""

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from plattfig import Schematic

sc = Schematic(74, 44)

pins = sc.dip(23.9, 16, "555")
p8, p7, p6, p5 = pins["8"], pins["7"], pins["6"], pins["5"]
p1, p2, p3, p4 = pins["1"], pins["2"], pins["3"], pins["4"]

# positive rail: supply -> along the top, down the right side to RESET
sc.supply_plus(8, 5, label="+5 V")
sc.wire([(8, 5), (46, 5), (46, 27), (40, 27), p4], role="pos")
sc.wire([(25, 5), p8], role="pos")           # pin 8, VCC
sc.dot(25, 5, "pos")
sc.dot(30, 5, "pos")

# timing: R1 from the rail down to pin 7, R2 across to pin 6
sc.resistor(30, 5, orient="v", length=6)     # R1
sc.wire([(30, 11), p7])
sc.resistor(30, 13, orient="h", length=5)    # R2
sc.dot(30, 13)
sc.wire([(35, 13), p6])
sc.dot(35, 13)

# trigger tied to threshold, around the right of the chip, down to the cap
sc.wire([(35, 13), (43.2, 13), (43.2, 31), (30, 31), p2])
sc.dot(30, 31)
sc.cap(30, 34, orient="v", polar=True)       # 10 uF, plus side up
sc.wire([(30, 35), (30, 38)])

# output: pin 3 -> LED -> 330 -> ground rail
sc.wire([p3, (35, 28.3)])
sc.led(35, 29)
sc.wire([(35, 29.6), (35, 31.8)])
sc.resistor(35, 31.8, orient="v", length=5)  # 330
sc.wire([(35, 36.8), (35, 38)])

# ground rail
sc.wire([(20, 38), (41, 38)], role="neg")
sc.wire([p1, (25, 38)], role="neg")
sc.wire([(20, 38), (20, 41)], role="neg")
sc.ground(20, 41)
sc.dot(25, 38, "neg")
sc.dot(30, 38, "neg")
sc.dot(35, 38, "neg")
sc.text("GND", 17.6, 41.6, size=12, bold=True, anchor="end")

# labels
sc.pill("R1", 33.5, 7.5, leader_to=(30.6, 8))
sc.pill("R2", 38.8, 10.8, leader_to=(34, 12.6))
sc.pill("C1", 26.3, 35.2, leader_to=(28.6, 34.6))
sc.pill("R3", 38.8, 33.5, leader_to=(35.4, 33.6))
sc.pill("IC1", 45.8, 20.5, leader_to=(41, 20.5))

# components table
sc.table(51, 8, "Components", [
    ("R1", "Timing, 10K"),
    ("R2", "Timing, 10K"),
    ("R3", "Current limiting, 330 ohms"),
    ("C1", "Timing, 10µF electrolytic"),
    ("IC1", "555 timer"),
])

out = pathlib.Path(__file__).parent / "output" / "astable-schematic.svg"
print(sc.save(str(out)))
