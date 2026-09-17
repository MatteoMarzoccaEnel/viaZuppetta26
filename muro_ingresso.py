"""Muro-schermo all'ingresso: quanto deve essere lungo per coprire la cucina.

Coordinate di disegno, le stesse di casa_pianta.py dopo il raddrizzamento:
  porta d'ingresso   Y = 697, X da 1335 a 1421
  spalla sinistra del vano d'ingresso (muro esistente)  X = 1252, da Y=601 a Y=697
  fronte cucina      X = 867, da Y = 108 a Y = 468  (360 cm)
Il muro-schermo prolunga la spalla esistente verso l'alto: X=1252, da Y=601 a Y=601-L.

Genera muro_ingresso.svg/.pdf/.png con tutte le lunghezze sovrapposte.
"""

import math

XW, YW = 1252.0, 601.0       # allineamento e partenza del muro
PORTA = (1335.0, 1421.0)
YP = 697.0
XK = 867.0                   # fronte cucina: il punto piu' esposto
KY0, KY1 = 108.0, 468.0
LUNG = KY1 - KY0

LUNGHEZZE = [0, 20, 30, 40, 50, 60, 70, 80, 85, 90, 100]
COLORI = ["#111111", "#e6194b", "#2f9e44", "#1c5fd8", "#f08c00", "#9c1fb4",
          "#00807a", "#9a6324", "#8a0000", "#000075", "#7a7a00"]

SCALA = 30
OUT = r"c:\WORK\GH\muro_ingresso"

# ---- ricalco della tavola originale, per il contesto ----
PDF = r"c:\WORK\GH\TAV 02_STATO DI PROGETTO.pdf"
PT_M, PDF_OX, PDF_OY, RY = 27.76, 609.18, 394.20, 638.0
VISTA = (790, 55, 1500, 755)


def Pt(px, py):
    return ((PDF_OX - px) / PT_M * 100, RY - (py - PDF_OY) / PT_M * 100)


def ricalco():
    try:
        import fitz
    except ImportError:
        return []
    out = []
    for p in fitz.open(PDF)[0].get_drawings():
        lw = p.get("width") or 0
        if lw < 0.3:
            continue
        col = p.get("color") or (0.25, 0.25, 0.25)
        if col[0] > 0.6 and col[2] > 0.6 and col[1] < 0.5:
            continue
        for it in p["items"]:
            if it[0] == "l":
                pts = [(it[1].x, it[1].y), (it[2].x, it[2].y)]
            elif it[0] == "re":
                r = it[1]
                pts = [(r.x0, r.y0), (r.x1, r.y0), (r.x1, r.y1), (r.x0, r.y1), (r.x0, r.y0)]
            else:
                continue
            q = [Pt(*a) for a in pts]
            if all(VISTA[0] <= a[0] <= VISTA[2] and VISTA[1] <= a[1] <= VISTA[3] for a in q):
                out.append((col, lw, q))
    return out


# ---- calcolo della visuale ----

def limite(L):
    """Quota sul fronte cucina oltre la quale si vede, guardando dal vano porta.

    Il punto di vista peggiore e' la spalla destra della porta: da li' il raggio
    supera la punta del muro con la pendenza piu' sfavorevole.
    """
    vx = PORTA[1]
    t = (vx - XW) / (vx - XK)
    return YP - (YP - (YW - L)) / t


def visibile(L):
    return max(0.0, min(KY1, limite(L)) - KY0)


print(f"fronte cucina: {LUNG:.0f} cm\n")
print(f"{'muro L':>8} {'visibile':>10} {'coperto':>9}")
print("-" * 30)
DATI = []
for L in LUNGHEZZE:
    v = visibile(L)
    DATI.append((L, v, 100 * (1 - v / LUNG)))
    print(f"{L:7.0f}  {v:8.0f} cm {100*(1-v/LUNG):8.0f}%")
print()
for quota in (0.50, 0.75, 1.00):
    L = 0.0
    while L < 300 and visibile(L) > LUNG * (1 - quota) + 1e-9:
        L += 0.5
    print(f"copertura {quota*100:3.0f}%  ->  muro lungo {L:.0f} cm")

# =====================================================================
# TAVOLA
# =====================================================================

VX0, VY0, VX1, VY1 = VISTA
W = 60 + (VX1 - VX0) + 400
H = 110 + (VY1 - VY0) + 40
S = []
add = S.append


def txt(x, y, s, size=14, col="#222", anchor="start", bold=False, halo=False):
    b = ' font-weight="bold"' if bold else ""
    if halo:
        add(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{col}" '
            f'text-anchor="{anchor}"{b} stroke="#ffffff" stroke-width="4" '
            f'stroke-linejoin="round">{s}</text>')
    add(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{col}" '
        f'text-anchor="{anchor}"{b}>{s}</text>')


add('<?xml version="1.0" encoding="UTF-8"?>')
add(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W/SCALA:.2f}cm" '
    f'height="{H/SCALA:.2f}cm" viewBox="0 0 {W} {H}" '
    f'font-family="Arial, Helvetica, sans-serif">')
add(f'<rect width="{W}" height="{H}" fill="#ffffff"/>')
txt(30, 40, "MURO-SCHERMO ALL'INGRESSO - copertura visiva del fronte cucina", 24, bold=True)
txt(30, 66, "Prolungamento verso l'alto della spalla sinistra del vano d'ingresso (X=1252). "
            "Visuale calcolata dal punto piu' sfavorevole del vano porta.", 15)
txt(30, 88, f"Fronte cucina {LUNG:.0f} cm - stampa 100% = 1:{SCALA}", 15)

