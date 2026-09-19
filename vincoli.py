"""Vincoli tecnici del progetto: cio' che NON puo' cambiare per caso.

La pianta (casa_pianta.py) e' la base di tutto: il modello 3D, il computo e gli
script parametrici leggono da li'. Questo modulo chiude il cerchio verificando,
a ogni import della pianta, che i dati immutabili siano ancora quelli e che le
regole tecniche siano rispettate:

  1. PERIMETRO           sagoma esterna e ingombro dell'appartamento
  2. STRUTTURA           pilastri e travi in c.a. (posizione e sezione)
  3. MURI ESISTENTI      tutte le murature bianche non demolite
  4. PORTE A SCOMPARSA   tasca piena (anta + battuta + guide), senza
                         sovrapposizioni e senza interferenze con struttura
  5. SPESSORI            muro sufficiente per il controtelaio e per gli incassi
  6. BATTISCOPA          percorso continuo, interrotto solo dai vani a terra

I primi tre sono bloccati da una FIRMA (hash dei dati): non e' un divieto di
modifica, e' un divieto di modifica *silenziosa*. Se un rilievo piu' accurato
cambia una quota, si aggiorna il dato e poi la firma con:

    python vincoli.py --firme

che stampa le nuove firme da incollare qui sotto: la modifica resta cosi'
esplicita, tracciabile nel diff e consapevole.

Esecuzione:  python vincoli.py        (esegue e riporta l'esito)
"""

import hashlib
import json
import os

# =====================================================================
# REGOLE TECNICHE
# =====================================================================

SP_CONTROTELAIO = 10.0   # spessore minimo del muro che ospita una scomparsa
SP_INCASSO = 14.0        # muro doppio con scarichi a incasso (bagno / camera)
GIOCO_TASCA = 5.0        # battuta, stipite e guide oltre la luce dell'anta
H_CONTROTELAIO = 7.0     # traverso del controtelaio sopra la luce della porta
SPALLETTA_MIN = 10.0     # muro che deve restare fra il vano e lo spigolo
MARGINE_TASCA = 0.1      # tolleranza di confronto, in cm

# muri che devono ospitare un incasso impiantistico: (locale A, locale B, spessore)
INCASSI = [("BAGNO", "LETTO MATRIMONIALE", SP_INCASSO)]

# ingombro esterno dei locali nel sistema di rilievo: (x min, y min, x max, y max)
PERIMETRO = (0.0, -59.0, 1471.0, 697.0)

# firme dei dati immutabili (vedi --firme)
FIRME = {
    "muri_esistenti": "698afb97395b6729",
    "pilastri": "788252a2eadcc581",
    "travi": "7c5edfc530ae127c",
}


class VincoloViolato(Exception):
    """Un dato immutabile e' cambiato, o una regola tecnica non e' rispettata."""


# =====================================================================
# ESTRAZIONE DEI DATI DA VERIFICARE
# =====================================================================


def segmenti(cp):
    """Tutti i tratti di muro dedotti dai locali, nel sistema di rilievo.

    Restituisce (asse, quota, da, a, locale): asse "x" = tratto verticale.
    """
    out = []
    for nome, poly in cp.LOCALI_RILIEVO.items():
        for i in range(len(poly)):
            p, q = poly[i], poly[(i + 1) % len(poly)]
            if abs(p[1] - q[1]) < 0.1:
                s = ("y", p[1], min(p[0], q[0]), max(p[0], q[0]))
            else:
                s = ("x", p[0], min(p[1], q[1]), max(p[1], q[1]))
            out.append((s[0], round(s[1], 1), round(s[2], 1), round(s[3], 1), nome))
    return sorted(out)


def e_nuovo(cp, asse, quota):
    """Il tratto appartiene a un muro di progetto (verde), quindi e' spostabile."""
    return any(a == asse and any(abs(quota - q) < 0.1 for q in quote)
               for a, quote, _lb in cp.MURI_NUOVI)


