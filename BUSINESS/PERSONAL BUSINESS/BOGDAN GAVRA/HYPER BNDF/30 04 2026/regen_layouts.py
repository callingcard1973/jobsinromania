"""Generate top-down playground floor plans (HTML+SVG) and PDFs for HYPER 1001/1002/1003.

3 variants per package: A=Classic (cardinal), B=Asymmetric (offset+loop), C=Linear (axial).
A3 landscape. Idempotent. No sidebars. Visual-only.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).parent
OUT = ROOT / "CATALOG" / "LAYOUTS"

# Color palette
GRASS = "#DCEDC8"
EPDM_COLORS = ["#FFCDD2", "#FFE0B2", "#C5E1A5", "#B3E5FC", "#D1C4E9"]
PATH_COL = "#D7CCC8"
FENCE = "#6D4C41"
TREE_CROWN = "#558B2F"
TREE_CROWN2 = "#689F38"
TREE_SHADOW = "#33691E"
SHRUB1 = "#7CB342"
SHRUB2 = "#9CCC65"
TRUNK = "#5D4037"
LED_HALO = "rgba(255,235,59,0.35)"
FLOWER_COLS = ["#F8BBD0", "#FFE082", "#CE93D8", "#F48FB1"]

# Scale: 1m = 25 svg units (so 18m = 450u, fits A3 viewbox nicely)
S = 25

PACKAGES = {
    "1001": {"w": 10, "h": 12, "title": "HYPER 1001", "central": ("EV101", 6.16, 4.55)},
    "1002": {"w": 12, "h": 14, "title": "HYPER 1002", "central": ("EV109", 6.36, 5.64)},
    "1003": {"w": 14, "h": 18, "title": "HYPER 1003", "central": ("GM108", 5.35, 3.71)},
}

VARIANT_NAMES = {"A": "Varianta A — Clasica", "B": "Varianta B — Asimetrica", "C": "Varianta C — Liniara"}


def svg_header(plot_w: float, plot_h: float) -> tuple[str, float, float, float, float]:
    """Compute SVG viewbox. Plot in meters; add margin for fence + dim labels."""
    pad_m = 1.5  # extra around plot for fence offset + labels
    label_m = 1.5  # extra for dimension labels
    total_w = (plot_w + 2 * pad_m + label_m) * S
    total_h = (plot_h + 2 * pad_m + label_m) * S
    ox = (pad_m + label_m) * S  # plot origin X
    oy = pad_m * S  # plot origin Y
    return "", total_w, total_h, ox, oy


def defs() -> str:
    return f"""<defs>
  <filter id="soft" x="-20%" y="-20%" width="140%" height="140%">
    <feGaussianBlur in="SourceAlpha" stdDeviation="2"/>
    <feOffset dx="2" dy="3"/>
    <feComponentTransfer><feFuncA type="linear" slope="0.35"/></feComponentTransfer>
    <feMerge><feMergeNode/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
  <radialGradient id="ledHalo" cx="50%" cy="50%" r="50%">
    <stop offset="0%" stop-color="{LED_HALO}"/>
    <stop offset="100%" stop-color="rgba(255,235,59,0)"/>
  </radialGradient>
  <pattern id="grassTex" width="12" height="12" patternUnits="userSpaceOnUse">
    <rect width="12" height="12" fill="{GRASS}"/>
    <circle cx="3" cy="3" r="0.6" fill="#C5E1A5" opacity="0.6"/>
    <circle cx="9" cy="7" r="0.5" fill="#AED581" opacity="0.5"/>
  </pattern>
