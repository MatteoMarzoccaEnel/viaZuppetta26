"""Pianta dell'intero appartamento e studio della posa del gres 90x90.

Misure in CENTIMETRI, rilevate da "TAV 02 - Stato di progetto"
(calibrazione 27,76 pt/m verificata sui vani porta 0,80 e sull'area del bagno).

Il dato di partenza e' definito in un sistema "di rilievo"; una rotazione di 180
lo porta nell'orientamento di disegno richiesto. La classificazione delle lastre
(intere / tagliate) e' calcolata cella per cella: gli stessi dati alimentano sia
il disegno sia le tabelle, quindi colori e numeri non possono divergere.

Esecuzione:  python casa_pianta.py
"""

import math
import re
import sys

_sys_argv = sys.argv[1:]

# =====================================================================
# PARAMETRI
# =====================================================================

SCALA = 60
OUT = r"c:\WORK\GH\casa"

LARG_TRAVE, H_TRAVE = 30.0, 240.0    # sezione e intradosso delle travi in c.a.

# ---- configurazioni di posa a confronto: si scorrono con B nel modello 3D ----
# Il formato entra nel modulo della griglia, quindi ogni configurazione ha una
# sua origine ottimale e un suo conteggio di lastre: non sono varianti grafiche.
# Il rivestimento del bagno chiude sempre all'intradosso della trave: cambia
# solo il numero di corsi necessari a raggiungerla.
FORMATI = [
    dict(piastrella=90.0, fuga=0.15,
         tex_pav="pavimento.png", tex_riv="piastrelle.png"),
    dict(piastrella=80.0, fuga=0.15,
         tex_pav="pavimento80x80.jpg", tex_riv="piastrella80x80.jpg"),
    dict(piastrella=60.0, fuga=0.15,
         tex_pav="pavimento80x80.jpg", tex_riv="piastrella80x80.jpg"),
]
for _f in FORMATI:
    # ultimo corso tagliato: si posa il minimo indispensabile per arrivare in quota
    _f["riv_corsi"] = math.ceil((H_TRAVE + _f["fuga"]) / (_f["piastrella"] + _f["fuga"]))
    _f["riv_h"] = H_TRAVE
    _p = int(_f["piastrella"])
    _f["nome"] = f"{_p}x{_p}, {_f['riv_corsi']} corsi a filo trave"
# valori della configurazione attiva, rimpiazzati da usa_formato()
FORMATO = FORMATI[0]
PIASTRELLA = FORMATO["piastrella"]
FUGA = FORMATO["fuga"]
MODULO = PIASTRELLA + FUGA
LASTRA = (PIASTRELLA / 100) ** 2

FINITURA = 1.0   # gres a parete nel bagno, battiscopa negli altri locali
SLIVER = 25.0    # sotto: taglio "brutto"
MEZZA = 45.0     # sopra: taglio di buona qualita'

RIV_CORSI = FORMATO["riv_corsi"]


def h_riv(f):
    """Altezza del rivestimento: corsi interi, oppure la quota imposta da riv_h."""
    if f.get("riv_h"):
        return f["riv_h"]
    return f["riv_corsi"] * f["piastrella"] + (f["riv_corsi"] - 1) * f["fuga"]


H_RIV = h_riv(FORMATO)

# ---- quote verticali: valgono sia per la pianta sia per il modello 3D ----
H_INT = 297.0        # altezza interna (da tavola: H = 2,97 m)
H_BATT = 8.0         # battiscopa
DAVANZALE = 89.0     # davanzale delle finestre (la luce sale fino a 224)
ALT_VANO = {"porta": 210, "battente": 210, "passaggio": 210,
            "finestra": 135, "portafinestra": 225}
SP_EST = 30.0        # spessore delle murature perimetrali

# finitura delle porte: laminato dello stesso bianco caldo delle pareti, cosi'
# le scomparse spariscono nel muro e il corridoio non viene spezzato
PORTE_COLORE = "#f1ece1"
PORTE_FINITURA = "laminato RAL 9010"

# ---- locali (poligoni rettilinei nel sistema di rilievo) ----
LOCALI = {
    "RIPOSTIGLIO": dict(peso=0.5, poly=[(0, 30), (199, 30), (199, 152), (0, 152)]),
    # il muro bagno/camera e' l'unico da 12 cm (scarico a incasso dietro al bidet),
    # tutti gli altri sono da 10: il bagno resta 158, i 3 cm vanno alla camera
    "LETTO MATRIMONIALE": dict(peso=1.5, poly=[(0, 162), (331, 162), (331, 565), (0, 565)]),
    "BAGNO": dict(peso=1.0, poly=[
        (343, 162), (343, 565), (370, 565), (370, 539), (423, 539),
        (423, 562), (501, 562), (501, 237), (576, 237), (576, 162)]),
    # il filo sud rientra in corrispondenza dei due pilastri squadrati sotto le
    # travi T3 e T2 (da tavola: y 37 contro y 17), e sul tratto del ripostiglio
    "DISIMPEGNO": dict(peso=1.0, poly=[
        (209, 30), (370, 30), (370, 37), (400, 37), (400, 17),
        (773, 17), (773, 37), (797, 37), (797, 152), (209, 152)]),
    "LETTO SINGOLO": dict(peso=1.5, poly=[
        (586, 162), (797, 162), (797, 563), (511, 563), (511, 247), (586, 247)]),
    "ZONA GIORNO": dict(peso=4.0, lab=(1300, 350), poly=[
        (807, 17), (1197, 17), (1197, 37), (1242, 37), (1242, 122), (1252, 122),
        (1252, -59), (1463, -59), (1463, 563), (1198, 563), (1198, 697), (807, 697)]),
}

# ---- aperture: (tipo, x0, y0, x1, y1, etichetta) ----
APERTURE = [
    ("battente", 1335, -59, 1421, -59, "INGRESSO 86"),
    ("porta", 204, 58, 204, 138, "80"),
    ("porta", 219, 157, 313, 157, "80"),
    ("porta", 393, 157, 478, 157, "80"),
    ("porta", 595, 157, 690, 157, "80"),
    # vano da tavola: comincia 10 cm dopo la faccia del pilastro P8 (y 37)
    ("passaggio", 802, 47, 802, 142, "80"),
    ("finestra", 423, 562, 474, 562, "51x135"),
    ("portafinestra", 208, 565, 318, 565, "BALCONE 110 - 2 ante"),
    ("portafinestra", 616, 563, 726, 563, "BALCONE 110 - 2 ante"),
    ("portafinestra", 1251, 564, 1361, 564, "BALCONE 110 - 2 ante"),
    ("finestra", 1053, 697, 1163, 697, "FINESTRA 110x135 - 2 ante"),
    # vano strutturale 67,8 da tavola (nominale 70): comincia dove finisce il blocco P3
    ("portafinestra", 802, 624, 802, 691, "BALCONE 70 - 1 anta"),
]

