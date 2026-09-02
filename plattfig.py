"""plattfig — breadboard and schematic illustrations as code.

Inspired by Charles Platt's illustrations in "Make: Electronics"
(O'Reilly / Make Community). Not affiliated with or endorsed by
Charles Platt or Make:.

Two renderers, both emitting standalone SVG from a few lines of Python:

  Breadboard  — flat top-down vector board: gray body with beveled
                square sockets, blue/red rail stripes, components drawn
                as flat color (routed jumpers with stripped tips, banded
                resistors, top-view caps and LEDs, black DIP ICs with
                visible legs), white pill callouts, off-board supply
                leads, scope-probe hooks.

  Schematic   — the semi-physical companion drawing: the IC as a gray
                DIP outline with pin numbers in physical order (not an
                abstract block), red wires for the positive supply,
                blue for ground, ink for signal, junction dots, pill
                labels, a components table.

Both support ghost() groups: a previous build stage rendered pale and
desaturated so the new additions carry the color.

Pure Python, no dependencies. See README.md and examples/.
"""

# ---------------------------------------------------------------- palette

INK = "#254a49"          # outline and label ink (deep teal; swap for your own)
WIRE_RED = "#a83226"     # positive supply
WIRE_BLUE = "#3d6ea8"    # ground / negative
WIRE_YELLOW = "#d9a520"  # signal jumpers
WIRE_GREEN = "#2e6b4f"   # signal jumpers (alt)
WIRE_MAGENTA = "#b5338f" # signal jumpers (alt); scope CH2 on Siglent/Rigol
WIRE_GRAY = "#8a9491"    # neutral jumper
LEAD = "#ffffff"         # component lead wire (white, dark-outlined)
LEAD_EDGE = "#3f4a49"    # lead outline

BOARD = "#ebebe8"        # breadboard body
BOARD_EDGE = "#c9c9c5"
TRENCH = "#dcdcd8"
SOCKET_RIM = "#f7f7f5"
SOCKET_WALL = "#a9a9a5"
SOCKET_HOLE = "#7c7c78"
STRIPE_RED = "#c4707f"
STRIPE_BLUE = "#7fa8c4"

RESISTOR_BODY = "#e6d5ae"
IC_BODY = "#3a3a3a"
IC_BODY_SCH = "#8f9694"

FONT = "Helvetica Neue, Helvetica, Arial, sans-serif"

BAND_COLORS = {
    0: "#1a1a1a", 1: "#6b4226", 2: "#b03024", 3: "#d97b1f", 4: "#e0c02e",
    5: "#3f7d3a", 6: "#3558a8", 7: "#7d3a9e", 8: "#8a8a8a", 9: "#f2f2f2",
}
BAND_GOLD = "#c9a227"


def _esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def resistor_bands(value):
    """'10k' -> band colors for 2 significant digits + multiplier."""
    v = str(value).lower().replace("Ω", "").replace("ohm", "").strip()
    mult = 1.0
    if v.endswith("m"):
        mult, v = 1e6, v[:-1]
    elif v.endswith("k"):
        mult, v = 1e3, v[:-1]
    ohms = float(v) * mult
    import math
    exp = int(math.floor(math.log10(ohms))) - 1
    sig = int(round(ohms / 10 ** exp))
    d1, d2 = sig // 10, sig % 10
    return [BAND_COLORS[d1], BAND_COLORS[d2], BAND_COLORS[exp]]


class _Canvas:
    """Shared SVG assembly: layered element lists plus ghost groups."""

    def __init__(self):
        self._under = []    # board / background
        self._parts = []    # components and wires
        self._over = []     # callouts, labels, probes
        self._ghosting = False
        self._ghost_parts = []

    def _emit(self, s, layer="parts"):
        if self._ghosting and layer == "parts":
            self._ghost_parts.append(s)
        else:
            {"under": self._under, "parts": self._parts,
             "over": self._over}[layer].append(s)

    # -- ghost stage -------------------------------------------------

    def ghost(self):
        """Context manager: parts drawn inside render pale and gray."""
        canvas = self

        class _G:
            def __enter__(self):
                canvas._ghosting = True

            def __exit__(self, *a):
                canvas._ghosting = False
        return _G()

    def _defs(self):
        return ('<filter id="ghost"><feColorMatrix type="saturate" values="0.05"/>'
                '</filter>')

    def _body(self):
        out = list(self._under)
        if self._ghost_parts:
            out.append('<g filter="url(#ghost)" opacity="0.32">')
            out.extend(self._ghost_parts)
            out.append('</g>')
        out.extend(self._parts)
        out.extend(self._over)
        return out

    # -- shared decorations ------------------------------------------

    def pill(self, text, x, y, leader_to=None, font_size=11, stroke=None):
        """White stadium callout with ink outline, centered on (x, y)."""
        w = max(26, 7.2 * len(str(text)) + 12)
        h = font_size + 9
        parts = []
        if leader_to:
            parts.append('<line x1="%g" y1="%g" x2="%g" y2="%g" stroke="%s" '
                         'stroke-width="1.2"/>' % (x, y, leader_to[0], leader_to[1], INK))
        parts.append('<rect x="%g" y="%g" width="%g" height="%g" rx="%g" '
                     'fill="#ffffff" stroke="%s" stroke-width="%g"/>'
                     % (x - w / 2, y - h / 2, w, h, h / 2, stroke or INK,
                        2.2 if stroke else 1.4))
        parts.append('<text x="%g" y="%g" font-family="%s" font-size="%g" '
                     'fill="%s" text-anchor="middle">%s</text>'
                     % (x, y + font_size * 0.34, FONT, font_size, INK, _esc(text)))
        self._emit("".join(parts), "over")

    def text(self, s, x, y, size=12, anchor="middle", bold=False, color=INK):
        self._emit('<text x="%g" y="%g" font-family="%s" font-size="%g" fill="%s" '
                   'text-anchor="%s"%s>%s</text>'
                   % (x, y, FONT, size, color, anchor,
                      ' font-weight="bold"' if bold else "", _esc(s)), "over")


