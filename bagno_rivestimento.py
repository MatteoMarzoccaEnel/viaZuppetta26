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

PIASTRELLA, FUGA = cp.PIASTRELLA_X, cp.FUGA
MODULO = cp.MODULO_X
LASTRA = cp.LASTRA
CORSI = cp.RIV_CORSI
# l'ultimo corso puo' essere tagliato in altezza (rivestimento a filo trave):
# consuma comunque una lastra per pezzo, ma la superficie e' quella vera
ALTEZZA = cp.H_RIV

# descrizione dei lati, nell'ordine del poligono del bagno in casa_pianta
LATI_BAGNO = {
    0: "parete sanitari (spalle lavabo/wc/bidet)",
    1: "testata doccia",
    2: "risvolto testata",
    3: "fronte colonna scarico",
    4: "risvolto colonna",
    5: "testata finestra",
    6: "parete lunga lato cameretta",
    7: "testata nicchia",
    8: "fianco nicchia",
    9: "parete porta",
}
# pareti con la piastrella dedicata: sono quelle che si vedono dai sanitari,
# cioe' il lato lungo del lavabo e tutta la testata con la finestra
PROPRIO = {0, 1, 2, 3, 4, 5}


def _finestre(orizz, c, a, b):
    """Luce delle finestre sul tratto: come i vani a terra, non si riveste."""
    tot = 0.0
    for tipo, x0, y0, x1, y1, _lb in cp.APERTURE:
        if tipo != "finestra":
            continue
        ao = abs(y1 - y0) < abs(x1 - x0)
        if ao != orizz or abs((y0 if ao else x0) - c) > 11:
            continue
        va, vb = (min(x0, x1), max(x0, x1)) if ao else (min(y0, y1), max(y0, y1))
        va, vb = max(va, a), min(vb, b)
        if vb - va > 0.5:
            tot += vb - va
    return tot


def _sviluppi():
    """(gruppo, descrizione, sviluppo) per ogni lato del bagno, al netto dei vani.

    Lunghezze e vani vengono dalla pianta: spostare un muro o una porta si
    riflette qui senza ritoccare nessun numero.
    """
    out = []
    for i, (orizz, c, a, b, _dentro) in enumerate(cp.lati(cp.LOCALI["BAGNO"]["poly"])):
        vani = cp.vani_sul_filo(orizz, c, a, b)
        L = (b - a) - sum(q - p for p, q in vani) - _finestre(orizz, c, a, b)
        if L <= 0.5:
            continue
        out.append(("proprio" if i in PROPRIO else "pavimento",
                    LATI_BAGNO.get(i, f"lato {i}"), L))
    return out


# (gruppo, descrizione, sviluppo in cm) - gia' al netto di porta e finestra
PARETI = _sviluppi()


def _nascosta():
    """mq di parete coperti dalle alzatine (nicchia e gradino): non si rivestono."""
    out = {"proprio": 0.0, "pavimento": 0.0}
    alz = [(x, y, w, h, cp.altezza(lb, tp)[0]) for lo, lb, x, y, w, h, tp in cp.ARREDO
           if lo == "BAGNO" and tp == "muretto"]
    for i, (orizz, c, a, b, _dentro) in enumerate(cp.lati(cp.LOCALI["BAGNO"]["poly"])):
        for x, y, w, h, alt in alz:
            lo, hi, p0, p1 = (y, y + h, x, x + w) if orizz else (x, x + w, y, y + h)
            if min(abs(lo - c), abs(hi - c)) < 1.5:
                out["proprio" if i in PROPRIO else "pavimento"] += \
                    max(0.0, min(b, p1) - max(a, p0)) * min(alt, cp.H_RIV) / 10000
    return out


NASCOSTA = _nascosta()


def calcola():
    """Conteggio per gruppo, con il formato attivo in casa_pianta."""
    P, F, C, H = cp.RIV_X, cp.FUGA, cp.RIV_CORSI, cp.H_RIV
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
        out[g] = dict(pareti=pareti, sviluppo=sviluppo, sup=sviluppo * H / 10000 - NASCOSTA[g],
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
                  ("pavimento", f"STESSO GRES {cp.NOME_RIV} DEL PAVIMENTO")):
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
