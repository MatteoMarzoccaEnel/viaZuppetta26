"""Genera la pianta del bagno (SVG + PDF + PNG) da un blocco di parametri.

Tutte le misure sono in CENTIMETRI, nel sistema locale del bagno:
  X = lunghezza, 0 = filo interno della parete con la porta
  Y = larghezza, 0 = filo interno del muro nuovo da 13 cm (lato camera matrimoniale)

Per modificare il progetto basta agire sul blocco PARAMETRI qui sotto.
Esecuzione:  python bagno_pianta.py
"""

import contextlib
import io
import math
import subprocess
import sys

with contextlib.redirect_stdout(io.StringIO()):
    import casa_pianta as cp

# =====================================================================
# PARAMETRI
# =====================================================================

SCALA = 25  # 1:SCALA alla stampa al 100%
OUT = r"c:\WORK\GH\bagno_pianta"

MURO = 13      # spessore grafico delle murature
RIV_SP = 2     # spessore del rivestimento interno (piastrella + colla)

# Vano AL GREZZO rilevato da "TAV 02 - Stato di progetto"
# (verificato: area 6,75 mq e perimetro 13,02 m come da tavola)
VANO = [
    (0, 0), (395, 0), (395, 27), (369, 27), (369, 80),
    (392, 80), (392, 158), (90, 158), (90, 233), (0, 233),
]

# Porta scorrevole a scomparsa sulla parete X=0
PORTA = dict(luce=(50, 135), tasca=(135, 225), larghezza=80, altezza=210)

# Finestrella nella parete di fondo
FINESTRA = dict(tratto=(80, 131), sguincio=31, larghezza=51, altezza=89, davanzale=135)

# Piastrelle
PIASTRELLA = 90.0
FUGA = 0.2
POSA_ORIGINE = (RIV_SP, RIV_SP)  # angolo di partenza della prima lastra intera
RIV_CORSI = cp.RIV_CORSI  # corsi di rivestimento a parete: si cambia in casa_pianta.py
RIV_H = cp.H_RIV          # l'ultimo corso e' tagliato a filo dell'intradosso trave
SFRIDO = 0.15

# Arredo: (chiave, etichetta, x, y, ingombro lungo X, ingombro lungo Y)
ARREDO = [
    ("lavabo", "MOBILE LAVABO 120x38", 29, 2, 120, 38),
    ("wc", "WC 37x48", 176, 2, 37, 48),
    ("bidet", "BIDET 37x48", 221, 2, 37, 48),
    ("doccia", "PIATTO DOCCIA 154x80", 287, 2, 80, 154),
    ("sedia", "SGABELLO 35x35", 206, 121, 35, 35),
    ("lavatrice", "LAVATRICE 60x60", 15, 163.5, 60, 60),
]

# Box doccia a nicchia: anta = tratto coperto da chiusa, luce = passaggio da aperta
BOX = dict(fronte_x=287, fronte_y=(2, 156), anta=(2, 122), luce=60)

# Catena di quote orizzontale (x0, x1, testo)
QUOTE_X = [
    (2, 29, "27"), (29, 149, "LAVABO 120"), (149, 176, "27"),
    (176, 258, "WC+BIDET 82"), (258, 287, "29"), (287, 367, "DOCCIA 80"),
]

NOTE = [
    "Rivestimento interno 2 cm (piastrella + colla) su tutte le pareti: misure FINITE 154 x 391 cm contro 158 x 395 al grezzo. Tutte le quote e l'arredo si riferiscono al finito.",
    "Sanitari accentrati sul tratto libero 2-287: interasse wc-bidet 45 cm, luce laterale 27 cm. Wc e bidet sospesi, profondi 48. Passaggio libero 106 cm per tutto il vano.",
    "Box a nicchia 154: anta scorrevole a 2 pannelli, 120 da chiusa e 60 da aperta, + fisso 34. Luce netta di accesso alla doccia 60 cm.",
    "Piatto doccia 154x80 su misura a filo colonna di scarico; nicchia 23x74 sotto la finestra da tamponare (seduta h 45). Porta 80x210 a scomparsa: parete finita min. 12,5 cm.",
    "Colonna montante di scarico nell'angolo di fondo, dietro al piatto: dal wc lo scarico corre ~2 m sotto pavimento (verificare pendenza e massetto).",
]

# =====================================================================
# GEOMETRIA
# =====================================================================