# ================================================================ breadboard


class Breadboard(_Canvas):
    """Half-size board by default (30 columns). Holes are addressed as
    (col, row) with rows 'a'-'e' above the trench and 'f'-'j' below,
    or ('T+'|'T-'|'B+'|'B-', col) for the rails."""

    PITCH = 18
    PAD_X = 40
    PAD_TOP = 8

    def __init__(self, cols=30, margin=56):
        super().__init__()
        self.cols = cols
        self.margin = margin  # blank canvas border around the board
        p, top = self.PITCH, self.PAD_TOP
        self.rail_skip = set(range(6, cols + 1, 6))  # rail hole gaps
        # vertical layout (board-local y)
        self.y_stripe_tb = top + 6            # top blue stripe
        self.y_rail_tm = top + 22             # T- row
        self.y_rail_tp = self.y_rail_tm + p   # T+ row
        self.y_stripe_tr = self.y_rail_tp + 14
        self.rows_top = {r: self.y_stripe_tr + 26 + i * p
                         for i, r in enumerate("abcde")}
        self.y_trench0 = self.rows_top["e"] + 13
        self.y_trench1 = self.y_trench0 + 22
        self.rows_bot = {r: self.y_trench1 + 13 + i * p
                         for i, r in enumerate("fghij")}
        self.y_stripe_bb = self.rows_bot["j"] + 26
        self.y_rail_bm = self.y_stripe_bb + 16  # B- row
        self.y_rail_bp = self.y_rail_bm + p     # B+ row
        self.y_stripe_br = self.y_rail_bp + 14
        self.board_h = self.y_stripe_br + 8
        self.board_w = 2 * self.PAD_X + (cols - 1) * p
        self.W = self.board_w + 2 * self.margin
        self.H = self.board_h + 2 * self.margin
        self._draw_board()

    # -- geometry ----------------------------------------------------

    def hole(self, a, b=None):
        """hole(col, 'c') or hole('T+', col) -> canvas (x, y)."""
        if isinstance(a, str):
            rail, col = a, b
            y = {"T+": self.y_rail_tp, "T-": self.y_rail_tm,
                 "B+": self.y_rail_bp, "B-": self.y_rail_bm}[rail]
        else:
            col, row = a, b
            y = self.rows_top.get(row) or self.rows_bot[row]
        x = self.PAD_X + (col - 1) * self.PITCH
        return (x + self.margin, y + self.margin)

    # -- board -------------------------------------------------------

    def _socket(self, x, y):
        return ('<g transform="translate(%g,%g)">'
                '<rect x="-5.5" y="-5.5" width="11" height="11" rx="1" fill="%s"/>'
                '<rect x="-4" y="-4" width="8.5" height="8.5" fill="%s"/>'
                '<rect x="-2.6" y="-2.6" width="5.2" height="5.2" fill="%s"/>'
                '</g>' % (x, y, SOCKET_RIM, SOCKET_WALL, SOCKET_HOLE))

    def _draw_board(self):
        m = self.margin
        b = []
        b.append('<rect x="%g" y="%g" width="%g" height="%g" rx="6" fill="%s" '
                 'stroke="%s" stroke-width="1.5"/>'
                 % (m, m, self.board_w, self.board_h, BOARD, BOARD_EDGE))
        b.append('<rect x="%g" y="%g" width="%g" height="%g" fill="%s"/>'
                 % (m + 2, m + self.y_trench0, self.board_w - 4,
                    self.y_trench1 - self.y_trench0, TRENCH))
        for y0 in (self.y_trench0, self.y_trench1):
            b.append('<line x1="%g" y1="%g" x2="%g" y2="%g" stroke="%s" '
                     'stroke-width="1"/>' % (m + 2, m + y0, m + self.board_w - 2,
                                             m + y0, BOARD_EDGE))
        for y, c in ((self.y_stripe_tb, STRIPE_BLUE), (self.y_stripe_tr, STRIPE_RED),
                     (self.y_stripe_bb, STRIPE_BLUE), (self.y_stripe_br, STRIPE_RED)):
            b.append('<line x1="%g" y1="%g" x2="%g" y2="%g" stroke="%s" '
                     'stroke-width="3.5"/>' % (m + 14, m + y, m + self.board_w - 14,
                                               m + y, c))
        holes = []
        for col in range(1, self.cols + 1):
            x = m + self.PAD_X + (col - 1) * self.PITCH
            if col not in self.rail_skip:
                for y in (self.y_rail_tm, self.y_rail_tp,
                          self.y_rail_bm, self.y_rail_bp):
                    holes.append(self._socket(x, m + y))
            for rows in (self.rows_top, self.rows_bot):
                for y in rows.values():
                    holes.append(self._socket(x, m + y))
        self._emit("".join(b) + "".join(holes), "under")

    # -- components --------------------------------------------------

    def xy(self, colf, key):
        """Free point on the board: fractional column + row/rail letter.
        Use for route() waypoints that sit between holes."""
        x = self.PAD_X + (colf - 1) * self.PITCH + self.margin
        if isinstance(key, str) and key in ("T+", "T-", "B+", "B-"):
            y = self.hole(key, 1)[1]
        else:
            y = self.hole(1, key)[1]
        return (x, y)

    def route(self, points, color=WIRE_YELLOW, tip=3.5, r=8):
        """Insulated wire routed flat over the board through waypoints,
        with rounded corners. First and last items are hole addresses;
        middle items may be hole addresses or raw (x, y) canvas points
        (see xy()). Stripped bare tips show at both ends."""
        pts = []
        for p in points:
            if isinstance(p[0], str) or isinstance(p[1], str):
                pts.append(self.hole(*p))
            else:
                pts.append(p)
        import math
        q0 = self._toward(pts[0], pts[1], tip)
        q1 = self._toward(pts[-1], pts[-2], tip)
        inner = [q0] + pts[1:-1] + [q1]
        d = ['M %g %g' % inner[0]]
        for i in range(1, len(inner) - 1):
            A, B, C = inner[i - 1], inner[i], inner[i + 1]
            rr = min(r, math.hypot(B[0] - A[0], B[1] - A[1]) / 2,
                     math.hypot(C[0] - B[0], C[1] - B[1]) / 2)
            e = self._toward(B, A, rr)
            x = self._toward(B, C, rr)
            d.append('L %g %g Q %g %g %g %g' % (e[0], e[1], B[0], B[1], x[0], x[1]))
        d.append('L %g %g' % inner[-1])
        path = " ".join(d)
        self._emit(self._lead(pts[0], self._toward(pts[0], pts[1], tip + 2)) +
                   self._lead(pts[-1], self._toward(pts[-1], pts[-2], tip + 2)) +
                   '<path d="%s" fill="none" stroke="%s" stroke-width="7.5" '
                   'stroke-linecap="round" stroke-linejoin="round" opacity="0.35"/>'
                   '<path d="%s" fill="none" stroke="%s" stroke-width="5.5" '
                   'stroke-linecap="round" stroke-linejoin="round"/>'
                   % (path, INK, path, color))

    @staticmethod
    def _toward(p, q, dist):
        """Point `dist` px from p along the line p->q."""
        import math
        L = max(math.hypot(q[0] - p[0], q[1] - p[1]), 1e-6)
        return (p[0] + (q[0] - p[0]) * dist / L, p[1] + (q[1] - p[1]) * dist / L)

    def jumper(self, a, b, color=WIRE_YELLOW, arc=0.0, tip=3.5):
        """Insulated wire between holes; arc>0 bows it (positive = right of
        the travel direction). A stripped bare tip shows at each end."""
        p0, p1 = self.hole(*a), self.hole(*b)
        (x0, y0), (x1, y1) = p0, p1
        if arc:
            import math
            mx, my = (x0 + x1) / 2, (y0 + y1) / 2
            dx, dy = x1 - x0, y1 - y0
            L = max(math.hypot(dx, dy), 1)
            c = (mx - dy / L * arc, my + dx / L * arc)
        else:
            c = None
        # insulation stops short of the holes; bare tips cover the rest
        q0 = self._toward(p0, c or p1, tip)
        q1 = self._toward(p1, c or p0, tip)
        if c:
            d = 'M %g %g Q %g %g %g %g' % (q0[0], q0[1], c[0], c[1], q1[0], q1[1])
        else:
            d = 'M %g %g L %g %g' % (q0[0], q0[1], q1[0], q1[1])
        self._emit(self._lead(p0, self._toward(p0, c or p1, tip + 2)) +
                   self._lead(p1, self._toward(p1, c or p0, tip + 2)) +
                   '<path d="%s" fill="none" stroke="%s" stroke-width="7.5" '
                   'stroke-linecap="round" opacity="0.35"/>'
                   '<path d="%s" fill="none" stroke="%s" stroke-width="5.5" '
                   'stroke-linecap="round"/>' % (d, INK, d, color))

    def _polarity_mark(self, p0, p1, sign="+", size=5, side=1):
        """Polarity mark beside the lead end p0 of a p0->p1 part, Platt
        style: a red "+" or a blue "-", ringed by a thin white line and
        a dark outline. Offset to the left of the travel direction and
        nudged a little outward so it clears the socket."""
        import math
        dx, dy = p1[0] - p0[0], p1[1] - p0[1]
        L = max(math.hypot(dx, dy), 1)
        px = p0[0] + side * dy / L * 12 - dx / L * 3
        py = p0[1] - side * dx / L * 12 - dy / L * 3
        d = "M %g %g H %g" % (px - size, py, px + size)
        if sign == "+":
            d += " M %g %g V %g" % (px, py - size, py + size)
        color = WIRE_RED if sign == "+" else WIRE_BLUE
        return "".join(
            '<path d="%s" stroke="%s" stroke-width="%g" stroke-linecap="round" fill="none"/>'
            % (d, c, w) for c, w in ((LEAD_EDGE, 7.4), (LEAD, 5.0), (color, 2.6)))

    def _lead(self, p0, p1):
        """Component lead: white wire with a dark outline, Platt-style."""
        seg = 'x1="%g" y1="%g" x2="%g" y2="%g"' % (p0[0], p0[1], p1[0], p1[1])
        return ('<line %s stroke="%s" stroke-width="4.6" stroke-linecap="round"/>'
                '<line %s stroke="%s" stroke-width="2.4" stroke-linecap="round"/>'
                % (seg, LEAD_EDGE, seg, LEAD))

    def resistor(self, a, b, value):
        p0, p1 = self.hole(*a), self.hole(*b)
        (x0, y0), (x1, y1) = p0, p1
        import math
        L = math.hypot(x1 - x0, y1 - y0)
        body_l = 28.0  # every body identical; only the leads vary
        ang = math.degrees(math.atan2(y1 - y0, x1 - x0))
        s = [self._lead(p0, p1)]
        s.append('<g transform="translate(%g,%g) rotate(%g)">'
                 % ((x0 + x1) / 2, (y0 + y1) / 2, ang))
        s.append('<rect x="%g" y="-6" width="%g" height="12" rx="5" fill="%s" '
                 'stroke="%s" stroke-width="1.2"/>'
                 % (-body_l / 2, body_l, RESISTOR_BODY, INK))
        bands = resistor_bands(value) + [BAND_GOLD]
        xs = [-body_l / 2 + body_l * f for f in (0.16, 0.34, 0.52, 0.82)]
        for bx, bc in zip(xs, bands):
            s.append('<rect x="%g" y="-5.4" width="3.2" height="10.8" fill="%s"/>'
                     % (bx - 1.6, bc))
        s.append('</g>')
        self._emit("".join(s))

    def electrolytic(self, pos, neg, r=13, polarity=True):
        """Top view: dark sleeve, aluminum top with vent score, white
        negative stripe on the sleeve toward the `neg` lead. With
        polarity=True a blue "-" sits beside the negative lead as well, the
        way Platt marks electrolytics."""
        p0, p1 = self.hole(*pos), self.hole(*neg)
        cx, cy = (p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2
        import math
        ang = math.degrees(math.atan2(p1[1] - p0[1], p1[0] - p0[0]))
        s = [self._lead(p0, p1)]
        if polarity:
            s.append(self._polarity_mark(p1, p0, "-", side=-1))
        s.append('<g transform="translate(%g,%g) rotate(%g)">' % (cx, cy, ang))
        s.append('<circle r="%g" fill="#38464a" stroke="%s" stroke-width="1.3"/>' % (r, INK))
        # negative stripe: sleeve wedge on the +x side (toward `neg`)
        s.append('<path d="M %g %g A %g %g 0 0 1 %g %g L %g %g A %g %g 0 0 0 %g %g Z" '
                 'fill="#f2f2ef"/>'
                 % (r * 0.42, -r * 0.9, r, r, r * 0.42, r * 0.9,
                    r * 0.31, r * 0.66, r * 0.72, r * 0.72, r * 0.31, -r * 0.66))
        s.append('<circle r="%g" fill="#b3bab8" stroke="#5a676b" stroke-width="1"/>'
                 % (r * 0.66))
        s.append('<path d="M %g 0 H %g M 0 %g V %g" stroke="#8a9290" '
                 'stroke-width="1.4"/>' % (-r * 0.5, r * 0.5, -r * 0.5, r * 0.5))
        s.append('<text x="%g" y="3" font-family="%s" font-size="8.5" fill="#38464a" '
                 'text-anchor="middle" font-weight="bold">−</text>' % (r * 0.86, FONT))
        s.append('</g>')
        self._emit("".join(s))

    def led(self, anode, cathode, color="#cc2b1f", r=11, polarity=True):
        """Top view. With polarity=True a red "+" sits beside the anode
        lead, on the side away from the body, so the longer leg is
        unambiguous at a glance."""
        p0, p1 = self.hole(*anode), self.hole(*cathode)
        cx, cy = (p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2
        s = [self._lead(p0, p1)]
        if polarity:
            s.append(self._polarity_mark(p0, p1))
        s.append('<circle cx="%g" cy="%g" r="%g" fill="%s" stroke="%s" '
                 'stroke-width="1.6"/>' % (cx, cy, r, color, INK))
        s.append('<circle cx="%g" cy="%g" r="%g" fill="#e8695c"/>'
                 % (cx - r * 0.22, cy - r * 0.25, r * 0.42))
        s.append('<circle cx="%g" cy="%g" r="%g" fill="#ffffff" opacity="0.8"/>'
                 % (cx - r * 0.32, cy - r * 0.38, r * 0.2))
        self._emit("".join(s))

    def ic(self, col, label, cols_wide=4):
        """DIP straddling the trench, notch on the left, top-row pins
        col..col+cols_wide-1 = pins 2n..n+1, bottom row = 1..n. Body is
        wide and flat (about 2:1) with visible silver legs reaching the
        hole rows, like Platt draws them."""
        x0, y_e = self.hole(col, "e")
        x1, _ = self.hole(col + cols_wide - 1, "e")
        _, y_f = self.hole(col, "f")
        ytop = y_e + 4        # body edge sits just past the leg holes
        ybot = y_f - 4
        bx0, bx1 = x0 - 12, x1 + 12
        s = []
        for c in range(col, col + cols_wide):
            px, _ = self.hole(c, "e")
            for y0, dy in ((y_e, ytop - y_e + 2), (y_f, ybot - y_f - 2)):
                s.append('<path d="M %g %g v %g" stroke="%s" stroke-width="8" '
                         'stroke-linecap="round"/>' % (px, y0, dy, LEAD_EDGE))
                s.append('<path d="M %g %g v %g" stroke="%s" stroke-width="5" '
                         'stroke-linecap="round"/>' % (px, y0, dy, LEAD))
        s.append('<rect x="%g" y="%g" width="%g" height="%g" rx="3.5" fill="%s" '
                 'stroke="#1c1c1c" stroke-width="1.2"/>'
                 % (bx0, ytop, bx1 - bx0, ybot - ytop, IC_BODY))
        cyc = (ytop + ybot) / 2
        s.append('<path d="M %g %g A 6.5 6.5 0 0 1 %g %g Z" fill="#5a5a5a"/>'
                 % (bx0, cyc - 6.5, bx0, cyc + 6.5))
        s.append('<circle cx="%g" cy="%g" r="2.2" fill="#d8d8d6"/>'
                 % (bx0 + 9, ybot - 7))
        s.append('<text x="%g" y="%g" font-family="%s" font-size="13" '
                 'fill="#e3bd58" text-anchor="middle" font-weight="bold" '
                 'letter-spacing="1.5">%s</text>'
                 % ((bx0 + bx1) / 2, cyc + 4.5, FONT, _esc(label)))
        self._emit("".join(s))

    def supply(self, rail_hole, kind="+", label=None, side="left", color=None):
        """Off-board supply lead ending in a plug circle at the canvas edge."""
        color = color or (WIRE_RED if kind == "+" else WIRE_BLUE)
        hx, hy = self.hole(*rail_hole)
        ex = self.margin - 26 if side == "left" else self.W - self.margin + 26
        tip = 3.5 if side == "left" else -3.5
        d = 'M %g %g L %g %g' % (ex, hy, hx - tip, hy)
        s = [self._lead((hx, hy), (hx - tip - (2 if side == "left" else -2), hy))]
        s.append('<path d="%s" stroke="%s" stroke-width="7.5" stroke-linecap="round" '
                 'opacity="0.35" fill="none"/>' % (d, INK))
        s.append('<path d="%s" stroke="%s" stroke-width="5.5" '
                 'stroke-linecap="round" fill="none"/>' % (d, color))
        s.append('<circle cx="%g" cy="%g" r="8" fill="%s" stroke="%s" '
                 'stroke-width="1.4"/>' % (ex, hy, color, INK))
        if kind == "+":
            s.append('<path d="M %g %g h 8 M %g %g v 8" stroke="#ffffff" '
                     'stroke-width="2"/>' % (ex - 4, hy, ex, hy - 4))
        self._emit("".join(s))
        if label:
            self.text(label, ex, hy - 16, size=13, anchor="middle", bold=True)

    def probe(self, hole, label, dx=0, dy=30, color=None):
        """Scope-probe hook: small hook glyph on the hole plus a pill.
        `color` tints the hook and the pill outline to match the scope's
        channel color (Siglent/Rigol: CH1 yellow, CH2 magenta)."""
        hx, hy = self.hole(*hole)
        c = color or INK
        s = ['<circle cx="%g" cy="%g" r="6" fill="none" stroke="%s" '
             'stroke-width="4.6"/>' % (hx, hy, INK),
             '<circle cx="%g" cy="%g" r="6" fill="none" stroke="%s" '
             'stroke-width="2.6"/>' % (hx, hy, c)]
        self._emit("".join(s), "over")
        self.pill(label, hx + dx, hy + dy,
                  leader_to=(hx, hy + 6) if (dx or dy > 24) else None,
                  stroke=color)

    # -- output ------------------------------------------------------

    def svg(self):
        head = ('<?xml version="1.0" encoding="UTF-8"?>'
                '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %g %g" '
                'font-family="%s">' % (self.W, self.H, FONT))
        return head + "<defs>" + self._defs() + "</defs>" + "".join(self._body()) + "</svg>"

    def save(self, path):
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.svg())
        return path


# ================================================================ schematic


class Schematic(_Canvas):
    """Semi-physical schematic on a 10px grid. Coordinates in the spec
    are grid units; wire roles pick the Platt colors."""

    G = 10
    ROLE = {"pos": WIRE_RED, "neg": WIRE_BLUE, "sig": INK}

    def __init__(self, w, h):
        super().__init__()
        self.W, self.H = w * self.G, h * self.G
        self._emit('<rect x="0" y="0" width="%g" height="%g" fill="#ffffff"/>'
                   % (self.W, self.H), "under")

    def _xy(self, x, y):
        return (x * self.G, y * self.G)

    def wire(self, points, role="sig", width=2.2):
        pts = [self._xy(*p) for p in points]
        d = "M " + " L ".join("%g %g" % p for p in pts)
        self._emit('<path d="%s" fill="none" stroke="%s" stroke-width="%g" '
                   'stroke-linejoin="round"/>' % (d, self.ROLE[role], width))

    def dot(self, x, y, role="sig"):
        px, py = self._xy(x, y)
        self._emit('<circle cx="%g" cy="%g" r="3.4" fill="%s"/>'
                   % (px, py, self.ROLE[role]))

    def resistor(self, x, y, orient="v", length=6, role="sig"):
        """Zigzag from (x, y) extending `length` grid units right or down."""
        px, py = self._xy(x, y)
        L = length * self.G
        n, amp = 6, 5.5
        step = L * 0.6 / n
        lead = L * 0.2
        pts = [(0, 0), (lead, 0)]
        for i in range(n):
            pts.append((lead + step * (i + 0.5), amp if i % 2 == 0 else -amp))
        pts.append((lead + step * n, 0))
        pts.append((L, 0))
        d = "M " + " L ".join("%g %g" % p for p in pts)
        rot = "rotate(90)" if orient == "v" else ""
        self._emit('<g transform="translate(%g,%g) %s"><path d="%s" fill="none" '
                   'stroke="%s" stroke-width="2.2" stroke-linejoin="round"/></g>'
                   % (px, py, rot, d, self.ROLE[role]))

    def cap(self, x, y, orient="v", polar=False, role="sig"):
        """Two plates centered on (x, y); wire up to the plates yourself.
        Occupies 1 grid unit across the gap, plates 2.4 units long."""
        px, py = self._xy(x, y)
        g = self.G
        c = self.ROLE[role]
        s = ['<g transform="translate(%g,%g)%s">'
             % (px, py, ' rotate(90)' if orient == "h" else "")]
        s.append('<line x1="-12" y1="-4" x2="12" y2="-4" stroke="%s" '
                 'stroke-width="2.6"/>' % c)
        if polar:
            s.append('<path d="M -12 6 Q 0 1.5 12 6" fill="none" stroke="%s" '
                     'stroke-width="2.6"/>' % c)
            s.append('<path d="M -19 -9 h 7 M -15.5 -12.5 v 7" stroke="%s" '
                     'stroke-width="1.8"/>' % c)
        else:
            s.append('<line x1="-12" y1="4" x2="12" y2="4" stroke="%s" '
                     'stroke-width="2.6"/>' % c)
        s.append('<line x1="0" y1="%g" x2="0" y2="-4" stroke="%s" stroke-width="2.2"/>'
                 % (-g, c))
        s.append('<line x1="0" y1="%g" x2="0" y2="%g" stroke="%s" stroke-width="2.2"/>'
                 % (g, 4 if not polar else 4, c))
        s.append('</g>')
        self._emit("".join(s))

    def led(self, x, y, orient="v", role="sig"):
        """Diode-with-arrows symbol centered on (x, y), pointing down/right."""
        import math
        px, py = self._xy(x, y)
        c = self.ROLE[role]
        s = ['<g transform="translate(%g,%g)%s">'
             % (px, py, ' rotate(-90)' if orient == "h" else "")]
        s.append('<polygon points="-8,-7 8,-7 0,6" fill="%s"/>' % c)
        s.append('<line x1="-8" y1="6" x2="8" y2="6" stroke="%s" stroke-width="2.6"/>' % c)
        # Emission arrows: 45-degree shafts with heads computed on the same
        # axis, so the points line up with the shafts.
        u = 1 / math.sqrt(2)
        for dx in (10, 15):
            x0, y0 = dx, -3.4
            tip = (x0 + 11 * u, y0 + 11 * u)
            base = (x0 + 6.5 * u, y0 + 6.5 * u)
            s.append('<line x1="%g" y1="%g" x2="%g" y2="%g" stroke="%s" '
                     'stroke-width="1.8"/>' % (x0, y0, base[0], base[1], c))
            s.append('<polygon points="%g,%g %g,%g %g,%g" fill="%s"/>'
                     % (round(tip[0], 2), round(tip[1], 2),
                        round(base[0] - 2.3 * u, 2), round(base[1] + 2.3 * u, 2),
                        round(base[0] + 2.3 * u, 2), round(base[1] - 2.3 * u, 2), c))
        s.append('</g>')
        self._emit("".join(s))

    def ground(self, x, y, role="neg"):
        px, py = self._xy(x, y)
        c = self.ROLE[role]
        self._emit('<g transform="translate(%g,%g)">'
                   '<line x1="-11" y1="0" x2="11" y2="0" stroke="%s" stroke-width="3"/>'
                   '<line x1="-11" y1="6" x2="11" y2="6" stroke="%s" stroke-width="3"/>'
                   '</g>' % (px, py, c, c))

    def supply_plus(self, x, y, label=None):
        px, py = self._xy(x, y)
        s = ['<circle cx="%g" cy="%g" r="9" fill="%s" stroke="%s" stroke-width="1.4"/>'
             % (px, py, WIRE_RED, INK)]
        s.append('<path d="M %g %g h 9 M %g %g v 9" stroke="#ffffff" stroke-width="2.2"/>'
                 % (px - 4.5, py, px, py - 4.5))
        self._emit("".join(s), "over")
        if label:
            _Canvas.text(self, label, px, py + 26, size=12, bold=True)

    def dip(self, x, y, label, pins_top=("8", "7", "6", "5"),
            pins_bot=("1", "2", "3", "4"), pin_pitch=5, h=8, nc=()):
        """Physical DIP outline, notch left. Returns {pin: (gx, gy)} of pin
        stub tips in grid units (top pins point up, bottom pins down).
        Pins named in `nc` are unconnected: numbered in the package but
        drawn without a stub, and left out of the returned dict."""
        px, py = self._xy(x, y)
        n = len(pins_top)
        w = (n - 1) * pin_pitch * self.G + 2.2 * self.G
        H = h * self.G
        s = ['<rect x="%g" y="%g" width="%g" height="%g" rx="4" fill="%s" '
             'stroke="%s" stroke-width="1.6"/>' % (px, py, w, H, IC_BODY_SCH, INK)]
        s.append('<path d="M %g %g A 8 8 0 0 1 %g %g Z" fill="#ffffff" '
                 'stroke="%s" stroke-width="1.2"/>'
                 % (px, py + H / 2 - 8, px, py + H / 2 + 8, INK))
        pins = {}
        for i, (pt, pb) in enumerate(zip(pins_top, pins_bot)):
            cx = px + 1.1 * self.G + i * pin_pitch * self.G
            if str(pt) not in nc:
                s.append('<line x1="%g" y1="%g" x2="%g" y2="%g" stroke="%s" '
                         'stroke-width="2.2"/>' % (cx, py, cx, py - self.G, INK))
            if str(pb) not in nc:
                s.append('<line x1="%g" y1="%g" x2="%g" y2="%g" stroke="%s" '
                         'stroke-width="2.2"/>' % (cx, py + H, cx, py + H + self.G, INK))
            s.append('<text x="%g" y="%g" font-family="%s" font-size="12" '
                     'fill="#ffffff" text-anchor="middle" font-weight="bold">%s</text>'
                     % (cx, py + 16, FONT, _esc(pt)))
            s.append('<text x="%g" y="%g" font-family="%s" font-size="12" '
                     'fill="#ffffff" text-anchor="middle" font-weight="bold">%s</text>'
                     % (cx, py + H - 7, FONT, _esc(pb)))
            gx = cx / self.G
            if str(pt) not in nc:
                pins[str(pt)] = (gx, y - 1)
            if str(pb) not in nc:
                pins[str(pb)] = (gx, y + h + 1)
        s.append('<text x="%g" y="%g" font-family="%s" font-size="14" fill="#ffffff" '
                 'text-anchor="middle" letter-spacing="2">%s</text>'
                 % (px + w / 2, py + H / 2 + 5, FONT, _esc(label)))
        self._emit("".join(s))
        return pins

    def pinout(self, x, y, label, left, right, pitch=4, width=12):
        """Top-view DIP pinout, notch at the top edge, pin 1 at top-left of the notch.
        `left` lists (number, name) pairs top to bottom for the left side,
        `right` lists them bottom to top for the right side, so both read
        in pin order. Names are ink text beside the stubs; a name of
        "VCC" is set with a subscript. Returns {number: (gx, gy)} of stub
        tips in grid units."""
        px, py = self._xy(x, y)
        n = len(left)
        W = width * self.G
        H = (n - 1) * pitch * self.G + 2.2 * self.G
        s = ['<rect x="%g" y="%g" width="%g" height="%g" rx="4" fill="%s" '
             'stroke="%s" stroke-width="1.6"/>' % (px, py, W, H, IC_BODY_SCH, INK)]
        # locating notch, top centre
        s.append('<path d="M %g %g A 8 8 0 0 0 %g %g Z" fill="#ffffff" '
                 'stroke="%s" stroke-width="1.2"/>'
                 % (px + W / 2 - 8, py, px + W / 2 + 8, py, INK))
        pins = {}

        def name_text(name, tx, anchor):
            if name.upper() == "VCC":
                return ('<text x="%g" y="%g" font-family="%s" font-size="13" fill="%s" '
                        'text-anchor="%s" font-weight="bold">V<tspan font-size="9" dy="3">CC'
                        '</tspan></text>' % (tx, cy + 4.5, FONT, INK, anchor))
            return ('<text x="%g" y="%g" font-family="%s" font-size="13" fill="%s" '
                    'text-anchor="%s" font-weight="bold">%s</text>'
                    % (tx, cy + 4.5, FONT, INK, anchor, _esc(name)))

        for i, (num, name) in enumerate(left):
            cy = py + 1.1 * self.G + i * pitch * self.G
            s.append('<line x1="%g" y1="%g" x2="%g" y2="%g" stroke="%s" stroke-width="2.2"/>'
                     % (px, cy, px - self.G, cy, INK))
            s.append('<text x="%g" y="%g" font-family="%s" font-size="12" fill="#ffffff" '
                     'text-anchor="start" font-weight="bold">%s</text>'
                     % (px + 7, cy + 4.5, FONT, _esc(num)))
            s.append(name_text(name, px - self.G - 6, "end"))
            pins[str(num)] = (x - 1, cy / self.G)
        for i, (num, name) in enumerate(right):
            cy = py + 1.1 * self.G + (n - 1 - i) * pitch * self.G
            s.append('<line x1="%g" y1="%g" x2="%g" y2="%g" stroke="%s" stroke-width="2.2"/>'
                     % (px + W, cy, px + W + self.G, cy, INK))
            s.append('<text x="%g" y="%g" font-family="%s" font-size="12" fill="#ffffff" '
                     'text-anchor="end" font-weight="bold">%s</text>'
                     % (px + W - 7, cy + 4.5, FONT, _esc(num)))
            s.append(name_text(name, px + W + self.G + 6, "start"))
            pins[str(num)] = (x + width + 1, cy / self.G)
        s.append('<text x="%g" y="%g" font-family="%s" font-size="14" fill="#ffffff" '
                 'text-anchor="middle" letter-spacing="2">%s</text>'
                 % (px + W / 2, py + H / 2 + 5, FONT, _esc(label)))
        self._emit("".join(s))
        return pins

    def arrow(self, points, role="sig", width=1.6):
        """Thin polyline ending in a filled arrowhead, for annotations."""
        import math
        pts = [self._xy(*p) for p in points]
        c = self.ROLE[role]
        (x0, y0), (x1, y1) = pts[-2], pts[-1]
        ang = math.atan2(y1 - y0, x1 - x0)
        L, hw = 10, 3.6
        bx, by = x1 - L * math.cos(ang), y1 - L * math.sin(ang)
        nx, ny = -math.sin(ang), math.cos(ang)
        # the shaft stops at the base of the head so the point stays sharp
        shaft = pts[:-1] + [(bx, by)]
        d = "M " + " L ".join("%g %g" % p for p in shaft)
        head = "%g,%g %g,%g %g,%g" % (x1, y1, bx + hw * nx, by + hw * ny, bx - hw * nx, by - hw * ny)
        self._emit('<path d="%s" fill="none" stroke="%s" stroke-width="%g" '
                   'stroke-linejoin="round"/><polygon points="%s" fill="%s" '
                   'stroke="%s" stroke-width="0.6" stroke-linejoin="miter"/>'
                   % (d, c, width, head, c, c), "over")

    def pill(self, text, x, y, leader_to=None, font_size=11, stroke=None):
        """Grid-unit wrapper over the shared pill."""
        lt = (leader_to[0] * self.G, leader_to[1] * self.G) if leader_to else None
        super().pill(text, x * self.G, y * self.G, leader_to=lt,
                     font_size=font_size, stroke=stroke)

    def text(self, s, x, y, size=12, anchor="middle", bold=False, color=INK):
        super().text(s, x * self.G, y * self.G, size=size, anchor=anchor,
                     bold=bold, color=color)

    def table(self, x, y, title, rows, col_w=(4.4, 16)):
        """Components table: title bar plus name/description rows."""
        px, py = self._xy(x, y)
        w0, w1 = col_w[0] * self.G, col_w[1] * self.G
        rh = 1.8 * self.G
        s = ['<rect x="%g" y="%g" width="%g" height="%g" fill="%s"/>'
             % (px, py, w0 + w1, rh, INK)]
        s.append('<text x="%g" y="%g" font-family="%s" font-size="11.5" fill="#ffffff" '
                 'font-weight="bold">%s</text>' % (px + 6, py + rh - 6, FONT, _esc(title)))
        for i, (name, desc) in enumerate(rows):
            ry = py + rh * (i + 1)
            s.append('<rect x="%g" y="%g" width="%g" height="%g" fill="#ffffff" '
                     'stroke="%s" stroke-width="0.8"/>' % (px, ry, w0, rh, INK))
            s.append('<rect x="%g" y="%g" width="%g" height="%g" fill="%s" '
                     'stroke="%s" stroke-width="0.8"/>'
                     % (px + w0, ry, w1, rh, "#f3f8f7", INK))
            s.append('<text x="%g" y="%g" font-family="%s" font-size="11" fill="%s" '
                     'font-weight="bold">%s</text>'
                     % (px + 6, ry + rh - 6, FONT, INK, _esc(name)))
            s.append('<text x="%g" y="%g" font-family="%s" font-size="11" fill="%s">%s'
                     '</text>' % (px + w0 + 6, ry + rh - 6, FONT, INK, _esc(desc)))
        self._emit("".join(s), "over")

    def svg(self):
        head = ('<?xml version="1.0" encoding="UTF-8"?>'
                '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %g %g" '
                'font-family="%s">' % (self.W, self.H, FONT))
        return head + "<defs>" + self._defs() + "</defs>" + "".join(self._body()) + "</svg>"

    def save(self, path):
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.svg())
        return path