# ---- arredo: (locale, etichetta, x, y, ingombro X, ingombro Y, tipo) ----
ARREDO = [
    ("RIPOSTIGLIO", "SCAFFALI 130x40", 0, 30, 40, 130, "scaffale"),

    ("LETTO MATRIMONIALE", "LETTO 160x200", 0, 250, 200, 160, "letto"),
    ("LETTO MATRIMONIALE", "", 0, 205, 45, 40, "box"),
    ("LETTO MATRIMONIALE", "", 0, 415, 45, 40, "box"),
    ("LETTO MATRIMONIALE", "ARMADIO 200x60", 5, 505, 200, 60, "box"),
    ("LETTO MATRIMONIALE", "MOBILE BASSO 200x35", 293, 230, 35, 200, "box"),

    ("BAGNO", "LAVABO 120x38", 344, 199, 38, 120, "box"),
    # 22 cm liberi fra lavabo, wc e bidet: interasse 59, sopra il minimo d'uso
    ("BAGNO", "WC", 344, 341, 48, 37, "wc"),
    ("BAGNO", "BIDET", 344, 400, 48, 37, "wc"),
    ("BAGNO", "DOCCIA 156x80", 344, 457, 156, 80, "doccia"),
    ("BAGNO", "ATTACCAPANNI 60x5", 493, 360, 5, 60, "appendi"),
    ("BAGNO", "LAVATRICE", 506, 170, 60, 60, "box"),
    ("BAGNO", "SPECCHIO 100x2", 344, 209, 2, 100, "specchio"),
    # colonna lavatrice + asciugatrice: 85 + 5 di kit + 85
    ("BAGNO", "KIT SOVRAPPOSIZIONE 60x60", 506, 170, 60, 60, "kit"),
    ("BAGNO", "ASCIUGATRICE 60x60", 506, 170, 60, 60, "elettro2"),
    # dietro il piatto doccia: riempiono i due rientri fino al filo della colonna
    ("BAGNO", "MURETTO 27x26", 343, 539, 27, 26, "muretto"),
    ("BAGNO", "MURETTO 78x23", 423, 539, 78, 23, "muretto"),

    # composizione a parete: libreria + scrivania + armadio, con due mensole sopra
    ("LETTO SINGOLO", "LETTO CONTENITORE 204x94", 511, 247, 94.2, 204.2, "letto"),
    ("LETTO SINGOLO", "LIBRERIA 40x33", 764, 270, 33, 40, "scaffale"),
    ("LETTO SINGOLO", "SCRIVANIA 100x50", 747, 310, 50, 100, "box"),
    ("LETTO SINGOLO", "ARMADIO 80x52", 745, 410, 52, 80, "box"),
    ("LETTO SINGOLO", "MENSOLA B 100x18", 779, 310, 18, 100, "mensola"),
    ("LETTO SINGOLO", "MENSOLA A 80x18", 779, 320, 18, 80, "mensola2"),

    # la parete sud del disimpegno rientra di 13 cm fra il risalto a x 370 e il
    # muro a x 797: la cassettiera riempie la nicchia e sporge di 5 cm
    ("DISIMPEGNO", "CASSETTIERA 427x18", 370, 17, 427, 18, "cassetti"),

    # fronte cucina 360 lungo il muro giorno/notte: dal basso verso l'alto
    ("ZONA GIORNO", "", 807, 170, 60, 360, "cucina"),
    ("ZONA GIORNO", "FRIGO", 807, 170, 60, 60, "elettro"),
    ("ZONA GIORNO", "LAVELLO 2V 120", 807, 230, 60, 120, "lavello"),
    ("ZONA GIORNO", "LAVAST.", 807, 350, 60, 60, "elettro"),
    ("ZONA GIORNO", "COTTURA", 807, 410, 60, 60, "fuochi"),
    ("ZONA GIORNO", "FORNO", 807, 470, 60, 60, "elettro"),
    ("ZONA GIORNO", "MOBILE TV 180x45", 1017, 17, 180, 45, "box"),
]

# setti di nuova costruzione: (x, y, larghezza, profondita', etichetta)
SETTI = [(1242, 37, 10, 85, "SETTO 10x85")]

# ---- muri di PROGETTO (verdi in tavola): sono gli unici spostabili ----
# (asse, (quota faccia 1, quota faccia 2), etichetta) nel sistema di rilievo.
# Tutto cio' che non compare qui e' muratura esistente (bianca) o perimetro:
# vincoli.py ne blocca le coordinate con una firma.
MURI_NUOVI = [
    ("y", (152, 162), "muro disimpegno / zona notte"),
    ("x", (331, 343), "muro 12 bagno / camera matrimoniale"),
    ("x", (199, 209), "muro ripostiglio"),
    ("x", (576, 586), "nicchia bagno - lato lungo"),
    ("y", (237, 247), "nicchia bagno - fondo"),
]

# box doccia: vetro fisso da x0, anta mobile della stessa luce su binario sfalsato
BOX = dict(x0=344, luce=60, h=200, y=457, sfalso=1.0)

# quote di verifica: (x0, y0, x1, y1, etichetta) in coordinate di rilievo
QUOTE = [
    (200, 330, 293, 330, "93 piede letto-mobile"),
    (100, 410, 100, 505, "95 letto-armadio"),
    (601, 416, 737, 416, "136 letto-armadio"),
    (500, 17, 500, 152, "135 disimpegno"),
    (344, 457, 344, 537, "80 doccia"),
    (399, 199, 399, 319, "120 lavabo"),
    (60, 30, 60, 152, "122 ripostiglio"),
    (1225, 37, 1225, 122, "85 setto schermo"),
]

# =====================================================================
# ORIENTAMENTO DELLA TAVOLA
# =====================================================================
# I poligoni sono stati ricavati dal PDF con X = (609,18 - x_pdf): poiche' anche
# l'asse Y del PDF e' rivolto verso il basso, quella mappatura inverte un solo
# asse ed e' quindi SPECULARE. RADDRIZZA=True ribalta alto/basso e ripristina il
# verso corretto: ingresso in basso a destra, balconi/strada in alto.
RADDRIZZA = True
ROTAZIONE = 0      # 0 oppure 180 (rotazione vera, da applicare dopo il raddrizzamento)

_xs = [p[0] for d in LOCALI.values() for p in d["poly"]]
_ys = [p[1] for d in LOCALI.values() for p in d["poly"]]
RX, RY = min(_xs) + max(_xs), min(_ys) + max(_ys)


def R(x, y):
    if RADDRIZZA:
        y = RY - y
    if ROTAZIONE == 180:
        x, y = RX - x, RY - y
    return (x, y)


def Rrect(x, y, w, h):
    a, b = R(x, y)
    c, d = R(x + w, y + h)
    return (min(a, c), min(b, d), w, h)


# ---- ricalco della tavola originale (muri reali, travi, spallette, balconi) ----
PDF = r"c:\WORK\GH\TAV 02_STATO DI PROGETTO.pdf"
PT_M = 27.76            # pt per metro
PDF_OX, PDF_OY = 609.18, 394.20
PDF_CLIP = (190, 375, 630, 625)


def P(px, py):
    return R((PDF_OX - px) / PT_M * 100, (py - PDF_OY) / PT_M * 100)


def ricalco():
    try:
        import fitz
    except ImportError:
        return []
    page = fitz.open(PDF)[0]
    x0, y0, x1, y1 = PDF_CLIP
    out = []
    for p in page.get_drawings():
        lw = p.get("width") or 0
        if lw < 0.3:
            continue
        col = p.get("color") or (0.25, 0.25, 0.25)
        for it in p["items"]:
            if it[0] == "l":
                pts, curva = [(it[1].x, it[1].y), (it[2].x, it[2].y)], False
            elif it[0] == "re":
                r = it[1]
                pts = [(r.x0, r.y0), (r.x1, r.y0), (r.x1, r.y1), (r.x0, r.y1), (r.x0, r.y0)]
                curva = False
            else:
                # le curve della tavola originale sono gli archi di apertura
                # delle porte a battente: qui le porte sono a scomparsa
                continue
            if not all(x0 <= q[0] <= x1 and y0 <= q[1] <= y1 for q in pts):
                continue
            out.append((col, lw, curva, [P(*q) for q in pts]))
    return out


BASE = ricalco()

# poligoni nel sistema di rilievo, prima di qualunque trasformazione: sono il
# dato originario, riferimento per le firme dei vincoli e per gli script
# parametrici (muri_nuovi.py, muro_disimpegno.py)
LOCALI_RILIEVO = {n: list(d["poly"]) for n, d in LOCALI.items()}


if RADDRIZZA or ROTAZIONE:
    for d in LOCALI.values():
        d["poly"] = [R(*p) for p in d["poly"]][::-1]
        if "lab" in d:
            d["lab"] = R(*d["lab"])
    APERTURE = [(t, *R(x0, y0), *R(x1, y1), lb) for t, x0, y0, x1, y1, lb in APERTURE]
    ARREDO = [(lo, lb, *Rrect(x, y, w, h), tp) for lo, lb, x, y, w, h, tp in ARREDO]
    SETTI = [(*Rrect(x, y, w, h), lb) for x, y, w, h, lb in SETTI]
    QUOTE = [(*R(x0, y0), *R(x1, y1), lb) for x0, y0, x1, y1, lb in QUOTE]
    BOX["y"] = R(0, BOX["y"])[1]

# ---- identificativo di ogni arredo: sigla del locale + progressivo ----
# Serve per riferirsi a un mobile senza descriverlo ("sposta LS-03"). I nuovi
# arredi vanno aggiunti in fondo al blocco del loro locale, cosi' gli altri
# identificativi non si spostano.
SIGLE = {"RIPOSTIGLIO": "RP", "LETTO MATRIMONIALE": "LM", "BAGNO": "BA",
         "DISIMPEGNO": "DI", "LETTO SINGOLO": "LS", "ZONA GIORNO": "ZG"}
ID_ARREDO = []
_prog = {}
for _lo, *_r in ARREDO:
    _prog[_lo] = _prog.get(_lo, 0) + 1
    ID_ARREDO.append(f"{SIGLE[_lo]}-{_prog[_lo]:02d}")

# ---- balconi, in coordinate di disegno (gia' raddrizzate) ----
# (x0, y0, x1, y1, ringhiera sul lato esterno / sinistro / destro)
H_RING, H_SEPARE = 110.0, 180.0
# il parapetto del balcone lungo sta a 696,6 dal filo interno della facciata:
# la soletta arriva quindi a -59, non a -37
BALCONI = [(0, -59, 808, 73, 1, 1, 0), (1197, -36, 1463, 74, 1, 0, 0)]
BALCONI_VICINO = []          # il balcone confinante non viene rappresentato
SEPARE = [(1463, -36, 1463, 74, H_SEPARE)]

