#!/usr/bin/env python3
"""Regenerate technical planse HTML files (deleted by mistake)."""
import os

BASE = r"D:\MEMORY\BUSINESS\PERSONAL BUSINESS\BOGDAN GAVRA\HYPER BNDF\30 04 2026"
PLANSE_DIR = os.path.join(BASE, "CATALOG", "PLANSE TEHNICE")
RENDER_DIR = os.path.join(BASE, "MEDIA", "RENDER")

PACKAGES = {
    "HYPER 1001": {
        "sku": "HYPER-1001-EV101-SET",
        "suprafata_m": "10 x 12 m",
        "suprafata_mp": "120",
        "render": "RENDER_HYPER_1001.png",
        "scale": "1:100",
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
        "components_layout": [
            {"name": "GM108", "label": "Piesa Centrala GM108", "x": 25, "y": 10, "w": 25, "h": 20, "color": "#2D5F8F", "desc": "5.35 x 3.71 m"},
            {"name": "TR110", "label": "Cataramatoare TR110", "x": 60, "y": 15, "w": 15, "h": 8, "color": "#C0392B", "desc": "3.12 x 1.20 m"},
            {"name": "ZIP1", "label": "Balansoar ZIP 1", "x": 78, "y": 35, "w": 5, "h": 5, "color": "#27AE60", "desc": "0.62 x 0.46 m"},
            {"name": "ZIP2", "label": "Balansoar ZIP 2", "x": 78, "y": 45, "w": 5, "h": 5, "color": "#27AE60", "desc": "0.62 x 0.46 m"},
            {"name": "B1", "label": "Banca 1", "x": 3, "y": 5, "w": 6, "h": 2, "color": "#7F8C8D", "desc": "1.80 x 0.45 m"},
            {"name": "B2", "label": "Banca 2", "x": 90, "y": 5, "w": 6, "h": 2, "color": "#7F8C8D", "desc": "1.80 x 0.45 m"},
            {"name": "B3", "label": "Banca 3", "x": 3, "y": 85, "w": 6, "h": 2, "color": "#7F8C8D", "desc": "1.80 x 0.45 m"},
            {"name": "B4", "label": "Banca 4", "x": 90, "y": 85, "w": 6, "h": 2, "color": "#7F8C8D", "desc": "1.80 x 0.45 m"},
            {"name": "L1", "label": "LED 1", "x": 1, "y": 30, "w": 2, "h": 2, "color": "#F39C12", "desc": "LED"},
            {"name": "L2", "label": "LED 2", "x": 97, "y": 30, "w": 2, "h": 2, "color": "#F39C12", "desc": "LED"},
            {"name": "L3", "label": "LED 3", "x": 1, "y": 65, "w": 2, "h": 2, "color": "#F39C12", "desc": "LED"},
            {"name": "L4", "label": "LED 4", "x": 97, "y": 65, "w": 2, "h": 2, "color": "#F39C12", "desc": "LED"},
            {"name": "T1", "label": "Arbore 1", "x": 8, "y": 70, "w": 4, "h": 4, "color": "#27AE60", "desc": "Arbore ornamental"},
            {"name": "T2", "label": "Arbore 2", "x": 88, "y": 70, "w": 4, "h": 4, "color": "#27AE60", "desc": "Arbore ornamental"},
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
    "Suprafata de siguranta: EPDM 10-15mm + SBR 40-50mm conform AVP Park (Zemin Kaplamalari), EN1177",
    "Borduri elastice: 100x25x5 cm - delimitare suprafata",
]


def generate_plansa_html(pkg_name, pkg):
    components = pkg["components_layout"]
    render_path = "../../MEDIA/RENDER/" + pkg["render"]

    svg_elements = []
    svg_elements.append('<defs>')
    svg_elements.append('  <pattern id="grid" width="50" height="50" patternUnits="userSpaceOnUse">')
    svg_elements.append('    <path d="M 50 0 L 0 0 0 50" fill="none" stroke="#E0E0E0" stroke-width="0.5"/>')
    svg_elements.append('  </pattern>')
    svg_elements.append('  <marker id="arrow" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto">')
    svg_elements.append('    <path d="M0,0 L0,6 L9,3 z" fill="#333"/>')
    svg_elements.append('  </marker>')
    svg_elements.append('</defs>')

    svg_elements.append('<rect width="100%" height="100%" fill="url(#grid)"/>')
    svg_elements.append('<rect x="0" y="0" width="1000" height="1000" fill="#E8F5E9" stroke="#4CAF50" stroke-width="2" stroke-dasharray="8,4"/>')
    svg_elements.append('<rect x="-20" y="-20" width="1040" height="1040" fill="none" stroke="#FF9800" stroke-width="1.5" stroke-dasharray="5,5"/>')

    for comp in components:
        color = comp["color"]
        x = comp["x"] * 10
        y = comp["y"] * 10
        w = comp["w"] * 10
        h = comp["h"] * 10

        if "Carusel" in comp["label"]:
            cx = x + w/2
            cy = y + h/2
            r = w/2
            svg_elements.append('<circle cx="' + str(cx) + '" cy="' + str(cy) + '" r="' + str(r) + '" fill="' + color + '" fill-opacity="0.6" stroke="' + color + '" stroke-width="1.5"/>')
        elif "Arbore" in comp["label"]:
            cx = x + w/2
            cy = y + h/2
            r = w/2
            svg_elements.append('<circle cx="' + str(cx) + '" cy="' + str(cy) + '" r="' + str(r) + '" fill="#27AE60" fill-opacity="0.5" stroke="#1B7A3D" stroke-width="1"/>')
            svg_elements.append('<circle cx="' + str(cx) + '" cy="' + str(cy) + '" r="' + str(r*0.3) + '" fill="#8B4513"/>')
        elif "Banca" in comp["label"]:
            svg_elements.append('<rect x="' + str(x) + '" y="' + str(y) + '" width="' + str(w) + '" height="' + str(h) + '" fill="' + color + '" fill-opacity="0.7" stroke="#555" stroke-width="1" rx="2"/>')
        elif "LED" in comp["label"]:
            cx = x + w/2
            cy = y + h/2
            svg_elements.append('<circle cx="' + str(cx) + '" cy="' + str(cy) + '" r="8" fill="#F39C12" fill-opacity="0.8" stroke="#E67E22" stroke-width="1"/>')
            svg_elements.append('<line x1="' + str(cx) + '" y1="' + str(cy-12) + '" x2="' + str(cx) + '" y2="' + str(cy+12) + '" stroke="#555" stroke-width="2"/>')
        elif "ZIP" in comp["label"]:
            svg_elements.append('<ellipse cx="' + str(x+w/2) + '" cy="' + str(y+h/2) + '" rx="' + str(w/2) + '" ry="' + str(h/2) + '" fill="' + color + '" fill-opacity="0.6" stroke="' + color + '" stroke-width="1.5"/>')
        elif "Cataramatoare" in comp["label"]:
            svg_elements.append('<polygon points="' + str(x) + ',' + str(y+h) + ' ' + str(x+w/2) + ',' + str(y) + ' ' + str(x+w) + ',' + str(y+h) + '" fill="' + color + '" fill-opacity="0.5" stroke="' + color + '" stroke-width="1.5"/>')
        else:
            svg_elements.append('<rect x="' + str(x) + '" y="' + str(y) + '" width="' + str(w) + '" height="' + str(h) + '" fill="' + color + '" fill-opacity="0.35" stroke="' + color + '" stroke-width="2" rx="3"/>')
            if "Piesa" in comp["label"]:
                for i in range(0, int(w), 20):
                    svg_elements.append('<line x1="' + str(x+i) + '" y1="' + str(y) + '" x2="' + str(x+i) + '" y2="' + str(y+h) + '" stroke="' + color + '" stroke-width="0.3" opacity="0.4"/>')
                for j in range(0, int(h), 20):
                    svg_elements.append('<line x1="' + str(x) + '" y1="' + str(y+j) + '" x2="' + str(x+w) + '" y2="' + str(y+j) + '" stroke="' + color + '" stroke-width="0.3" opacity="0.4"/>')

        font_size = max(8, min(11, w/3))
        svg_elements.append('<text x="' + str(x+w/2) + '" y="' + str(y+h/2+4) + '" text-anchor="middle" font-family="Arial" font-size="' + str(font_size) + '" fill="#333" font-weight="bold">' + comp["name"] + '</text>')

        if "Piesa" in comp["label"] or "Cataramatoare" in comp["label"] or "Leagane" in comp["label"]:
            dim_y = y - 12
            svg_elements.append('<line x1="' + str(x) + '" y1="' + str(dim_y) + '" x2="' + str(x+w) + '" y2="' + str(dim_y) + '" stroke="#333" stroke-width="0.8" marker-start="url(#arrow)" marker-end="url(#arrow)"/>')
            svg_elements.append('<line x1="' + str(x) + '" y1="' + str(y) + '" x2="' + str(x) + '" y2="' + str(dim_y+3) + '" stroke="#333" stroke-width="0.5"/>')
            svg_elements.append('<line x1="' + str(x+w) + '" y1="' + str(y) + '" x2="' + str(x+w) + '" y2="' + str(dim_y+3) + '" stroke="#333" stroke-width="0.5"/>')
            desc_parts = comp["desc"].split("x")
            dim_label = desc_parts[0] if len(desc_parts) > 0 else comp["desc"]
            svg_elements.append('<text x="' + str(x+w/2) + '" y="' + str(dim_y-3) + '" text-anchor="middle" font-family="Arial" font-size="9" fill="#C0392B" font-weight="bold">' + dim_label + '</text>')

            dim_x = x - 12
            svg_elements.append('<line x1="' + str(dim_x) + '" y1="' + str(y) + '" x2="' + str(dim_x) + '" y2="' + str(y+h) + '" stroke="#333" stroke-width="0.8" marker-start="url(#arrow)" marker-end="url(#arrow)"/>')
            svg_elements.append('<line x1="' + str(x) + '" y1="' + str(y) + '" x2="' + str(dim_x+3) + '" y2="' + str(y) + '" stroke="#333" stroke-width="0.5"/>')
            svg_elements.append('<line x1="' + str(x) + '" y1="' + str(y+h) + '" x2="' + str(dim_x+3) + '" y2="' + str(y+h) + '" stroke="#333" stroke-width="0.5"/>')
            if len(desc_parts) > 1:
                svg_elements.append('<text x="' + str(dim_x-4) + '" y="' + str(y+h/2+3) + '" text-anchor="end" font-family="Arial" font-size="9" fill="#C0392B" font-weight="bold">' + desc_parts[1].strip() + '</text>')

    svg_elements.append('<line x1="800" y1="970" x2="950" y2="970" stroke="#333" stroke-width="2"/>')
    svg_elements.append('<line x1="800" y1="965" x2="800" y2="975" stroke="#333" stroke-width="2"/>')
    svg_elements.append('<line x1="950" y1="965" x2="950" y2="975" stroke="#333" stroke-width="2"/>')
    svg_elements.append('<text x="875" y="962" text-anchor="middle" font-family="Arial" font-size="10" fill="#333">5 m</text>')
    svg_elements.append('<line x1="960" y1="50" x2="960" y2="20" stroke="#333" stroke-width="2" marker-end="url(#arrow)"/>')
    svg_elements.append('<text x="960" y="14" text-anchor="middle" font-family="Arial" font-size="11" fill="#333" font-weight="bold">N</text>')

    svg_content = "\n".join(svg_elements)

    legend_rows = ""
    for comp in components:
        legend_rows += '<tr><td style="width:20px;text-align:center;"><span style="display:inline-block;width:14px;height:14px;background:' + comp["color"] + ';border-radius:2px;"></span></td><td style="font-size:9pt;">' + comp["label"] + '</td><td style="font-size:8pt;color:#666;">' + comp["desc"] + '</td></tr>'

    materiale_rows = ""
    for i, m in enumerate(MATERIALE_NOTE):
        bg = "#F5F5F5" if i % 2 == 0 else "#FFFFFF"
        materiale_rows += '<tr style="background:' + bg + ';"><td style="padding:4px 8px;font-size:8pt;border-bottom:1px solid #E0E0E0;">' + str(i+1) + '</td><td style="padding:4px 8px;font-size:8pt;border-bottom:1px solid #E0E0E0;">' + m + '</td></tr>'

    html = '''<!DOCTYPE html>
<html lang="ro">
<head>
<meta charset="UTF-8">
<title>Plansa Tehnica ''' + pkg_name + ''' - HYPER BNDF SRL</title>
<style>
  * { margin:0; padding:0; box-sizing:border-box; }
  @page { size: A3 landscape; margin: 0; }
  body {
    font-family: Arial, Helvetica, sans-serif;
    width: 420mm;
    height: 297mm;
    background: #FFFFFF;
    color: #333;
  }
  .page {
    width: 420mm;
    height: 297mm;
    display: flex;
    flex-direction: column;
    padding: 10mm;
  }
  .header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 3px solid #2D5F8F;
    padding-bottom: 6mm;
    margin-bottom: 6mm;
  }
  .header-left h1 { font-size: 16pt; color: #2D5F8F; margin: 0; }
  .header-left p { font-size: 9pt; color: #666; margin: 2px 0 0 0; }
  .header-right { text-align: right; }
  .header-right .sku { font-size: 11pt; font-weight: bold; color: #2D5F8F; }
  .header-right .scale { font-size: 9pt; color: #666; }

  .main { display: flex; flex: 1; gap: 8mm; }
  .drawing-area { flex: 1.6; border: 1px solid #CCC; background: #FAFAFA; position: relative; min-height: 0; }
  .drawing-area svg { width: 100%; height: 100%; }

  .sidebar { flex: 1; display: flex; flex-direction: column; gap: 6mm; }
  .panel { border: 1px solid #DDD; border-radius: 4px; overflow: hidden; }
  .panel-title { background: #2D5F8F; color: #FFF; padding: 5px 10px; font-size: 9pt; font-weight: bold; }
  .panel table { width: 100%; border-collapse: collapse; }
  .panel td { padding: 3px 8px; }
  .legend-table td { border-bottom: 1px solid #F0F0F0; }
  .render-img { width: 100%; height: auto; display: block; border: 1px solid #DDD; }

  .footer { margin-top: auto; display: flex; justify-content: space-between; align-items: center; border-top: 2px solid #2D5F8F; padding-top: 4mm; font-size: 8pt; color: #666; }
  .footer strong { color: #2D5F8F; font-size: 9pt; }

  .suprafata-info { background: #E8F5E9; padding: 6px 10px; border-left: 3px solid #4CAF50; margin: 4px 0; font-size: 8pt; }
  .suprafata-info strong { color: #2E7D32; }
</style>
</head>
<body>
<div class="page">
  <div class="header">
    <div class="header-left">
      <h1>HYPER BNDF SRL</h1>
      <p>CUI RO33286554 | Calea Serban Voda 234, Sector 4, Bucuresti</p>
      <p>Plansa Tehnica - Amplasare Echipamente</p>
    </div>
    <div class="header-right">
      <div class="sku">''' + pkg_name + '''</div>
      <div class="scale">Scara: ''' + pkg["scale"] + ''' | Format: A3</div>
      <div class="scale">Suprafata: ''' + pkg["suprafata_m"] + ''' (''' + pkg["suprafata_mp"] + ''' m2)</div>
      <div class="scale">Data: 30.04.2026</div>
    </div>
  </div>

  <div class="main">
    <div class="drawing-area">
      <svg viewBox="-30 -30 1060 1060" xmlns="http://www.w3.org/2000/svg">''' + svg_content + '''</svg>
    </div>

    <div class="sidebar">
      <div class="panel">
        <div class="panel-title">DATE TEHNICE</div>
        <div style="padding:6px 10px;">
          <div class="suprafata-info">
            <strong>Suprafata totala:</strong> ''' + pkg["suprafata_m"] + ''' (''' + pkg["suprafata_mp"] + ''' m2)<br>
            <strong>Zona siguranta EPDM+SBR:</strong> conform EN1177<br>
            <strong>Strat EPDM:</strong> 10-15 mm | <strong>SBR:</strong> 40-50 mm
          </div>
        </div>
      </div>

      <div class="panel" style="flex:1;">
        <div class="panel-title">LEGENDA ECHIPAMENTE</div>
        <table class="legend-table">''' + legend_rows + '''</table>
      </div>

      <div class="panel">
        <div class="panel-title">MATERIALE</div>
        <table>''' + materiale_rows + '''</table>
      </div>

      <div class="panel">
        <div class="panel-title">RENDER 3D</div>
        <img src="''' + render_path + '''" alt="Render ''' + pkg_name + '''" class="render-img">
      </div>
    </div>
  </div>

  <div class="footer">
    <div>
      <strong>HYPER BNDF SRL</strong> | Locuri de Joaca &amp; spatii Verzi<br>
      Bogdan Gavra | +40 722 380 349 | gavrabogdan@yahoo.com
    </div>
    <div style="text-align:right;">
      Plansa Tehnica ''' + pkg_name + ''' | Pagina 1/1<br>
      Suprafata de siguranta: EPDM + SBR conform AVP Park, EN1177
    </div>
  </div>
</div>
</body>
</html>'''

    return html


if __name__ == "__main__":
    for pkg_name, pkg in PACKAGES.items():
        html = generate_plansa_html(pkg_name, pkg)
        path = os.path.join(PLANSE_DIR, pkg_name, "PLANSA_TEHNICA_" + pkg_name.replace(" ", "_") + ".html")
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
        print("OK: " + path)
    print("Done - technical planse HTML regenerated")
