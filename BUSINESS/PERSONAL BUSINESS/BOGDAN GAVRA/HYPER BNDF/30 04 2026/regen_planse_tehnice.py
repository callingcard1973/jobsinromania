#!/usr/bin/env python3
"""Regenerate technical planse HTML files - Stilul Bun (warm family park style).

Adaugă elemente decorative: tufe, pomi ornamentali, flori, alei pavate curbe,
gazon, imprejmuire perimetrala cu poarta, conuri lumina LED, roza vanturilor.
Idempotent - se poate rula de mai multe ori, regenereaza fisierele HTML.
"""
import os
import random

BASE = r"D:\MEMORY\BUSINESS\PERSONAL BUSINESS\BOGDAN GAVRA\HYPER BNDF\30 04 2026"
PLANSE_DIR = os.path.join(BASE, "CATALOG", "PLANSE TEHNICE")

# ----- Configuratie pachete (dimensiuni & layout echipamente fixed) -----
PACKAGES = {
    "HYPER 1001": {
        "sku": "HYPER-1001-EV101-SET",
        "suprafata_m": "10 x 12 m",
        "suprafata_mp": "120",
        "render": "RENDER_HYPER_1001.png",
        "scale": "1:100",
        "decor_seed": 1001,
        "components_layout": [
            {"name": "EV101", "label": "Piesa Centrala EV101", "x": 35, "y": 20, "w": 25, "h": 20, "color": "#2D5F8F", "desc": "6.16 x 4.55 m"},
            {"name": "SE001", "label": "Leagane Dublu", "x": 75, "y": 25, "w": 14, "h": 12, "color": "#E67E22", "desc": "3.40 x 2.65 m"},
            {"name": "ZIP", "label": "Balansoar ZIP", "x": 78, "y": 55, "w": 5, "h": 5, "color": "#27AE60", "desc": "0.62 x 0.46 m"},
            {"name": "CR002", "label": "Carusel", "x": 15, "y": 55, "w": 10, "h": 10, "color": "#8E44AD", "desc": "D 2.15 m"},
            {"name": "B1", "label": "Banca 1", "x": 5, "y": 10, "w": 6, "h": 2, "color": "#7F8C8D", "desc": "1.80 x 0.45 m"},
            {"name": "B2", "label": "Banca 2", "x": 88, "y": 75, "w": 6, "h": 2, "color": "#7F8C8D", "desc": "1.80 x 0.45 m"},
            {"name": "L1", "label": "Stalp LED 1", "x": 2, "y": 45, "w": 2, "h": 2, "color": "#F39C12", "desc": "LED parc"},
            {"name": "L2", "label": "Stalp LED 2", "x": 95, "y": 15, "w": 2, "h": 2, "color": "#F39C12", "desc": "LED parc"},
        ],
    },
    "HYPER 1002": {
        "sku": "HYPER-1002-EV109-SET",
        "suprafata_m": "12 x 14 m",
        "suprafata_mp": "168",
        "render": "RENDER_HYPER_1002.png",
        "scale": "1:100",
        "decor_seed": 1002,
        "components_layout": [
            {"name": "EV109", "label": "Piesa Centrala EV109", "x": 30, "y": 15, "w": 28, "h": 24, "color": "#2D5F8F", "desc": "6.36 x 5.64 m"},
            {"name": "SE001", "label": "Leagane Dublu", "x": 72, "y": 20, "w": 14, "h": 12, "color": "#E67E22", "desc": "3.40 x 2.65 m"},
            {"name": "ZIP1", "label": "Balansoar ZIP 1", "x": 75, "y": 50, "w": 5, "h": 5, "color": "#27AE60", "desc": "0.62 x 0.46 m"},
            {"name": "ZIP2", "label": "Balansoar ZIP 2", "x": 75, "y": 60, "w": 5, "h": 5, "color": "#27AE60", "desc": "0.62 x 0.46 m"},
            {"name": "B1", "label": "Banca 1", "x": 3, "y": 8, "w": 6, "h": 2, "color": "#7F8C8D", "desc": "1.80 x 0.45 m"},
            {"name": "B2", "label": "Banca 2", "x": 90, "y": 8, "w": 6, "h": 2, "color": "#7F8C8D", "desc": "1.80 x 0.45 m"},
            {"name": "B3", "label": "Banca 3", "x": 3, "y": 80, "w": 6, "h": 2, "color": "#7F8C8D", "desc": "1.80 x 0.45 m"},
            {"name": "B4", "label": "Banca 4", "x": 90, "y": 80, "w": 6, "h": 2, "color": "#7F8C8D", "desc": "1.80 x 0.45 m"},
            {"name": "L1", "label": "LED 1", "x": 1, "y": 40, "w": 2, "h": 2, "color": "#F39C12", "desc": "LED"},
            {"name": "L2", "label": "LED 2", "x": 97, "y": 40, "w": 2, "h": 2, "color": "#F39C12", "desc": "LED"},
            {"name": "L3", "label": "LED 3", "x": 50, "y": 1, "w": 2, "h": 2, "color": "#F39C12", "desc": "LED"},
            {"name": "L4", "label": "LED 4", "x": 50, "y": 96, "w": 2, "h": 2, "color": "#F39C12", "desc": "LED"},
        ],
    },
    "HYPER 1003": {
        "sku": "HYPER-1003-GM108-TR110-SET",
        "suprafata_m": "14 x 18 m",
        "suprafata_mp": "252",
        "render": "RENDER_HYPER_1003.png",
        "scale": "1:100",
        "decor_seed": 1003,
        "components_layout": [
            {"name": "GM108", "label": "Piesa Centrala GM108", "x": 25, "y": 10, "w": 25, "h": 20, "color": "#2D5F8F", "desc": "5.35 x 3.71 m"},
            {"name": "TR110", "label": "Cataratoare TR110", "x": 60, "y": 15, "w": 15, "h": 8, "color": "#C0392B", "desc": "3.12 x 1.20 m"},
            {"name": "ZIP1", "label": "Balansoar ZIP 1", "x": 78, "y": 35, "w": 5, "h": 5, "color": "#27AE60", "desc": "0.62 x 0.46 m"},
            {"name": "ZIP2", "label": "Balansoar ZIP 2", "x": 78, "y": 45, "w": 5, "h": 5, "color": "#27AE60", "desc": "0.62 x 0.46 m"},
            {"name": "B1", "label": "Banca 1", "x": 3, "y": 5, "w": 6, "h": 2, "color": "#7F8C8D", "desc": "1.80 x 0.45 m"},
            {"name": "B2", "label": "Banca 2", "x": 90, "y": 5, "w": 6, "h": 2, "color": "#7F8C8D", "desc": "1.80 x 0.45 m"},
            {"name": "B3", "label": "Banca 3", "x": 3, "y": 85, "w": 6, "h": 2, "color": "#7F8C8D", "desc": "1.80 x 0.45 m"},
            {"name": "B4", "label": "Banca 4", "x": 90, "y": 85, "w": 6, "h": 2, "color": "#7F8C8D", "desc": "1.80 x 0.45 m"},
            {"name": "B5", "label": "Banca 5", "x": 30, "y": 92, "w": 6, "h": 2, "color": "#7F8C8D", "desc": "1.80 x 0.45 m"},
            {"name": "B6", "label": "Banca 6", "x": 60, "y": 92, "w": 6, "h": 2, "color": "#7F8C8D", "desc": "1.80 x 0.45 m"},
            {"name": "L1", "label": "LED 1", "x": 1, "y": 30, "w": 2, "h": 2, "color": "#F39C12", "desc": "LED"},
            {"name": "L2", "label": "LED 2", "x": 97, "y": 30, "w": 2, "h": 2, "color": "#F39C12", "desc": "LED"},
        ],
    },
}