# ---- struttura in c.a. esistente, ricavata dai risalti della tavola ----
# pilastri squadrati: (x0, y0, x1, y1, etichetta)
PILASTRI = [
    (370, 73, 423, 99, "P1"),
    (506, 76, 560, 94, "P2"),
    (778, 14, 807, 45, "P3"),
    (778, -88, 807, -59, "P4"),
    (1198, -88, 1228, -59, "P5"),
    (1228, 44, 1252, 74, "P6"),
    (370, 601, 400, 621, "P7"),      # sotto T3, sporge 20 nel disimpegno
    (773, 601, 804, 621, "P8"),      # sotto T2, sporge 20 nel disimpegno
]
# le tre travi sono TRASVERSALI (corrono da balcone a ingresso, non lungo la casa)
# e appoggiano sui pilastri: T3 su P1, T2 su P3/P4, T1 su P6/P5
TRAVI = [
    (370, 73, 400, 621, "T3 bagno / disimpegno"),
    (773, 14, 804, 621, "T2 giorno / notte (porte 6 e 12)"),
    (1228, 44, 1252, 697, "T1 ingresso / zona giorno"),
]

# controsoffitti in cartongesso che chiudono i vuoti a fianco delle travi:
# (x0, y0, x1, y1, quota, passo dei faretti, etichetta)
CONTROSOFFITTI = [
    (343, 73, 370, 483, H_TRAVE, 85, "bagno, fascia lato lavabo"),
]

# =====================================================================
# GEOMETRIA
# =====================================================================


def area(poly):
    s = sum(poly[i][0] * poly[(i + 1) % len(poly)][1] - poly[(i + 1) % len(poly)][0] * poly[i][1]
            for i in range(len(poly)))
    return abs(s) / 2


def orientamento(poly):
    s = sum(poly[i][0] * poly[(i + 1) % len(poly)][1] - poly[(i + 1) % len(poly)][0] * poly[i][1]
            for i in range(len(poly)))
    return 1 if s > 0 else -1


def offset_poly(poly, d):
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


def intervalli(poly, asse, c):
    vals = []
    for i in range(len(poly)):
        p, q = poly[i], poly[(i + 1) % len(poly)]
        if asse == "x" and p[1] == q[1] and min(p[0], q[0]) < c < max(p[0], q[0]):
            vals.append(p[1])
        if asse == "y" and p[0] == q[0] and min(p[1], q[1]) < c < max(p[1], q[1]):
            vals.append(p[0])
    vals.sort()
    return list(zip(vals[0::2], vals[1::2]))


def rettangoli(poly):
    """Scompone un poligono rettilineo in rettangoli disgiunti."""
    xs = sorted({p[0] for p in poly})
    out = []
    for a, b in zip(xs, xs[1:]):
        for y0, y1 in intervalli(poly, "x", (a + b) / 2):
            out.append((a, y0, b, y1))
    return out


for nome, d in LOCALI.items():
    if orientamento(d["poly"]) < 0:
        d["poly"] = d["poly"][::-1]
    d["fin"] = offset_poly(d["poly"], FINITURA)
    d["rect"] = rettangoli(d["fin"])
    d["area"] = area(d["fin"]) / 10000
    d["bb"] = (min(p[0] for p in d["fin"]), min(p[1] for p in d["fin"]),
               max(p[0] for p in d["fin"]), max(p[1] for p in d["fin"]))

AREA_TOT = sum(d["area"] for d in LOCALI.values())


def spessore(nome, c, orizz, a, b):
    """Spessore del muro nel tratto a-b: lo stesso lato puo' confinare con un altro
    locale in un tratto ed essere perimetrale in un altro (es. affaccio sul balcone)."""
    m = (a + b) / 2
    # un setto a penisola ha entrambe le facce sul perimetro dello stesso locale:
    # senza questo verrebbe fuori spesso come una muratura perimetrale
    for sx, sy, sw, sh, lb in SETTI:
        if orizz and (abs(c - sy) < 0.6 or abs(c - (sy + sh)) < 0.6) \
                and sx - 0.5 <= m <= sx + sw + 0.5:
            return min(sw, sh)
        if not orizz and (abs(c - sx) < 0.6 or abs(c - (sx + sw)) < 0.6) \
                and sy - 0.5 <= m <= sy + sh + 0.5:
            return min(sw, sh)
    best = None
    for n2, d2 in LOCALI.items():
        if n2 == nome:
            continue
        p2 = d2["poly"]
        for i in range(len(p2)):
            r, s = p2[i], p2[(i + 1) % len(p2)]
            if (abs(r[1] - s[1]) < 0.1) != orizz:
                continue
            c2 = r[1] if orizz else r[0]
            a2, b2 = (min(r[0], s[0]), max(r[0], s[0])) if orizz \
                else (min(r[1], s[1]), max(r[1], s[1]))
            if not (a2 - 0.5 <= m <= b2 + 0.5):
                continue
            dd = abs(c2 - c)
            if 1 < dd < 40 and (best is None or dd < best):
                best = dd
    return best if best else SP_EST


def bordi(nome, c, orizz):
    """Coordinate dove cambia il locale confinante: li' lo spessore del muro cambia."""
    bs = set()
    # anche l'inizio e la fine di un setto: oltre il setto il muro torna pieno
    for sx, sy, sw, sh, lb in SETTI:
        if orizz and (abs(c - sy) < 0.6 or abs(c - (sy + sh)) < 0.6):
            bs.update((sx, sx + sw))
        if not orizz and (abs(c - sx) < 0.6 or abs(c - (sx + sw)) < 0.6):
            bs.update((sy, sy + sh))
    for n2, d2 in LOCALI.items():
        if n2 == nome:
            continue
        p2 = d2["poly"]
        for i in range(len(p2)):
            r, s = p2[i], p2[(i + 1) % len(p2)]
            if (abs(r[1] - s[1]) < 0.1) != orizz:
                continue
            c2 = r[1] if orizz else r[0]
            if not (1 < abs(c2 - c) < 40):
                continue
            bs.update((r[0], s[0]) if orizz else (r[1], s[1]))
    return sorted(bs)

# =====================================================================
# TASCHE DELLE PORTE A SCOMPARSA
# =====================================================================
# Una tasca deve ospitare l'anta piu' la battuta e le guide, e non puo'
# sovrapporsi a quella di un'altra porta sullo stesso filo murario.

ANTA = 80.0        # luce netta dell'anta
TOLL = 5.0         # battuta, stipite e guide
PIEGHEVOLI = {2}   # porte a libro: non hanno tasca
TASCA = ANTA + TOLL


def _estensione(c, o):
    amin, amax = 1e9, -1e9
    for d in LOCALI.values():
        p = d["poly"]
        for i in range(len(p)):
            r, s = p[i], p[(i + 1) % len(p)]
            if (abs(r[1] - s[1]) < 0.1) != o or abs((r[1] if o else r[0]) - c) > 11:
                continue
            a2, b2 = (min(r[0], s[0]), max(r[0], s[0])) if o \
                else (min(r[1], s[1]), max(r[1], s[1]))
            amin, amax = min(amin, a2), max(amax, b2)
    return amin, amax


def _calcola_tasche():
    linee = {}
    for k, (tipo, x0, y0, x1, y1, lb) in enumerate(APERTURE, 1):
        if tipo not in ("porta", "passaggio") or k in PIEGHEVOLI:
            continue
        o = abs(y1 - y0) < abs(x1 - x0)
        c = y0 if o else x0
        va, vb = (min(x0, x1), max(x0, x1)) if o else (min(y0, y1), max(y0, y1))
        linee.setdefault((o, round(c / 15)), []).append([va, vb, k, c, o])

    versi, tasche = {}, {}
    for ap in linee.values():
        ap.sort()
        amin, amax = _estensione(ap[0][3], ap[0][4])
        occupato = []

        def libero(x0, x1):
            return all(x1 <= r0 + 0.1 or x0 >= r1 - 0.1 for r0, r1 in occupato)

        margine = []
        for i, (va, vb, k, _, _) in enumerate(ap):
            sx = va - (ap[i - 1][1] if i else amin)
            dx = (ap[i + 1][0] if i < len(ap) - 1 else amax) - vb
            margine.append((min(sx, dx), i, sx, dx))
        for _, i, sx, dx in sorted(margine):      # prima le porte piu' vincolate
            va, vb, k = ap[i][0], ap[i][1], ap[i][2]
            opz = []
            if sx >= TASCA and libero(va - TASCA, va):
                opz.append((sx, -1, (va - TASCA, va)))
            if dx >= TASCA and libero(vb, vb + TASCA):
                opz.append((dx, 1, (vb, vb + TASCA)))
            if not opz:                            # nessun lato sufficiente
                opz.append((sx, -1, (va - TASCA, va)) if sx >= dx
                           else (dx, 1, (vb, vb + TASCA)))
            _, v, t = max(opz)
            versi[k], tasche[k] = v, t
            occupato.append(t)
    return versi, tasche