add(f'<g transform="translate({60-VX0},{110-VY0})">')

for col, lw, pts in ricalco():
    c = "#%02x%02x%02x" % tuple(int(255 * v) for v in col)
    d = "M " + " L ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    add(f'<path d="{d}" fill="none" stroke="{c}" stroke-width="{2.6 if lw>=0.8 else 1.4}"/>')

# fronte cucina
add(f'<rect x="{XK-60}" y="{KY0}" width="60" height="{LUNG}" fill="#eef3f7" '
    f'stroke="#1f5673" stroke-width="2"/>')
for y in (168, 228, 288, 408):
    add(f'<line x1="{XK-60}" y1="{y}" x2="{XK}" y2="{y}" stroke="#1f5673" stroke-width="1.2"/>')
txt(XK - 30, KY0 - 12, "FRONTE CUCINA 360", 15, "#1f5673", "middle", True)

# porta d'ingresso e punto di vista
add(f'<line x1="{PORTA[0]}" y1="{YP}" x2="{PORTA[1]}" y2="{YP}" stroke="#c0392b" stroke-width="5"/>')
txt((PORTA[0]+PORTA[1])/2, YP + 26, "INGRESSO", 15, "#c0392b", "middle", True)
add(f'<circle cx="{PORTA[1]}" cy="{YP}" r="6" fill="#c0392b"/>')
txt(PORTA[1] + 12, YP - 10, "punto di vista piu' sfavorevole", 13, "#c0392b")

# muri, raggi limite e tratti scoperti
ordine = sorted(range(len(DATI)), key=lambda i: min(max(limite(DATI[i][0]), KY0), KY1))
posy, ylast = {}, -1e9
for k, i in enumerate(ordine):
    lim = min(max(limite(DATI[i][0]), KY0), KY1)
    y = max(lim, ylast + 20)
    posy[i] = y
    ylast = y

for i, ((L, v, cop), c) in enumerate(zip(DATI, COLORI)):
    lim = min(max(limite(L), KY0), KY1)
    if L > 0:
        add(f'<line x1="{XW}" y1="{YW}" x2="{XW}" y2="{YW-L}" stroke="{c}" '
            f'stroke-width="{18-i*1.4:.1f}" stroke-linecap="butt"/>')
        tx = XW - 16 - (i % 3) * 48
        add(f'<line x1="{tx+4}" y1="{YW-L}" x2="{XW}" y2="{YW-L}" stroke="{c}" stroke-width="0.8"/>')
        txt(tx, YW - L + 5, f"{L:.0f}", 15, c, "end", True, halo=True)
    add(f'<line x1="{PORTA[1]}" y1="{YP}" x2="{XK}" y2="{limite(L):.1f}" stroke="{c}" '
        f'stroke-width="1.1" stroke-dasharray="7 5" opacity="0.85"/>')
    add(f'<line x1="{XK-60}" y1="{lim}" x2="{XK}" y2="{lim}" stroke="{c}" stroke-width="3"/>')
    add(f'<line x1="{XK}" y1="{lim}" x2="{XK+16}" y2="{posy[i]}" stroke="{c}" stroke-width="0.8"/>')
    txt(XK + 20, posy[i] + 5, f"L={L:.0f}  vis {v:.0f}  cop {cop:.0f}%",
        14, c, "start", True, halo=True)

add(f'<line x1="{XW}" y1="{YW}" x2="{XW}" y2="{YP}" stroke="#555" stroke-width="6"/>')
txt(XW - 16, (YW + YP) / 2, "muro esistente", 13, "#555", "end")
add("</g>")

# legenda
lx, ly = 60 + (VX1 - VX0) + 30, 150
txt(lx, ly - 18, "LUNGHEZZE A CONFRONTO", 17, bold=True)
for i, ((L, v, cop), c) in enumerate(zip(DATI, COLORI)):
    y = ly + i * 26
    add(f'<rect x="{lx}" y="{y-13}" width="26" height="18" fill="{c}"/>')
    txt(lx + 36, y + 2, f"L = {L:>3.0f} cm", 15, c, bold=True)
    txt(lx + 150, y + 2, f"visibile {v:>3.0f} cm", 15, c)
    txt(lx + 270, y + 2, f"coperto {cop:>3.0f}%", 15, c)

ly2 = ly + len(DATI) * 26 + 30
txt(lx, ly2, "SOGLIE", 17, bold=True)
for k, (q, lab) in enumerate([(0.50, "meta' cucina"), (0.75, "3/4 di cucina"), (1.00, "cucina intera")]):
    L = 0.0
    while L < 300 and visibile(L) > LUNG * (1 - q) + 1e-9:
        L += 0.5
    txt(lx, ly2 + 24 + k * 22, f"{lab:16} -> muro {L:.0f} cm", 15)
txt(lx, ly2 + 24 + 3 * 22 + 14, "consigliato 90 cm: copre tutto e cade", 14, "#1c5fd8")
txt(lx, ly2 + 24 + 3 * 22 + 32, "su una fuga del 90x90 (nessun taglio in piu')", 14, "#1c5fd8")

add("</svg>")
with open(OUT + ".svg", "w", encoding="utf-8") as f:
    f.write("\n".join(S))

try:
    from svglib.svglib import svg2rlg
    from reportlab.graphics import renderPDF
    import fitz

    renderPDF.drawToFile(svg2rlg(OUT + ".svg"), OUT + ".pdf")
    fitz.open(OUT + ".pdf")[0].get_pixmap(matrix=fitz.Matrix(2, 2)).save(OUT + ".png")
    print("\nscritti:", OUT + ".svg/.pdf/.png")
except Exception as e:
    print("anteprima non generata:", e)
