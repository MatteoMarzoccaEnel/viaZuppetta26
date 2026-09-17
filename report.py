"""Report tecnico di posa in PDF, uno per configurazione di casa_pianta.FORMATI.

Ogni report e' autoconsistente: specifiche del materiale, computo del pavimento
locale per locale con la classificazione dei tagli, rivestimento del bagno diviso
per prodotto, battiscopa, sfrido con e senza riuso degli scarti, consumi di colla
e fuga. I numeri non sono trascritti da nessuna parte: arrivano dagli stessi
script che generano pianta e modello 3D, rieseguiti per ogni formato.

Esecuzione:  python report.py            (tutti i formati)
             python report.py --posa=2   (solo quello indicato)
"""

import contextlib
import io
import math
import re
import sys
from datetime import date

with contextlib.redirect_stdout(io.StringIO()):
    import casa_pianta as cp
    import bagno_rivestimento as br
    import battiscopa as bs
    import casa_3d as c3

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.graphics.shapes import Drawing, Polygon
from reportlab.platypus import (PageBreak, Paragraph, SimpleDocTemplate, Spacer,
                                Table, TableStyle)
from svglib.svglib import svg2rlg

# =====================================================================
# SPECIFICHE DI CAPITOLATO
# =====================================================================

SPESSORE = 10.0        # mm, gres porcellanato
PESO_MQ = 23.0         # kg/mq di gres da 10 mm
COLLA_MQ = 5.0         # kg/mq, doppia spalmatura obbligatoria sui grandi formati
DENS_FUGA = 1.6        # kg/dm3 del riempitivo
PROF_FUGA = SPESSORE   # la fuga si riempie per tutto lo spessore
SFRIDO_CANTIERE = 0.05  # rotture e prove di posa, oltre ai tagli calcolati

PREVENTIVO = {"gres": 105.3, "dedicata": 32.4}   # mq da preventivo fornitore

BLU = colors.HexColor("#0b4fa0")
GRIGIO = colors.HexColor("#eef1f4")
ROSSO = colors.HexColor("#b03020")

S_TIT = ParagraphStyle("tit", fontName="Helvetica-Bold", fontSize=17, leading=21,
                       textColor=BLU, spaceAfter=2)
S_SOT = ParagraphStyle("sot", fontName="Helvetica", fontSize=10, leading=13,
                       textColor=colors.HexColor("#555555"), spaceAfter=10)
S_SEZ = ParagraphStyle("sez", fontName="Helvetica-Bold", fontSize=11.5, leading=14,
                       textColor=BLU, spaceBefore=12, spaceAfter=5)
S_TXT = ParagraphStyle("txt", fontName="Helvetica", fontSize=8.5, leading=11.5,
                       spaceAfter=3)
S_NOTA = ParagraphStyle("nota", fontName="Helvetica-Oblique", fontSize=7.8,
                        leading=10.5, textColor=colors.HexColor("#555555"))