def muri_esistenti(cp):
    """I tratti di muratura esistente, con gli estremi che appoggiano su un muro
    di progetto sostituiti da 'M': spostare un muro verde accorcia i muri esistenti
    che ci arrivano contro, e non deve far scattare la firma."""
    out = []
    for asse, quota, da, a, nome in segmenti(cp):
        if e_nuovo(cp, asse, quota):
            continue
        span = "y" if asse == "x" else "x"
        out.append((asse, quota,
                    "M" if e_nuovo(cp, span, da) else da,
                    "M" if e_nuovo(cp, span, a) else a,
                    nome))
    return out


def _firma(dati):
    return hashlib.sha256(json.dumps(dati, sort_keys=True).encode()).hexdigest()[:16]


def firme(cp):
    return {
        "muri_esistenti": _firma(muri_esistenti(cp)),
        "pilastri": _firma(sorted(cp.PILASTRI)),
        "travi": _firma(sorted(cp.TRAVI)),
    }


# =====================================================================
# CONTROLLI
# =====================================================================


def _controlla_firme(cp, errori):
    attuali = firme(cp)
    for k, atteso in FIRME.items():
        if not atteso:
            # stato iniziale: le firme si generano con --firme, quindi qui non blocca
            continue
        if attuali[k] != atteso:
            errori.append(
                f"dato immutabile '{k}' modificato (firma {attuali[k]}, attesa {atteso}). "
                f"Se la modifica deriva da un rilievo piu' accurato, aggiornare FIRME "
                f"in vincoli.py con  python vincoli.py --firme")


def _controlla_perimetro(cp, errori):
    xs = [p[0] for poly in cp.LOCALI_RILIEVO.values() for p in poly]
    ys = [p[1] for poly in cp.LOCALI_RILIEVO.values() for p in poly]
    att = (min(xs), min(ys), max(xs), max(ys))
    if any(abs(a - b) > 0.1 for a, b in zip(att, PERIMETRO)):
        errori.append(f"perimetro cambiato: {tuple(round(v, 1) for v in att)} "
                      f"invece di {PERIMETRO}")


def _controlla_struttura(cp, errori):
    if cp.H_TRAVE >= cp.H_INT:
        errori.append(f"trave h={cp.H_TRAVE} non compatibile con altezza interna {cp.H_INT}")
    for x0, y0, x1, y1, lb in cp.TRAVI:
        larg = min(x1 - x0, y1 - y0)
        if not (20 <= larg <= 40):
            errori.append(f"trave {lb}: larghezza {larg:.0f} cm fuori dal plausibile (20-40)")
    # il perimetro e' in coordinate di rilievo, i pilastri in coordinate di disegno
    px0, py0, px1, py1 = PERIMETRO
    for x0, y0, x1, y1, lb in cp.PILASTRI:
        if x1 <= x0 or y1 <= y0:
            errori.append(f"pilastro {lb}: rettangolo degenere")
        ry0, ry1 = cp.RY - y1, cp.RY - y0
        if x0 < px0 - 0.1 or x1 > px1 + 0.1 or ry0 < py0 - 30.1 or ry1 > py1 + 30.1:
            errori.append(f"pilastro {lb} fuori dal perimetro dell'edificio")


def spessore_apertura(cp, orizz, c, va, vb):
    """Spessore del muro che ospita l'apertura: distanza fra le due facce.

    Non serve il nome del locale: si cercano il filo piu' vicino da una parte e
    quello piu' vicino dall'altra, sulla stessa retta del vano.
    """
    m = (va + vb) / 2
    giu = su = None
    for d in cp.LOCALI.values():
        p = d["poly"]
        for i in range(len(p)):
            r, s = p[i], p[(i + 1) % len(p)]
            if (abs(r[1] - s[1]) < 0.1) != orizz:
                continue
            c2 = r[1] if orizz else r[0]
            a2, b2 = (min(r[0], s[0]), max(r[0], s[0])) if orizz \
                else (min(r[1], s[1]), max(r[1], s[1]))
            if not (a2 - 0.5 <= m <= b2 + 0.5) or abs(c2 - c) > 40:
                continue
            if c2 <= c + 0.1 and (giu is None or c2 > giu):
                giu = c2
            if c2 >= c - 0.1 and (su is None or c2 < su):
                su = c2
    if giu is None or su is None or su - giu < 1:
        return cp.SP_EST
    return su - giu


