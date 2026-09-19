"""Quanto conviene stringere il disimpegno per migliorare la posa del 90x90.

Il muro fra disimpegno e zona notte e' nuovo (verde in tavola), quindi la sua
posizione e' un parametro di progetto. Lo script lo arretra di s centimetri,
ricostruisce i locali e rilancia l'ottimizzazione della griglia, riportando
per ogni posizione le metriche calcolate lastra per lastra.

Vincolo: larghezza minima del disimpegno (al grezzo) impostabile qui sotto.
"""

import contextlib
import io
import math

with contextlib.redirect_stdout(io.StringIO()):
    import casa_pianta as cp

LARGH_MIN = 100.0        # larghezza minima del disimpegno al grezzo
PASSO = 1.0

# poligoni nominali, prima di qualunque trasformazione: letti dalla pianta
BASE = cp.LOCALI_RILIEVO
# le due facce del muro nuovo fra disimpegno e zona notte
Q_MURO = next(q for a, q, lb in cp.MURI_NUOVI if lb.startswith("muro disimpegno"))
LARGH_DISIMPEGNO = min(Q_MURO) - 17.0


def ricostruisci(s):
    """Arretra di s il muro nuovo: le due facce si spostano insieme."""
    for nome, base in BASE.items():
        poly = [(x, y - s if any(abs(y - q) < 0.1 for q in Q_MURO) else y) for x, y in base]
        poly = [cp.R(*p) for p in poly][::-1]
        if cp.orientamento(poly) < 0:
            poly = poly[::-1]
        d = cp.LOCALI[nome]
        d["poly"] = poly
        d["fin"] = cp.offset_poly(poly, cp.FINITURA)
        d["rect"] = cp.rettangoli(d["fin"])
        d["area"] = cp.area(d["fin"]) / 10000
        xs = [p[0] for p in d["fin"]]
        ys = [p[1] for p in d["fin"]]
        d["bb"] = (min(xs), min(ys), max(xs), max(ys))


print(f"{'s':>4}{'disimp.':>9}{'ripost.':>9}{'intere':>8}{'<25cm':>7}{'lato min':>10}"
      f"{'lastre':>8}{'sfrido':>8}{'obiettivo':>11}")
print("-" * 74)

RIS = []
s = 0.0
while s <= LARGH_DISIMPEGNO - LARGH_MIN + 0.01:
    ricostruisci(s)
    o = cp.cerca()
    tot, per = cp.analizza(*o)
    ob = cp.obiettivo(*o)
    RIS.append((s, o, tot, ob))
    print(f"{s:4.0f}{LARGH_DISIMPEGNO-s:8.0f} {135-s:8.0f} {tot['intere']:8d}"
          f"{tot['sliver']:7d}{tot['min_lato']:10.1f}{tot['lastre']:8d}"
          f"{tot['sfrido']*100:7.1f}%{ob:11.1f}")
    s += PASSO

best = min(RIS, key=lambda r: r[3])
print("\nmigliore:")
s, o, tot, ob = best
print(f"  arretramento muro     {s:.0f} cm")
print(f"  disimpegno            {LARGH_DISIMPEGNO-s:.0f} cm (al grezzo), "
      f"{LARGH_DISIMPEGNO-s-2:.0f} finito")
print(f"  ripostiglio           {135-s:.0f} cm di profondita'")
print(f"  origine griglia       {o[0]:.1f} / {o[1]:.1f}")
print(f"  lastre intere         {tot['intere']}   tagli sotto 25 cm: {tot['sliver']}")
print(f"  lato minimo           {tot['min_lato']:.1f} cm")
print(f"  lastre totali         {tot['lastre']}   sfrido {tot['sfrido']*100:.1f}%")

ricostruisci(0.0)
o0 = cp.cerca()
t0, _ = cp.analizza(*o0)
print(f"\nconfronto con lo stato attuale (s=0):")
print(f"  intere {t0['intere']} -> {tot['intere']}   "
      f"listelli {t0['sliver']} -> {tot['sliver']}   "
      f"lato min {t0['min_lato']:.1f} -> {tot['min_lato']:.1f}   "
      f"lastre {t0['lastre']} -> {tot['lastre']}")