MATERIALE_NOTE = [
    "Tuburi metalice O76x76x3mm - galvanizate si acoperite cu pulbere epoxidica",
    "Tuburi O48x48x2.5mm si O42x42x2mm - structura secundara",
    "HPL (High Pressure Laminate) 19mm - panouri decorative",
    "Podea HDPE - platforme si accese",
    "Acoperis policarbonat - protectie UV",
    "Elemente turnate din aluminiu - imbinari",
    "Accesorii din otel inox - prinderi si fixari",
    "Suprafata de siguranta: EPDM 10-15mm + SBR 40-50mm conform EN 1177",
    "Borduri elastice: 100x25x5 cm - delimitare suprafata",
    "Vegetatie ornamentala: tufe, pomi, flori - integrata peisagistic",
    "Alei pavate curbe - dale beton 40x40 cm sau pavaj decorativ",
]

# ----- Decor palettes (Stilul Bun: naturals, NO neon) -----
BUSH_COLORS = ["#7CB342", "#9CCC65", "#C0CA33", "#8BC34A"]
TREE_CROWN = ["#558B2F", "#689F38", "#33691E"]
TREE_TRUNK = "#5D4037"
FLOWER_COLORS = ["#F8BBD0", "#FFE082", "#CE93D8", "#80DEEA", "#FFAB91", "#F48FB1"]
LAWN = "#DCEDC8"
PATH_COLOR = "#D7CCC8"
FENCE_COLOR = "#6D4C41"