def _interferenza(orizz, c, t0, t1, rects):
    """Un ostacolo attraversato dalla tasca, fra i rettangoli dati."""
    for x0, y0, x1, y1, lb in rects:
        if orizz:
            if y0 - 0.1 < c < y1 + 0.1 and min(t1, x1) - max(t0, x0) > 1.0:
                return lb
        else:
            if x0 - 0.1 < c < x1 + 0.1 and min(t1, y1) - max(t0, y0) > 1.0:
                return lb
    return None


def _controlla_porte(cp, errori):
    minima = cp.ANTA + GIOCO_TASCA
    if cp.TASCA < minima - MARGINE_TASCA:
        errori.append(f"TASCA={cp.TASCA} insufficiente: servono {minima} cm "
                      f"(anta {cp.ANTA} + battuta/guide {GIOCO_TASCA})")
    per_filo = {}
    for k, (tipo, x0, y0, x1, y1, lb) in enumerate(cp.APERTURE, 1):
        if tipo not in ("porta", "passaggio") or k in cp.PIEGHEVOLI:
            continue
        if k not in cp.TASCHE:
            errori.append(f"apertura {k} ({lb}): nessuna tasca calcolata")
            continue
        orizz = abs(y1 - y0) < abs(x1 - x0)
        c = y0 if orizz else x0
        t0, t1 = cp.TASCHE[k]
        if t1 - t0 < minima - MARGINE_TASCA:
            errori.append(f"apertura {k} ({lb}): tasca di {t1 - t0:.1f} cm, "
                          f"ne servono {minima:.0f}")
        amin, amax = cp._estensione(c, orizz)
        if t0 < amin - MARGINE_TASCA or t1 > amax + MARGINE_TASCA:
            errori.append(f"apertura {k} ({lb}): tasca {t0:.0f}..{t1:.0f} fuori dal muro "
                          f"({amin:.0f}..{amax:.0f})")
        sp = spessore_apertura(cp, orizz, c, min(x0, x1), max(x0, x1))
        if sp < SP_CONTROTELAIO - MARGINE_TASCA:
            errori.append(f"apertura {k} ({lb}): muro da {sp:.0f} cm, il controtelaio "
                          f"a scomparsa ne richiede {SP_CONTROTELAIO:.0f}")
        ost = _interferenza(orizz, c, t0, t1, cp.PILASTRI)
        if ost:
            errori.append(f"apertura {k} ({lb}): la tasca attraversa il pilastro {ost}")
        trave = _interferenza(orizz, c, t0, t1, cp.TRAVI)
        if trave and cp.ALT_VANO[tipo] + H_CONTROTELAIO > cp.H_TRAVE:
            errori.append(f"apertura {k} ({lb}): sotto {trave} (intradosso {cp.H_TRAVE:.0f}) "
                          f"non c'e' posto per il controtelaio "
                          f"({cp.ALT_VANO[tipo]:.0f}+{H_CONTROTELAIO:.0f} cm)")
        for k2, (c2, u0, u1, lb2) in per_filo.items():
            if abs(c2 - c) < 15 and min(t1, u1) - max(t0, u0) > MARGINE_TASCA:
                errori.append(f"aperture {k2} ({lb2}) e {k} ({lb}): tasche sovrapposte")
        per_filo[k] = (c, t0, t1, lb)


def _controlla_incassi(cp, errori):
    for a, b, sp_min in INCASSI:
        pa, pb = cp.LOCALI[a]["poly"], cp.LOCALI[b]["poly"]
        trovato = 0.0
        for i in range(len(pa)):
            r, s = pa[i], pa[(i + 1) % len(pa)]
            orizz = abs(r[1] - s[1]) < 0.1
            c = r[1] if orizz else r[0]
            for j in range(len(pb)):
                u, v = pb[j], pb[(j + 1) % len(pb)]
                if (abs(u[1] - v[1]) < 0.1) != orizz:
                    continue
                c2 = u[1] if orizz else u[0]
                i0 = max(min(r[0], s[0]), min(u[0], v[0])) if orizz \
                    else max(min(r[1], s[1]), min(u[1], v[1]))
                i1 = min(max(r[0], s[0]), max(u[0], v[0])) if orizz \
                    else min(max(r[1], s[1]), max(u[1], v[1]))
                if i1 - i0 > 1.0 and 1 < abs(c2 - c) < 40:
                    trovato = max(trovato, abs(c2 - c))
        if trovato < sp_min - MARGINE_TASCA:
            errori.append(f"muro {a}/{b}: {trovato:.0f} cm, l'incasso ne richiede {sp_min:.0f}")