def area(poly):
    s = 0.0
    for i in range(len(poly)):
        x0, y0 = poly[i]
        x1, y1 = poly[(i + 1) % len(poly)]
        s += x0 * y1 - x1 * y0
    return abs(s) / 2


def perimetro(poly):
    s = 0.0
    for i in range(len(poly)):
        x0, y0 = poly[i]
        x1, y1 = poly[(i + 1) % len(poly)]
        s += math.hypot(x1 - x0, y1 - y0)
    return s


def intervalli(poly, asse, c):
    """Intervalli interni al poligono rettilineo lungo la retta asse=c."""
    vals = []
    for i in range(len(poly)):
        p, q = poly[i], poly[(i + 1) % len(poly)]
        if asse == "x" and p[1] == q[1] and min(p[0], q[0]) < c < max(p[0], q[0]):
            vals.append(p[1])
        if asse == "y" and p[0] == q[0] and min(p[1], q[1]) < c < max(p[1], q[1]):
            vals.append(p[0])
    vals.sort()
    return list(zip(vals[0::2], vals[1::2]))


def offset_poly(poly, d):
    """Offset di un poligono rettilineo: d>0 verso l'interno, d<0 verso l'esterno."""
    n = len(poly)
    rette = []
    for i in range(n):
        p, q = poly[i], poly[(i + 1) % n]
        if p[1] == q[1]:
            rette.append(("h", p[1] + d * (1 if q[0] > p[0] else -1)))
        else:
            rette.append(("v", p[0] + d * (-1 if q[1] > p[1] else 1)))
    out = []
    for i in range(n):
        prev, cur = rette[(i - 1) % n], rette[i]
        out.append((prev[1], cur[1]) if prev[0] == "v" else (cur[1], prev[1]))
    return out


def pts(poly):
    return " ".join(f"{x:.2f},{y:.2f}" for x, y in poly)


# =====================================================================
# DISEGNO
# =====================================================================

S = []


def add(s):
    S.append(s)