def is_in_equipment(cx, cy, components, padding=15):
    """Check if a point overlaps any equipment bounding box."""
    for comp in components:
        x = comp["x"] * 10
        y = comp["y"] * 10
        w = comp["w"] * 10
        h = comp["h"] * 10
        if (x - padding) < cx < (x + w + padding) and (y - padding) < cy < (y + h + padding):
            return True
    return False


def generate_decor(components, seed):
    """Generate bushes, trees, flowers respecting equipment positions."""
    rng = random.Random(seed)
    bushes, trees, flowers = [], [], []

    # Bushes around perimeter (8-10)
    perimeter_zones = [
        (50, 950, 30, 80), (50, 950, 920, 970),
        (30, 80, 50, 950), (920, 970, 50, 950),
    ]
    attempts = 0
    while len(bushes) < 10 and attempts < 60:
        attempts += 1
        zx1, zx2, zy1, zy2 = rng.choice(perimeter_zones)
        cx = rng.randint(zx1, zx2)
        cy = rng.randint(zy1, zy2)
        if is_in_equipment(cx, cy, components, padding=8):
            continue
        rx = rng.randint(10, 18)
        ry = rng.randint(8, 14)
        bushes.append({"cx": cx, "cy": cy, "rx": rx, "ry": ry, "color": rng.choice(BUSH_COLORS)})

    # Pomi ornamentali (4-5) - corners and a few mid-points
    tree_spots = [(60, 60), (940, 60), (60, 940), (940, 940), (500, 50), (500, 950)]
    rng.shuffle(tree_spots)
    for cx, cy in tree_spots[:5]:
        if not is_in_equipment(cx, cy, components, padding=20):
            r = rng.randint(20, 28)
            trees.append({"cx": cx, "cy": cy, "r": r, "crown": rng.choice(TREE_CROWN)})

    # Flori - clustere langa banci si pe alei
    for comp in components:
        if "Banca" in comp["label"]:
            bx = comp["x"] * 10 + comp["w"] * 5
            by = comp["y"] * 10
            for _ in range(rng.randint(4, 6)):
                fx = bx + rng.randint(-25, 25)
                fy = by + rng.randint(15, 35) * (1 if by < 500 else -1)
                if 20 < fx < 980 and 20 < fy < 980 and not is_in_equipment(fx, fy, components, padding=5):
                    flowers.append({"cx": fx, "cy": fy, "color": rng.choice(FLOWER_COLORS)})

    return bushes, trees, flowers