def _controlla_battiscopa(cp, errori):
    """Ogni lato deve essere coperto per intero da battiscopa piu' vani: nessun buco.

    Cosi' i tratti risultano contigui fra loro e il percorso va senza interruzioni
    da un vano al successivo. Il bagno e' escluso: ha il rivestimento a parete.
    """
    for nome, tratti in cp.BATTISCOPA.items():
        per_lato = {}
        for sa, sb, c, orizz, dentro, i in tratti:
            per_lato.setdefault(i, []).append((sa, sb))
        for i, (orizz, c, a, b, dentro) in enumerate(cp.lati(cp.LOCALI[nome]["poly"])):
            pezzi = sorted(per_lato.get(i, []))
            for (p0, p1), (q0, q1) in zip(pezzi, pezzi[1:]):
                if q0 < p1 - MARGINE_TASCA:
                    errori.append(f"battiscopa {nome} lato {i}: tratti sovrapposti "
                                  f"{p0:.0f}-{p1:.0f} e {q0:.0f}-{q1:.0f}")
            vani = cp.vani_sul_filo(orizz, c, a, b)
            coperto = sum(q - p for p, q in pezzi) + sum(q - p for p, q in vani)
            if abs(coperto - (b - a)) > 1.0:
                mancante = b - a - coperto
                errori.append(f"battiscopa {nome} lato {i} ({a:.0f}-{b:.0f}): "
                              f"{mancante:.0f} cm non coperti ne' da battiscopa ne' da vani")


def _controlla_spallette(cp, errori):
    """Fra il vano e lo spigolo del muro deve restare della muratura.

    Senza questo un'apertura puo' finire a filo dell'angolo: lo stipite non ha
    su cosa appoggiare e la porta non ci sta tutta. Vale per i vani di passaggio:
    le portefinestre si attestano contro parapetti e spalle di balcone.
    """
    for k, (tipo, x0, y0, x1, y1, lb) in enumerate(cp.APERTURE, 1):
        if tipo not in ("porta", "passaggio", "battente"):
            continue
        orizz = abs(y1 - y0) < abs(x1 - x0)
        c = y0 if orizz else x0
        va, vb = (min(x0, x1), max(x0, x1)) if orizz else (min(y0, y1), max(y0, y1))
        amin, amax = cp._estensione(c, orizz)
        if amin > 1e8:
            continue
        for lato, gioco in (("inizio", va - amin), ("fine", amax - vb)):
            if gioco < SPALLETTA_MIN - MARGINE_TASCA:
                errori.append(
                    f"apertura {k} ({lb}): {gioco:.0f} cm di spalletta a {lato} del vano, "
                    f"ne servono {SPALLETTA_MIN:.0f}")


CONTROLLI = (_controlla_firme, _controlla_perimetro, _controlla_struttura,
             _controlla_porte, _controlla_incassi, _controlla_battiscopa,
             _controlla_spallette)


def verifica(cp, alza=True):
    """Esegue tutti i controlli sulla pianta. Restituisce la lista degli errori."""
    errori = []
    for c in CONTROLLI:
        c(cp, errori)
    # con le firme da rigenerare l'import deve poter arrivare in fondo lo stesso
    if errori and alza and os.environ.get("VINCOLI_BYPASS") != "1":
        raise VincoloViolato("vincoli non rispettati:\n  - " + "\n  - ".join(errori))
    return errori


if __name__ == "__main__":
    import contextlib
    import io
    import sys

    if "--firme" in sys.argv:
        os.environ["VINCOLI_BYPASS"] = "1"
    with contextlib.redirect_stdout(io.StringIO()):
        import casa_pianta as cp

    if "--firme" in sys.argv:
        print("FIRME = {")
        for k, v in firme(cp).items():
            print(f'    "{k}": "{v}",')
        print("}")
    else:
        err = verifica(cp, alza=False)
        for e in err:
            print("VIOLATO:", e)
        print(f"\n{len(CONTROLLI)} controlli eseguiti, {len(err)} violazioni.")