</defs>"""


def fence(ox: float, oy: float, w_m: float, h_m: float) -> str:
    """3-bar fence around the plot."""
    fx = ox - 0.4 * S
    fy = oy - 0.4 * S
    fw = (w_m + 0.8) * S
    fh = (h_m + 0.8) * S
    parts = [f'<rect x="{fx}" y="{fy}" width="{fw}" height="{fh}" fill="none" stroke="{FENCE}" stroke-width="2.5"/>']
    # inner bars
    for off in (4, 8):
        parts.append(
            f'<rect x="{fx + off}" y="{fy + off}" width="{fw - 2 * off}" height="{fh - 2 * off}" '
            f'fill="none" stroke="{FENCE}" stroke-width="1" opacity="0.6"/>'
        )
    # entrance gap south (centered)
    gap_w = 1.5 * S
    gx = ox + (w_m * S - gap_w) / 2
    gy = fy + fh - 6
    parts.append(f'<rect x="{gx}" y="{gy - 4}" width="{gap_w}" height="14" fill="{GRASS}"/>')
    parts.append(
        f'<text x="{gx + gap_w / 2}" y="{gy + 18}" text-anchor="middle" '
        f'font-family="Arial" font-size="9" fill="{FENCE}" font-weight="bold">INTRARE</text>'
    )
    return "\n".join(parts)


def epdm_zone(cx: float, cy: float, rx: float, ry: float, color: str) -> str:
    return (
        f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="{color}" '
        f'opacity="0.85" stroke="#fff" stroke-width="1.5"/>'
    )


def tree(cx: float, cy: float, r: float = 1.2) -> str:
    rs = r * S
    return (
        f'<g filter="url(#soft)">'
        f'<ellipse cx="{cx + 3}" cy="{cy + 4}" rx="{rs * 0.95}" ry="{rs * 0.85}" fill="{TREE_SHADOW}" opacity="0.5"/>'
        f'<circle cx="{cx}" cy="{cy}" r="{rs}" fill="{TREE_CROWN}"/>'
        f'<circle cx="{cx - rs * 0.3}" cy="{cy - rs * 0.2}" r="{rs * 0.55}" fill="{TREE_CROWN2}"/>'
        f'<rect x="{cx - 2}" y="{cy + rs * 0.6}" width="4" height="6" fill="{TRUNK}"/>'
        f"</g>"
    )


def shrub(cx: float, cy: float, r: float = 0.5) -> str:
    rs = r * S
    return (
        f'<g><ellipse cx="{cx}" cy="{cy}" rx="{rs}" ry="{rs * 0.7}" fill="{SHRUB1}"/>'
        f'<ellipse cx="{cx - rs * 0.3}" cy="{cy - rs * 0.2}" rx="{rs * 0.6}" ry="{rs * 0.45}" fill="{SHRUB2}"/></g>'
    )


def flowers(cx: float, cy: float) -> str:
    parts = []
    for i, col in enumerate(FLOWER_COLS):
        ang = i * 1.2
        x = cx + math.cos(ang) * 6
        y = cy + math.sin(ang) * 6
        parts.append(f'<circle cx="{x}" cy="{y}" r="2" fill="{col}"/>')
    return "".join(parts)


def led_post(cx: float, cy: float) -> str:
    halo_r = 2.5 * S
    return (
        f'<circle cx="{cx}" cy="{cy}" r="{halo_r}" fill="url(#ledHalo)"/>'
        f'<circle cx="{cx}" cy="{cy}" r="4" fill="#263238" stroke="#FFC107" stroke-width="1.5"/>'
    )


def bench(cx: float, cy: float, rot: float = 0) -> str:
    w = 1.8 * S
    h = 0.45 * S
    return (
        f'<g transform="translate({cx},{cy}) rotate({rot})" filter="url(#soft)">'
        f'<rect x="{-w / 2}" y="{-h / 2}" width="{w}" height="{h}" fill="#8D6E63" rx="3"/>'
        f'<rect x="{-w / 2}" y="{-h / 2 - 3}" width="{w}" height="3" fill="#6D4C41"/>'
        f"</g>"
    )


def central_eq(cx: float, cy: float, w_m: float, h_m: float, label: str, color: str = "#FF7043") -> str:
    w = w_m * S
    h = h_m * S
    return (
        f'<g filter="url(#soft)">'
        f'<rect x="{cx - w / 2}" y="{cy - h / 2}" width="{w}" height="{h}" fill="{color}" '
        f'stroke="#BF360C" stroke-width="2" rx="6"/>'
        f'<rect x="{cx - w / 2 + 6}" y="{cy - h / 2 + 6}" width="{w - 12}" height="{h - 12}" '
        f'fill="none" stroke="#fff" stroke-width="1" stroke-dasharray="3,3" opacity="0.7"/>'
        f'<text x="{cx}" y="{cy + 4}" text-anchor="middle" font-family="Arial" '
        f'font-size="11" font-weight="bold" fill="#fff">{label}</text>'
        f"</g>"
    )


def swing(cx: float, cy: float, rot: float = 0) -> str:
    w = 3.4 * S
    return (
        f'<g transform="translate({cx},{cy}) rotate({rot})" filter="url(#soft)">'
        f'<line x1="{-w / 2}" y1="0" x2="{w / 2}" y2="0" stroke="#37474F" stroke-width="4"/>'
        f'<line x1="{-w / 2 + 4}" y1="-15" x2="{-w / 2 + 4}" y2="0" stroke="#37474F" stroke-width="3"/>'
        f'<line x1="{w / 2 - 4}" y1="-15" x2="{w / 2 - 4}" y2="0" stroke="#37474F" stroke-width="3"/>'
        f'<rect x="{-w / 4 - 8}" y="-2" width="16" height="6" fill="#FBC02D" rx="2"/>'
        f'<rect x="{w / 4 - 8}" y="-2" width="16" height="6" fill="#FBC02D" rx="2"/>'
        f'<line x1="{-w / 4}" y1="-15" x2="{-w / 4}" y2="0" stroke="#212121" stroke-width="1"/>'
        f'<line x1="{w / 4}" y1="-15" x2="{w / 4}" y2="0" stroke="#212121" stroke-width="1"/>'
        f"</g>"
    )


def spring_rocker(cx: float, cy: float, color: str = "#E91E63") -> str:
    return (
        f'<g filter="url(#soft)">'
        f'<ellipse cx="{cx}" cy="{cy}" rx="14" ry="9" fill="{color}" stroke="#880E4F" stroke-width="1.5"/>'
        f'<circle cx="{cx - 8}" cy="{cy - 3}" r="2" fill="#fff"/>'
        f'<path d="M{cx - 4},{cy + 8} Q{cx},{cy + 14} {cx + 4},{cy + 8}" stroke="#37474F" stroke-width="2" fill="none"/>'
        f"</g>"
    )


def carousel(cx: float, cy: float) -> str:
    r = 1.075 * S
    return (
        f'<g filter="url(#soft)">'
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="#4FC3F7" stroke="#0277BD" stroke-width="2"/>'
        f'<circle cx="{cx}" cy="{cy}" r="{r * 0.65}" fill="#81D4FA"/>'
        f'<circle cx="{cx}" cy="{cy}" r="6" fill="#01579B"/>'
        + "".join(
            f'<line x1="{cx}" y1="{cy}" x2="{cx + math.cos(a) * r}" y2="{cy + math.sin(a) * r}" '
            f'stroke="#0277BD" stroke-width="1.5"/>'
            for a in [i * math.pi / 3 for i in range(6)]
        )
        + "</g>"
    )


def climb(cx: float, cy: float, w_m: float = 3.12, h_m: float = 1.20) -> str:
    w = w_m * S
    h = h_m * S
    return (
        f'<g filter="url(#soft)">'
        f'<rect x="{cx - w / 2}" y="{cy - h / 2}" width="{w}" height="{h}" fill="#7CB342" '
        f'stroke="#33691E" stroke-width="2" rx="4"/>'
        + "".join(
            f'<circle cx="{cx - w / 2 + 12 + i * 14}" cy="{cy - h / 2 + 8 + (i % 2) * 12}" r="4" fill="#FFEB3B"/>'
            for i in range(int(w / 14) - 1)
        )
        + "</g>"
    )


def path_bezier(points: list[tuple[float, float]]) -> str:
    if len(points) < 2:
        return ""
    d = f"M{points[0][0]},{points[0][1]}"
    for i in range(1, len(points)):
        px, py = points[i - 1]
        cx, cy = points[i]
        mx, my = (px + cx) / 2, (py + cy) / 2
        d += f" Q{px + (cx - px) * 0.3},{py + (cy - py) * 0.7} {mx},{my} T{cx},{cy}"
    return (
        f'<path d="{d}" stroke="{PATH_COL}" stroke-width="{1.0 * S}" fill="none" '
        f'stroke-linecap="round" opacity="0.9"/>'
        f'<path d="{d}" stroke="#A1887F" stroke-width="{1.0 * S}" fill="none" '
        f'stroke-linecap="round" opacity="0.15" stroke-dasharray="2,8"/>'
    )


def dim_arrows(ox: float, oy: float, w_m: float, h_m: float) -> str:
    """Top dim arrow + left dim arrow."""
    parts = []
    # top
    y = oy - 0.8 * S
    parts.append(
        f'<line x1="{ox}" y1="{y}" x2="{ox + w_m * S}" y2="{y}" stroke="#37474F" stroke-width="1"/>'
        f'<line x1="{ox}" y1="{y - 5}" x2="{ox}" y2="{y + 5}" stroke="#37474F" stroke-width="1"/>'
        f'<line x1="{ox + w_m * S}" y1="{y - 5}" x2="{ox + w_m * S}" y2="{y + 5}" stroke="#37474F" stroke-width="1"/>'
        f'<text x="{ox + w_m * S / 2}" y="{y - 8}" text-anchor="middle" font-family="Arial" '
        f'font-size="11" font-weight="bold" fill="#37474F">{w_m:.2f} m</text>'
    )
    # left
    x = ox - 0.8 * S
    parts.append(
        f'<line x1="{x}" y1="{oy}" x2="{x}" y2="{oy + h_m * S}" stroke="#37474F" stroke-width="1"/>'
        f'<line x1="{x - 5}" y1="{oy}" x2="{x + 5}" y2="{oy}" stroke="#37474F" stroke-width="1"/>'
        f'<line x1="{x - 5}" y1="{oy + h_m * S}" x2="{x + 5}" y2="{oy + h_m * S}" stroke="#37474F" stroke-width="1"/>'
        f'<text x="{x - 8}" y="{oy + h_m * S / 2}" text-anchor="middle" font-family="Arial" '
        f'font-size="11" font-weight="bold" fill="#37474F" '
        f'transform="rotate(-90 {x - 8} {oy + h_m * S / 2})">{h_m:.2f} m</text>'
    )
    return "\n".join(parts)


def compass(total_w: float) -> str:
    cx = total_w - 35
    cy = 35
    return (
        f'<g><circle cx="{cx}" cy="{cy}" r="18" fill="#fff" stroke="#37474F" stroke-width="1"/>'
        f'<polygon points="{cx},{cy - 14} {cx - 5},{cy} {cx},{cy - 4} {cx + 5},{cy}" fill="#D32F2F"/>'
        f'<polygon points="{cx},{cy + 14} {cx - 5},{cy} {cx},{cy + 4} {cx + 5},{cy}" fill="#37474F"/>'
        f'<text x="{cx}" y="{cy - 20}" text-anchor="middle" font-family="Arial" '
        f'font-size="10" font-weight="bold" fill="#37474F">N</text></g>'
    )


def title_box(title: str, variant_name: str) -> str:
    return (
        f'<g><rect x="14" y="14" width="240" height="38" fill="#fff" stroke="#37474F" stroke-width="1" rx="3"/>'
        f'<text x="22" y="32" font-family="Arial" font-size="14" font-weight="bold" fill="#263238">{title}</text>'
        f'<text x="22" y="46" font-family="Arial" font-size="11" fill="#546E7A">{variant_name}</text></g>'
    )


def legend(total_w: float, total_h: float) -> str:
    x = total_w - 230
    y = total_h - 130
    rows = [
        ("#FFCDD2", "Zona EPDM (cauciuc)"),
        (GRASS, "Gazon natural"),
        (PATH_COL, "Alei pavate (1.0 m)"),
        (SHRUB1, "Tufe ornamentale"),
        (TREE_CROWN, "Pomi"),
    ]
    parts = [f'<rect x="{x}" y="{y}" width="216" height="116" fill="#fff" stroke="#37474F" stroke-width="1" rx="3"/>']
    for i, (col, lbl) in enumerate(rows):
        ry = y + 12 + i * 16
        parts.append(f'<rect x="{x + 8}" y="{ry}" width="14" height="10" fill="{col}" stroke="#37474F" stroke-width="0.5"/>')
        parts.append(f'<text x="{x + 28}" y="{ry + 9}" font-family="Arial" font-size="9" fill="#263238">{lbl}</text>')
    parts.append(
        f'<text x="{x + 8}" y="{y + 108}" font-family="Arial" font-size="8" '
        f'font-style="italic" fill="#546E7A">EPDM 15mm + SBR 50mm conform EN 1177</text>'
    )
    return "\n".join(parts)


# ============================================================
# Layout builders — return list of SVG fragments
# ============================================================


def safety_zones(cfg: list[dict[str, Any]]) -> str:
    """cfg: list of {x,y,rx,ry,col} in plot coords (already scaled)."""
    return "\n".join(epdm_zone(c["x"], c["y"], c["rx"], c["ry"], c["col"]) for c in cfg)


def build_1001(variant: str, ox: float, oy: float) -> str:
    """HYPER 1001 — 10x12m. EV101 + SE001 swing + ZIP + CR002 + 2 banci + 2 LED."""
    w_m, h_m = 10, 12
    cx0 = ox + w_m * S / 2
    cy0 = oy + h_m * S / 2

    if variant == "A":
        # Classic: central EV101 in center, satellites at cardinals
        central = (cx0, cy0)
        swing_pos = (cx0, oy + 1.8 * S)  # N
        zip_pos = (ox + 1.5 * S, cy0)  # W
        carousel_pos = (cx0, oy + h_m * S - 2.0 * S)  # S
        # carousel south, swing north, ZIP west, then add another small element east
        bench_pos = [(ox + w_m * S - 1.0 * S, cy0 - 1.5 * S), (ox + w_m * S - 1.0 * S, cy0 + 1.5 * S)]
        leds = [(ox + 1.0 * S, oy + 1.0 * S), (ox + w_m * S - 1.0 * S, oy + h_m * S - 1.0 * S)]
        trees = [(ox + 0.7 * S, oy + 0.7 * S), (ox + w_m * S - 0.7 * S, oy + 0.7 * S),
                 (ox + 0.7 * S, oy + h_m * S - 0.7 * S), (ox + w_m * S - 0.7 * S, oy + h_m * S - 0.7 * S)]
        shrubs = [(ox + 2 * S, oy + 0.8 * S), (ox + w_m * S - 2 * S, oy + 0.8 * S),
                  (ox + 2 * S, oy + h_m * S - 0.8 * S), (ox + w_m * S - 2 * S, oy + h_m * S - 0.8 * S),
                  (ox + 0.7 * S, cy0), (ox + w_m * S - 0.7 * S, cy0 - 3 * S),
                  (ox + w_m * S - 0.7 * S, cy0 + 3 * S), (ox + 0.7 * S, cy0 - 3 * S)]
        path = [swing_pos, central, carousel_pos, (cx0, oy + h_m * S - 0.5 * S)]

    elif variant == "B":
        # Asymmetric: central NW-offset, organic distribution, vegetation south
        central = (ox + w_m * S * 0.40, oy + h_m * S * 0.38)
        swing_pos = (ox + w_m * S * 0.75, oy + h_m * S * 0.25)
        zip_pos = (ox + w_m * S * 0.20, oy + h_m * S * 0.70)
        carousel_pos = (ox + w_m * S * 0.70, oy + h_m * S * 0.65)
        bench_pos = [(ox + w_m * S * 0.30, oy + h_m * S * 0.85), (ox + w_m * S * 0.85, oy + h_m * S * 0.50)]
        leds = [(ox + 0.8 * S, oy + 0.8 * S), (ox + w_m * S * 0.95, oy + h_m * S * 0.85)]
        trees = [(ox + 0.7 * S, oy + 0.7 * S), (ox + w_m * S - 0.7 * S, oy + 1.5 * S),
                 (ox + 1.2 * S, oy + h_m * S - 1.2 * S), (ox + w_m * S * 0.5, oy + h_m * S - 0.7 * S),
                 (ox + w_m * S - 0.7 * S, oy + h_m * S - 1.0 * S)]
        shrubs = [(ox + w_m * S * 0.15, oy + h_m * S * 0.92), (ox + w_m * S * 0.40, oy + h_m * S * 0.93),
                  (ox + w_m * S * 0.65, oy + h_m * S * 0.92), (ox + w_m * S * 0.90, oy + h_m * S * 0.93),
                  (ox + w_m * S * 0.05, oy + h_m * S * 0.55), (ox + w_m * S * 0.95, oy + h_m * S * 0.30),
                  (ox + w_m * S * 0.50, oy + 0.5 * S), (ox + w_m * S * 0.10, oy + 2.5 * S),
                  (ox + w_m * S * 0.30, oy + h_m * S - 0.5 * S),
                  (ox + w_m * S * 0.55, oy + h_m * S - 0.5 * S)]
        # double curved loop
        path = [swing_pos, central, zip_pos, carousel_pos, swing_pos]

    else:  # C linear
        # Long axis vertical (12m). Central piece on long axis, satellites along the other axis
        central = (cx0, oy + h_m * S * 0.40)
        swing_pos = (cx0, oy + h_m * S * 0.78)
        zip_pos = (ox + w_m * S * 0.22, oy + h_m * S * 0.70)
        carousel_pos = (ox + w_m * S * 0.78, oy + h_m * S * 0.70)
        bench_pos = [(ox + 1.0 * S, oy + h_m * S * 0.40), (ox + w_m * S - 1.0 * S, oy + h_m * S * 0.40)]
        leds = [(ox + 1.0 * S, oy + 1.0 * S), (ox + w_m * S - 1.0 * S, oy + h_m * S - 1.0 * S)]
        # vegetation buffer on short edges (top + bottom)
        trees = [(ox + 1.5 * S, oy + 0.7 * S), (ox + w_m * S * 0.5, oy + 0.7 * S),
                 (ox + w_m * S - 1.5 * S, oy + 0.7 * S),
                 (ox + 1.5 * S, oy + h_m * S - 0.7 * S), (ox + w_m * S - 1.5 * S, oy + h_m * S - 0.7 * S)]
        shrubs = [(ox + 0.6 * S + i * 1.6 * S, oy + 1.6 * S) for i in range(5)] + \
                 [(ox + 0.6 * S + i * 1.6 * S, oy + h_m * S - 1.5 * S) for i in range(5)]
        path = [(cx0, oy + 0.5 * S), central, swing_pos, (cx0, oy + h_m * S - 0.5 * S)]

    return _assemble(
        ox, oy, w_m, h_m,
        central=central, central_dim=("EV101", 6.16, 4.55),
        swing=swing_pos, zip_pos=[zip_pos], extra_carousel=carousel_pos,
        benches=bench_pos, leds=leds, trees=trees, shrubs=shrubs, path=path,
        zone_colors_idx=[0, 1, 2, 3],
    )


def build_1002(variant: str, ox: float, oy: float) -> str:
    """HYPER 1002 — 12x14m. EV109 + SE001 swing + 2x ZIP + 4 banci + 4 LED."""
    w_m, h_m = 12, 14
    cx0 = ox + w_m * S / 2
    cy0 = oy + h_m * S / 2

    if variant == "A":
        central = (cx0, cy0)
        swing_pos = (cx0, oy + 2.0 * S)
        zip_a = (ox + 1.6 * S, cy0)
        zip_b = (ox + w_m * S - 1.6 * S, cy0)
        bench_pos = [(ox + 1.5 * S, oy + 2.0 * S), (ox + w_m * S - 1.5 * S, oy + 2.0 * S),
                     (ox + 2.5 * S, oy + h_m * S - 1.5 * S), (ox + w_m * S - 2.5 * S, oy + h_m * S - 1.5 * S)]
        leds = [(ox + 1.0 * S, oy + 1.0 * S), (ox + w_m * S - 1.0 * S, oy + 1.0 * S),
                (ox + 1.0 * S, oy + h_m * S - 1.0 * S), (ox + w_m * S - 1.0 * S, oy + h_m * S - 1.0 * S)]
        trees = [(ox + 0.7 * S, oy + 4.0 * S), (ox + w_m * S - 0.7 * S, oy + 4.0 * S),
                 (ox + 0.7 * S, oy + h_m * S - 3.0 * S), (ox + w_m * S - 0.7 * S, oy + h_m * S - 3.0 * S),
                 (cx0, oy + h_m * S - 0.7 * S)]
        shrubs = [(ox + 0.7 * S + i * 1.5 * S, oy + h_m * S - 0.6 * S) for i in range(8)]
        path = [swing_pos, central, (cx0, oy + h_m * S - 1.5 * S)]

    elif variant == "B":
        central = (ox + w_m * S * 0.38, oy + h_m * S * 0.40)
        swing_pos = (ox + w_m * S * 0.78, oy + h_m * S * 0.28)
        zip_a = (ox + w_m * S * 0.20, oy + h_m * S * 0.72)
        zip_b = (ox + w_m * S * 0.72, oy + h_m * S * 0.65)
        bench_pos = [(ox + w_m * S * 0.20, oy + h_m * S * 0.20), (ox + w_m * S * 0.92, oy + h_m * S * 0.45),
                     (ox + w_m * S * 0.40, oy + h_m * S * 0.85), (ox + w_m * S * 0.85, oy + h_m * S * 0.85)]
        leds = [(ox + 1.0 * S, oy + 1.0 * S), (ox + w_m * S * 0.95, oy + 1.0 * S),
                (ox + 1.0 * S, oy + h_m * S * 0.95), (ox + w_m * S * 0.95, oy + h_m * S * 0.95)]
        trees = [(ox + 0.7 * S, oy + 0.7 * S), (ox + w_m * S - 0.7 * S, oy + 2.0 * S),
                 (ox + 0.7 * S, oy + h_m * S - 1.5 * S), (ox + w_m * S - 0.7 * S, oy + h_m * S - 0.7 * S),
                 (ox + w_m * S * 0.5, oy + h_m * S - 0.5 * S), (ox + w_m * S * 0.30, oy + h_m * S - 1.5 * S)]
        shrubs = [(ox + w_m * S * 0.10, oy + h_m * S * 0.90), (ox + w_m * S * 0.30, oy + h_m * S * 0.95),
                  (ox + w_m * S * 0.55, oy + h_m * S * 0.95), (ox + w_m * S * 0.75, oy + h_m * S * 0.95),
                  (ox + w_m * S * 0.95, oy + h_m * S * 0.75), (ox + w_m * S * 0.05, oy + h_m * S * 0.50),
                  (ox + w_m * S * 0.50, oy + 0.5 * S), (ox + w_m * S * 0.95, oy + h_m * S * 0.55),
                  (ox + w_m * S * 0.60, oy + h_m * S * 0.05), (ox + w_m * S * 0.20, oy + h_m * S * 0.05)]
        path = [swing_pos, central, zip_a, zip_b, swing_pos]

    else:  # C
        central = (cx0, oy + h_m * S * 0.42)
        swing_pos = (cx0, oy + h_m * S * 0.78)
        zip_a = (ox + w_m * S * 0.22, oy + h_m * S * 0.70)
        zip_b = (ox + w_m * S * 0.78, oy + h_m * S * 0.70)
        bench_pos = [(ox + 1.2 * S, oy + h_m * S * 0.42), (ox + w_m * S - 1.2 * S, oy + h_m * S * 0.42),
                     (ox + 1.2 * S, oy + h_m * S * 0.70), (ox + w_m * S - 1.2 * S, oy + h_m * S * 0.70)]
        leds = [(ox + 1.0 * S, oy + 0.9 * S), (ox + w_m * S - 1.0 * S, oy + 0.9 * S),
                (ox + 1.0 * S, oy + h_m * S - 0.9 * S), (ox + w_m * S - 1.0 * S, oy + h_m * S - 0.9 * S)]
        trees = [(ox + 1.0 * S + i * 2.0 * S, oy + 0.8 * S) for i in range(5)] + \
                [(ox + 1.0 * S + i * 2.0 * S, oy + h_m * S - 0.8 * S) for i in range(5)]
        shrubs = [(ox + 0.6 * S, oy + 3.0 * S + i * 1.6 * S) for i in range(5)] + \
                 [(ox + w_m * S - 0.6 * S, oy + 3.0 * S + i * 1.6 * S) for i in range(5)]
        path = [(cx0, oy + 1.8 * S), central, swing_pos, (cx0, oy + h_m * S - 0.5 * S)]

    return _assemble(
        ox, oy, w_m, h_m,
        central=central, central_dim=("EV109", 6.36, 5.64),
        swing=swing_pos, zip_pos=[zip_a, zip_b], extra_carousel=None,
        benches=bench_pos, leds=leds, trees=trees, shrubs=shrubs, path=path,
        zone_colors_idx=[2, 0, 1, 3],
    )


def build_1003(variant: str, ox: float, oy: float) -> str:
    """HYPER 1003 — 14x18m. GM108 + TR110 cataratoare + 2x ZIP + 4 banci + 4 LED."""
    w_m, h_m = 14, 18
    cx0 = ox + w_m * S / 2
    cy0 = oy + h_m * S / 2

    if variant == "A":
        central = (cx0, cy0)
        climb_pos = (cx0, oy + 2.5 * S)
        zip_a = (ox + 2.0 * S, cy0 + 1.5 * S)
        zip_b = (ox + w_m * S - 2.0 * S, cy0 + 1.5 * S)
        bench_pos = [(ox + 1.5 * S, oy + 2.5 * S), (ox + w_m * S - 1.5 * S, oy + 2.5 * S),
                     (ox + 2.0 * S, oy + h_m * S - 2.0 * S), (ox + w_m * S - 2.0 * S, oy + h_m * S - 2.0 * S)]
        leds = [(ox + 1.0 * S, oy + 1.0 * S), (ox + w_m * S - 1.0 * S, oy + 1.0 * S),
                (ox + 1.0 * S, oy + h_m * S - 1.0 * S), (ox + w_m * S - 1.0 * S, oy + h_m * S - 1.0 * S)]
        trees = [(ox + 0.7 * S, oy + 6.0 * S), (ox + w_m * S - 0.7 * S, oy + 6.0 * S),
                 (ox + 0.7 * S, oy + h_m * S - 5.0 * S), (ox + w_m * S - 0.7 * S, oy + h_m * S - 5.0 * S),
                 (ox + 3.0 * S, oy + h_m * S - 0.7 * S), (ox + w_m * S - 3.0 * S, oy + h_m * S - 0.7 * S)]
        shrubs = [(ox + 0.6 * S + i * 1.6 * S, oy + h_m * S - 0.6 * S) for i in range(9)]
        path = [climb_pos, central, (cx0, oy + h_m * S - 1.5 * S)]

    elif variant == "B":
        central = (ox + w_m * S * 0.38, oy + h_m * S * 0.42)
        climb_pos = (ox + w_m * S * 0.75, oy + h_m * S * 0.22)
        zip_a = (ox + w_m * S * 0.20, oy + h_m * S * 0.72)
        zip_b = (ox + w_m * S * 0.72, oy + h_m * S * 0.65)
        bench_pos = [(ox + w_m * S * 0.20, oy + h_m * S * 0.20), (ox + w_m * S * 0.92, oy + h_m * S * 0.45),
                     (ox + w_m * S * 0.30, oy + h_m * S * 0.88), (ox + w_m * S * 0.85, oy + h_m * S * 0.88)]
        leds = [(ox + 1.0 * S, oy + 1.0 * S), (ox + w_m * S * 0.95, oy + 1.0 * S),
                (ox + 1.0 * S, oy + h_m * S * 0.95), (ox + w_m * S * 0.95, oy + h_m * S * 0.95)]
        trees = [(ox + 0.7 * S, oy + 0.7 * S), (ox + w_m * S - 0.7 * S, oy + 3.0 * S),
                 (ox + 0.7 * S, oy + h_m * S - 1.5 * S), (ox + w_m * S - 0.7 * S, oy + h_m * S - 0.7 * S),
                 (ox + w_m * S * 0.5, oy + h_m * S - 0.5 * S), (ox + w_m * S * 0.30, oy + h_m * S - 1.5 * S),
                 (ox + 0.7 * S, oy + h_m * S * 0.50)]
        shrubs = [(ox + w_m * S * 0.05 + i * w_m * S * 0.11, oy + h_m * S - 0.5 * S) for i in range(9)] + \
                 [(ox + w_m * S * 0.05, oy + h_m * S * 0.55), (ox + w_m * S * 0.95, oy + h_m * S * 0.55),
                  (ox + w_m * S * 0.55, oy + 0.5 * S)]
        path = [climb_pos, central, zip_a, zip_b, climb_pos]

    else:  # C
        central = (cx0, oy + h_m * S * 0.45)
        climb_pos = (cx0, oy + h_m * S * 0.78)
        zip_a = (ox + w_m * S * 0.22, oy + h_m * S * 0.72)
        zip_b = (ox + w_m * S * 0.78, oy + h_m * S * 0.72)
        bench_pos = [(ox + 1.2 * S, oy + h_m * S * 0.45), (ox + w_m * S - 1.2 * S, oy + h_m * S * 0.45),
                     (ox + 1.2 * S, oy + h_m * S * 0.72), (ox + w_m * S - 1.2 * S, oy + h_m * S * 0.72)]
        leds = [(ox + 1.0 * S, oy + 0.9 * S), (ox + w_m * S - 1.0 * S, oy + 0.9 * S),
                (ox + 1.0 * S, oy + h_m * S - 0.9 * S), (ox + w_m * S - 1.0 * S, oy + h_m * S - 0.9 * S)]
        trees = [(ox + 1.0 * S + i * 2.5 * S, oy + 0.8 * S) for i in range(5)] + \
                [(ox + 1.0 * S + i * 2.5 * S, oy + h_m * S - 0.8 * S) for i in range(5)]
        shrubs = [(ox + 0.6 * S, oy + 3.0 * S + i * 1.6 * S) for i in range(7)] + \
                 [(ox + w_m * S - 0.6 * S, oy + 3.0 * S + i * 1.6 * S) for i in range(7)]
        path = [(cx0, oy + 1.8 * S), central, climb_pos, (cx0, oy + h_m * S - 0.5 * S)]

    return _assemble(
        ox, oy, w_m, h_m,
        central=central, central_dim=("GM108", 5.35, 3.71),
        swing=None, zip_pos=[zip_a, zip_b], extra_carousel=None,
        climb_pos=climb_pos, climb_dim=("TR110", 3.12, 1.20),
        benches=bench_pos, leds=leds, trees=trees, shrubs=shrubs, path=path,
        zone_colors_idx=[3, 1, 2, 4],
    )


def _assemble(
    ox: float, oy: float, w_m: float, h_m: float, *,
    central: tuple[float, float], central_dim: tuple[str, float, float],
    swing: tuple[float, float] | None = None,
    zip_pos: list[tuple[float, float]] | None = None,
    extra_carousel: tuple[float, float] | None = None,
    climb_pos: tuple[float, float] | None = None,
    climb_dim: tuple[str, float, float] | None = None,
    benches: list[tuple[float, float]] | None = None,
    leds: list[tuple[float, float]] | None = None,
    trees: list[tuple[float, float]] | None = None,
    shrubs: list[tuple[float, float]] | None = None,
    path: list[tuple[float, float]] | None = None,
    zone_colors_idx: list[int] | None = None,
) -> str:
    parts = []
    # background plot grass
    parts.append(f'<rect x="{ox}" y="{oy}" width="{w_m * S}" height="{h_m * S}" fill="url(#grassTex)"/>')

    # EPDM zones (under equipment)
    zci = zone_colors_idx or [0, 1, 2, 3]
    parts.append(epdm_zone(central[0], central[1],
                           (central_dim[1] / 2 + 1.8) * S, (central_dim[2] / 2 + 1.8) * S,
                           EPDM_COLORS[zci[0]]))
    if swing:
        parts.append(epdm_zone(swing[0], swing[1], 3.7 * S, 2.8 * S, EPDM_COLORS[zci[1] % len(EPDM_COLORS)]))
    if extra_carousel:
        parts.append(epdm_zone(extra_carousel[0], extra_carousel[1], 2.1 * S, 2.1 * S, EPDM_COLORS[zci[2] % len(EPDM_COLORS)]))
    if climb_pos:
        parts.append(epdm_zone(climb_pos[0], climb_pos[1], 2.6 * S, 1.8 * S, EPDM_COLORS[zci[1] % len(EPDM_COLORS)]))
    for zp in zip_pos or []:
        parts.append(epdm_zone(zp[0], zp[1], 1.8 * S, 1.7 * S, EPDM_COLORS[zci[3] % len(EPDM_COLORS)]))

    # path
    if path:
        parts.append(path_bezier(path))

    # vegetation back layer
    for sx, sy in (shrubs or []):
        parts.append(shrub(sx, sy))

    # equipment
    parts.append(central_eq(central[0], central[1], central_dim[1], central_dim[2], central_dim[0]))
    if swing:
        parts.append(swing_pos_render(swing))
    if extra_carousel:
        parts.append(carousel(extra_carousel[0], extra_carousel[1]))
        parts.append(
            f'<text x="{extra_carousel[0]}" y="{extra_carousel[1] + 4 * S}" text-anchor="middle" '
            f'font-family="Arial" font-size="9" fill="#01579B" font-weight="bold">CR002</text>'
        )
    if climb_pos and climb_dim:
        parts.append(climb(climb_pos[0], climb_pos[1], climb_dim[1], climb_dim[2]))
        parts.append(
            f'<text x="{climb_pos[0]}" y="{climb_pos[1] + 1.5 * S}" text-anchor="middle" '
            f'font-family="Arial" font-size="9" fill="#33691E" font-weight="bold">{climb_dim[0]}</text>'
        )
    for i, zp in enumerate(zip_pos or []):
        col = ["#E91E63", "#03A9F4"][i % 2]
        parts.append(spring_rocker(zp[0], zp[1], col))
        parts.append(
            f'<text x="{zp[0]}" y="{zp[1] + 18}" text-anchor="middle" font-family="Arial" '
            f'font-size="8" fill="#37474F">ZIP</text>'
        )

    # benches with flowers
    for bx, by in benches or []:
        parts.append(bench(bx, by))
        parts.append(flowers(bx, by + 14))

    # LEDs
    for lx, ly in leds or []:
        parts.append(led_post(lx, ly))

    # trees on top
    for tx, ty in trees or []:
        parts.append(tree(tx, ty))

    return "\n".join(parts)


def swing_pos_render(p: tuple[float, float]) -> str:
    return swing(p[0], p[1])


# ============================================================
# Page generation
# ============================================================


def render_page(pkg_id: str, variant: str) -> str:
    cfg = PACKAGES[pkg_id]
    w_m, h_m = cfg["w"], cfg["h"]
    _, total_w, total_h, ox, oy = svg_header(w_m, h_m)

    if pkg_id == "1001":
        body = build_1001(variant, ox, oy)
    elif pkg_id == "1002":
        body = build_1002(variant, ox, oy)
    else:
        body = build_1003(variant, ox, oy)

    title = f"{cfg['title']} ({w_m}x{h_m}m)"
    vname = VARIANT_NAMES[variant]

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {total_w} {total_h}" preserveAspectRatio="xMidYMid meet" style="width:100%;height:100%;">
{defs()}
<rect width="{total_w}" height="{total_h}" fill="#F5F5F0"/>
{body}
{fence(ox, oy, w_m, h_m)}
{dim_arrows(ox, oy, w_m, h_m)}
{compass(total_w)}
{title_box(title, vname)}
{legend(total_w, total_h)}
</svg>"""

    html = f"""<!DOCTYPE html>
<html lang="ro">
<head>
<meta charset="UTF-8">
<title>{title} - {vname}</title>
<style>
@page {{ size: A3 landscape; margin: 8mm; }}
* {{ box-sizing: border-box; }}
html, body {{ margin: 0; padding: 0; background: #F5F5F0; font-family: Arial, sans-serif; }}
.page {{ width: 100%; height: 100vh; display: flex; align-items: center; justify-content: center; padding: 4mm; }}
.page svg {{ max-width: 100%; max-height: 100%; }}
@media print {{ .page {{ height: auto; padding: 0; }} }}
</style>
</head>
<body>
<div class="page">{svg}</div>
</body>
</html>"""
    return html