def tabella(dati, larghezze, allinea_dx=None, totale=False):
    t = Table(dati, colWidths=larghezze, repeatRows=1)
    st = [
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("LEADING", (0, 0), (-1, -1), 10),
        ("BACKGROUND", (0, 0), (-1, 0), GRIGIO),
        ("TEXTCOLOR", (0, 0), (-1, 0), BLU),
        ("LINEBELOW", (0, 0), (-1, 0), 0.8, BLU),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7f9fb")]),
    ]
    for c in (allinea_dx or range(1, len(dati[0]))):
        st.append(("ALIGN", (c, 0), (c, -1), "RIGHT"))
    if totale:
        st += [("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
               ("LINEABOVE", (0, -1), (-1, -1), 0.8, BLU),
               ("BACKGROUND", (0, -1), (-1, -1), GRIGIO)]
    t.setStyle(TableStyle(st))
    return t


def n(v, d=2):
    return f"{v:,.{d}f}".replace(",", " ").replace(".", ",")


# =====================================================================
# ANTEPRIME
# =====================================================================

H_SEZIONE = 130.0       # quota di taglio dell'assonometria: sopra si vedrebbe solo il tetto
_C30, _S30 = math.cos(math.radians(30)), math.sin(math.radians(30))


def _proj(x, q, z):
    """Assonometria isometrica: x e z sono la pianta, q la quota."""
    return ((x - z) * _C30, (x + z) * _S30 - q)


def _volumi():
    """Parallelepipedi da disegnare: (x0, z0, x1, z1, base, cima, colore)."""
    v = []
    for x0, z0, x1, z1 in c3.pavimento:
        v.append((x0, z0, x1, z1, -2.0, 0.0, colors.HexColor("#e9e4da")))
    for a, b, c, orizz, q0, q1, sp in c3.muri:
        if q0 >= H_SEZIONE:
            continue
        if orizz:
            box = (a, c - sp / 2, b, c + sp / 2)
        else:
            box = (c - sp / 2, a, c + sp / 2, b)
        v.append((*box, q0, min(q1, H_SEZIONE), colors.HexColor("#d8d3c9")))
    for x, z, w, h, base, alt, col, tipo in c3.mobili:
        if base >= H_SEZIONE:
            continue
        v.append((x, z, x + w, z + h, base, min(base + alt, H_SEZIONE),
                  colors.HexColor(col)))
    for x, z, w, h, base, alt in c3.muretti:
        v.append((x, z, x + w, z + h, base, min(base + alt, H_SEZIONE),
                  colors.HexColor("#e6e2db")))
    return v


def assonometria(larghezza, altezza):
    """Vista assonometrica sezionata, costruita dagli stessi volumi del modello 3D."""
    v = _volumi()
    pts = [_proj(x, q, z) for x0, z0, x1, z1, q0, q1, _ in v
           for x, z in ((x0, z0), (x1, z1), (x0, z1), (x1, z0)) for q in (q0, q1)]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    dx, dy = max(xs) - min(xs), max(ys) - min(ys)
    k = min(larghezza / dx, altezza / dy)
    ox, oy = -min(xs) * k, -min(ys) * k

    def P(x, q, z):
        a, b = _proj(x, q, z)
        return [a * k + ox, b * k + oy]

    d = Drawing(dx * k, dy * k)
    # pittore: prima i volumi lontani, cioe' quelli con x+z minore
    for x0, z0, x1, z1, q0, q1, col in sorted(v, key=lambda t: t[0] + t[1]):
        facce = [
            ([P(x0, q1, z0), P(x1, q1, z0), P(x1, q1, z1), P(x0, q1, z1)], 1.00),
            ([P(x1, q0, z0), P(x1, q0, z1), P(x1, q1, z1), P(x1, q1, z0)], 0.80),
            ([P(x0, q0, z1), P(x1, q0, z1), P(x1, q1, z1), P(x0, q1, z1)], 0.64),
        ]
        for punti, ombra in facce:
            c = colors.Color(col.red * ombra, col.green * ombra, col.blue * ombra)
            d.add(Polygon([c for p in punti for c in p], fillColor=c,
                          strokeColor=colors.Color(0, 0, 0, 0.25), strokeWidth=0.2))
    return d


def pianta(i, larghezza, altezza):
    """La pianta di posa del formato attivo, in vettoriale."""
    p = cp.disegna(cp.VARIANTI["A"], suffisso=f"_posa{i}")
    dis = svg2rlg(p + ".svg")
    k = min(larghezza / dis.width, altezza / dis.height)
    dis.scale(k, k)
    dis.width *= k
    dis.height *= k
    return dis


# =====================================================================
# CONTENUTO
# =====================================================================


def costruisci(i):
    """Elementi del report per la configurazione i-esima."""
    f = cp.usa_formato(i)
    var = cp.VARIANTI["A"]
    tot, loc = var["tot"], var["loc"]
    riv = br.calcola()
    bat = bs.calcola()
    P, L = cp.PIASTRELLA, cp.LASTRA
    e = []

    # ---- intestazione ----
    e.append(Paragraph(f"Computo di posa &ndash; {f['nome']}", S_TIT))
    e.append(Paragraph(
        f"Appartamento di {n(cp.AREA_TOT)} mq calpestabili &middot; variante di posa A "
        f"(origine griglia {n(var['o'][0], 1)} / {n(var['o'][1], 1)} cm) &middot; "
        f"emesso il {date.today().strftime('%d/%m/%Y')}", S_SOT))

    # ---- specifiche materiale ----
    e.append(Paragraph("1. Specifiche del materiale", S_SEZ))
    riemp = (2 * P * 10) / (P * 10 * P * 10) * (cp.FUGA * 10) * PROF_FUGA * DENS_FUGA
    e.append(tabella([
        ["grandezza", "valore", "note"],
        ["formato nominale", f"{P:.0f} x {P:.0f} cm", "gres porcellanato rettificato"],
        ["spessore", f"{SPESSORE:.0f} mm", "confermato in capitolato"],
        ["superficie lastra", f"{n(L)} mq", "al netto della fuga"],
        ["peso", f"{n(PESO_MQ, 1)} kg/mq", f"{n(L * PESO_MQ, 1)} kg a lastra"],
        ["fuga di posa", f"{n(cp.FUGA * 10, 1)} mm", "giunto minimo per rettificato"],
        ["modulo di posa", f"{n(cp.MODULO)} cm", "formato + fuga: passo della griglia"],
        ["riempitivo fuga", f"{n(riemp, 3)} kg/mq",
         f"(A+B)/(A\u00b7B) \u00b7 {n(cp.FUGA * 10, 1)} \u00b7 "
         f"{PROF_FUGA:.0f} \u00b7 {n(DENS_FUGA, 1)}"],
        ["adesivo", f"{n(COLLA_MQ, 1)} kg/mq", "C2TE S1, doppia spalmatura"],
    ], [42 * mm, 32 * mm, 106 * mm], allinea_dx=[1]))

    # ---- pavimento ----
    e.append(Paragraph("2. Pavimento &ndash; analisi lastra per lastra", S_SEZ))
    righe = [["locale", "superficie", "lastre\nintere", "lastre\ntagliate",
              "di cui\n< 25 cm", "25-45\ncm", "> 45\ncm", "lato\nminimo",
              "% da\nlastra intera", "lastre\ncon riuso"]]
    for nome, d in cp.LOCALI.items():
        l = loc[nome]
        righe.append([nome.title(), n(d["area"]) + " mq", l["intere"], l["tagli"],
                      l["sliver"], l["medi"], l["buoni"], n(l["min_lato"], 1) + " cm",
                      n(l["q_intere"] * 100, 1) + "%", l["lastre"]])
    righe.append(["TOTALE", n(cp.AREA_TOT) + " mq", tot["intere"], tot["tagli"],
                  tot["sliver"], tot["medi"], tot["buoni"],
                  n(tot["min_lato"], 1) + " cm",
                  n(tot["q_intere"] * 100, 1) + "%", tot["lastre"]])
    e.append(tabella(righe, [30 * mm, 19 * mm, 15 * mm, 16 * mm, 14 * mm, 13 * mm,
                             13 * mm, 15 * mm, 20 * mm, 17 * mm], totale=True))
    senza = tot["intere"] + tot["tagli"]
    e.append(Spacer(1, 4))
    e.append(Paragraph(
        f"Le lastre tagliate sono {tot['tagli']}: accoppiando due pezzi piccoli sulla "
        f"stessa lastra ne servono {tot['lastre']}, tagliandone una per pezzo "
        f"{senza}. I pezzi con lato inferiore a {cp.SLIVER:.0f} cm sono listelli di "
        f"difficile posa: in questa configurazione sono {tot['sliver']}, il lato piu' "
        f"stretto misura {n(tot['min_lato'], 1)} cm.", S_TXT))

    # ---- rivestimento ----
    e.append(Paragraph("3. Rivestimento del bagno", S_SEZ))
    tagliato = cp.FORMATO.get("riv_h")
    e.append(Paragraph(
        f"Altezza rivestita {n(cp.H_RIV, 1)} cm su {cp.RIV_CORSI} corsi"
        + (f", con l'ultimo corso tagliato a {n(cp.H_RIV - (cp.RIV_CORSI - 1) * cp.MODULO, 1)} cm "
           f"per chiudere a filo dell'intradosso della trave." if tagliato
           else ", tutti interi.") +
        " Il bagno e' privo di battiscopa.", S_TXT))
    righe = [["prodotto", "sviluppo", "superficie", "lastre\nintere",
              "pezzi\ntagliati", "lastre da\npezzi accopp.", "lastre\ncon riuso",
              "lastre\nsenza riuso"]]
    et = {"proprio": "Piastrella dedicata (sanitari e testata)",
          "pavimento": f"Gres {P:.0f}x{P:.0f}, pareti restanti"}
    for g in ("proprio", "pavimento"):
        d = riv[g]
        righe.append([et[g], n(d["sviluppo"] / 100) + " m", n(d["sup"]) + " mq",
                      d["intere"], d["tagli"], d["accoppiate"],
                      d["lastre_riuso"], d["lastre_senza"]])
    e.append(tabella(righe, [58 * mm, 18 * mm, 19 * mm, 15 * mm, 15 * mm,
                             22 * mm, 16 * mm, 17 * mm]))
    e.append(Spacer(1, 4))
    e.append(Paragraph("Sviluppo delle pareti considerate, gia' al netto di porta e "
                       "finestra:", S_TXT))
    righe = [["prodotto", "parete", "sviluppo"]]
    for g in ("proprio", "pavimento"):
        for _, desc, lung in riv[g]["pareti"]:
            righe.append(["dedicata" if g == "proprio" else "gres", desc,
                          n(lung / 100) + " m"])
    e.append(tabella(righe, [24 * mm, 116 * mm, 20 * mm], allinea_dx=[2]))

    # ---- battiscopa ----
    e.append(PageBreak())
    e.append(Paragraph("4. Battiscopa", S_SEZ))
    e.append(Paragraph(
        f"Battiscopa h {bs.H_BATT:.0f} cm ricavato tagliando le lastre in strisce: "
        f"{bs.STRISCE} strisce utili per lastra, pari a {n(bat['ml_lastra'], 1)} m. "
        f"Il percorso e' continuo lungo il perimetro di ogni locale e si interrompe "
        f"solo sui vani che arrivano a terra; la contiguita' dei tratti e' verificata "
        f"automaticamente.", S_TXT))
    righe = [["locale", "perimetro", "detrazione vani", "netto", "tratti"]]
    for k, d in bat["per_loc"].items():
        righe.append([k.title(), n(d["perimetro"] / 100) + " m",
                      n(d["aperture"] / 100) + " m", n(d["netto"] / 100) + " m",
                      d["tratti"]])
    righe.append(["TOTALE", "", "", n(bat["netto"]) + " m",
                  sum(d["tratti"] for d in bat["per_loc"].values())])
    e.append(tabella(righe, [40 * mm, 30 * mm, 35 * mm, 30 * mm, 20 * mm],
                     totale=True))
    e.append(Spacer(1, 4))
    e.append(Paragraph(
        f"Con la maggiorazione del {bs.MAGGIORAZIONE * 100:.0f}% per spezzoni d'angolo "
        f"e ricongiunzioni si posano {n(bat['ml'])} m, pari a {bat['lastre']} lastre "
        f"({n(bat['lastre'] * L)} mq). Dietro cucina e armadiature il battiscopa non "
        f"serve: si scenderebbe a {n(bat['senza_arredo'])} m.", S_TXT))

    # ---- riepilogo e sfrido ----
    e.append(Paragraph("5. Riepilogo, sfrido e forniture", S_SEZ))
    v_gres = [("Pavimento", cp.AREA_TOT - 1.25, tot["lastre"], senza),
              (f"Rivestimento bagno in {P:.0f}x{P:.0f}", riv["pavimento"]["sup"],
               riv["pavimento"]["lastre_riuso"], riv["pavimento"]["lastre_senza"]),
              (f"Battiscopa h {bs.H_BATT:.0f} ({n(bat['ml'])} m)",
               bat["lastre"] * L, bat["lastre"], bat["lastre"])]
    v_ded = [("Rivestimento bagno, piastrella dedicata", riv["proprio"]["sup"],
              riv["proprio"]["lastre_riuso"], riv["proprio"]["lastre_senza"])]

    def blocco(titolo, voci, preventivo):
        righe = [["voce", "superficie\nnetta", "lastre\ncon riuso", "mq", "sfrido",
                  "lastre\nsenza riuso", "mq", "sfrido"]]
        smq = sc = ss = 0
        for nome, mq, c, s in voci:
            smq += mq
            sc += c
            ss += s
            righe.append([nome, n(mq) + " mq", c, n(c * L), n((c * L - mq) / (c * L) * 100, 1) + "%",
                          s, n(s * L), n((s * L - mq) / (s * L) * 100, 1) + "%"])
        righe.append(["TOTALE " + titolo, n(smq) + " mq", sc, n(sc * L),
                      n((sc * L - smq) / (sc * L) * 100, 1) + "%", ss, n(ss * L),
                      n((ss * L - smq) / (ss * L) * 100, 1) + "%"])
        t = tabella(righe, [56 * mm, 20 * mm, 16 * mm, 14 * mm, 14 * mm, 18 * mm,
                            14 * mm, 14 * mm], totale=True)
        p = preventivo / L
        nota = Paragraph(
            f"Preventivo fornitore {n(preventivo, 1)} mq = {p:.0f} lastre: "
            f"<b>{p - sc:+.0f}</b> lastre rispetto al fabbisogno con riuso, "
            f"<b>{p - ss:+.0f}</b> senza riuso.", S_TXT)
        return t, nota, smq, sc, ss

    t1, n1, mq1, c1, s1 = blocco("gres", v_gres, PREVENTIVO["gres"])
    e.append(Paragraph(f"Gres {P:.0f}x{P:.0f} &ndash; pavimento, battiscopa e "
                       f"meta' rivestimento del bagno", S_TXT))
    e.append(t1)
    e.append(n1)
    t2, n2, mq2, c2, s2 = blocco("dedicata", v_ded, PREVENTIVO["dedicata"])
    e.append(Spacer(1, 6))
    e.append(Paragraph("Piastrella dedicata &ndash; parete dei sanitari e testata "
                       "della finestra", S_TXT))
    e.append(t2)
    e.append(n2)

    # ---- consumi ----
    mq_tot, lastre_tot = mq1 + mq2, c1 + c2
    ordine = math.ceil(lastre_tot * (1 + SFRIDO_CANTIERE))
    e.append(Paragraph("6. Forniture accessorie e scorta", S_SEZ))
    e.append(tabella([
        ["voce", "quantita'", "base di calcolo"],
        ["superficie da posare", f"{n(mq_tot)} mq", "pavimento + rivestimento + battiscopa"],
        ["lastre da fornire", f"{lastre_tot}", "fabbisogno con riuso degli scarti"],
        ["sfrido di taglio", f"{n(lastre_tot * L - mq_tot)} mq",
         f"{n((lastre_tot * L - mq_tot) / (lastre_tot * L) * 100, 1)}% del materiale fornito"],
        ["scorta di cantiere", f"{ordine - lastre_tot} lastre",
         f"{SFRIDO_CANTIERE * 100:.0f}% per rotture e ricambi futuri"],
        ["TOTALE DA ORDINARE", f"{ordine} lastre = {n(ordine * L)} mq", ""],
        ["peso complessivo", f"{n(ordine * L * PESO_MQ, 0)} kg",
         f"{n(PESO_MQ, 1)} kg/mq, spessore {SPESSORE:.0f} mm"],
        ["adesivo", f"{n(mq_tot * COLLA_MQ, 0)} kg",
         f"{n(COLLA_MQ, 1)} kg/mq in doppia spalmatura"],
        ["riempitivo fuga", f"{n(mq_tot * riemp, 1)} kg",
         f"{n(riemp, 3)} kg/mq con fuga {n(cp.FUGA * 10, 1)} mm"],
        ["metri di taglio", f"{n((tot['tagli'] + riv['proprio']['tagli'] + riv['pavimento']['tagli']) * P / 100, 1)} m",
         "un taglio per pezzo, lato lastra"],
    ], [42 * mm, 50 * mm, 88 * mm], allinea_dx=[1], totale=False))

    e.append(Spacer(1, 8))
    e.append(Paragraph(
        "Sfrido con riuso: i pezzi piccoli vengono ricavati a coppie dalla stessa "
        "lastra, che e' possibile solo se le due misure stanno nel formato e se il "
        "posatore accetta di accantonare gli scarti. Senza riuso ogni pezzo tagliato "
        "consuma una lastra intera: e' l'ipotesi prudenziale da usare in fase di "
        "ordine se la posa e' affidata a terzi.", S_NOTA))

    # ---- anteprime ----
    e.append(PageBreak())
    e.append(Paragraph("7. Pianta di posa", S_SEZ))
    e.append(Paragraph(
        f"Griglia con origine {n(var['o'][0], 1)} / {n(var['o'][1], 1)} cm e modulo "
        f"{n(cp.MODULO)} cm. Il colore di ogni lastra indica come viene tagliata: "
        f"bianco intera, giallo taglio oltre {cp.MEZZA:.0f} cm, arancio fra "
        f"{cp.SLIVER:.0f} e {cp.MEZZA:.0f}, rosso listello sotto {cp.SLIVER:.0f} cm.",
        S_TXT))
    e.append(pianta(i, 180 * mm, 205 * mm))

    e.append(PageBreak())
    e.append(Paragraph("8. Anteprima tridimensionale", S_SEZ))
    e.append(Paragraph(
        f"Assonometria sezionata a {H_SEZIONE:.0f} cm dal pavimento, ricavata dagli "
        f"stessi volumi del modello navigabile casa_3d.html: murature, arredo e "
        f"apparecchi sanitari sono quelli del progetto corrente.", S_TXT))
    e.append(assonometria(180 * mm, 200 * mm))
    return e


def intestazione(canv, doc):
    canv.saveState()
    canv.setStrokeColor(BLU)
    canv.setLineWidth(0.8)
    canv.line(15 * mm, A4[1] - 12 * mm, A4[0] - 15 * mm, A4[1] - 12 * mm)
    canv.setFont("Helvetica", 7.5)
    canv.setFillColor(colors.HexColor("#666666"))
    canv.drawString(15 * mm, A4[1] - 10 * mm, doc.titolo)
    canv.drawRightString(A4[0] - 15 * mm, 10 * mm, f"pagina {doc.page}")
    canv.drawString(15 * mm, 10 * mm,
                    "generato da report.py - i valori derivano dalla pianta, non sono trascritti")
    canv.restoreState()


def scrivi(i):
    f = cp.FORMATI[i]
    nome = re.sub(r"[^a-z0-9]+", "_", f["nome"].lower()).strip("_")
    out = fr"c:\WORK\GH\computo_{nome}.pdf"
    doc = SimpleDocTemplate(out, pagesize=A4, title=f"Computo di posa - {f['nome']}",
                            author="report.py", leftMargin=15 * mm, rightMargin=15 * mm,
                            topMargin=18 * mm, bottomMargin=16 * mm)
    doc.titolo = f"Computo di posa - {f['nome']}"
    doc.build(costruisci(i), onFirstPage=intestazione, onLaterPages=intestazione)
    return out


if __name__ == "__main__":
    quali = [int(a.split("=", 1)[1]) for a in sys.argv[1:] if a.startswith("--posa=")]
    for k in (quali or range(len(cp.FORMATI))):
        try:
            print("scritto:", scrivi(k))
        except PermissionError as err:
            print("NON scritto (file aperto):", err.filename)