VERSI, TASCHE = _calcola_tasche()

# =====================================================================
# BATTISCOPA
# =====================================================================
# Il battiscopa e' un percorso continuo lungo il perimetro del locale, interrotto
# solo dai vani che arrivano a terra: i tratti calcolati qui alimentano sia il 3D
# sia il computo, e vincoli.py ne verifica la contiguita'.

VANI_TERRA = {"porta", "battente", "passaggio", "portafinestra"}
SENZA_BATTISCOPA = {"BAGNO"}      # rivestito a parete


def seg_meno(a, b, vani):
    """Il tratto a-b meno gli intervalli occupati."""
    fuori = [(a, b)]
    for va, vb in vani:
        nuovo = []
        for p, q in fuori:
            if vb <= p or va >= q:
                nuovo.append((p, q))
                continue
            if p < va:
                nuovo.append((p, va))
            if vb < q:
                nuovo.append((vb, q))
        fuori = nuovo
    return [(p, q) for p, q in fuori if q - p > 0.5]


def vani_sul_filo(orizz, c, a, b):
    """Vani che arrivano a terra sul tratto a-b della retta c."""
    out = []
    for tipo, x0, y0, x1, y1, lb in APERTURE:
        if tipo not in VANI_TERRA:
            continue
        ao = abs(y1 - y0) < abs(x1 - x0)
        if ao != orizz or abs((y0 if ao else x0) - c) > 11:
            continue
        va, vb = (min(x0, x1), max(x0, x1)) if ao else (min(y0, y1), max(y0, y1))
        va, vb = max(va, a), min(vb, b)
        if vb - va > 0.5:
            out.append((va, vb))
    return sorted(out)


def lati(poly):
    """I lati del poligono: (orizzontale, quota, da, a, verso l'interno)."""
    out = []
    for i in range(len(poly)):
        p, q = poly[i], poly[(i + 1) % len(poly)]
        orizz = abs(p[1] - q[1]) < 0.1
        c = p[1] if orizz else p[0]
        a, b = (min(p[0], q[0]), max(p[0], q[0])) if orizz \
            else (min(p[1], q[1]), max(p[1], q[1]))
        dentro = (1 if q[0] > p[0] else -1) if orizz else (-1 if q[1] > p[1] else 1)
        out.append((orizz, c, a, b, dentro))
    return out


def battiscopa_locali():
    """Tratti di battiscopa per locale: (da, a, quota, orizzontale, verso, n. lato)."""
    out = {}
    for nome, d in LOCALI.items():
        if nome in SENZA_BATTISCOPA:
            continue
        tratti = []
        for i, (orizz, c, a, b, dentro) in enumerate(lati(d["poly"])):
            for sa, sb in seg_meno(a, b, vani_sul_filo(orizz, c, a, b)):
                tratti.append((sa, sb, c, orizz, dentro, i))
        out[nome] = tratti
    return out


BATTISCOPA = battiscopa_locali()

# =====================================================================
# ARREDO: ALTEZZE E DESCRIZIONE
# =====================================================================
# Le altezze stanno qui con il resto della geometria: la pianta le usa per le
# etichette, il 3D per costruire i volumi.

# tipo -> (altezza, quota di attacco: 0 = appoggiato a terra)
H_TIPO = {
    "letto": (45, 0), "divano": (80, 0), "cucina": (90, 0), "elettro": (85, 0),
    "lavello": (90, 0), "fuochi": (90, 0), "doccia": (4, 0),
    "wc": (25, 15),                       # sospeso: seduta a 40
    "appendi": (8, 165), "box": (75, 0), "cassetti": (150, 0),
    "scaffale": (220, 0), "mensola": (20, 112), "mensola2": (20, 152),
    "specchio": (80, 110), "kit": (5, 85), "elettro2": (85, 90),
    "muretto": (120, 0),
}
# altezze per etichetta: la chiave e' un prefisso, va resa specifica quando due
# arredi omonimi hanno altezze diverse (ARMADIO 200x60 e ARMADIO 80x52)
H_LABEL = {
    "ARMADIO 200x60": 240, "ARMADIO 80x52": 180, "SCAFFALI": 220,
    "LIBRERIA": 180, "MOBILE TV": 45, "TAVOLINO": 42, "MOBILE BASSO": 45,
    "LAVATRICE": 85, "LAVABO": 85, "SEDIA": 45, "SGABELLO": 45,
    "MOBILETTO": 150, "LETTO CONTENITORE": 50, "TAVOLO": 75, "POLTRONA": 75,
    "CONSOLLE": 80, "SCRIVANIA 100x50": 70,
    "MURETTO 27": 120, "MURETTO 78": 40,
}


def altezza(label, tipo):
    alt, base = H_TIPO.get(tipo, H_TIPO["box"])
    for k, v in H_LABEL.items():
        if label.startswith(k):
            alt = v
    return alt, base


def _contatti(lo, x, y, w, h):
    """Quanto il mobile appoggia contro i fili verticali e contro quelli orizzontali."""
    cv = ch = 0.0
    for orizz, c, a, b, dentro in lati(LOCALI[lo]["poly"]):
        if orizz:
            if min(abs(c - y), abs(c - (y + h))) < 2:
                ch = max(ch, min(b, x + w) - max(a, x))
        else:
            if min(abs(c - x), abs(c - (x + w))) < 2:
                cv = max(cv, min(b, y + h) - max(a, y))
    return cv, ch


def misure(i):
    """Larghezza, profondita' dal muro e altezza dell'i-esimo arredo.

    La profondita' e' l'ingombro perpendicolare al muro contro cui il mobile
    appoggia: per un wc accostato a una parete verticale sono i 55 cm di
    sporgenza, non i 37 di fronte.
    """
    lo, lb, x, y, w, h, tp = ARREDO[i]
    cv, ch = _contatti(lo, x, y, w, h)
    if cv > ch:
        larg, prof = h, w
    elif ch > cv:
        larg, prof = w, h
    else:
        larg, prof = max(w, h), min(w, h)
    return larg, prof, altezza(lb, tp)[0]


def descrizione(i):
    """Etichetta completa: identificativo, nome e le tre misure."""
    lo, lb, x, y, w, h, tp = ARREDO[i]
    nome = re.sub(r"\s*\d+[xX]\d+\s*$", "", lb).strip() or tp.upper()
    larg, prof, alt = misure(i)
    base = altezza(lb, tp)[1]
    s = f"{ID_ARREDO[i]} {nome} L{larg:.0f} P{prof:.0f} H{alt:.0f}"
    return s + (f" sosp.{base:.0f}" if base else "")


# I vincoli tecnici (perimetro, struttura, muri esistenti, tasche, incassi) sono
# verificati a ogni import: se un dato immutabile cambia, qui si ferma tutto.
import sys as _sys                                            # noqa: E402

from vincoli import verifica as _verifica                     # noqa: E402

_verifica(_sys.modules[__name__])

# =====================================================================
# POSA: classificazione lastra per lastra
# =====================================================================


def celle(d, ox, oy):
    """Ogni cella della griglia che tocca il locale, con le sue parti effettive."""
    x0, y0, x1, y1 = d["bb"]
    out = []
    for i in range(math.floor((x0 - ox) / MODULO), math.ceil((x1 - ox) / MODULO) + 1):
        for j in range(math.floor((y0 - oy) / MODULO), math.ceil((y1 - oy) / MODULO) + 1):
            a0, a1 = ox + i * MODULO, ox + (i + 1) * MODULO
            b0, b1 = oy + j * MODULO, oy + (j + 1) * MODULO
            parti = []
            for rx0, ry0, rx1, ry1 in d["rect"]:
                cx0, cx1 = max(a0, rx0), min(a1, rx1)
                cy0, cy1 = max(b0, ry0), min(b1, ry1)
                if cx1 - cx0 > 0.05 and cy1 - cy0 > 0.05:
                    parti.append((cx0, cy0, cx1, cy1))
            if not parti:
                continue
            sup = sum((p[2] - p[0]) * (p[3] - p[1]) for p in parti)
            dx = max(p[2] for p in parti) - min(p[0] for p in parti)
            dy = max(p[3] for p in parti) - min(p[1] for p in parti)
            out.append(dict(parti=parti, sup=sup, dx=dx, dy=dy,
                            intera=sup > MODULO * MODULO - 1.0,
                            lato=min(dx, dy)))
    return out


