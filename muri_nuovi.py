"""Ottimizzazione della posizione dei muri nuovi (verdi) rispetto alla posa.

I muri verdi della tavola sono di progetto, quindi la loro posizione e' una
variabile: portandone la faccia finita su una fuga si azzerano i tagli su quel
lato. Lo script fa una discesa per coordinate: sposta un muro alla volta,
rioptimizza l'origine della griglia e ripete.

Tutte le metriche vengono dalla stessa analisi lastra per lastra di casa_pianta.
"""

import contextlib
import io

with contextlib.redirect_stdout(io.StringIO()):
    import casa_pianta as cp

BASE = cp.LOCALI_RILIEVO

# escursione ammessa per ciascun muro di progetto; elenco e quote sono quelli di
# casa_pianta.MURI_NUOVI, qui si dichiara solo quanto ognuno puo' spostarsi:
# il disimpegno puo' solo stringersi (min 100 cm), il bagno resta 150-168
ESCURSIONI = {
    "muro disimpegno / zona notte": (-43, 0),
    "muro 14 bagno / camera matrimoniale": (-25, 8),
    "muro ripostiglio": (-20, 40),
    "nicchia bagno - lato lungo": (-40, 40),
    "nicchia bagno - fondo": (-40, 50),
}
MURI = {lb: (asse, list(quote), ESCURSIONI[lb]) for asse, quote, lb in cp.MURI_NUOVI}
PASSO = 0.5


def ricostruisci(sp):
    for nome, base in BASE.items():
        poly = []
        for x, y in base:
            for _, (asse, quote, _r) in MURI.items():
                pass
            nx, ny = x, y
            for m, (asse, quote, _r) in MURI.items():
                if asse == "x" and any(abs(x - q) < 0.1 for q in quote):
                    nx = x + sp[m]
                if asse == "y" and any(abs(y - q) < 0.1 for q in quote):
                    ny = y + sp[m]
            poly.append((nx, ny))
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


def stato(sp, o):
    ricostruisci(sp)
    tot, per = cp.analizza(*o)
    return tot, per, cp.obiettivo(*o)


sp = {m: 0.0 for m in MURI}
ricostruisci(sp)
orig = cp.cerca()
t0, _, ob0 = stato(sp, orig)
print("stato di progetto")
print(f"  intere {t0['intere']}  listelli<25 {t0['sliver']}  lato min {t0['min_lato']:.1f}"
      f"  lastre {t0['lastre']}  sfrido {t0['sfrido']*100:.1f}%\n")

for giro in range(3):
    for m, (asse, quote, (lo, hi)) in MURI.items():
        best, bd = None, sp[m]
        d = lo
        while d <= hi + 1e-9:
            prova = dict(sp, **{m: d})
            _, _, ob = stato(prova, orig)
            if best is None or ob < best - 1e-9:
                best, bd = ob, d
            d += PASSO
        sp[m] = bd
    ricostruisci(sp)
    orig = cp.cerca()
    tot, per, ob = stato(sp, orig)
    print(f"giro {giro+1}: obiettivo {ob:.1f}  intere {tot['intere']}  "
          f"listelli {tot['sliver']}  lato min {tot['min_lato']:.1f}  lastre {tot['lastre']}")

print("\nspostamenti proposti (cm, positivo = verso valori crescenti)")
for m, v in sp.items():
    print(f"  {m:28}{v:+7.1f}")

print(f"\norigine griglia  {orig[0]:.1f} / {orig[1]:.1f}")
print(f"\n{'locale':22}{'area':>8}{'intere':>8}{'tagli':>7}{'<25':>6}{'lato min':>10}")
print("-" * 61)
for nome, d in cp.LOCALI.items():
    l = per[nome]
    print(f"{nome:22}{d['area']:7.2f} {l['intere']:8d}{l['tagli']:7d}{l['sliver']:6d}{l['min_lato']:10.1f}")
print("-" * 61)
print(f"{'TOTALE':22}{sum(d['area'] for d in cp.LOCALI.values()):7.2f} "
      f"{tot['intere']:8d}{tot['tagli']:7d}{tot['sliver']:6d}{tot['min_lato']:10.1f}")
print(f"\nlastre {t0['lastre']} -> {tot['lastre']}   "
      f"listelli {t0['sliver']} -> {tot['sliver']}   "
      f"lato minimo {t0['min_lato']:.1f} -> {tot['min_lato']:.1f} cm")
_disimp = "muro disimpegno / zona notte"
_bagno = "muro 14 bagno / camera matrimoniale"
_L_DISIMP = min(MURI[_disimp][1]) - 17.0
_L_CAMERA = min(MURI[_bagno][1])
print(f"disimpegno {_L_DISIMP + sp[_disimp]:.0f} cm al grezzo, "
      f"bagno largo {169.1 - sp[_bagno]:.0f} cm, "
      f"camera larga {_L_CAMERA + sp[_bagno]:.0f} cm")
