"""Piantina 2D in PDF: pianta intera e due ingrandimenti (zona giorno, zona notte).

Su ogni foglio: muri sezionati, infissi, posa del pavimento lastra per lastra,
quote del perimetro, dei muri di ogni locale e delle aperture. La posa e' quella
col numero mostrato nel modello 3D (ordine di sfrido della tabella pavimento).
Tutta la geometria arriva da casa_pianta.py e casa_3d.py: qui non c'e' nessuna misura.

Esecuzione:  python piantina_2d.py            (posa #5 del 3D)
             python piantina_2d.py --posa3d=N
"""

import contextlib
import io
import math
import sys

with contextlib.redirect_stdout(io.StringIO()):
    import casa_pianta as cp
    import casa_3d as c3

from reportlab.lib import colors
from reportlab.lib.pagesizes import A3, landscape, portrait
from reportlab.lib.units import mm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

OUT = r"c:\WORK\GH\piantina_2d.pdf"
POSA_3D = 5
for _a in sys.argv[1:]:
    if _a.startswith("--posa3d="):
        POSA_3D = int(_a.split("=", 1)[1])

# stesso ordinamento della tabella del 3D: sfrido crescente, a pari merito l'indice
_ord = sorted(range(len(c3.POSA)), key=lambda k: (c3.POSA[k]["stat"]["sfrido"], k))
K_POSA = _ord[POSA_3D - 1]
I_FORMATO = next(i for i, f in enumerate(cp.FORMATI) if c3._POSA_DI[c3._chiave_pav(f)] == K_POSA)
cp.usa_formato(I_FORMATO)
VAR = cp.OTTIMO
STAT = c3.POSA[K_POSA]["stat"]

H_TAGLIO = 150.0       # quota del piano di sezione: sotto ci sono tutti i davanzali
SCALE = (20, 25, 30, 40, 50, 75, 100)
MARG, TITOLO, LEGENDA, FASCIA = 8 * mm, 15 * mm, 19 * mm, 20 * mm
LIVELLI = (5 * mm, 11 * mm, 17 * mm)     # distanza delle tre catene esterne dal riquadro
DIM_INT = 14.0                           # quote dei locali: rientro dal filo muro (cm)

NOTTE = [n for n in cp.LOCALI if n != "ZONA GIORNO"]
FOGLI = [
    ("PIANTA GENERALE", list(cp.LOCALI), True),
    ("ZONA GIORNO - soggiorno, cucina, ingresso", ["ZONA GIORNO"], False),
    ("ZONA NOTTE - camere, bagno, disimpegno, ripostiglio", NOTTE, False),
]

# bianco e nero: solo grigi, per la stampa
NERO = colors.black
C_MURO = colors.HexColor("#4d4d4d")
C_CA = NERO
C_CANNA = colors.HexColor("#a6a6a6")
C_FUGA = colors.HexColor("#7a7a7a")
C_GRIGIO = colors.HexColor("#9a9a9a")
C_QUOTA = C_EST = C_INFISSO = C_VETRO = C_LOCALE = C_PEZZO = NERO
C_INTERA, C_TAGLIATA, C_LISTELLO = colors.white, colors.HexColor("#e6e6e6"), colors.HexColor("#bdbdbd")
CLASSI = [(C_INTERA, f"lastra intera {cp.NOME_FORMATO}"),
          (C_TAGLIATA, "lastra tagliata"),
          (C_LISTELLO, f"listello, lato < {cp.SLIVER:.0f} cm")]


def tono(c):
    if c["intera"]:
        return C_INTERA
    return C_LISTELLO if c["lato"] < cp.SLIVER else C_TAGLIATA


def fmt(v):
    """Misura in cm: decimale solo se c'e' (rilievo al mm sulle luci)."""
    s = f"{v:.1f}"
    return s[:-2] if s.endswith(".0") else s.replace(".", ",")


def lato_apertura(t, locali):
    """Il lato di locale che ospita l'apertura: (nome, orizz, c, a, b, dentro, va, vb)."""
    tipo, x0, y0, x1, y1, _lb = t
    ao = abs(y1 - y0) < abs(x1 - x0)
    q = y0 if ao else x0
    va, vb = (min(x0, x1), max(x0, x1)) if ao else (min(y0, y1), max(y0, y1))
    for nome in locali:
        for orizz, c, a, b, dentro in cp.lati(cp.LOCALI[nome]["poly"]):
            if orizz == ao and abs(c - q) <= 11 and min(b, vb) - max(a, va) > 1:
                return nome, orizz, c, a, b, dentro, va, vb
    return None