def analizza(ox, oy):
    tot = dict(intere=0, tagli=0, sliver=0, medi=0, buoni=0, lastre=0, min_lato=1e9)
    per_loc = {}
    for nome, d in LOCALI.items():
        cs = celle(d, ox, oy)
        ints = [c for c in cs if c["intera"]]
        cut = [c for c in cs if not c["intera"]]
        sliver = [c for c in cut if c["lato"] < SLIVER]
        medi = [c for c in cut if SLIVER <= c["lato"] < MEZZA]
        buoni = [c for c in cut if c["lato"] >= MEZZA]
        # una lastra intera per ogni pezzo con entrambi i lati > meta' modulo,
        # due pezzi piccoli si ricavano dalla stessa lastra
        grandi = sum(1 for c in cut if c["dx"] > MODULO / 2 and c["dy"] > MODULO / 2)
        piccoli = len(cut) - grandi
        lastre = len(ints) + grandi + math.ceil(piccoli / 2)
        mlato = min([c["lato"] for c in cut], default=PIASTRELLA)
        per_loc[nome] = dict(celle=cs, intere=len(ints), tagli=len(cut),
                             sliver=len(sliver), medi=len(medi), buoni=len(buoni),
                             lastre=lastre, min_lato=mlato,
                             q_intere=len(ints) * LASTRA / d["area"])
        tot["intere"] += len(ints)
        tot["tagli"] += len(cut)
        tot["sliver"] += len(sliver)
        tot["medi"] += len(medi)
        tot["buoni"] += len(buoni)
        tot["lastre"] += lastre
        tot["min_lato"] = min(tot["min_lato"], mlato)
    tot["q_intere"] = tot["intere"] * LASTRA / AREA_TOT
    tot["sfrido"] = (tot["lastre"] * LASTRA - AREA_TOT) / (tot["lastre"] * LASTRA)
    return tot, per_loc


def obiettivo(ox, oy, modo="materiale"):
    """Costo reale, calcolato sulle stesse celle che finiscono nel disegno."""
    tot, per = analizza(ox, oy)
    inutili = {n: sum(1 for c in l["celle"] if not c["intera"] and c["lato"] < 10)
               for n, l in per.items()}
    if modo == "materiale":
        # meno lastre acquistate, poi meno pezzi da tagliare: i listelli restano
        # penalizzati perche' in opera sono lenti e fragili
        return (tot["lastre"] * 10 + tot["tagli"] + tot["sliver"] * 3
                + sum(inutili.values()) * 10)
    s = 0.0
    for nome, d in LOCALI.items():
        l = per[nome]
        s += d["peso"] * (inutili[nome] * 30 + l["sliver"] * 8 + l["medi"] * 2
                          + (1 - l["q_intere"]) * 20)
    s += tot["lastre"] * 0.5
    if modo == "zg":
        zg = per["ZONA GIORNO"]
        s = -zg["intere"] * 100 + inutili["ZONA GIORNO"] * 500 + zg["sliver"] * 40 + s * 0.05
    return s


def _candidati(idx):
    """Offset critici: la funzione obiettivo cambia solo quando una fuga
    attraversa un bordo, quindi basta provare quei valori e i punti medi."""
    vals = sorted({round(p[idx] % MODULO, 3)
                   for d in LOCALI.values() for p in d["fin"]})
    out = list(vals)
    for a, b in zip(vals, vals[1:]):
        out.append((a + b) / 2)
    out.append(((vals[-1] + vals[0] + MODULO) / 2) % MODULO)
    return sorted(set(out))


def cerca(modo="materiale"):
    best, arg = None, (0.0, 0.0)
    for o in _candidati(0):
        for p in _candidati(1):
            s = obiettivo(o, p, modo)
            if best is None or s < best:
                best, arg = s, (o, p)
    return arg


def _varianti():
    v = {
        "A": dict(o=cerca("materiale"), titolo="A - minimo consumo: meno lastre e meno tagli in tutta la casa"),
        "B": dict(o=cerca("equilibrio"), titolo="B - equilibrata: minimizza i listelli locale per locale (zona giorno pesata x4)"),
        "C": dict(o=cerca("zg"), titolo="C - zona giorno prioritaria: massimo numero di lastre intere nell'ambiente principale"),
    }
    for k, d in v.items():
        d["nome"] = k
        d["tot"], d["loc"] = analizza(*d["o"])
    return v


def usa_formato(i):
    """Rende attiva una configurazione di posa e rifa' l'ottimizzazione.

    Formato e corsi di rivestimento cambiano il modulo della griglia, quindi
    origine ottimale, lastre e sfrido vanno ricalcolati: non basta ridisegnare.
    """
    global FORMATO, PIASTRELLA, FUGA, MODULO, LASTRA, RIV_CORSI, H_RIV, VARIANTI
    FORMATO = FORMATI[i]
    PIASTRELLA = FORMATO["piastrella"]
    FUGA = FORMATO["fuga"]
    MODULO = PIASTRELLA + FUGA
    LASTRA = (PIASTRELLA / 100) ** 2
    RIV_CORSI = FORMATO["riv_corsi"]
    H_RIV = h_riv(FORMATO)
    VARIANTI = _varianti()
    return FORMATO


POSA_ATTIVA = 1
for _a in _sys_argv:
    if _a.startswith("--posa="):
        POSA_ATTIVA = int(_a.split("=", 1)[1])
usa_formato(POSA_ATTIVA)

# =====================================================================
# REPORT
# =====================================================================

print(f"superficie pavimentata (al netto di battiscopa/rivestimento): {AREA_TOT:.2f} mq\n")

ALT_VANO_STAMPA = ALT_VANO
print("ELENCO INFISSI (numerazione riportata in pianta)")
print(f"{'n':>3}  {'tipo':16}{'larghezza':>10}{'altezza':>9}  posizione")
print("-" * 62)
for n, (tipo, x0, y0, x1, y1, lb) in enumerate(APERTURE, 1):
    w = max(abs(x1 - x0), abs(y1 - y0))
    t = f"tasca {'-' if VERSI[n] < 0 else '+'} {TASCHE[n][0]:.0f}..{TASCHE[n][1]:.0f}" if n in VERSI else ""
    print(f"{n:3}  {tipo:16}{w:9.0f} {ALT_VANO[tipo]:8.0f}   "
          f"x {min(x0,x1):.0f}-{max(x0,x1):.0f}  y {min(y0,y1):.0f}-{max(y0,y1):.0f}   {lb}  {t}")
print()
print()
print("ELENCO ARREDI (identificativo riportato in pianta e nel modello 3D)")
print(f"{'id':8}{'locale':22}{'L':>6}{'P':>6}{'H':>6}{'sosp.':>7}  descrizione")
print("-" * 76)
for i, (lo, lb, x, y, w, h, tp) in enumerate(ARREDO):
    larg, prof, alt = misure(i)
    base = altezza(lb, tp)[1]
    nome = re.sub(r"\s*\d+[xX]\d+\s*$", "", lb).strip() or tp.upper()
    print(f"{ID_ARREDO[i]:8}{lo:22}{larg:6.0f}{prof:6.0f}{alt:6.0f}"
          f"{(f'{base:.0f}' if base else '-'):>7}  {nome}")
print("\nL = larghezza lungo il muro, P = profondita' dal muro, H = altezza,")
print("sosp. = quota di attacco da terra per gli elementi sospesi (cm)")
print()
print("CONFRONTO CONFIGURAZIONI DI POSA (variante A, tasto B nel modello 3D)")
print(f"{'n':>2}  {'configurazione':30}{'modulo':>8}{'intere':>8}{'listelli':>9}"
      f"{'lato min':>10}{'lastre':>8}{'sfrido':>8}{'h riv.':>8}")
print("-" * 91)
for _i, _f in enumerate(FORMATI):
    usa_formato(_i)
    _t = VARIANTI["A"]["tot"]
    print(f"{_i:>2}  {_f['nome']:30}{MODULO:8.2f}{_t['intere']:8d}{_t['sliver']:9d}"
          f"{_t['min_lato']:10.1f}{_t['lastre']:8d}{_t['sfrido']*100:7.1f}%{H_RIV:8.1f}")
usa_formato(POSA_ATTIVA)
print(f"\nconfigurazione attiva negli elaborati: {POSA_ATTIVA} - {FORMATO['nome']}"
      f"   (si cambia con  python casa_pianta.py --posa=N)")
print()

hdr = (f"{'var':3} {'origine X/Y':>13} {'lastre intere':>14} {'tagliate':>9} "
       f"{'di cui <25cm':>13} {'25-45':>6} {'>45':>5} {'lato min':>9} "
       f"{'% sup. intera':>14} {'lastre tot':>11} {'sfrido':>7}")
