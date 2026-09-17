"""Computo del rivestimento del bagno, diviso per tipo di piastrella.

Il bagno e' rivestito con due prodotti:
  PROPRIO    piastrella dedicata: parete dei sanitari (spalle lavabo) e testata
             con la finestra, compresi i risvolti
  PAVIMENTO  stesso gres 90x90 del pavimento, sulle pareti restanti

Conteggio lastra per lastra, con accoppiamento dei tagli sulla stessa lastra
(first-fit decreasing sulla larghezza). Il numero di corsi da 90 e' quello di
casa_pianta.RIV_CORSI; fuga 1,5 mm.
Nel bagno non c'e' battiscopa.
"""

import contextlib
import io

with contextlib.redirect_stdout(io.StringIO()):
    import casa_pianta as cp

PIASTRELLA, FUGA = cp.PIASTRELLA, cp.FUGA
MODULO = PIASTRELLA + FUGA
LASTRA = cp.LASTRA
CORSI = cp.RIV_CORSI
# l'ultimo corso puo' essere tagliato in altezza (rivestimento a filo trave):
# consuma comunque una lastra per pezzo, ma la superficie e' quella vera
ALTEZZA = cp.H_RIV

# (gruppo, descrizione, sviluppo in cm) - gia' al netto di porta e finestra
PARETI = [
    ("proprio", "parete sanitari (spalle lavabo/wc/bidet)", 395),
    ("proprio", "testata finestra", 27),
    ("proprio", "risvolto testata", 27),
    ("proprio", "risvolto testata", 26),
    ("proprio", "fronte colonna scarico", 53),
    ("proprio", "risvolto colonna", 23),
    ("pavimento", "parete lunga lato cameretta", 302),
    ("pavimento", "testata nicchia", 75),
    ("pavimento", "fianco nicchia", 90),
    ("pavimento", "parete porta, tratto sx", 50),
    ("pavimento", "parete porta, tratto dx", 98),
]


def calcola():
    """Conteggio per gruppo, con il formato attivo in casa_pianta."""
    P, F, C, H = cp.PIASTRELLA, cp.FUGA, cp.RIV_CORSI, cp.H_RIV
    M = P + F
    out = {}
    for g in ("proprio", "pavimento"):
        pareti = [p for p in PARETI if p[0] == g]
        intere, tagli = 0, []
        for _, _, L in pareti:
            n = int(L // M)
            resto = L - n * M
            if resto >= P - 1:
                n, resto = n + 1, 0.0
            intere += n * C
            if resto > 0.5:
                tagli += [resto] * C
        # i pezzi tagliati si accoppiano sulla stessa lastra (first-fit decreasing)
        lastre_tagli = []
        for t in sorted(tagli, reverse=True):
            for i, r in enumerate(lastre_tagli):
                if r + t + F <= P:
                    lastre_tagli[i] = r + t + F
                    break
            else:
                lastre_tagli.append(t)
        sviluppo = sum(L for _, _, L in pareti)
        out[g] = dict(pareti=pareti, sviluppo=sviluppo, sup=sviluppo * H / 10000,
                      intere=intere, tagli=len(tagli), accoppiate=len(lastre_tagli),
                      lastre_riuso=intere + len(lastre_tagli),
                      lastre_senza=intere + len(tagli))
    return out


DETT = calcola()
tot = {g: (d["sup"], d["lastre_riuso"], d["lastre_senza"]) for g, d in DETT.items()}

if __name__ == "__main__":
    _tagliato = " (ultimo corso tagliato)" if cp.FORMATO.get("riv_h") else ""
    print(f"altezza rivestita {ALTEZZA:.1f} cm ({CORSI} corsi da {PIASTRELLA:.0f}, "
          f"fuga {FUGA*10:.1f} mm){_tagliato}\n")
    for g, et in (("proprio", "PIASTRELLA DEDICATA (spalle lavabo + testata finestra)"),
                  ("pavimento", f"STESSO GRES {PIASTRELLA:.0f}x{PIASTRELLA:.0f} DEL PAVIMENTO")):
        d = DETT[g]
        print(f"{et}")
        print(f"  sviluppo          {d['sviluppo']/100:.2f} m")
        print(f"  superficie        {d['sup']:.2f} mq")
        print(f"  lastre intere     {d['intere']}")
        print(f"  pezzi tagliati    {d['tagli']}  -> {d['accoppiate']} lastre con accoppiamento")
        print(f"  LASTRE            {d['lastre_riuso']} con riuso, {d['lastre_senza']} senza")
        print(f"                    = {d['lastre_riuso']*LASTRA:.2f} / "
              f"{d['lastre_senza']*LASTRA:.2f} mq\n")
    s = sum(v[0] for v in tot.values())
    print(f"totale rivestimento {s:.2f} mq  "
          f"({tot['proprio'][0]/s*100:.0f}% dedicata, {tot['pavimento'][0]/s*100:.0f}% dal pavimento)")