def line(x1, y1, x2, y2, cls="", extra=""):
    add(f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" class="{cls}" {extra}/>')


def rect(x, y, w, h, cls="", extra=""):
    add(f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" class="{cls}" {extra}/>')


def txt(x, y, s, cls="lbl", anchor="middle", rot=None):
    t = f' transform="rotate(-90 {x:.2f} {y:.2f})"' if rot else ""
    add(f'<text x="{x:.2f}" y="{y:.2f}" class="{cls}" text-anchor="{anchor}"{t}>{s}</text>')


def dim_h(x0, x1, y, label):
    line(x0, y, x1, y, "dl", 'marker-start="url(#tick)" marker-end="url(#tick)"')
    txt((x0 + x1) / 2, y - 3, label, "dim")


def dim_v(y0, y1, x, label):
    line(x, y0, x, y1, "dl", 'marker-start="url(#tick)" marker-end="url(#tick)"')
    txt(x - 3, (y0 + y1) / 2, label, "dim", rot=True)


def scalimetro(x, y, tot=300, passo=100):
    txt(x, y - 4, f"scala 1:{SCALA} alla stampa 100%", "dim", "start")
    rect(x, y, tot, 6, extra='fill="none" stroke="#333" stroke-width="0.6"')
    for i in range(int(tot // passo)):
        if i % 2 == 0:
            rect(x + i * passo, y, passo, 6, extra='fill="#333"')
        txt(x + i * passo, y + 13, f"{i}", "dim")
    txt(x + tot, y + 13, f"{tot/100:.0f} m", "dim")


W, H = 620, 470
TX, TY = 70, 125

FINITO = offset_poly(VANO, RIV_SP)
EST = offset_poly(VANO, -MURO)
XG = [p[0] for p in VANO]
YG = [p[1] for p in VANO]
XF = [p[0] for p in FINITO]
YF = [p[1] for p in FINITO]

AREA = area(FINITO) / 10000
PERIM = perimetro(FINITO) / 100
MODULO = PIASTRELLA + FUGA
LASTRA = (PIASTRELLA / 100) ** 2

vuoti = PORTA["larghezza"] * min(PORTA["altezza"], RIV_H) / 10000
vuoti += FINESTRA["larghezza"] * max(
    0.0, min(FINESTRA["davanzale"] + FINESTRA["altezza"], RIV_H) - FINESTRA["davanzale"]
) / 10000
RIV_MQ = PERIM * RIV_H / 100 - vuoti

n_pav = math.ceil(AREA / LASTRA * (1 + SFRIDO))
n_riv = math.ceil(RIV_MQ / LASTRA * (1 + SFRIDO))

add(f'<?xml version="1.0" encoding="UTF-8"?>')
add(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W/SCALA:.2f}cm" '
    f'height="{H/SCALA:.2f}cm" viewBox="0 0 {W} {H}">')
add("""<defs>
<marker id="tick" markerWidth="8" markerHeight="8" refX="4" refY="4" orient="auto">
  <line x1="1" y1="7" x2="7" y2="1" stroke="#444" stroke-width="1"/></marker>
<style>
text { font-family: Arial, Helvetica, sans-serif; fill: #222; }
.t1 { font-size: 11px; font-weight: bold; }
.t2 { font-size: 6.5px; }
.t3 { font-size: 7px; font-weight: bold; }
.lbl { font-size: 6px; }
.lbls { font-size: 5px; fill: #555; }
.lblw { font-size: 5px; fill: #ffffff; }
.dim { font-size: 5.5px; fill: #333; }
.dl { stroke: #666; stroke-width: 0.6; }
.ext { stroke: #999; stroke-width: 0.4; stroke-dasharray: 3 2; }
.tile { stroke: #c9d3dc; stroke-width: 0.5; }
.riv { fill: #e9c9a8; stroke: none; }
.fix { fill: #ffffff; stroke: #1f5673; stroke-width: 1.2; }
.fixl { fill: none; stroke: #1f5673; stroke-width: 0.8; }
.glass { stroke: #1f5673; stroke-width: 2.6; }
.leaf { stroke: #1f5673; stroke-width: 1.6; stroke-dasharray: 5 2; }
.door { stroke: #c0392b; stroke-width: 1.2; stroke-dasharray: 4 2; fill: none; }
</style></defs>""")
rect(0, 0, W, H, extra='fill="#ffffff"')

txt(14, 16, "BAGNO - pianta di progetto", "t1", "start")
txt(14, 28, f"Vano finito {max(XF)-min(XF):.0f} x {max(YF)-min(YF)-75:.0f} cm - {AREA:.2f} mq - "
            f"perimetro {PERIM:.2f} m - rivestimento interno {RIV_SP} cm - "
            f"piastrelle {PIASTRELLA:.0f}x{PIASTRELLA:.0f}", "t2", "start")

add(f'<g transform="translate({TX},{TY})">')

# --- murature ---
add(f'<polygon points="{pts(EST)}" fill="#4a4a4a"/>')
rect(369, 27, 26, 53, extra='fill="#4a4a4a"')  # pilastro esistente
rect(max(XG), -MURO, FINESTRA["sguincio"], 170 + MURO, extra='fill="#4a4a4a"')
rect(-MURO, -MURO, max(XG) + FINESTRA["sguincio"] + MURO, MURO,
     extra='fill="#00b050" opacity="0.85"')  # muro nuovo da 13

# --- rivestimento interno 2 cm ---
add(f'<polygon points="{pts(VANO)}" class="riv"/>')
add(f'<polygon points="{pts(FINITO)}" fill="#ffffff" stroke="#8a8a8a" stroke-width="0.4"/>')

# --- piastrelle a pavimento ---
c = POSA_ORIGINE[0]
while c <= max(XF):
    if c > min(XF):
        for a, b in intervalli(FINITO, "x", c):
            line(c, a, c, b, "tile")
    c += MODULO
c = POSA_ORIGINE[1]
while c <= max(YF):
    if c > min(YF):
        for a, b in intervalli(FINITO, "y", c):
            line(a, c, b, c, "tile")
    c += MODULO
nx = int((max(XF) - POSA_ORIGINE[0]) // MODULO)
ny = int((max(YF) - POSA_ORIGINE[1]) // MODULO)
taglio_fondo = max(XF) - POSA_ORIGINE[0] - nx * MODULO
taglio_lato = 156 - POSA_ORIGINE[1] - int((156 - POSA_ORIGINE[1]) // MODULO) * MODULO
taglio_nicchia = max(YF) - POSA_ORIGINE[1] - ny * MODULO
txt(POSA_ORIGINE[0] + 6, POSA_ORIGINE[1] + 9, "partenza posa", "lbls", "start")

# --- finestra ---
rect(max(XF), FINESTRA["tratto"][0], max(XG) + FINESTRA["sguincio"] - max(XF),
     FINESTRA["tratto"][1] - FINESTRA["tratto"][0],
     extra='fill="#ffffff" stroke="#4a4a4a" stroke-width="0.5"')
line(max(XG) + FINESTRA["sguincio"], FINESTRA["tratto"][0],
     max(XG) + FINESTRA["sguincio"], FINESTRA["tratto"][1], "glass")
txt(405, sum(FINESTRA["tratto"]) / 2, f'FINESTRA {FINESTRA["larghezza"]}', "lblw", rot=True)

# --- porta scorrevole a scomparsa ---
l0, l1 = PORTA["luce"]
t0, t1 = PORTA["tasca"]
rect(-MURO, l0, MURO + RIV_SP, l1 - l0, extra='fill="#ffffff"')
rect(-MURO + 2, t0, MURO - 4, t1 - t0, "door")
line(-MURO / 2, l1 + 6, -MURO / 2, t1 - 6, "door")
add(f'<path d="M {-MURO/2-2},{t1-12} L {-MURO/2},{t1-4} L {-MURO/2+2},{t1-12}" '
    f'fill="none" stroke="#c0392b" stroke-width="1"/>')
txt(-19, (l0 + l1) / 2, f'PORTA SCORREVOLE A SCOMPARSA {PORTA["larghezza"]}', "lbls", rot=True)

# --- arredo ---
for kind, label, x, y, w, h in ARREDO:
    if kind == "doccia":
        rect(x, y, w, h, extra='fill="#dff1fb" stroke="#1f5673" stroke-width="1.2"')
        add(f'<circle cx="{x+w/2}" cy="{y+h/2}" r="4" class="fixl"/>')
        txt(x + w - 12, y + h / 2, label, "lbl", rot=True)
        continue
    rect(x, y, w, h, "fix", 'rx="3"')
    if kind == "lavabo":
        rect(x + 7, y + 6, w - 14, h - 12, "fixl", 'rx="4"')
        add(f'<circle cx="{x+w/2}" cy="{y+h/2-6}" r="3" class="fixl"/>')
    elif kind == "wc":
        rect(x, y, w, 14, "fixl")
        add(f'<ellipse cx="{x+w/2}" cy="{y+35}" rx="14" ry="17" class="fixl"/>')
    elif kind == "bidet":
        add(f'<ellipse cx="{x+w/2}" cy="{y+30}" rx="14" ry="20" class="fixl"/>')
    elif kind == "lavatrice":
        add(f'<circle cx="{x+w/2}" cy="{y+h/2}" r="19" class="fixl"/>')
    elif kind == "mobiletto":
        line(x, y, x + w, y, "fixl")
        line(x + w / 2, y, x + w / 2, y + h, "fixl")
    elif kind == "sedia":
        rect(x + 4, y + h - 9, w - 8, 5, "fixl")
    ty = y + h + 8 if kind in ("wc", "bidet") else y + h / 2 + 2
    txt(x + w / 2, ty, label, "lbl")

# --- box doccia ---
fx, (fy0, fy1) = BOX["fronte_x"], BOX["fronte_y"]
a0, a1 = BOX["anta"]
ap = a1 - BOX["luce"]  # ingombro dell'anta impacchettata
line(fx, fy0, fx, fy1, "glass")
line(fx - 5, ap, fx - 5, a1, "leaf")
line(fx - 5, a1, fx - 5, a1 + 12, "dl")
add(f'<path d="M {fx-5},{a1+14} l -2.5,-6 l 5,0 Z" fill="#1f5673"/>')
dim_v(fy0, ap, fx + 11, f"LUCE {BOX['luce']:.0f}")
dim_v(fy0, a1, fx + 28, f"ANTA SCORR. {a1-a0:.0f}")
dim_v(a1, fy1, fx + 28, f"FISSO {fy1-a1:.0f}")

# --- nicchia residua sotto la finestra ---
FONDO_FIN = 390  # filo finito della parete di fondo nel tratto della finestra
rect(367, 82, FONDO_FIN - 367, 156 - 82,
     extra='fill="none" stroke="#9aa5b1" stroke-width="0.6" stroke-dasharray="3 2"')
txt(378, 119, f"nicchia {FONDO_FIN-367:.0f}x74", "lbls", rot=True)
txt(383, 55, "COLONNA SCARICO", "lblw", rot=True)

# --- quote ---
for x0, x1, label in QUOTE_X:
    line(x0, -4, x0, -38, "ext")
    line(x1, -4, x1, -38, "ext")
    dim_h(x0, x1, -36, label)
line(min(XF), -40, min(XF), -80, "ext")
line(max(XF), -4, max(XF), -58, "ext")
dim_h(min(XF), max(XF), -56, f"{max(XF)-min(XF):.0f} finito")
line(min(XG), -4, min(XG), -80, "ext")
line(max(XG), -4, max(XG), -80, "ext")
dim_h(min(XG), max(XG), -76, f"{max(XG)-min(XG):.0f} al grezzo")

line(-4, min(YF), -38, min(YF), "ext")
line(-4, 156, -38, 156, "ext")
dim_v(min(YF), 156, -36, "154 finito")
dim_v(min(YG), 158, -54, "158 grezzo")
dim_v(40, 121, 118, "81 sgabello-lavabo")
dim_v(50, 156, 272, "106")
dim_h(min(XF), 88, 240, "86")
dim_v(156, max(YF), 85, "75")

txt(200, -16, "muro nuovo 13 cm  -  CAMERA MATRIMONIALE", "lbls")
txt(240, 167, "CAMERETTA", "lblw")
txt(-19, 200, "DISIMPEGNO", "lbls", rot=True)
txt(415, 40, "MURO PERIMETRALE", "lblw", rot=True)
add("</g>")

# --- computo piastrelle ---
bx, by = 505, 125
rect(bx, by, 100, 158, extra='fill="#f5f7f9" stroke="#9aa5b1" stroke-width="0.6"')
txt(bx + 6, by + 14, f"PIASTRELLE {PIASTRELLA:.0f}x{PIASTRELLA:.0f}", "t3", "start")
righe = [
    f"lastra: {LASTRA:.2f} mq - fuga {FUGA*10:.0f} mm",
    "",
    f"PAVIMENTO  {AREA:.2f} mq",
    f"  file intere: {nx} x {ny}",
    f"  taglio in fondo: {taglio_fondo:.0f} cm",
    f"  taglio lato cameretta: {taglio_lato:.0f} cm",
    f"  taglio fondo nicchia: {taglio_nicchia:.0f} cm",
    f"  lastre (+{SFRIDO*100:.0f}%): {n_pav}",
    "",
    f"RIVESTIMENTO h {RIV_H:.0f} cm",
    f"  {PERIM:.2f} m x {RIV_H/100:.2f} m - vuoti",
    f"  = {RIV_MQ:.2f} mq",
    f"  {RIV_CORSI} corsi da {cp.PIASTRELLA:.0f}, l'ultimo tagliato",
    f"  spessore in opera: {RIV_SP} cm",
    f"  lastre (+{SFRIDO*100:.0f}%): {n_riv}",
    "",
    f"TOTALE {n_pav + n_riv} lastre = {(n_pav+n_riv)*LASTRA:.1f} mq",
]
for i, r in enumerate(righe):
    txt(bx + 6, by + 27 + i * 8, r, "t3" if r.startswith(("PAVI", "RIVE", "TOTA")) else "t2", "start")

for i, n in enumerate(NOTE):
    txt(14, 382 + i * 11, n, "t2", "start")

scalimetro(14, 442)

add("</svg>")

svg = "\n".join(S)
with open(OUT + ".svg", "w", encoding="utf-8") as f:
    f.write(svg)

print(f"area   {AREA:.3f} mq   perimetro {PERIM:.3f} m")
print(f"tagli  fondo {taglio_fondo:.1f} | lato {taglio_lato:.1f} | nicchia {taglio_nicchia:.1f}")
print(f"lastre pavimento {n_pav}  rivestimento {n_riv} ({RIV_MQ:.2f} mq)")

try:
    from svglib.svglib import svg2rlg
    from reportlab.graphics import renderPDF
    import fitz

    d = svg2rlg(OUT + ".svg")
    renderPDF.drawToFile(d, OUT + ".pdf")
    doc = fitz.open(OUT + ".pdf")
    doc[0].get_pixmap(matrix=fitz.Matrix(3, 3)).save(OUT + ".png")
    print("scritti:", OUT + ".svg/.pdf/.png")
except Exception as e:  # anteprima opzionale
    print("anteprima non generata:", e)