print(hdr)
print("-" * len(hdr))
for k, v in VARIANTI.items():
    t = v["tot"]
    print(f"{k:3} {v['o'][0]:5.1f}/{v['o'][1]:6.1f} {t['intere']:14d} {t['tagli']:9d} "
          f"{t['sliver']:13d} {t['medi']:6d} {t['buoni']:5d} {t['min_lato']:8.1f} "
          f"{t['q_intere']*100:13.1f}% {t['lastre']:11d} {t['sfrido']*100:6.1f}%")
print()
for k, v in VARIANTI.items():
    print(f"--- variante {k}")
    for nome in LOCALI:
        l = v["loc"][nome]
        print(f"    {nome:20} intere {l['intere']:3d}  tagliate {l['tagli']:3d} "
              f"(<25: {l['sliver']}, 25-45: {l['medi']}, >45: {l['buoni']})  "
              f"lato min {l['min_lato']:5.1f}  sup. intera {l['q_intere']*100:5.1f}%  lastre {l['lastre']:3d}")
    print()

# =====================================================================
# DISEGNO
# =====================================================================

W, H = 1800, 1190
TX, TY = 155, 250

COL_INT = "#ffffff"
COL_BUONO = "#fff3c4"
COL_MEDIO = "#ffd08a"
COL_SLIVER = "#ff9b8a"


def colore(c):
    if c["intera"]:
        return COL_INT
    if c["lato"] >= MEZZA:
        return COL_BUONO
    if c["lato"] >= SLIVER:
        return COL_MEDIO
    return COL_SLIVER


