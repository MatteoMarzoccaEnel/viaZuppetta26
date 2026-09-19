"""Computo finale, distinto per tipo di piastrella.

Fonti:
  pavimento            casa_pianta.py          (variante A, analisi lastra per lastra)
  rivestimento bagno   bagno_rivestimento.py   (diviso fra piastrella dedicata e 90x90)
  battiscopa           battiscopa.py           (h 8, 10 strisce per lastra; assente in bagno)

Il piatto doccia non viene pavimentato: toglie 1,25 mq di posa ma NON riduce le
lastre, perche' con 80 cm di profondita' non copre mai una piastrella intera.
"""

import contextlib
import io
import math

with contextlib.redirect_stdout(io.StringIO()):
    import casa_pianta as cp
    import bagno_rivestimento as br
    import battiscopa as bs

PIASTRELLA = cp.PIASTRELLA
LASTRA = cp.LASTRA

CALPESTABILE = cp.AREA_TOT
PIATTO_DOCCIA = 1.34

# tutte le voci arrivano dagli script che le calcolano: cambiando formato in
# casa_pianta.FORMATI questo computo si aggiorna da solo
_pav = cp.OTTIMO["tot"]
_batt = math.ceil(bs.ml / (10 * cp.LATO_MAX / 100))    # h 8, 10 strisce per lastra

# voce: (superficie netta, lastre con riuso, lastre senza riuso)
GRES = {
    "Pavimento (netto del piatto doccia)":
        (cp.AREA_TOT - PIATTO_DOCCIA, _pav["lastre"], _pav["intere"] + _pav["tagli"]),
    f"Rivestimento bagno in {cp.NOME_RIV} ({br.CORSI} corsi)":
        br.tot["pavimento"],
    f"Battiscopa h 8 ({bs.ml:.1f} ml)": (_batt * LASTRA, _batt, _batt),
}
DEDICATA = {f"Rivestimento bagno, piastrella dedicata ({br.CORSI} corsi)":
            br.tot["proprio"]}

PREVENTIVO = {"gres 90x90": 105.3, "dedicata": 32.4}


def blocco(titolo, voci, preventivo):
    print(f"\n{titolo}")
    print(f"{'  voce':52}{'netto':>9}{'lastre':>8}{'mq':>8}{'lastre':>8}{'mq':>8}")
    print(f"{'':52}{'':9}{'CON RIUSO':>16}{'SENZA RIUSO':>16}")
    print("  " + "-" * 91)
    smq = sc = ss = 0
    for nome, (mq, c, s) in voci.items():
        smq += mq
        sc += c
        ss += s
        print(f"  {nome:50}{mq:8.2f} {c:8d}{c*LASTRA:8.2f}{s:8d}{s*LASTRA:8.2f}")
    print("  " + "-" * 91)
    print(f"  {'TOTALE':50}{smq:8.2f} {sc:8d}{sc*LASTRA:8.2f}{ss:8d}{ss*LASTRA:8.2f}")
    p = preventivo / LASTRA
    print(f"  preventivo: {preventivo:.1f} mq = {p:.0f} lastre   "
          f"-> {p-sc:+.0f} lastre rispetto al caso migliore, {p-ss:+.0f} rispetto al peggiore")
    return smq, sc, ss


print(f"superficie calpestabile {CALPESTABILE:.2f} mq al grezzo")
a = blocco(f"GRES {cp.NOME_FORMATO} (pavimento + battiscopa + meta' rivestimento bagno)", GRES, PREVENTIVO["gres 90x90"])
b = blocco("PIASTRELLA DEDICATA (spalle lavabo + testata finestra)", DEDICATA, PREVENTIVO["dedicata"])

print(f"\nRIEPILOGO")
print(f"  superficie da rivestire   {a[0]+b[0]:.2f} mq")
print(f"  fabbisogno                {a[1]+b[1]} lastre ({(a[1]+b[1])*LASTRA:.1f} mq) con riuso, "
      f"{a[2]+b[2]} ({(a[2]+b[2])*LASTRA:.1f} mq) senza")
tot_prev = sum(PREVENTIVO.values())
print(f"  preventivo                {tot_prev:.1f} mq = {tot_prev/LASTRA:.0f} lastre")
print(f"  saldo                     {tot_prev/LASTRA-(a[1]+b[1]):+.0f} lastre nel caso migliore, "
      f"{tot_prev/LASTRA-(a[2]+b[2]):+.0f} nel peggiore")
