"""Computo del battiscopa ricavato dalle stesse lastre 90x90.

Il battiscopa si ottiene tagliando in strisce le lastre: con l'altezza H si
ricavano int(90/H) strisce teoriche, ma ogni taglio consuma la lama, quindi il
conteggio usa le strisce effettivamente ottenibili dichiarate dal rivenditore.
Il bagno e' escluso: ha il rivestimento a parete.
"""

import contextlib
import io
import math

with contextlib.redirect_stdout(io.StringIO()):
    import casa_pianta as cp

PIASTRELLA = cp.PIASTRELLA
LASTRA = cp.LASTRA
MAGGIORAZIONE = 0.10     # spezzoni d'angolo e ricongiunzioni

# i tratti sono quelli della pianta: percorso continuo interrotto solo dai vani
# a terra, gia' verificato per contiguita' da vincoli.py
TRATTI = cp.BATTISCOPA

# tratti coperti da arredo fisso: battiscopa non necessario
ARREDO_FISSO = {
    "RIPOSTIGLIO": 130, "LETTO MATRIMONIALE": 200,
    "LETTO SINGOLO": 220, "ZONA GIORNO": 360,
}


def perimetro(p):
    return sum(abs(p[(i + 1) % len(p)][0] - p[i][0]) + abs(p[(i + 1) % len(p)][1] - p[i][1])
               for i in range(len(p)))


H_BATT = 8.0
STRISCE = 10             # strisce da h 8 effettivamente ricavabili da una lastra


def calcola():
    """Metri di battiscopa per locale e lastre necessarie, col formato attivo."""
    per_loc = {}
    for k, tratti in TRATTI.items():
        per = perimetro(cp.LOCALI[k]["poly"])
        net = sum(b - a for a, b, *_ in tratti)
        per_loc[k] = dict(perimetro=per, netto=net, aperture=per - net,
                          tratti=len(tratti))
    tot = sum(d["netto"] for d in per_loc.values())
    ml = tot / 100 * (1 + MAGGIORAZIONE)
    ml_lastra = STRISCE * cp.PIASTRELLA / 100
    return dict(per_loc=per_loc, netto=tot / 100, ml=ml, ml_lastra=ml_lastra,
                lastre=math.ceil(ml / ml_lastra),
                senza_arredo=(tot - sum(ARREDO_FISSO.values())) / 100)


DETT = calcola()
ml = DETT["ml"]

if __name__ == "__main__":
    print(f"{'locale':22}{'perimetro':>11}{'aperture':>10}{'netto':>9}{'tratti':>8}")
    print("-" * 60)
    for k, d in DETT["per_loc"].items():
        print(f"{k:22}{d['perimetro']/100:9.2f} m{d['aperture']/100:8.2f} m"
              f"{d['netto']/100:7.2f} m{d['tratti']:8d}")
    print("-" * 60)
    print(f"{'TOTALE':22}{'':11}{'':10}{DETT['netto']:7.2f} m")
    print(f"\nsenza battiscopa dietro cucina e armadiature: {DETT['senza_arredo']:.2f} m")
    print(f"da posare con maggiorazione {MAGGIORAZIONE*100:.0f}%: {ml:.2f} m\n")
    print(f"{'altezza':>8}{'strisce/lastra':>16}{'ml per lastra':>15}{'lastre':>8}{'mq':>8}")
    print("-" * 55)
    for h, strisce in ((8.0, 10), (10.0, 8), (10.0, 9), (7.0, 12)):
        ml_l = strisce * PIASTRELLA / 100
        n = math.ceil(ml / ml_l)
        print(f"{h:6.0f} cm{strisce:16d}{ml_l:14.1f} m{n:8d}{n*LASTRA:8.2f}")