def render_decor_svg(bushes, trees, flowers):
    """SVG markup for vegetation layer (rendered BEFORE equipment)."""
    out = []
    # Gazon (lawn) base
    out.append('<rect x="0" y="0" width="1000" height="1000" fill="' + LAWN + '"/>')
    # Imprejmuire (fence) - 3 rectangles for triple-bar effect, with gate gap
    out.append('<rect x="10" y="10" width="980" height="980" fill="none" stroke="' + FENCE_COLOR + '" stroke-width="3"/>')
    out.append('<rect x="14" y="14" width="972" height="972" fill="none" stroke="' + FENCE_COLOR + '" stroke-width="1.5" stroke-dasharray="2,3"/>')
    # Gate (gap on south side, marked)
    out.append('<rect x="450" y="985" width="100" height="14" fill="' + LAWN + '"/>')
    out.append('<line x1="450" y1="992" x2="550" y2="992" stroke="' + FENCE_COLOR + '" stroke-width="1.5" stroke-dasharray="3,2"/>')
    out.append('<text x="500" y="1008" text-anchor="middle" font-family="Arial" font-size="9" fill="#5D4037" font-weight="bold">INTRARE</text>')

    # Alee pavata curba: bezier de la poarta la centru si laterale
    out.append('<path d="M 500 985 Q 500 700 350 500 Q 200 350 100 200" '
               'fill="none" stroke="' + PATH_COLOR + '" stroke-width="22" stroke-linecap="round" opacity="0.95"/>')
    out.append('<path d="M 500 985 Q 500 700 350 500 Q 200 350 100 200" '
               'fill="none" stroke="#FFFFFF" stroke-width="1.2" stroke-dasharray="6,8" opacity="0.7"/>')
    out.append('<path d="M 500 985 Q 600 750 750 600 Q 870 480 920 350" '
               'fill="none" stroke="' + PATH_COLOR + '" stroke-width="22" stroke-linecap="round" opacity="0.95"/>')
    out.append('<path d="M 500 985 Q 600 750 750 600 Q 870 480 920 350" '
               'fill="none" stroke="#FFFFFF" stroke-width="1.2" stroke-dasharray="6,8" opacity="0.7"/>')

    # Tufe
    for b in bushes:
        out.append('<ellipse cx="' + str(b["cx"]) + '" cy="' + str(b["cy"]) + '" rx="' + str(b["rx"]) +
                   '" ry="' + str(b["ry"]) + '" fill="' + b["color"] + '" fill-opacity="0.85" stroke="#558B2F" stroke-width="0.6"/>')

    # Pomi ornamentali (coroana + trunchi)
    for t in trees:
        out.append('<circle cx="' + str(t["cx"]) + '" cy="' + str(t["cy"]) + '" r="' + str(t["r"]) +
                   '" fill="' + t["crown"] + '" fill-opacity="0.85" stroke="#33691E" stroke-width="0.8"/>')
        out.append('<circle cx="' + str(t["cx"]) + '" cy="' + str(t["cy"]) + '" r="' + str(int(t["r"] * 0.25)) +
                   '" fill="' + TREE_TRUNK + '"/>')

    # Flori (clustere mici)
    for f in flowers:
        out.append('<circle cx="' + str(f["cx"]) + '" cy="' + str(f["cy"]) + '" r="2.2" fill="' + f["color"] + '" stroke="#FFF" stroke-width="0.3"/>')

    return "\n".join(out)


def render_compass(x=940, y=60):
    """Compass rose - drafting style, small."""
    return ('<g transform="translate(' + str(x) + ',' + str(y) + ')">'
            '<circle r="22" fill="#FFFFFF" stroke="#5D4037" stroke-width="1"/>'
            '<polygon points="0,-20 5,0 0,20 -5,0" fill="#5D4037"/>'
            '<polygon points="0,-20 5,0 0,0" fill="#37474F"/>'
            '<text y="-26" text-anchor="middle" font-family="Arial" font-size="11" fill="#37474F" font-weight="bold">N</text>'
            '<text y="32" text-anchor="middle" font-family="Arial" font-size="8" fill="#888">S</text>'
            '<text x="-28" y="3" text-anchor="middle" font-family="Arial" font-size="8" fill="#888">V</text>'
            '<text x="28" y="3" text-anchor="middle" font-family="Arial" font-size="8" fill="#888">E</text>'
            '</g>')