def regione(locali, balconi):
    xs = [p[0] for n in locali for p in cp.LOCALI[n]["poly"]]
    ys = [p[1] for n in locali for p in cp.LOCALI[n]["poly"]]
    r = [min(xs) - cp.SP_EST, min(ys) - cp.SP_EST, max(xs) + cp.SP_EST, max(ys) + cp.SP_EST]
    if balconi:
        for b in cp.BALCONI:
            r = [min(r[0], b[0] - 5), min(r[1], b[1] - 5), max(r[2], b[2] + 5), max(r[3], b[3] + 5)]
    return r


def impagina(reg):
    """Formato e scala standard piu' grande che fa stare la regione nel foglio."""
    rw, rh = reg[2] - reg[0], reg[3] - reg[1]
    for s in SCALE:
        for fmt_ in (landscape(A3), portrait(A3)):
            w, h = fmt_
            aw = w - 2 * MARG - 2 * FASCIA
            ah = h - 2 * MARG - TITOLO - LEGENDA - 2 * FASCIA
            k = 10 * mm / s
            if rw * k <= aw and rh * k <= ah:
                return fmt_, s, k
    raise ValueError("regione troppo grande per l'A3")


class Foglio:
    def __init__(self, cv, reg, locali, generale):
        self.cv, self.reg, self.locali, self.generale = cv, reg, locali, generale
        (self.w, self.h), self.scala, self.k = impagina(reg)
        cv.setPageSize((self.w, self.h))
        rw, rh = (reg[2] - reg[0]) * self.k, (reg[3] - reg[1]) * self.k
        aw = self.w - 2 * MARG - 2 * FASCIA
        ah = self.h - 2 * MARG - TITOLO - LEGENDA - 2 * FASCIA
        self.fx0 = MARG + FASCIA + (aw - rw) / 2
        self.fy1 = self.h - MARG - TITOLO - FASCIA - (ah - rh) / 2
        self.fx1, self.fy0 = self.fx0 + rw, self.fy1 - rh
        self.dim = 5.0 if generale else 6.5

    def X(self, x):
        return self.fx0 + (x - self.reg[0]) * self.k

    def Y(self, y):
        return self.fy1 - (y - self.reg[1]) * self.k

    # ---------------- primitive ----------------
    def rett(self, x0, y0, x1, y1, fill=None, stroke=None, lw=0.3, dash=None):
        cv = self.cv
        cv.saveState()
        if dash:
            cv.setDash(*dash)
        if stroke is not None:
            cv.setStrokeColor(stroke)
            cv.setLineWidth(lw)
        if fill is not None:
            cv.setFillColor(fill)
        cv.rect(self.X(min(x0, x1)), self.Y(max(y0, y1)), abs(x1 - x0) * self.k, abs(y1 - y0) * self.k,
                stroke=int(stroke is not None), fill=int(fill is not None))
        cv.restoreState()

    def linea(self, x0, y0, x1, y1, col, lw, dash=None):
        cv = self.cv
        cv.saveState()
        cv.setStrokeColor(col)
        cv.setLineWidth(lw)
        if dash:
            cv.setDash(*dash)
        cv.line(self.X(x0), self.Y(y0), self.X(x1), self.Y(y1))
        cv.restoreState()

    def testo(self, px, py, s, size, col, bold=False, rot=0, alone=True):
        """Testo centrato nel punto (px, py) della pagina, con alone bianco."""
        cv = self.cv
        font = "Helvetica-Bold" if bold else "Helvetica"
        w = stringWidth(s, font, size)
        cv.saveState()
        cv.translate(px, py)
        cv.rotate(rot)
        if alone:
            t = cv.beginText(-w / 2, -size * 0.35)
            t.setFont(font, size)
            t.setTextRenderMode(1)
            cv.setStrokeColor(colors.white)
            cv.setLineWidth(size * 0.35)
            cv.setLineJoin(1)
            t.textOut(s)
            # il modo di resa resta nello stato grafico: si rimette "pieno" prima di ET
            t.setTextRenderMode(0)
            cv.drawText(t)
        cv.setFillColor(col)
        cv.setFont(font, size)
        cv.drawString(-w / 2, -size * 0.35, s)
        cv.restoreState()

    def tick(self, px, py, col, lw=0.5):
        d = 0.8 * mm
        self.cv.setStrokeColor(col)
        self.cv.setLineWidth(lw)
        self.cv.line(px - d, py - d, px + d, py + d)

    def catena(self, vals, orizz, pos, verso, col, size, estremi=None):
        """Catena di quote in coordinate di pagina: pos e' la quota della linea
        (Y se orizz, X se verticale), verso = +1/-1 dove scrivere i numeri."""
        cv = self.cv
        vals = sorted({round(v, 1) for v in vals})
        if len(vals) < 2:
            return
        P = self.X if orizz else self.Y
        cv.saveState()
        cv.setStrokeColor(col)
        cv.setLineWidth(0.35)
        if orizz:
            cv.line(P(vals[0]), pos, P(vals[-1]), pos)
        else:
            cv.line(pos, P(vals[0]), pos, P(vals[-1]))
        for v in vals:
            self.tick(P(v), pos, col) if orizz else self.tick(pos, P(v), col)
            if estremi is not None:
                cv.setStrokeColor(C_GRIGIO)
                cv.setLineWidth(0.2)
                cv.setDash(1.5, 1.5)
                if orizz:
                    cv.line(P(v), estremi, P(v), pos + verso * 1.2 * mm)
                else:
                    cv.line(estremi, P(v), pos + verso * 1.2 * mm, P(v))
                cv.setDash()
        cv.restoreState()
        prima = None
        for i, (a, b) in enumerate(zip(vals, vals[1:])):
            s = fmt(b - a)
            lung = abs(P(b) - P(a))
            w = stringWidth(s, "Helvetica", size)
            off = 0.6 * mm + size * 0.4
            # numeri che non stanno nel tratto: sfalsati sull'altro lato, a turno
            if w + 1.5 > lung:
                prima = not prima if prima is not None else True
                if prima:
                    off = -off
            else:
                prima = None
            m = (P(a) + P(b)) / 2
            if orizz:
                self.testo(m, pos + verso * off, s, size, col)
            else:
                self.testo(pos + verso * off, m, s, size, col, rot=90)

    # ---------------- contenuto ----------------
    def posa(self):
        for nome in cp.LOCALI:
            for c in VAR["loc"][nome]["celle"]:
                col = tono(c)
                for p in c["parti"]:
                    self.rett(p[0], p[1], p[2], p[3], fill=col, stroke=C_FUGA, lw=0.25)
        # il pavimento prosegue sotto le porte, con la stessa griglia
        interne = {s["k"] for s in cp.SOGLIE_INTERNE} if VAR.get("o_loc") else set()
        for nome, k, r in c3.soglie_loc:
            if k in interne:
                continue
            ox, oy = VAR.get("o_loc", {}).get(nome, VAR["o"])
            for a0, a1, b0, b1 in cp._griglia(r, ox, oy):
                x0, x1 = max(a0, r[0]), min(a1, r[2])
                y0, y1 = max(b0, r[1]), min(b1, r[3])
                if x1 - x0 > 0.05 and y1 - y0 > 0.05:
                    self.rett(x0, y0, x1, y1, fill=colors.white, stroke=C_FUGA, lw=0.25)
        for d in cp.LOCALI.values():
            p = self.cv.beginPath()
            pts = d["fin"]
            p.moveTo(self.X(pts[0][0]), self.Y(pts[0][1]))
            for x, y in pts[1:]:
                p.lineTo(self.X(x), self.Y(y))
            p.close()
            self.cv.setStrokeColor(C_FUGA)
            self.cv.setLineWidth(0.35)
            self.cv.drawPath(p, stroke=1, fill=0)

    def balconi(self):
        cv = self.cv
        for x0, y0, x1, y1, rn, ro, re, sm in cp.BALCONI:
            pts = ((x0, y0), (x1 - sm, y0), (x1, y0 + sm), (x1, y1), (x0, y1))
            p = cv.beginPath()
            p.moveTo(self.X(pts[0][0]), self.Y(pts[0][1]))
            for x, y in pts[1:]:
                p.lineTo(self.X(x), self.Y(y))
            p.close()
            cv.saveState()
            cv.setFillColor(colors.white)
            cv.setStrokeColor(C_GRIGIO)
            cv.setLineWidth(0.3)
            cv.setDash(3, 2)
            cv.drawPath(p, stroke=1, fill=1)
            cv.restoreState()
            ring = []
            if rn:
                ring.append((x0, y0, x1 - sm, y0))
                if sm:
                    ring.append((x1 - sm, y0, x1, y0 + sm))
            if ro:
                ring.append((x0, y0, x0, y1))
            if re:
                ring.append((x1, y0 + sm, x1, y1))
            for r in ring:
                self.linea(*r, NERO, 1.4)
            self.testo(self.X((x0 + x1) / 2), self.Y((y0 + y1) / 2), f"BALCONE {fmt(x1 - x0)} x {fmt(y1 - y0)}",
                       self.dim + 1, NERO)
        for x0, y0, x1, y1, _h in cp.SEPARE:
            self.linea(x0, y0, x1, y1, NERO, 2.2)

    def muri(self):
        for a, b, cc, orizz, q0, q1, sp in c3.muri:
            if not q0 <= H_TAGLIO < q1:
                continue
            if orizz:
                self.rett(a, cc - sp / 2, b, cc + sp / 2, fill=C_MURO)
            else:
                self.rett(cc - sp / 2, a, cc + sp / 2, b, fill=C_MURO)
        # i muri sono generati lato per lato: negli spigoli convessi dei locali
        # (angoli esterni e innesti dei tramezzi) resta un quadrato vuoto
        def verso(d):
            """Normale verso l'interno del locale per un lato percorso nella direzione d."""
            return (-math.copysign(1, d[1]) if d[1] else 0, math.copysign(1, d[0]) if d[0] else 0)

        def sp_presso(nome, v, d, s):
            """Spessore del muro del lato di direzione d, nei 3 cm accanto al vertice v."""
            orizz = bool(d[0])
            c, t = (v[1], v[0]) if orizz else (v[0], v[1])
            return cp.spessore(nome, c, orizz, *sorted((t, t + s * math.copysign(3, d[0] or d[1]))))

        for nome, d in cp.LOCALI.items():
            poly = d["poly"]
            for i, v in enumerate(poly):
                p, q = poly[i - 1], poly[(i + 1) % len(poly)]
                da = (v[0] - p[0], v[1] - p[1])
                db = (q[0] - v[0], q[1] - v[1])
                na, nb = verso(da), verso(db)
                if db[0] * na[0] + db[1] * na[1] <= 0:      # spigolo rientrante
                    continue
                ta, tb = sp_presso(nome, v, da, -1), sp_presso(nome, v, db, 1)
                self.rett(v[0], v[1], v[0] - na[0] * ta - nb[0] * tb, v[1] - na[1] * ta - nb[1] * tb,
                          fill=C_MURO)
        for x0, y0, x1, y1, lb in cp.PILASTRI:
            self.rett(x0, y0, x1, y1, fill=C_CA)
            if not self.generale:
                self.testo(self.X((x0 + x1) / 2), self.Y((y0 + y1) / 2), lb, self.dim, colors.white,
                           bold=True, alone=False)
        for x0, y0, x1, y1, lb in cp.CANNE:
            self.rett(x0, y0, x1, y1, fill=C_CANNA)

    def infissi(self):
        cv = self.cv
        for n, t in enumerate(cp.APERTURE, 1):
            tipo = t[0]
            lato = lato_apertura(t, cp.LOCALI)
            if not lato:
                continue
            nome, orizz, c, a, b, dentro, va, vb = lato
            sp = cp.spessore(nome, c, orizz, va, vb)
            cc = c - dentro * sp / 2

            def P(s, q):   # s lungo il muro, q trasversale
                return (self.X(s), self.Y(q)) if orizz else (self.X(q), self.Y(s))

            def seg(s0, q0, s1, q1, col, lw, dash=None):
                cv.saveState()
                cv.setStrokeColor(col)
                cv.setLineWidth(lw)
                if dash:
                    cv.setDash(*dash)
                cv.line(*P(s0, q0), *P(s1, q1))
                cv.restoreState()

            def arco(cs, cq, r, s_da, q_da):
                """Quarto di cerchio dal punto (s_da, q_da) attorno al cardine (cs, cq)."""
                pts = []
                a0 = math.atan2(q_da - cq, s_da - cs)
                a1 = math.atan2(dentro, 0)
                da = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
                for i in range(25):
                    an = a0 + da * i / 24
                    pts.append(P(cs + r * math.cos(an), cq + r * math.sin(an)))
                p = cv.beginPath()
                p.moveTo(*pts[0])
                for q in pts[1:]:
                    p.lineTo(*q)
                cv.saveState()
                cv.setStrokeColor(C_INFISSO)
                cv.setLineWidth(0.3)
                cv.setDash(2, 1.5)
                cv.drawPath(p, stroke=1, fill=0)
                cv.restoreState()

            def anta(cardine, libero):
                """Anta a battente aperta a 90 gradi verso il locale, con il suo arco."""
                r = abs(libero - cardine)
                seg(cardine, c, cardine, c + dentro * r, C_INFISSO, 0.9)
                arco(cardine, c, r, libero, c)

            if tipo in ("finestra", "portafinestra"):
                # telaio a filo interno e vetro
                seg(va, c, vb, c, C_VETRO, 0.5)
                seg(va, cc, vb, cc, C_VETRO, 0.9)
                seg(va, c - dentro * sp, vb, c - dentro * sp, C_VETRO, 0.3)
                if c3.ANTE_N.get(n, 1) == 2:
                    m = (va + vb) / 2
                    anta(va, m)
                    anta(vb, m)
                elif c3.CARDINI.get(n, 1):
                    anta(vb, va)
                else:
                    anta(va, vb)
            elif tipo == "battente":
                if c3.CARDINI.get(n, 1):
                    anta(vb, va)
                else:
                    anta(va, vb)
            elif n in cp.PIEGHEVOLI:
                m = (va + vb) / 2
                seg(va, c, m, c + dentro * 24, C_INFISSO, 0.8)
                seg(m, c + dentro * 24, vb, c, C_INFISSO, 0.8)
            else:
                # scomparsa: anta chiusa nel vano e tasca tratteggiata nel muro
                la, lb = va, vb
                if vb - va > cp.ANTA + 1:
                    mg = (vb - va - cp.ANTA) / 2
                    la, lb = va + mg, vb - mg
                seg(la, cc, lb, cc, C_INFISSO, 1.6)
                if n in cp.TASCHE:
                    t0, t1 = cp.TASCHE[n]
                    for q in (cc - 3, cc + 3):
                        seg(t0, q, t1, q, C_INFISSO, 0.35, (2, 1.2))
                    for s in (t0, t1):
                        seg(s, cc - 3, s, cc + 3, C_INFISSO, 0.35, (2, 1.2))

    def quote_locali(self):
        """Una quota per lato di ogni locale; dove ci sono aperture diventa una catena."""
        assegnate = {}
        for n, t in enumerate(cp.APERTURE, 1):
            lato = lato_apertura(t, self.locali)
            if lato:
                assegnate.setdefault((lato[0], lato[1], round(lato[2], 1)), []).append((n, t, lato))
        for nome in self.locali:
            for orizz, c, a, b, dentro in cp.lati(cp.LOCALI[nome]["poly"]):
                if b - a < 25:
                    continue
                vals = [a, b]
                for n, t, (_nm, _o, _c, _a, _b, _d, va, vb) in assegnate.get((nome, orizz, round(c, 1)), []):
                    vals += [max(va, a), min(vb, b)]
                q = c + dentro * DIM_INT
                pos = self.Y(q) if orizz else self.X(q)
                verso = -dentro if orizz else dentro
                self.catena(vals, orizz, pos, verso, C_QUOTA, self.dim)
        # sigla di ogni apertura, dentro il locale che la quota
        for lst in assegnate.values():
            for n, t, (nome, orizz, c, a, b, dentro, va, vb) in lst:
                tipo = t[0]
                z0, z1 = cp.quote_vano(n, tipo)
                if tipo in ("porta", "passaggio"):
                    luce = min(vb - va, cp.ANTA)
                    s = f"{n} PORTA {fmt(luce)}x{fmt(z1 - z0)}"
                    if vb - va > luce + 1:
                        s += f" (vano {fmt(vb - va)})"
                elif tipo == "battente":
                    s = f"{n} PORTONCINO {fmt(vb - va)}x{fmt(z1 - z0)}"
                elif tipo == "finestra":
                    s = f"{n} FINESTRA {fmt(vb - va)}x{fmt(z1 - z0)} dav. {fmt(z0)}"
                else:
                    s = f"{n} PORTAFINESTRA {fmt(vb - va)}x{fmt(z1 - z0)}"
                q = c + dentro * (DIM_INT + 16)
                m = (va + vb) / 2
                if orizz:
                    self.testo(self.X(m), self.Y(q), s, self.dim, C_INFISSO, bold=True)
                else:
                    self.testo(self.X(q), self.Y(m), s, self.dim, C_INFISSO, bold=True, rot=90)

    def etichette(self):
        for nome in self.locali:
            d = cp.LOCALI[nome]
            l = VAR["loc"][nome]
            x0, y0, x1, y1 = d["bb"]
            cx, cy = d.get("lab", ((x0 + x1) / 2, (y0 + y1) / 2))
            px, py = self.X(cx), self.Y(cy)
            s = self.dim + 3
            self.testo(px, py + s * 0.6, nome, s, C_LOCALE, bold=True)
            self.testo(px, py - s * 0.6, f"{d['area']:.2f} mq".replace(".", ","), self.dim + 1, C_LOCALE)
            self.testo(px, py - s * 0.6 - self.dim * 1.4,
                       f"{l['intere']} intere / {l['tagli']} tagliate", self.dim, C_LOCALE)

    def pezzi(self):
        """Misure dei pezzi tagliati, scritte dentro il pezzo se ci stanno."""
        size = 4.2
        for nome in self.locali:
            for c in VAR["loc"][nome]["celle"]:
                if c["intera"]:
                    continue
                x0 = min(p[0] for p in c["parti"])
                y0 = min(p[1] for p in c["parti"])
                x1 = max(p[2] for p in c["parti"])
                y1 = max(p[3] for p in c["parti"])
                # la cella comprende una fuga: la lastra e' piu' corta di quella
                lx, ly = c["dx"] - cp.FUGA, c["dy"] - cp.FUGA
                if lx > cp.PIASTRELLA_X - 0.5 and ly > cp.PIASTRELLA_Y - 0.5:
                    continue
                s = f"{lx:.0f}x{ly:.0f}"
                w = stringWidth(s, "Helvetica", size)
                bw, bh = (x1 - x0) * self.k, (y1 - y0) * self.k
                px, py = self.X((x0 + x1) / 2), self.Y((y0 + y1) / 2)
                if w + 2 < bw and bh > size + 2:
                    self.testo(px, py, s, size, C_PEZZO, alone=False)
                elif w + 2 < bh and bw > size + 2:
                    self.testo(px, py, s, size, C_PEZZO, rot=90, alone=False)

    def quote_esterne(self):
        """Tre catene per lato: aperture in facciata, fili dei muri, totale."""
        xs = [p[0] for n in self.locali for p in cp.LOCALI[n]["poly"]]
        ys = [p[1] for n in self.locali for p in cp.LOCALI[n]["poly"]]
        vani = {"top": [], "bottom": [], "left": [], "right": []}
        rects = [r for d in cp.LOCALI.values() for r in d["rect"]]
        for n, t in enumerate(cp.APERTURE, 1):
            if t[0] not in ("finestra", "portafinestra", "battente"):
                continue
            lato = lato_apertura(t, self.locali)
            if not lato:
                continue
            nome, orizz, c, a, b, dentro, va, vb = lato
            m = (va + vb) / 2
            # in facciata solo se verso l'esterno non c'e' un altro locale davanti
            if orizz:
                davanti = any(r[0] < m < r[2] and (r[3] < c - 1 if dentro > 0 else r[1] > c + 1) for r in rects)
                lato_f = "top" if dentro > 0 else "bottom"
            else:
                davanti = any(r[1] < m < r[3] and (r[2] < c - 1 if dentro > 0 else r[0] > c + 1) for r in rects)
                lato_f = "left" if dentro > 0 else "right"
            if not davanti:
                vani[lato_f] += [va, vb]
        for lato, orizz, base, verso, vv in (
                ("top", True, self.fy1, 1, xs), ("bottom", True, self.fy0, -1, xs),
                ("left", False, self.fx0, -1, ys), ("right", False, self.fx1, 1, ys)):
            catene = [vani[lato] + [min(vv), max(vv)] if vani[lato] else [], vv, [min(vv), max(vv)]]
            for liv, vals in zip(LIVELLI, catene):
                if vals:
                    self.catena(vals, orizz, base + verso * liv, verso, C_EST, self.dim + 0.5,
                                estremi=base if liv == LIVELLI[0] or not catene[0] and liv == LIVELLI[1] else None)

    # ---------------- foglio ----------------
    def disegna(self, titolo, n_foglio):
        cv = self.cv
        cv.saveState()
        p = cv.beginPath()
        p.rect(self.fx0, self.fy0, self.fx1 - self.fx0, self.fy1 - self.fy0)
        cv.clipPath(p, stroke=0, fill=0)
        self.balconi()
        self.posa()
        self.muri()
        self.infissi()
        if not self.generale:
            self.pezzi()
        self.quote_locali()
        self.etichette()
        cv.restoreState()
        cv.setStrokeColor(C_GRIGIO)
        cv.setLineWidth(0.3)
        cv.rect(self.fx0, self.fy0, self.fx1 - self.fx0, self.fy1 - self.fy0)
        self.quote_esterne()
        self.cartiglio(titolo, n_foglio)

    def cartiglio(self, titolo, n_foglio):
        cv = self.cv
        f = cp.FORMATO
        cv.setFillColor(NERO)
        cv.setFont("Helvetica-Bold", 13)
        cv.drawString(MARG, self.h - MARG - 5 * mm, f"{titolo}  -  scala 1:{self.scala} (A3)")
        cv.setFont("Helvetica", 8)
        orig = "origine ottimale per ogni stanza" if VAR.get("o_loc") else \
            f"origine griglia {fmt(VAR['o'][0])} / {fmt(VAR['o'][1])}"
        cv.drawString(MARG, self.h - MARG - 10.5 * mm,
                      f"Posa pavimento #{POSA_3D} (ordine di sfrido del modello 3D): gres {c3.POSA[K_POSA]['nome']}, "
                      f"fuga {f['fuga'] * 10:.0f} mm, {orig}  -  {STAT['lastre']} lastre ({fmt(STAT['mq'])} mq), "
                      f"{STAT['intere']} intere, {STAT['tagli']} tagliate, sfrido {fmt(STAT['sfrido'])}%")
        cv.drawRightString(self.w - MARG, self.h - MARG - 5 * mm, f"foglio {n_foglio}/{len(FOGLI)}")
        # scala grafica (1 m per tacca), legenda e note dal basso verso l'alto
        n = 5 if self.k * 500 < 120 * mm else 3
        sx, sy = MARG, MARG + 12.5 * mm
        cv.setStrokeColor(NERO)
        cv.setLineWidth(0.4)
        for i in range(n):
            cv.setFillColor(NERO if i % 2 == 0 else colors.white)
            cv.rect(sx + i * 100 * self.k, sy + 3 * mm, 100 * self.k, 1.8 * mm, stroke=1, fill=1)
        cv.setFillColor(NERO)
        cv.setFont("Helvetica", 6.5)
        for i in range(n + 1):
            cv.drawCentredString(sx + i * 100 * self.k, sy, f"{i} m" if i == n else str(i))
        y = MARG + 5 * mm
        x = MARG
        cv.setFont("Helvetica", 7)
        for col, lab in CLASSI + [(C_MURO, f"muri sezionati a {H_TAGLIO:.0f} cm"), (C_CA, "pilastri in c.a.")]:
            cv.setFillColor(col)
            cv.setStrokeColor(NERO)
            cv.setLineWidth(0.4)
            cv.rect(x, y, 6 * mm, 3.5 * mm, stroke=1, fill=1)
            cv.setFillColor(NERO)
            cv.drawString(x + 7.5 * mm, y + 1 * mm, lab)
            x += 7.5 * mm + stringWidth(lab, "Helvetica", 7) + 6 * mm
        cv.setFont("Helvetica", 6.5)
        nota = ("quote in cm al filo muro (prima di rivestimento e battiscopa); dentro i locali le misure di "
                "ogni lato con le aperture, fuori le catene di facciata; porte a scomparsa con tasca tratteggiata")
        if not self.generale:
            nota += "; nei pezzi tagliati la misura della lastra (x per y)"
        cv.drawString(MARG, MARG, nota)


def main():
    cv = canvas.Canvas(OUT)
    cv.setTitle(f"Piantina 2D - posa #{POSA_3D} {c3.POSA[K_POSA]['nome']}")
    for i, (titolo, locali, generale) in enumerate(FOGLI, 1):
        reg = regione(locali, balconi=generale)
        Foglio(cv, reg, locali, generale).disegna(titolo, i)
        cv.showPage()
    try:
        cv.save()
        print("scritto:", OUT)
    except PermissionError as e:
        print("pdf non scritto (aperto in un visualizzatore?):", e)


if __name__ == "__main__":
    main()
