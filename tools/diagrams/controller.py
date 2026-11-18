"""Controller-board drawings for the RGB LED Cube.

    uv run --with matplotlib tools/diagrams/controller.py docs/attachments

Writes cube-controller-wiring.png (pictorial wiring, true pin order) and
cube-controller-perfboard.png (placement on a 7x9 cm perfboard).
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyBboxPatch, Rectangle

OUT = Path(sys.argv[1] if len(sys.argv) > 1 else "."); OUT.mkdir(parents=True, exist_ok=True)
INK, MUTED = "#1f2328", "#6e7781"
RED, BLK, DATA, MIC, BTN, WARN, UI = "#cf222e", "#24292f", "#0969da", "#8250df", "#1a7f37", "#bf8700", "#d4580b"
FILL = {DATA: "#ddf4ff", MIC: "#fbefff", BTN: "#dafbe1", RED: "#fff1f1", BLK: "#eaeef2", UI: "#fff1e5"}
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "text.color": INK})


def save(fig, name):
    fig.savefig(OUT / name, dpi=150, bbox_inches="tight", pad_inches=0.25, facecolor="white")
    plt.close(fig)
    print("wrote", OUT / name)


# =============================================================================== wiring
def wiring():
    fig, ax = plt.subplots(figsize=(22, 13.6))
    ax.set_xlim(-0.5, 31.3); ax.set_ylim(-3.4, 15.6); ax.set_aspect("equal"); ax.axis("off")
    ax.set_title("Controller board wiring: true pin order. Power drawn as wires; every signal pin is tagged with "
                 "its destination", fontsize=14, fontweight="bold")
    P = {}
    W, UX, EX0, EX1, RX = 3.2, 15.6, 6.4, 9.4, 25.0

    def pin(name, x, y, label="", side="in_R", col=INK, fs=8, dot=True):
        P[name] = (x, y)
        if dot:
            ax.add_patch(Circle((x, y), 0.12, fc="#d4a017", ec=INK, lw=0.8, zorder=6))
        if label:
            dx = 0.22 if side == "in_R" else -0.22
            ax.text(x + dx, y, label, ha="left" if side == "in_R" else "right", va="center", fontsize=fs, color=col,
                    zorder=7, family="DejaVu Sans Mono", fontweight="bold")

    def tag(name, text, col, side, length=0.45):
        x, y = P[name]
        sx = x - length if side == "L" else x + length
        ax.plot([x, sx], [y, y], color=col, lw=2, zorder=5)
        ax.text(sx + (-0.08 if side == "L" else 0.08), y, text, ha="right" if side == "L" else "left", va="center",
                fontsize=7.6, color=col, zorder=7, bbox=dict(boxstyle="round,pad=0.22", fc=FILL[col], ec=col, lw=1))

    def poly(pts, col, lw=2.0):
        xs, ys = zip(*[P[p] if isinstance(p, str) else p for p in pts])
        ax.plot(xs, ys, color=col, lw=lw, zorder=4, solid_capstyle="round", solid_joinstyle="round")

    # rails
    ax.plot([0.0, 30.2], [15.0, 15.0], color=RED, lw=4, zorder=3)
    ax.text(30.3, 15.0, "+5V", color=RED, va="center", fontweight="bold")
    ax.plot([0.0, 30.2], [14.4, 14.4], color=BLK, lw=4, zorder=3)
    ax.text(30.3, 14.4, "GND", color=BLK, va="center", fontweight="bold")

    # J1 + C1
    ax.add_patch(FancyBboxPatch((0.1, 12.4), 1.6, 1.3, boxstyle="round,pad=0.02", fc="#fff1f1", ec=RED, lw=1.4))
    pin("J1+", 0.5, 13.0); pin("J1-", 1.3, 13.0)
    ax.text(0.5, 13.3, "+5V", ha="center", fontsize=7, color=RED); ax.text(1.3, 13.3, "GND", ha="center", fontsize=7)
    ax.text(0.9, 12.2, "J1 power in\n(1 A fuse)", ha="center", va="top", fontsize=7.5, color=MUTED)
    poly(["J1+", (0.5, 15.0)], RED, 2.4); poly(["J1-", (1.3, 14.4)], BLK, 2.4)
    ax.add_patch(Rectangle((3.6, 14.55), 0.5, 0.3, fc="#ddf4ff", ec=DATA, zorder=5))
    ax.plot([3.85, 3.85], [14.85, 15.0], color=RED, lw=1.5); ax.plot([3.85, 3.85], [14.55, 14.4], color=BLK, lw=1.5)
    ax.text(4.2, 14.7, "C1 470 µF (− to GND)", fontsize=7.5, color=DATA, va="center")

    # ESP32 DevKit V1
    ax.add_patch(FancyBboxPatch((EX0, 0.9), EX1 - EX0, 11.4, boxstyle="round,pad=0.05", fc="#1e3a5f", ec=INK,
                                lw=1.5, zorder=2))
    ax.add_patch(Rectangle((EX0 + 0.8, 9.0), 1.4, 3.0, fc="#c0c4c8", ec=INK, zorder=3))
    ax.text(EX0 + 1.5, 10.5, "WROOM\n-32", ha="center", va="center", fontsize=7.5, zorder=4)
    ax.add_patch(Rectangle((EX0 + 1.05, 0.45), 0.9, 0.6, fc="#c0c4c8", ec=INK, zorder=3))
    ax.text(EX0 + 1.5, 0.15, "USB → back wall", ha="center", va="top", fontsize=7.5, color=MUTED)
    ax.text(EX0 + 1.5, 5.0, "ESP32\nDevKit V1\n30-pin\n\nin 2× 1×15\nfemale\nheaders", ha="center", va="center",
            fontsize=8.5, color="white", zorder=4)
    left = ["EN", "36", "39", "34", "35", "32", "33", "25", "26", "27", "14", "12", "13", "GND", "VIN"]
    right = ["23", "22", "TX", "RX", "21", "19", "18", "5", "17", "16", "4", "2", "15", "GND", "3V3"]
    for i, l in enumerate(left):
        y = 11.6 - i * 0.72
        ax.text(EX0 + 0.25, y, l, ha="left", va="center", fontsize=7.5, color="white", family="DejaVu Sans Mono",
                fontweight="bold", zorder=7)
        pin("EL" + l, EX0, y)
    for i, l in enumerate(right):
        y = 11.6 - i * 0.72
        ax.text(EX1 - 0.25, y, l, ha="right", va="center", fontsize=7.5, color="white", family="DejaVu Sans Mono",
                fontweight="bold", zorder=7)
        pin("ER" + l, EX1, y)

    tag("EL25", "S5 → U2 pin 5 (2A)", DATA, "L"); tag("EL26", "S6 → U2 pin 9 (3A)", DATA, "L")
    tag("EL27", "S7 → U2 pin 12 (4A)", DATA, "L"); tag("EL32", "mic SD → J10 pin 6", MIC, "L")
    tag("EL14", "mic SCK → J10 pin 5", MIC, "L"); tag("EL13", "button → J11 pin 1", BTN, "L")
    tag("EL34", "knob wiper → J13 pin 2", UI, "L")
    tag("ER23", "S4 → U2 pin 2 (1A)", DATA, "R"); tag("ER19", "S3 → U1 pin 12 (4A)", DATA, "R")
    tag("ER18", "S2 → U1 pin 9 (3A)", DATA, "R"); tag("ER17", "S1 → U1 pin 5 (2A)", DATA, "R")
    tag("ER16", "S0 → U1 pin 2 (1A)", DATA, "R"); tag("ER15", "mic WS → J10 pin 4", MIC, "R")
    tag("ER21", "OLED SDA → J12 pin 4", UI, "R"); tag("ER22", "OLED SCL → J12 pin 3", UI, "R")
    tag("ER3V3", "3V3 → J10·1, J12·2, J13·1", MIC, "R")

    # ESP power
    vy = P["ELVIN"][1]
    ax.add_patch(Rectangle((2.35, 12.3), 0.5, 1.1, fc="#24292f", ec=INK, zorder=5))
    ax.add_patch(Rectangle((2.35, 12.3), 0.5, 0.22, fc="#c0c4c8", ec=INK, zorder=6))
    ax.text(3.0, 12.85, "D1 SS34\n(band = VIN side)", ha="left", va="center", fontsize=7.5, color=RED)
    poly([(2.6, 15.0), (2.6, 13.4)], RED, 2.0)
    poly([(2.6, 12.3), (2.6, vy), "ELVIN"], RED, 2.0)
    poly(["ELGND", (5.6, P["ELGND"][1]), (5.6, 14.4)], BLK, 1.6)
    poly(["ERGND", (EX1 + 0.35, P["ERGND"][1]), (EX1 + 0.35, 0.6), (UX - 0.4, 0.6)], BLK, 1.6)

    # level shifters
    def dip(name, x, ytop):
        h = 0.75
        ax.add_patch(FancyBboxPatch((x, ytop - 6 * h - 0.3), W, 6 * h + 0.6, boxstyle="round,pad=0.03",
                                    fc="#2d333b", ec=INK, lw=1.4, zorder=2))
        ax.add_patch(Circle((x + W / 2, ytop + 0.12), 0.18, fc="#adbac7", ec="none", zorder=3))
        ax.text(x + W / 2, ytop - 3 * h, f"{name}\nSN74\nAHCT125\n(DIP-14\nsocket)", ha="center", va="center",
                color="white", fontsize=7.5, zorder=4)
        L = ["1OE", "1A", "1Y", "2OE", "2A", "2Y", "GND"]
        R = ["VCC", "4OE", "4A", "4Y", "3OE", "3A", "3Y"]
        for i in range(7):
            y = ytop - i * h
            pin(f"{name}.{i + 1}", x, y, f"{i + 1} {L[i]}", "in_R", "white", 7)
            pin(f"{name}.{14 - i}", x + W, y, f"{R[i]} {14 - i}", "in_L", "white", 7)

    dip("U1", UX, 12.6)
    dip("U2", UX, 6.1)
    for u, base in (("U1", 0), ("U2", 4)):
        x14, y14 = P[f"{u}.14"]
        poly([f"{u}.14", (x14 + 0.45, y14), (x14 + 0.45, 15.0)], RED, 1.8)
        spine_l = UX - 0.4
        for p_ in (1, 4, 7):
            poly([f"{u}.{p_}", (spine_l, P[f"{u}.{p_}"][1])], BLK, 1.5)
        poly([(spine_l, P[f"{u}.1"][1]), (spine_l, P[f"{u}.7"][1])], BLK, 1.5)
        for p_ in (13, 10):
            poly([f"{u}.{p_}", (UX + W + 0.25, P[f"{u}.{p_}"][1])], BLK, 1.5)
        poly([(UX + W + 0.25, P[f"{u}.13"][1]), (UX + W + 0.25, P[f"{u}.10"][1])], BLK, 1.5)
        ax.text(UX + W + 0.32, (P[f"{u}.13"][1] + P[f"{u}.10"][1]) / 2, "OE→GND", fontsize=6.3, color=BLK,
                va="center", rotation=90)
        poly([(UX + W + 0.25, P[f"{u}.10"][1]), (UX + W + 0.25, P[f"{u}.7"][1] - 0.45),
              (spine_l, P[f"{u}.7"][1] - 0.45), (spine_l, P[f"{u}.7"][1])], BLK, 1.2)
        ax.add_patch(Rectangle((x14 + 0.65, y14 + 0.25), 0.4, 0.22, fc="#f6f8fa", ec=DATA, zorder=5))
        ax.text(x14 + 1.12, y14 + 0.36, "100 nF pin 14 ↔ pin 7", fontsize=6.5, color=DATA, va="center")
        gp = [16, 17, 18, 19] if u == "U1" else [23, 25, 26, 27]
        tag(f"{u}.2", f"← GPIO{gp[0]} (S{base})", DATA, "L", 0.6)
        tag(f"{u}.5", f"← GPIO{gp[1]} (S{base + 1})", DATA, "L", 0.6)
        tag(f"{u}.3", f"S{base} → R{base + 1}", DATA, "L", 0.6)
        tag(f"{u}.6", f"S{base + 1} → R{base + 2}", DATA, "L", 0.6)
        tag(f"{u}.9", f"← GPIO{gp[2]} (S{base + 2})", DATA, "R", 0.75)
        tag(f"{u}.12", f"← GPIO{gp[3]} (S{base + 3})", DATA, "R", 0.75)
        tag(f"{u}.8", f"S{base + 2} → R{base + 3}", DATA, "R", 0.75)
        tag(f"{u}.11", f"S{base + 3} → R{base + 4}", DATA, "R", 0.75)
    poly([(UX - 0.4, P["U1.1"][1]), (UX - 0.4, 14.4)], BLK, 1.5)
    poly([(UX - 0.4, P["U2.1"][1]), (UX - 0.4, P["U1.7"][1] - 0.45)], BLK, 1.5)
    poly([(UX - 0.4, P["U2.7"][1]), (UX - 0.4, 0.6)], BLK, 1.5)

    # outputs
    srcs = ["U1 pin 3 (1Y)", "U1 pin 6 (2Y)", "U1 pin 8 (3Y)", "U1 pin 11 (4Y)",
            "U2 pin 3 (1Y)", "U2 pin 6 (2Y)", "U2 pin 8 (3Y)", "U2 pin 11 (4Y)"]
    for s in range(8):
        y = 12.4 - s * 1.45
        pin(f"R{s}a", RX, y)
        tag(f"R{s}a", f"from {srcs[s]}", DATA, "L", 0.25)
        ax.add_patch(Rectangle((RX + 0.15, y - 0.14), 1.1, 0.28, fc="#e8d5a8", ec=WARN, lw=1.2, zorder=5))
        for bx, c in [(RX + 0.35, "#8b4513"), (RX + 0.5, "#000000"), (RX + 0.65, "#8b4513"), (RX + 0.95, "#d4a017")]:
            ax.add_patch(Rectangle((bx, y - 0.14), 0.07, 0.28, fc=c, ec="none", zorder=6))
        ax.text(RX + 0.7, y + 0.3, f"R{s + 1} 100 Ω", ha="center", fontsize=7, color=WARN)
        poly([(RX, y), (RX + 0.15, y)], DATA, 1.6); poly([(RX + 1.25, y), (RX + 1.9, y)], DATA, 1.6)
        ax.add_patch(FancyBboxPatch((RX + 1.9, y - 0.33), 1.0, 0.66, boxstyle="round,pad=0.02", fc="#f0ead6",
                                    ec=INK, lw=1.1, zorder=5))
        pin(f"J{s}D", RX + 2.15, y); pin(f"J{s}G", RX + 2.65, y)
        ax.text(RX + 2.15, y - 0.55, "D", ha="center", fontsize=6.5, color=DATA)
        ax.text(RX + 2.65, y - 0.55, "G", ha="center", fontsize=6.5)
        ax.text(RX + 3.05, y + 0.1, f"J{s + 2}", fontsize=8.5, fontweight="bold", va="center")
        ax.text(RX + 3.05, y - 0.25, f"→ slab {s}", fontsize=7.5, va="center", color=MUTED)
        poly([f"J{s}G", (RX + 2.65, y + 0.5), (29.8, y + 0.5)], BLK, 1.0)
    poly([(29.8, 14.4), (29.8, 12.4 - 7 * 1.45 + 0.5)], BLK, 1.5)
    ax.text(29.95, 6.5, "every connector's G pin → GND", rotation=90, fontsize=7, color=MUTED, va="center")
    ax.text(RX + 1.4, 13.35, "8× JST-XH 2-pin + 100 Ω", ha="center", fontsize=8.5, fontweight="bold")

    # bottom headers: J10 mic, J12 OLED, J13 knob, J11 button
    def header(x0, name, pins, col, caption):
        n = len(pins)
        ax.add_patch(FancyBboxPatch((x0, -1.75), 0.84 * n + 0.1, 0.9, boxstyle="round,pad=0.02", fc=FILL[col],
                                    ec=col, lw=1.3))
        for i, (lab, src, c) in enumerate(pins):
            x = x0 + 0.45 + i * 0.84
            pin(f"{name}{i}", x, -1.3)
            ax.text(x, -0.95, f"{i + 1}·{lab}", ha="center", fontsize=6.8, color=c, fontweight="bold")
            ax.text(x, -1.95, src, ha="center", va="top", fontsize=6.6, color=c)
        ax.text(x0 + (0.84 * n + 0.1) / 2, -2.45, caption, ha="center", fontsize=8, color=col)

    header(6.3, "M", [("3V3", "← 3V3", MIC), ("GND", "GND", BLK), ("L/R", "GND", BLK), ("WS", "← 15", MIC),
                      ("SCK", "← 14", MIC), ("SD", "← 32", MIC)], MIC, "J10 mic (1×6) → INMP441")
    header(12.0, "O", [("GND", "GND", BLK), ("VCC", "← 3V3", MIC), ("SCL", "← 22", UI), ("SDA", "← 21", UI)],
           UI, "J12 OLED 128×64 (1×4)")
    header(16.0, "K", [("3V3", "← 3V3", MIC), ("WIPER", "→ 34", UI), ("GND", "GND", BLK)], UI,
           "J13 knob: 10 kΩ linear pot")
    header(19.6, "B", [("SW", "← 13", BTN), ("GND", "GND", BLK)], BTN, "J11 button")
    # grounds of the bottom headers to the ground line at y=0.6
    for g in ("M1", "M2", "O0", "K2", "B1"):
        x, _ = P[g]
        poly([g, (x, -0.55), (x, 0.6)], BLK, 1.0)
    poly([(P["M1"][0], 0.6), (P["B1"][0], 0.6)], BLK, 1.2)
    # 100 nF wiper filter
    kx, _ = P["K1"]
    ax.add_patch(Rectangle((kx + 0.12, -0.75), 0.36, 0.2, fc="#f6f8fa", ec=DATA, zorder=5))
    ax.text(kx + 0.3, -0.42, "100 nF\nwiper–GND", ha="center", fontsize=6, color=DATA)
    # parts off-board
    ax.add_patch(Circle((23.4, -1.3), 0.42, fc="#dafbe1", ec=BTN, lw=1.5))
    ax.add_patch(Circle((23.4, -1.3), 0.22, fc=BTN, ec="none"))
    ax.plot([21.3, 22.98], [-1.3, -1.3], color=BTN, lw=2, ls=(0, (3, 2)))
    ax.text(23.95, -1.1, "front panel: push button,\nknob, OLED window, mic hole", fontsize=7.5, color=MUTED,
            va="center")

    for i, (c, t) in enumerate([(RED, "+5 V wire"), (BLK, "GND wire"), (DATA, "LED data"), (MIC, "mic / 3V3"),
                                (UI, "OLED / knob"), (BTN, "button")]):
        ax.plot([0.2 + i * 3.0, 0.8 + i * 3.0], [-3.1, -3.1], color=c, lw=3)
        ax.text(0.9 + i * 3.0, -3.1, t, va="center", fontsize=8.5)
    save(fig, "cube-controller-wiring.png")


# =============================================================================== perfboard
def perfboard():
    C, R = 30, 24
    fig, ax = plt.subplots(figsize=(14, 11.8))
    ax.set_xlim(-1.5, C + 0.5); ax.set_ylim(-3.4, R + 1.2); ax.set_aspect("equal"); ax.axis("off")
    ax.add_patch(Rectangle((-0.7, -0.7), C + 0.4, R + 0.4, fc="#e9dcc0", ec="#9a8455", lw=2))
    for x in range(C):
        for y in range(R):
            ax.add_patch(Circle((x, y), 0.14, fc="#c9b78f", ec="none"))
    for x in range(0, C, 5):
        ax.text(x, -1.05, str(x), ha="center", va="center", fontsize=7, color=MUTED)
    for y in range(0, R, 5):
        ax.text(-1.2, y, str(y), ha="center", va="center", fontsize=7, color=MUTED)

    def pad(x, y, label, col=INK, side="below", fs=6.6):
        ax.add_patch(Circle((x, y), 0.3, fc="white", ec=col, lw=1.4, zorder=5))
        dy = -0.55 if side == "below" else 0.55
        ax.text(x, y + dy, label, ha="center", va="top" if side == "below" else "bottom", fontsize=fs, color=col,
                rotation=90, zorder=6)

    top = ["VIN", "GND", "13", "12", "14", "27", "26", "25", "33", "32", "35", "34", "39", "36", "EN"]
    bot = ["3V3", "GND", "15", "2", "4", "16", "17", "5", "18", "19", "21", "RX", "TX", "22", "23"]
    yt, yb = 13, 3
    ax.add_patch(Rectangle((1.4, yb - 0.8), 18.6, yt - yb + 1.6, fc="none", ec=INK, lw=1.4, ls="--", zorder=4))
    ax.text(10.5, 8.0, "ESP32 DevKit V1\nsits here on its headers\n(USB → left edge)", ha="center", va="center",
            fontsize=10, fontweight="bold")
    ax.text(10.5, 6.2, "header rows 10 holes apart (1.0″).\nMeasure your board; some are 0.9″ (9 holes).",
            ha="center", fontsize=8, color=WARN)
    colmap = {"VIN": RED, "GND": BLK, "3V3": MIC, "16": DATA, "17": DATA, "18": DATA, "19": DATA, "23": DATA,
              "25": DATA, "26": DATA, "27": DATA, "15": MIC, "14": MIC, "32": MIC, "13": BTN, "34": UI, "21": UI,
              "22": UI}
    for i, l in enumerate(top):
        pad(3 + i, yt, l, colmap.get(l, MUTED), side="above")
    for i, l in enumerate(bot):
        pad(3 + i, yb, l, colmap.get(l, MUTED), side="below")
    ax.text(0.2, 8, "USB", ha="center", fontsize=9, color=MUTED, rotation=90)

    def dip(x0, y0, name):
        ax.add_patch(Rectangle((x0 - 0.5, y0 - 0.5), 7, 4, fc="#ddf4ff", ec=DATA, lw=1.4, zorder=3))
        ax.text(x0 + 3, y0 + 1.5, name, ha="center", va="center", fontsize=8.5, fontweight="bold", zorder=6)
        lower = ["1OE", "1A", "1Y", "2OE", "2A", "2Y", "GND"]
        upper = ["VCC", "4OE", "4A", "4Y", "3OE", "3A", "3Y"]
        for i, l in enumerate(lower):
            pad(x0 + i, y0, l, BLK if ("OE" in l or l == "GND") else DATA, side="below", fs=6)
        for i, l in enumerate(upper):
            pad(x0 + i, y0 + 3, l, RED if l == "VCC" else (BLK if "OE" in l else DATA), side="above", fs=6)
        ax.add_patch(Circle((x0 - 0.25, y0 + 0.35), 0.12, fc=INK))
    dip(22, 14, "U1 (slabs 0–3)")
    dip(22, 4, "U2 (slabs 4–7)")
    ax.text(25, 12.2, "100 nF across\nVCC–GND", ha="center", fontsize=7, color=MUTED)
    ax.text(25, 2.2, "100 nF across\nVCC–GND", ha="center", fontsize=7, color=MUTED)

    for s in range(8):
        x = 3 + s * 3
        ax.add_patch(Rectangle((x - 0.5, 21.5), 2.0, 1.0, fc="#f6f8fa", ec=INK, lw=1.2, zorder=3))
        pad(x, 22, "D", DATA, side="above"); pad(x + 1, 22, "G", BLK, side="above")
        ax.text(x + 0.5, 20.9, f"J{s + 2}\nS{s}", ha="center", va="top", fontsize=7.5, fontweight="bold")
        ax.add_patch(Rectangle((x - 0.1, 18.4), 0.2, 1.6, fc="#fff8c5", ec=WARN, zorder=3))
        ax.text(x - 0.35, 19.2, f"R{s + 1}", ha="right", va="center", fontsize=6.5, color=WARN, rotation=90)
    ax.text(27.4, 22.0, "← 8 slab\noutputs", fontsize=8, va="center", color=MUTED)
    ax.text(13.0, 17.4, "100 Ω resistors stand upright between each Y output and its connector", ha="center",
            fontsize=7.5, color=MUTED)

    # bottom edge: J10 mic, J12 OLED, J13 knob, J11 button, J1 power
    def row(x0, labels, col, caption):
        for i, l in enumerate(labels):
            pad(x0 + i, 0, l, col, side="above", fs=6)
        ax.text(x0 + (len(labels) - 1) / 2, -1.8, caption, ha="center", fontsize=7.3, color=col)
    row(1, ["3V3", "GND", "L/R", "WS", "SCK", "SD"], MIC, "J10 mic")
    row(8, ["GND", "VCC", "SCL", "SDA"], UI, "J12 OLED")
    row(13, ["3V3", "WPR", "GND"], UI, "J13 knob")
    row(17, ["SW", "GND"], BTN, "J11 button")
    ax.add_patch(Rectangle((21.5, -0.5), 3.0, 1.0, fc="#fff1f1", ec=RED, lw=1.4, zorder=3))
    pad(22, 0, "+5V", RED, side="above"); pad(24, 0, "GND", BLK, side="above")
    ax.text(23, -1.8, "J1 power (screw terminal)", ha="center", fontsize=7.3, color=RED)
    ax.add_patch(Circle((27.5, 1.0), 1.0, fc="#ddf4ff", ec=DATA, lw=1.3, zorder=3))
    ax.text(27.5, 1.0, "C1\n470µF", ha="center", va="center", fontsize=7, zorder=6)
    ax.add_patch(Rectangle((19.6, 1.6), 1.8, 0.5, fc="#fff1f1", ec=RED, zorder=3))
    ax.text(20.5, 2.25, "D1 → VIN", ha="center", fontsize=7, color=RED)

    ax.plot([0.0, 29.0], [23.3, 23.3], color=BLK, lw=2.4, alpha=0.6)
    ax.text(29.2, 23.3, "GND bus", fontsize=7, va="center", color=BLK)
    ax.plot([29.0, 29.0], [0.0, 23.0], color=RED, lw=2.4, alpha=0.6)
    ax.text(29.4, 12, "+5V bus (bare wire\nalong the right edge)", fontsize=7, rotation=90, va="center", color=RED)
    ax.set_title("Controller board placement, 7 × 9 cm dual-sided perfboard (~30 × 24 holes), component side",
                 fontsize=12, fontweight="bold")
    ax.text(14.5, -2.9, "Wire point to point from the wiring diagram / netlist. Red = 5 V, black = GND, blue = data, "
                        "purple = mic / 3V3, orange = OLED / knob, green = button.", ha="center", fontsize=8.3,
            color=MUTED)
    save(fig, "cube-controller-perfboard.png")


if __name__ == "__main__":
    wiring()
    perfboard()