def render_equipment_svg(components):
    """SVG markup for equipment layer (top of decor)."""
    out = []
    out.append('<defs>')
    out.append('  <radialGradient id="ledGlow"><stop offset="0%" stop-color="#FFF59D" stop-opacity="0.6"/><stop offset="100%" stop-color="#FFF59D" stop-opacity="0"/></radialGradient>')
    out.append('  <marker id="arrow" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto">')
    out.append('    <path d="M0,0 L0,6 L9,3 z" fill="#333"/>')
    out.append('  </marker>')
    out.append('</defs>')

    for comp in components:
        color = comp["color"]
        x = comp["x"] * 10
        y = comp["y"] * 10
        w = comp["w"] * 10
        h = comp["h"] * 10

        if "Carusel" in comp["label"]:
            cx, cy, r = x + w / 2, y + h / 2, w / 2
            out.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{color}" fill-opacity="0.7" stroke="{color}" stroke-width="1.5"/>')
        elif "Banca" in comp["label"]:
            out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="#8D6E63" fill-opacity="0.95" stroke="#3E2723" stroke-width="1" rx="2"/>')
        elif "LED" in comp["label"]:
            cx, cy = x + w / 2, y + h / 2
            # Cone of light
            out.append(f'<circle cx="{cx}" cy="{cy}" r="40" fill="url(#ledGlow)"/>')
            out.append(f'<circle cx="{cx}" cy="{cy}" r="6" fill="#F39C12" stroke="#E67E22" stroke-width="1"/>')
            out.append(f'<line x1="{cx}" y1="{cy - 10}" x2="{cx}" y2="{cy + 10}" stroke="#37474F" stroke-width="2"/>')
        elif "ZIP" in comp["label"] or "Balansoar" in comp["label"]:
            out.append(f'<ellipse cx="{x + w / 2}" cy="{y + h / 2}" rx="{w / 2}" ry="{h / 2}" fill="{color}" fill-opacity="0.7" stroke="{color}" stroke-width="1.5"/>')
        elif "Cataratoare" in comp["label"]:
            out.append(f'<polygon points="{x},{y + h} {x + w / 2},{y} {x + w},{y + h}" fill="{color}" fill-opacity="0.6" stroke="{color}" stroke-width="1.5"/>')
        else:
            out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{color}" fill-opacity="0.45" stroke="{color}" stroke-width="2" rx="3"/>')
            if "Piesa" in comp["label"]:
                for i in range(0, int(w), 20):
                    out.append(f'<line x1="{x + i}" y1="{y}" x2="{x + i}" y2="{y + h}" stroke="{color}" stroke-width="0.3" opacity="0.4"/>')
                for j in range(0, int(h), 20):
                    out.append(f'<line x1="{x}" y1="{y + j}" x2="{x + w}" y2="{y + j}" stroke="{color}" stroke-width="0.3" opacity="0.4"/>')

        font_size = max(8, min(11, w / 3))
        out.append(f'<text x="{x + w / 2}" y="{y + h / 2 + 4}" text-anchor="middle" font-family="Arial" font-size="{font_size}" fill="#1A1A1A" font-weight="bold">{comp["name"]}</text>')

        if "Piesa" in comp["label"] or "Cataratoare" in comp["label"] or "Leagane" in comp["label"]:
            dim_y = y - 12
            out.append(f'<line x1="{x}" y1="{dim_y}" x2="{x + w}" y2="{dim_y}" stroke="#333" stroke-width="0.8" marker-start="url(#arrow)" marker-end="url(#arrow)"/>')
            desc_parts = comp["desc"].split("x")
            dim_label = desc_parts[0] if desc_parts else comp["desc"]
            out.append(f'<text x="{x + w / 2}" y="{dim_y - 3}" text-anchor="middle" font-family="Arial" font-size="9" fill="#C0392B" font-weight="bold">{dim_label}</text>')

    # Scale bar
    out.append('<line x1="800" y1="970" x2="950" y2="970" stroke="#333" stroke-width="2"/>')
    out.append('<text x="875" y="962" text-anchor="middle" font-family="Arial" font-size="10" fill="#333">5 m</text>')
    return "\n".join(out)