def write_html_files() -> list[Path]:
    paths = []
    for pkg in PACKAGES:
        pkg_dir = OUT / f"HYPER {pkg}"
        pkg_dir.mkdir(parents=True, exist_ok=True)
        for variant, label in [("A", "classic"), ("B", "asymmetric"), ("C", "linear")]:
            p = pkg_dir / f"LAYOUT_HYPER_{pkg}_{variant}_{label}.html"
            p.write_text(render_page(pkg, variant), encoding="utf-8")
            paths.append(p)
            print(f"  HTML  {p.name}  {p.stat().st_size:>6} bytes")
    return paths


def write_pdfs(html_paths: list[Path]) -> list[Path]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[WARN] playwright not installed; skipping PDF generation")
        return []
    pdf_paths = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context()
        page = ctx.new_page()
        for hp in html_paths:
            url = hp.resolve().as_uri()
            page.goto(url, wait_until="load")
            pdf_path = hp.with_suffix(".pdf")
            page.pdf(
                path=str(pdf_path),
                format="A3",
                landscape=True,
                margin={"top": "8mm", "right": "8mm", "bottom": "8mm", "left": "8mm"},
                print_background=True,
            )
            pdf_paths.append(pdf_path)
            print(f"  PDF   {pdf_path.name}  {pdf_path.stat().st_size:>7} bytes")
        browser.close()
    return pdf_paths


def main() -> int:
    print(f"[regen_layouts] OUT={OUT}")
    OUT.mkdir(parents=True, exist_ok=True)
    htmls = write_html_files()
    print(f"[regen_layouts] {len(htmls)} HTML files written")
    pdfs = write_pdfs(htmls)
    print(f"[regen_layouts] {len(pdfs)} PDF files written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