def disegna(var, suffisso=""):
    S = []
    add = S.append
    ox, oy = var["o"]

    def line(x1, y1, x2, y2, cls="", extra=""):
        add(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" class="{cls}" {extra}/>')

    def rect(x, y, w, h, cls="", extra=""):
        add(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" class="{cls}" {extra}/>')

    def txt(x, y, s, cls="lbl", anchor="middle", rot=False, alone=False):
        t = f' transform="rotate(-90 {x:.1f} {y:.1f})"' if rot else ""
        if alone:
            add(f'<text x="{x:.1f}" y="{y:.1f}" class="{cls}" text-anchor="{anchor}"{t} '
                f'stroke="#ffffff" stroke-width="4" stroke-linejoin="round">{s}</text>')
        add(f'<text x="{x:.1f}" y="{y:.1f}" class="{cls}" text-anchor="{anchor}"{t}>{s}</text>')

    add('<?xml version="1.0" encoding="UTF-8"?>')
    add(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W/SCALA:.2f}cm" '
        f'height="{H/SCALA:.2f}cm" viewBox="0 0 {W} {H}">')
    add("""<defs>
<marker id="tick" markerWidth="9" markerHeight="9" refX="4.5" refY="4.5" orient="auto">
  <line x1="1.5" y1="7.5" x2="7.5" y2="1.5" stroke="#555" stroke-width="1.1"/></marker>
<style>
text { font-family: Arial, Helvetica, sans-serif; fill: #222; }
.t1 { font-size: 26px; font-weight: bold; }
.t2 { font-size: 15px; }
.t3 { font-size: 15px; font-weight: bold; }
.room { font-size: 18px; font-weight: bold; fill: #12506e; }
.lbl { font-size: 12px; fill: #333; }
.joint { stroke: #8ea0b0; stroke-width: 0.9; }
.fix { fill: none; stroke: #1f5673; stroke-width: 2; }
.fixl { fill: none; stroke: #1f5673; stroke-width: 1.4; }
.ap { stroke: #c0392b; stroke-width: 2.5; }
.apf { stroke: #0f7fbf; stroke-width: 3; }
.dim { font-size: 11px; fill: #444; }
.dimq { font-size: 11px; fill: #0a6a3a; font-weight: bold; }
.dimr { font-size: 13px; fill: #0b4fa0; font-weight: bold; }
.num { font-size: 13px; fill: #ffffff; font-weight: bold; }
.dl { stroke: #777; stroke-width: 0.8; }
.dq { stroke: #0a6a3a; stroke-width: 0.9; }
.dr { stroke: #0b4fa0; stroke-width: 1.1; }
.ext { stroke: #aaa; stroke-width: 0.5; stroke-dasharray: 4 3; }
</style></defs>""")
    rect(0, 0, W, H, extra='fill="#ffffff"')
    txt(30, 45, f"APPARTAMENTO - posa gres {PIASTRELLA:.0f}x{PIASTRELLA:.0f}  |  variante {var['nome']}", "t1", "start")
    txt(30, 72, var["titolo"], "t2", "start")
    txt(30, 95, f"fuga {FUGA*10:.1f} mm - modulo {MODULO:.2f} cm - griglia unica continua su tutta la casa - "
                f"battiscopa/rivestimento {FINITURA:.0f} cm - origine {ox:.1f}/{oy:.1f} - stampa 100% = 1:{SCALA}", "t2", "start")

    add(f'<g transform="translate({TX},{TY})">')

    bx0 = min(d["bb"][0] for d in LOCALI.values()) - 14
    by0 = min(d["bb"][1] for d in LOCALI.values()) - 14
    bx1 = max(d["bb"][2] for d in LOCALI.values()) + 14
    by1 = max(d["bb"][3] for d in LOCALI.values()) + 14

    for nome, d in LOCALI.items():
        for c in var["loc"][nome]["celle"]:
            col = colore(c)
            for p in c["parti"]:
                rect(p[0], p[1], p[2] - p[0], p[3] - p[1], extra=f'fill="{col}"')
        # fughe
        x0, y0, x1, y1 = d["bb"]
        k = math.ceil((x0 - ox) / MODULO)
        while ox + k * MODULO < x1:
            for a, b in intervalli(d["fin"], "x", ox + k * MODULO):
                line(ox + k * MODULO, a, ox + k * MODULO, b, "joint")
            k += 1
        k = math.ceil((y0 - oy) / MODULO)
        while oy + k * MODULO < y1:
            for a, b in intervalli(d["fin"], "y", oy + k * MODULO):
                line(a, oy + k * MODULO, b, oy + k * MODULO, "joint")
            k += 1
        pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in d["fin"])
        add(f'<polygon points="{pts}" fill="none" stroke="#8a9aa8" stroke-width="0.8"/>')

    # ricalco della tavola originale, sopra la posa
    for col, lw, curva, pts in BASE:
        c = "#%02x%02x%02x" % tuple(int(255 * v) for v in col)
        magenta = col[0] > 0.6 and col[2] > 0.6 and col[1] < 0.5
        w = 1.0 if magenta else (2.6 if lw >= 0.8 else 1.4)
        op = 0.2 if magenta else 1.0
        if curva:
            d0 = (f"M {pts[0][0]:.1f},{pts[0][1]:.1f} C {pts[1][0]:.1f},{pts[1][1]:.1f} "
                  f"{pts[2][0]:.1f},{pts[2][1]:.1f} {pts[3][0]:.1f},{pts[3][1]:.1f}")
        else:
            d0 = "M " + " L ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        add(f'<path d="{d0}" fill="none" stroke="{c}" stroke-width="{w}" stroke-opacity="{op}"/>')

    # balconi
    for x0, y0, x1, y1, rn, ro, re in BALCONI + BALCONI_VICINO:
        proprio = (x0, y0, x1, y1, rn, ro, re) in BALCONI
        rect(x0, y0, x1 - x0, y1 - y0,
             extra=f'fill="{"#eceff1" if proprio else "#e0ddd8"}" '
                   f'stroke="#9aa5b1" stroke-width="0.8" stroke-dasharray="6 3"')
        for on, (ax, ay, bx, by) in ((rn, (x0, y0, x1, y0)), (ro, (x0, y0, x0, y1)),
                                     (re, (x1, y0, x1, y1))):
            if on:
                line(ax, ay, bx, by, "", 'stroke="#2f4f3a" stroke-width="3.5"')
        txt((x0 + x1) / 2, (y0 + y1) / 2 + 4,
            f"BALCONE {x1-x0:.0f}x{y1-y0:.0f}" if proprio else "balcone confinante", "lbl")
    for x0, y0, x1, y1, h in SEPARE:
        line(x0, y0, x1, y1, "", 'stroke="#2f4f3a" stroke-width="6"')
        txt(x0 + 12, (y0 + y1) / 2, f"SEPARE h {h:.0f}", "lbl", rot=True)

    # aperture
    for n, (tipo, x0, y0, x1, y1, lb) in enumerate(APERTURE, 1):
        orizz = abs(y1 - y0) < abs(x1 - x0)
        sp = 16
        if orizz:
            rect(min(x0, x1), y0 - sp / 2, abs(x1 - x0), sp, extra='fill="#ffffff"')
        else:
            rect(x0 - sp / 2, min(y0, y1), sp, abs(y1 - y0), extra='fill="#ffffff"')
        cls = "apf" if tipo in ("finestra", "portafinestra") else "ap"
        if tipo == "passaggio":
            continue
        line(x0, y0, x1, y1, cls)
        if tipo == "battente":
            # ingresso: cardini a destra, apertura verso l'interno
            a, b = min(x0, x1), max(x0, x1)
            L = b - a
            oy = y0 - L
            line(b, y0, b, oy, "", 'stroke="#c0392b" stroke-width="3"')
            add(f'<path d="M {a},{y0} A {L},{L} 0 0 1 {b},{oy}" fill="none" '
                f'stroke="#c0392b" stroke-width="1" stroke-dasharray="6 4"/>')
        elif tipo in ("porta", "passaggio"):
            if n in PIEGHEVOLI:
                # porta a libro: anta nel vano, nessuna tasca
                if orizz:
                    a, b = min(x0, x1), max(x0, x1)
                    rect(a + 2, y0 - 2.5, b - a - 4, 5, "door")
                    line(a, y0, (a + b) / 2, y0 - 26, "", 'stroke="#c0392b" stroke-width="1.2"')
                    line((a + b) / 2, y0 - 26, b, y0 - 4, "", 'stroke="#c0392b" stroke-width="1.2"')
                    txt((a + b) / 2, y0 - 31, "2 ante a libro", "lbl")
                else:
                    a, b = min(y0, y1), max(y0, y1)
                    rect(x0 - 2.5, a + 2, 5, b - a - 4, "door")
                    line(x0, a, x0 - 26, (a + b) / 2, "", 'stroke="#c0392b" stroke-width="1.2"')
                    line(x0 - 26, (a + b) / 2, x0 - 4, b, "", 'stroke="#c0392b" stroke-width="1.2"')
                    txt(x0 - 31, (a + b) / 2, "2 ante a libro", "lbl", rot=True)
            else:
                # porta a scomparsa: anta nel vano, tasca tratteggiata e verso di rientro
                t0, t1 = TASCHE[n]
                v = VERSI[n]
                if orizz:
                    a, b = min(x0, x1), max(x0, x1)
                    mg = max(0.0, (b - a - ANTA) / 2)
                    for sa, sb in ((a, a + mg), (b - mg, b)):   # spallette
                        if sb - sa > 0.5:
                            rect(sa, y0 - 7, sb - sa, 14, extra='fill="#4a4a4a"')
                    rect(a + mg, y0 - 2.5, b - a - 2 * mg, 5, "door")
                    rect(t0, y0 - 6, t1 - t0, 12, extra='fill="none" stroke="#c0392b" '
                         'stroke-width="0.8" stroke-dasharray="5 3"')
                    fx = t1 - 6 if v > 0 else t0 + 6
                    line((a + b) / 2, y0 - 17, fx, y0 - 17, "", 'stroke="#c0392b" stroke-width="1.2"')
                    add(f'<path d="M {fx},{y0-17} l {8*-v},-3.5 l 0,7 Z" fill="#c0392b"/>')
                    txt((t0 + t1) / 2, y0 - 22, f"tasca {t1-t0:.0f}", "lbl")
                else:
                    a, b = min(y0, y1), max(y0, y1)
                    rect(x0 - 2.5, a + 2, 5, b - a - 4, "door")
                    rect(x0 - 6, t0, 12, t1 - t0, extra='fill="none" stroke="#c0392b" '
                         'stroke-width="0.8" stroke-dasharray="5 3"')
                    fy = t1 - 6 if v > 0 else t0 + 6
                    line(x0 - 17, (a + b) / 2, x0 - 17, fy, "", 'stroke="#c0392b" stroke-width="1.2"')
                    add(f'<path d="M {x0-17},{fy} l -3.5,{8*-v} l 7,0 Z" fill="#c0392b"/>')
                    txt(x0 - 22, (t0 + t1) / 2, f"tasca {t1-t0:.0f}", "lbl", rot=True)
        if lb:
            txt((x0 + x1) / 2, (y0 + y1) / 2 - 8, lb, "lbl", rot=not orizz)
        bx, by = (x0 + x1) / 2, (y0 + y1) / 2
        add(f'<circle cx="{bx:.1f}" cy="{by:.1f}" r="15" fill="#c0392b" '
            f'stroke="#ffffff" stroke-width="2"/>')
        txt(bx, by + 5, str(n), "num")

    # arredo
    for x, y, w, h, lb in SETTI:
        rect(x, y, w, h, extra='fill="#4a4a4a"')
        txt(x + w / 2, y - 9, lb, "lbl", alone=True)

    for x0, y0, x1, y1, lb in TRAVI:
        rect(x0, y0, x1 - x0, y1 - y0,
             extra='fill="#8e44ad" fill-opacity="0.18" stroke="#8e44ad" '
                   'stroke-width="1.2" stroke-dasharray="7,4"')
        txt((x0 + x1) / 2, y1 + 34, f"{lb}  h {H_TRAVE:.0f}", "lbl", alone=True)

    for x0, y0, x1, y1, lb in PILASTRI:
        rect(x0, y0, x1 - x0, y1 - y0, extra='fill="#5d4037" stroke="#3e2723"')
        txt((x0 + x1) / 2, (y0 + y1) / 2 + 4,
            f"{lb} {x1-x0:.0f}x{y1-y0:.0f}", "num", alone=True)

    # arredi impilati (lavatrice + kit + asciugatrice) hanno lo stesso ingombro:
    # le etichette vanno sfalsate o diventano un groviglio
    sovrapposti = {}
    for idx, (loc, label, x, y, w, h, tipo) in enumerate(ARREDO):
        rect(x, y, w, h, "fix", 'rx="3" fill="#ffffff" fill-opacity="0.65"')
        if tipo == "letto":
            if w > h:
                rect(x + 6, y + 6, 36, h - 12, "fixl", 'rx="3"')
            else:
                rect(x + 6, y + 6, w - 12, 36, "fixl", 'rx="3"')
        elif tipo == "divano":
            rect(x, y, w, 22, "fixl")
        elif tipo == "cucina":
            pass
        elif tipo == "elettro":
            line(x + 5, y + 5, x + w - 5, y + h - 5, "fixl")
        elif tipo == "lavello":
            rect(x + 7, y + 8, w - 14, h / 2 - 12, "fixl", 'rx="3"')
            rect(x + 7, y + h / 2 + 4, w - 14, h / 2 - 12, "fixl", 'rx="3"')
            add(f'<circle cx="{x+w-12:.1f}" cy="{y+h/2:.1f}" r="4" class="fixl"/>')
        elif tipo == "fuochi":
            for dx in (0.3, 0.7):
                for dy in (0.3, 0.7):
                    add(f'<circle cx="{x+w*dx:.1f}" cy="{y+h*dy:.1f}" r="9" class="fixl"/>')
        elif tipo == "appendi":
            n = max(2, int(abs(h if h > w else w) // 20))
            for k in range(n):
                if h > w:
                    yy = y + (k + 0.5) * h / n
                    line(x, yy, x + w, yy, "fixl")
                else:
                    xx = x + (k + 0.5) * w / n
                    line(xx, y, xx, y + h, "fixl")
        elif tipo in ("cassetti", "scaffale"):
            passo = 90 if tipo == "cassetti" else 45
            lungo, n = (w, max(2, int(w // passo))) if w > h else (h, max(2, int(h // passo)))
            for k in range(1, n):
                if w > h:
                    line(x + k * lungo / n, y, x + k * lungo / n, y + h, "fixl")
                else:
                    line(x, y + k * lungo / n, x + w, y + k * lungo / n, "fixl")
        elif tipo == "doccia":
            add(f'<circle cx="{x+w/2:.1f}" cy="{y+h/2:.1f}" r="7" class="fixl"/>')
        elif tipo == "wc":
            add(f'<ellipse cx="{x+w/2:.1f}" cy="{y+h/2:.1f}" rx="{abs(w)/2-6:.1f}" '
                f'ry="{abs(h)/2-4:.1f}" class="fixl"/>')
        if label:
            eti = descrizione(idx)
            k = sovrapposti.get((x, y, w, h), 0)
            sovrapposti[(x, y, w, h)] = k + 1
            dy = k * 13
            if tipo == "appendi":
                txt(x + w + 13, y + h / 2 + dy, eti, "lbl", rot=True, alone=True)
            elif h > w * 1.4 or tipo in ("elettro", "lavello", "fuochi"):
                txt(x + w / 2 + 4 + dy, y + h / 2, eti, "lbl", rot=True)
            else:
                txt(x + w / 2, y + h / 2 + 4 + dy, eti, "lbl")

    # ---- quote ----
    def catena(vals, c, orizz):
        vals = sorted(set(round(v, 1) for v in vals))
        for i, (a, b) in enumerate(zip(vals, vals[1:])):
            sfalsa = 15 if (b - a) < 48 and i % 2 else 0
            if orizz:
                line(a, c, b, c, "dl", 'marker-start="url(#tick)" marker-end="url(#tick)"')
                if b - a >= 8:
                    txt((a + b) / 2, c - 6 - sfalsa, f"{b-a:.0f}", "dim")
            else:
                line(c, a, c, b, "dl", 'marker-start="url(#tick)" marker-end="url(#tick)"')
                if b - a >= 8:
                    txt(c - 6 - sfalsa, (a + b) / 2, f"{b-a:.0f}", "dim", rot=True)
        for v in vals:
            if orizz:
                line(v, c + 3, v, c + 22, "ext")
            else:
                line(c + 3, v, c + 22, v, "ext")

    XS = [p[0] for d in LOCALI.values() for p in d["fin"]]
    YS = [p[1] for d in LOCALI.values() for p in d["fin"]]
    catena(XS, -78, True)
    catena([min(XS), max(XS)], -120, True)
    catena(YS, -78, False)
    catena([min(YS), max(YS)], -120, False)

    for x0, y0, x1, y1, lb in QUOTE:
        line(x0, y0, x1, y1, "dq", 'marker-start="url(#tick)" marker-end="url(#tick)"')
        if abs(x1 - x0) >= abs(y1 - y0):
            txt((x0 + x1) / 2, min(y0, y1) - 5, lb, "dimq")
        else:
            txt(min(x0, x1) - 5, (y0 + y1) / 2, lb, "dimq", rot=True)

    # ingombro complessivo di ogni stanza, per non dover sommare la catena
    for nome, d in LOCALI.items():
        x0, y0, x1, y1 = d["bb"]
        line(x0, y0 + 11, x1, y0 + 11, "dr", 'marker-start="url(#tick)" marker-end="url(#tick)"')
        txt((x0 + x1) / 2, y0 + 7, f"{x1-x0:.0f}", "dimr", alone=True)
        line(x0 + 11, y0, x0 + 11, y1, "dr", 'marker-start="url(#tick)" marker-end="url(#tick)"')
        txt(x0 + 7, (y0 + y1) / 2, f"{y1-y0:.0f}", "dimr", rot=True, alone=True)

    # lastra tipo quotata nel soggiorno
    zg = var["loc"]["ZONA GIORNO"]
    bb = LOCALI["ZONA GIORNO"]["bb"]
    mira = ((bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2)
    piene = [c for c in zg["celle"] if c["intera"]]
    if piene:
        c = min(piene, key=lambda c: (c["parti"][0][0] - mira[0]) ** 2 + (c["parti"][0][1] - mira[1]) ** 2)
        a0, b0, a1, b1 = c["parti"][0]
        rect(a0, b0, PIASTRELLA, PIASTRELLA, extra='fill="#ffe9a8" stroke="#b06a00" stroke-width="1.6"')
        line(a0, b0 - 9, a0 + PIASTRELLA, b0 - 9, "dq", 'marker-start="url(#tick)" marker-end="url(#tick)"')
        txt(a0 + PIASTRELLA / 2, b0 - 13, f"{PIASTRELLA:.0f}", "dimq", alone=True)
        line(a0 - 9, b0, a0 - 9, b0 + PIASTRELLA, "dq", 'marker-start="url(#tick)" marker-end="url(#tick)"')
        txt(a0 - 13, b0 + PIASTRELLA / 2, f"{PIASTRELLA:.0f}", "dimq", rot=True, alone=True)
        line(a0 + PIASTRELLA, b1 - 14, a1, b1 - 14, "dq", 'marker-start="url(#tick)" marker-end="url(#tick)"')
        txt(a1 + 30, b1 - 10, f"fuga {FUGA*10:.1f} mm - modulo {MODULO:.2f}", "dimq", alone=True)
        txt(a0 + PIASTRELLA / 2, b0 + PIASTRELLA / 2 + 5, "LASTRA TIPO", "dimq", alone=True)

    # box doccia
    bx, bl, by, bs = BOX["x0"], BOX["luce"], BOX["y"], BOX["sfalso"]
    line(bx, by, bx + bl, by, "", 'stroke="#1f5673" stroke-width="3.2"')
    txt(bx + bl / 2, by + 13, f"FISSO {bl:.0f}", "lbl")
    line(bx + bl, by + bs, bx + 2 * bl, by + bs, "", 'stroke="#1f5673" stroke-width="3.2"'
         ' stroke-dasharray="7 3"')
    txt(bx + 1.5 * bl, by + 13, f"ANTA MOBILE {bl:.0f}", "lbl")
    line(bx + 1.5 * bl, by + 21, bx + bl / 2 + 8, by + 21, "", 'stroke="#1f5673" stroke-width="1.2"')
    add(f'<path d="M {bx+bl/2},{by+21} l 8,-3.5 l 0,7 Z" fill="#1f5673"/>')

    for nome, d in LOCALI.items():
        l = var["loc"][nome]
        x0, y0, x1, y1 = d["bb"]
        cx, cy = d.get("lab", ((x0 + x1) / 2, y0 + 26))
        txt(cx, cy, nome, "room", alone=True)
        txt(cx, cy + 17, f"{d['area']:.2f} mq  -  {x1-x0:.0f} x {y1-y0:.0f} cm", "lbl", alone=True)
        txt(cx, cy + 32, f"{l['intere']} intere / {l['tagli']} tagliate  (min {l['min_lato']:.0f} cm)",
            "lbl", alone=True)

    add("</g>")

    # scalimetro
    sx, sy = 155, H - 250
    txt(sx, sy - 6, f"scala 1:{SCALA} alla stampa 100%", "t2", "start")
    rect(sx, sy, 300, 12, extra='fill="none" stroke="#333" stroke-width="1"')
    for i in range(3):
        if i % 2 == 0:
            rect(sx + i * 100, sy, 100, 12, extra='fill="#333"')
        txt(sx + i * 100, sy + 28, f"{i}", "t2")
    txt(sx + 300, sy + 28, "3 m", "t2")

    # legenda
    ly = H - 170
    txt(30, ly - 8, "LEGENDA LASTRE", "t3", "start")
    for i, (col, lab) in enumerate([
            (COL_INT, f"intera {PIASTRELLA:.0f}x{PIASTRELLA:.0f}"),
            (COL_BUONO, f"tagliata, lato &gt;= {MEZZA:.0f} cm (taglio buono)"),
            (COL_MEDIO, f"tagliata, lato {SLIVER:.0f}-{MEZZA:.0f} cm"),
            (COL_SLIVER, f"tagliata, lato &lt; {SLIVER:.0f} cm (listello: da evitare)")]):
        rect(30 + i * 330, ly, 28, 20, extra=f'fill="{col}" stroke="#3a3a3a" stroke-width="1"')
        txt(66 + i * 330, ly + 15, lab, "t2", "start")

    by = H - 120
    rect(30, by, W - 60, 104, extra='fill="#f5f7f9" stroke="#9aa5b1" stroke-width="1"')
    txt(45, by + 22, "CONFRONTO VARIANTI (stessi dati del disegno)", "t3", "start")
    col = [45, 230, 420, 560, 700, 880, 1010, 1160, 1330, 1520]
    intest = ["variante", "origine X/Y", "lastre intere", "tagliate", "tagli &lt; 25 cm",
              "tagli 25-45", "tagli &gt; 45", "lato minimo", "% sup. con intere", "lastre / sfrido"]
    for c, t in zip(col, intest):
        txt(c, by + 44, t, "t2", "start")
    for i, (k, v) in enumerate(VARIANTI.items()):
        t = v["tot"]
        yy = by + 64 + i * 15
        vals = [k, f"{v['o'][0]:.1f} / {v['o'][1]:.1f}", str(t["intere"]), str(t["tagli"]),
                str(t["sliver"]), str(t["medi"]), str(t["buoni"]), f"{t['min_lato']:.0f} cm",
                f"{t['q_intere']*100:.0f}%", f"{t['lastre']} / {t['sfrido']*100:.0f}%"]
        for c, tt in zip(col, vals):
            txt(c, yy, tt, "t3" if k == var["nome"] else "t2", "start")

    add("</svg>")
    path = f"{OUT}_var_{var['nome']}{suffisso}"
    with open(path + ".svg", "w", encoding="utf-8") as f:
        f.write("\n".join(S))
    return path


paths = [disegna(VARIANTI[k]) for k in ("A", "B")]

try:
    from svglib.svglib import svg2rlg
    from reportlab.graphics import renderPDF
    import fitz

    for p in paths:
        renderPDF.drawToFile(svg2rlg(p + ".svg"), p + ".pdf")
        fitz.open(p + ".pdf")[0].get_pixmap(matrix=fitz.Matrix(2, 2)).save(p + ".png")
    print("scritti:", ", ".join(p + ".svg/.pdf/.png" for p in paths))
except Exception as e:
    print("anteprima non generata:", e)