def build_html(pkg_name, pkg):
    components = pkg["components_layout"]
    render_path = "../../MEDIA/RENDER/" + pkg["render"]
    bushes, trees, flowers = generate_decor(components, pkg["decor_seed"])
    decor_svg = render_decor_svg(bushes, trees, flowers)
    equip_svg = render_equipment_svg(components)
    compass_svg = render_compass()

    legend_rows = ""
    for comp in components:
        legend_rows += ('<tr><td style="width:18px;text-align:center;"><span style="display:inline-block;width:12px;height:12px;background:'
                        + comp["color"] + ';border-radius:2px;"></span></td><td style="font-size:8.5pt;">'
                        + comp["label"] + '</td><td style="font-size:7.5pt;color:#666;">' + comp["desc"] + '</td></tr>')
    decor_legend = (
        '<tr><td style="text-align:center;"><span style="display:inline-block;width:12px;height:12px;background:' + BUSH_COLORS[0] + ';border-radius:50%;"></span></td><td style="font-size:8.5pt;">Tufe ornamentale</td><td style="font-size:7.5pt;color:#666;">' + str(len(bushes)) + ' buc.</td></tr>'
        '<tr><td style="text-align:center;"><span style="display:inline-block;width:12px;height:12px;background:' + TREE_CROWN[0] + ';border-radius:50%;"></span></td><td style="font-size:8.5pt;">Pomi ornamentali</td><td style="font-size:7.5pt;color:#666;">' + str(len(trees)) + ' buc.</td></tr>'
        '<tr><td style="text-align:center;"><span style="display:inline-block;width:12px;height:12px;background:' + FLOWER_COLORS[0] + ';border-radius:50%;"></span></td><td style="font-size:8.5pt;">Flori (clustere)</td><td style="font-size:7.5pt;color:#666;">' + str(len(flowers)) + ' buc.</td></tr>'
        '<tr><td style="text-align:center;"><span style="display:inline-block;width:12px;height:6px;background:' + PATH_COLOR + ';"></span></td><td style="font-size:8.5pt;">Alei pavate curbe</td><td style="font-size:7.5pt;color:#666;">dale beton</td></tr>'
        '<tr><td style="text-align:center;"><span style="display:inline-block;width:12px;height:12px;background:' + LAWN + ';border:1px solid #999;"></span></td><td style="font-size:8.5pt;">Gazon</td><td style="font-size:7.5pt;color:#666;">' + pkg["suprafata_mp"] + ' m2</td></tr>'
        '<tr><td style="text-align:center;"><span style="display:inline-block;width:12px;height:12px;background:' + FENCE_COLOR + ';"></span></td><td style="font-size:8.5pt;">Imprejmuire perimetrala</td><td style="font-size:7.5pt;color:#666;">cu poarta intrare</td></tr>'
    )
    legend_rows = decor_legend + legend_rows

    materiale_rows = ""
    for i, m in enumerate(MATERIALE_NOTE):
        bg = "#F5F5F5" if i % 2 == 0 else "#FFFFFF"
        materiale_rows += ('<tr style="background:' + bg + ';"><td style="padding:4px 8px;font-size:8pt;border-bottom:1px solid #E0E0E0;">'
                           + str(i + 1) + '</td><td style="padding:4px 8px;font-size:8pt;border-bottom:1px solid #E0E0E0;">' + m + '</td></tr>')

    return f'''<!DOCTYPE html>
<html lang="ro">
<head>
<meta charset="UTF-8">
<title>Plansa Tehnica {pkg_name} - HYPER BNDF SRL</title>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  @page {{ size: A3 landscape; margin: 0; }}
  body {{ font-family: Arial, Helvetica, sans-serif; width: 420mm; height: 297mm; background: #FFFFFF; color: #333; }}
  .page {{ width: 420mm; height: 297mm; display: flex; flex-direction: column; padding: 10mm; }}
  .header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 3px solid #2D5F8F; padding-bottom: 5mm; margin-bottom: 5mm; }}
  .header-left h1 {{ font-size: 16pt; color: #2D5F8F; margin: 0; }}
  .header-left p {{ font-size: 9pt; color: #666; margin: 2px 0 0 0; }}
  .header-right {{ text-align: right; }}
  .header-right .sku {{ font-size: 11pt; font-weight: bold; color: #2D5F8F; }}
  .header-right .scale {{ font-size: 9pt; color: #666; }}
  .main {{ display: flex; flex: 1; gap: 8mm; }}
  .drawing-area {{ flex: 1.6; border: 1px solid #CCC; background: #FAFAFA; position: relative; min-height: 0; }}
  .drawing-area svg {{ width: 100%; height: 100%; }}
  .sidebar {{ flex: 1; display: flex; flex-direction: column; gap: 5mm; }}
  .panel {{ border: 1px solid #DDD; border-radius: 4px; overflow: hidden; }}
  .panel-title {{ background: #2D5F8F; color: #FFF; padding: 5px 10px; font-size: 9pt; font-weight: bold; }}
  .panel table {{ width: 100%; border-collapse: collapse; }}
  .panel td {{ padding: 3px 8px; }}
  .legend-table td {{ border-bottom: 1px solid #F0F0F0; }}
  .render-img {{ width: 100%; height: auto; display: block; border: 1px solid #DDD; }}
  .footer {{ margin-top: auto; display: flex; justify-content: space-between; align-items: center; border-top: 2px solid #2D5F8F; padding-top: 4mm; font-size: 8pt; color: #666; }}
  .footer strong {{ color: #2D5F8F; font-size: 9pt; }}
  .suprafata-info {{ background: #E8F5E9; padding: 6px 10px; border-left: 3px solid #4CAF50; margin: 4px 0; font-size: 8pt; }}
  .suprafata-info strong {{ color: #2E7D32; }}
</style>
</head>
<body>
<div class="page">
  <div class="header">
    <div class="header-left">
      <h1>HYPER BNDF SRL</h1>
      <p>CUI RO33286554 | Calea Serban Voda 234, Sector 4, Bucuresti</p>
      <p>Plansa Tehnica - Amplasare Echipamente &amp; Amenajare Peisagistica</p>
    </div>
    <div class="header-right">
      <div class="sku">{pkg_name}</div>
      <div class="scale">Scara: {pkg["scale"]} | Format: A3</div>
      <div class="scale">Suprafata: {pkg["suprafata_m"]} ({pkg["suprafata_mp"]} m2)</div>
      <div class="scale">Data: 30.04.2026</div>
    </div>
  </div>

  <div class="main">
    <div class="drawing-area">
      <svg viewBox="-30 -30 1060 1080" xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="xMidYMid meet">
{decor_svg}
{equip_svg}
{compass_svg}
      </svg>
    </div>

    <div class="sidebar">
      <div class="panel">
        <div class="panel-title">DATE TEHNICE</div>
        <div style="padding:6px 10px;">
          <div class="suprafata-info">
            <strong>Suprafata totala:</strong> {pkg["suprafata_m"]} ({pkg["suprafata_mp"]} m2)<br>
            <strong>Zona siguranta EPDM+SBR:</strong> conform EN 1177<br>
            <strong>Strat EPDM:</strong> 10-15 mm | <strong>SBR:</strong> 40-50 mm<br>
            <strong>Amenajare peisagistica:</strong> tufe, pomi, flori, alei pavate, gazon
          </div>
        </div>
      </div>

      <div class="panel" style="flex:1;">
        <div class="panel-title">LEGENDA</div>
        <table class="legend-table">{legend_rows}</table>
      </div>

      <div class="panel">
        <div class="panel-title">MATERIALE</div>
        <table>{materiale_rows}</table>
      </div>

      <div class="panel">
        <div class="panel-title">RENDER 3D</div>
        <img src="{render_path}" alt="Render {pkg_name}" class="render-img">
      </div>
    </div>
  </div>

  <div class="footer">
    <div>
      <strong>HYPER BNDF SRL</strong> | Locuri de Joaca &amp; Spatii Verzi<br>
      Bogdan Gavra | +40721944281 | gavrabogdan@yahoo.com
    </div>
    <div style="text-align:right;">
      Plansa Tehnica {pkg_name} | Pagina 1/1<br>
      Suprafata de siguranta: EPDM + SBR conform EN 1177 | Stilul Bun - parc familial
    </div>
  </div>
</div>
</body>
</html>'''


if __name__ == "__main__":
    for pkg_name, pkg in PACKAGES.items():
        html = build_html(pkg_name, pkg)
        path = os.path.join(PLANSE_DIR, pkg_name, "PLANSA_TEHNICA_" + pkg_name.replace(" ", "_") + ".html")
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
        print("OK: " + path)
    print("Done - planse tehnice regenerate cu Stilul Bun (decor + equipment)")
