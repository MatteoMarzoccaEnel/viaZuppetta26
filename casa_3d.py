"""Genera casa_3d.html: passeggiata in prima persona dentro l'appartamento.

La geometria e' quella di casa_pianta.py (stessi locali, aperture, arredo e
stessa origine della griglia di posa), quindi le fughe in 3D cadono esattamente
dove le calcola il computo.

Comandi: W/S avanti-indietro seguendo lo sguardo (si sale e si scende guardando
in alto o in basso, come in modalita' ghost), A/D laterale, frecce per muoversi
sul piano orizzontale, mouse per guardare, E apre/chiude la porta
piu' vicina, Q mostra/nasconde le quote, Shift corri.
Texture del pavimento: salvare l'immagine della lastra come piastrella.png
accanto all'html (in mancanza viene generata una texture di ripiego).
"""

import base64
import contextlib
import io
import json
import re

with contextlib.redirect_stdout(io.StringIO()):
    import casa_pianta as cp

OUT = r"c:\WORK\GH\casa_3d.html"
H_INT = cp.H_INT
H_BATT = cp.H_BATT
H_RIV = cp.H_RIV                            # rivestimento bagno
BALC_P = cp.H_RING

OX, OY = cp.VARIANTI["A"]["o"]

COL = {
    "letto": "#c9c2b6", "divano": "#8d99a6", "cucina": "#ececec",
    "elettro": "#c3c9cf", "lavello": "#dbe0e5", "fuochi": "#3a3a3a",
    "doccia": "#e6eef4", "wc": "#fbfbfb", "appendi": "#b8b0a4",
    "box": "#d9d4cb", "cassetti": "#cfc7ba", "scaffale": "#cbbfa8",
    "mensola": "#cbbfa8", "mensola2": "#cbbfa8", "specchio": "#dfe7ea",
    "kit": "#9aa3ab", "elettro2": "#c3c9cf", "muretto": "#f0ece6",
}

VANI = {t: ((cp.DAVANZALE, cp.DAVANZALE + h) if t == "finestra" else (0, h))
        for t, h in cp.ALT_VANO.items()}

BALCONI = cp.BALCONI
BALCONI_VICINO = cp.BALCONI_VICINO
SEPARE = cp.SEPARE

ANTE_N = {8: 2, 9: 2, 10: 2, 11: 2}     # infissi a due ante
CARDINI = {12: 0}           # lato del perno: 1 = coordinata maggiore, 0 = minore
SP_ANTA = 5.0               # spessore dell'anta, telaio PVC compreso
FIN_APRIBILI = {7, 11}      # finestre apribili (le altre sono fisse)
PIEGHEVOLI = {2}            # porte a libro (due ante a fisarmonica)
OFF_QUOTA = 3.0             # rientro della quota dal filo del muro
QUOTE_TRASVERSALI = {"DISIMPEGNO"}   # larghezza misurata tratto per tratto
COL_RING = "#2f4f3a"


def incorpora(path, lato=1024, q=90):
    """Immagine come data URI: da file:// il browser non puo' usarne una locale."""
    try:
        from PIL import Image
        im = Image.open(path).convert("RGB")
    except Exception:
        return None
    if max(im.size) > lato:
        im = im.resize((lato, lato), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=q)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


BASE_DIR = r"c:\WORK\GH" + "\\"


# spessori, bordi e sottrazione dei vani vengono dalla pianta: nessuna geometria
# duplicata qui
spessore = cp.spessore
bordi = cp.bordi
seg_meno = cp.seg_meno


pavimento, muri, vetri, ante, mobili, riv, batt, quote = [], [], [], [], [], [], [], []
etichette, aree, pareti_bagno, muretti = [], [], [], []
fatte, soglie = set(), set()

for nome, d in cp.LOCALI.items():
    for r in d["rect"]:
        pavimento.append(list(r))

    poly = d["poly"]
    for i in range(len(poly)):
        p, q = poly[i], poly[(i + 1) % len(poly)]
        orizz = abs(p[1] - q[1]) < 0.1
        c = p[1] if orizz else p[0]
        a, b = (min(p[0], q[0]), max(p[0], q[0])) if orizz else (min(p[1], q[1]), max(p[1], q[1]))
        dentro = (1 if q[0] > p[0] else -1) if orizz else (-1 if q[1] > p[1] else 1)

        def murata(sa, sb):
            s = spessore(nome, c, orizz, sa, sb)
            return s, c - dentro * s / 2

        brd = bordi(nome, c, orizz)
        vani, finestre = [], []
        for k, (tipo, ax0, ay0, ax1, ay1, lb) in enumerate(cp.APERTURE):
            ao = abs(ay1 - ay0) < abs(ax1 - ax0)
            if ao != orizz:
                continue
            if abs((ay0 if ao else ax0) - c) > 11:
                continue
            va, vb = (min(ax0, ax1), max(ax0, ax1)) if ao else (min(ay0, ay1), max(ay0, ay1))
            if vb <= a or va >= b:
                continue
            z0, z1 = VANI[tipo]
            va, vb = max(va, a), min(vb, b)
            sp, cc = murata(va, vb)
            # l'anta a battente e' a filo interno: in mezzeria ruoterebbe dentro la muratura
            ci = c - dentro * SP_ANTA / 2
            vani.append((va, vb))
            if z0 < 1:
                if k not in soglie:
                    # il pavimento prosegue sotto la porta, per tutto lo spessore del muro
                    soglie.add(k)
                    e0 = c + dentro * cp.FINITURA
                    e1 = c - dentro * (sp + cp.FINITURA)
                    lo, hi = min(e0, e1), max(e0, e1)
                    pavimento.append([va, lo, vb, hi] if orizz else [lo, va, hi, vb])
            else:
                finestre.append((va, vb, z0, z1))
            if z1 < H_INT:
                muri.append([va, vb, cc, orizz, z1, H_INT, sp])
            if z0 > 0:
                muri.append([va, vb, cc, orizz, 0, z0, sp])
            if k in fatte:
                continue
            fatte.add(k)
            n = k + 1
            # l'anta e' da 80: il resto del vano murario diventa spalletta
            la, lb = va, vb
            if tipo in ("porta", "passaggio") and (vb - va) > cp.ANTA + 1:
                m = (vb - va - cp.ANTA) / 2
                la, lb = va + m, vb - m
                muri.append([va, la, cc, orizz, 0, z1, sp])
                muri.append([lb, vb, cc, orizz, 0, z1, sp])
            apribile = tipo == "portafinestra" or (tipo == "finestra" and n in FIN_APRIBILI)
            if apribile:
                if ANTE_N.get(n, 1) == 2:
                    mid = (va + vb) / 2
                    ante.append([va, mid, ci, orizz, z0, z1, "pf", dentro, 1, n, 0, sp])
                    ante.append([mid, vb, ci, orizz, z0, z1, "pf", dentro, 1, 0, 1, sp])
                else:
                    ante.append([va, vb, ci, orizz, z0, z1, "pf", dentro, 1, n,
                                 CARDINI.get(n, 1), sp])
            elif tipo == "finestra":
                vetri.append([va, vb, cc, orizz, z0, z1, n])
            elif tipo == "passaggio":
                ante.append([la, lb, cc, orizz, z0, z1, "porta", dentro, cp.VERSI[n],
                             n, 1, sp])
            elif n in PIEGHEVOLI:
                ante.append([la, lb, ci, orizz, z0, z1, "fisar", dentro, 1, n, 0, sp])
            else:
                # la scomparsa e' centrata nel muro: scorre dentro la muratura
                cp_ = cc if tipo == "porta" else ci
                ante.append([la, lb, cp_, orizz, z0, z1, tipo, dentro, cp.VERSI.get(n, 1),
                             n, CARDINI.get(n, 1), sp])
        for sa, sb in seg_meno(a, b, vani):
            tagli = [sa] + [t for t in brd if sa + 0.5 < t < sb - 0.5] + [sb]
            for ta, tb in zip(tagli, tagli[1:]):
                s, cs = murata(ta, tb)
                muri.append([ta, tb, cs, orizz, 0, H_INT, s])

        faccia = c + dentro * 0.6
        if nome == "BAGNO":
            # meta' rivestimento dedicato (sanitari + testata finestra), meta' in 90x90
            prop = (not orizz and abs(c - 343) < 1) or (orizz and c <= 100) \
                or (not orizz and abs(c - 370) < 1) or (not orizz and abs(c - 423) < 1)
            g = 1 if prop else 0
            pareti_bagno.append((a, b, list(vani), list(finestre), faccia,
                                 orizz, dentro, g))

    x0, y0, x1, y1 = d["bb"]
    # una quota per lato, a filo del muro e rientrata di pochi cm dentro la stanza
    for orizz, c, a, b, dentro in cp.lati(d["poly"]):
        if b - a < 25:
            continue
        cq = c + dentro * OFF_QUOTA
        seg = [a, cq, b, cq] if orizz else [cq, a, cq, b]
        quote.append(seg + [f"{b - a:.0f}"])
    # dove la larghezza cambia (risalti e pilastri) serve una quota per ogni tratto
    if nome in QUOTE_TRASVERSALI:
        for rx0, ry0, rx1, ry1 in cp.rettangoli(d["poly"]):
            if rx1 - rx0 < 25 or ry1 - ry0 < 25:
                continue
            xq = (rx0 + rx1) / 2
            quote.append([xq, ry0 + OFF_QUOTA, xq, ry1 - OFF_QUOTA, f"{ry1 - ry0:.0f}"])
    etichette.append([(x0 + x1) / 2, (y0 + y1) / 2, 245, nome, "#0b4fa0"])
    aree.append([(x0 + x1) / 2, (y0 + y1) / 2, f"{d['area']:.2f} mq".replace(".", ",")])

# Fronte sul balcone: i muri generati locale per locale lasciano un vuoto in
# corrispondenza di ogni tramezzo, e i fili non coincidono (565 / 563 / 562 di
# rilievo). Una pelle continua sul filo piu' esterno chiude i buchi e rende la
# facciata piana, con i soli vani ritagliati.
# (orizzontale, quota del filo esterno, da, a, verso l'interno, spessore)
PELLI = [(True, 43.0, 0.0, 808.0, 1, 3.0)]

for orizz, c, a, b, dentro, sp in PELLI:
    cc = c - dentro * sp / 2
    vani = []
    for tipo, x0, y0, x1, y1, lb in cp.APERTURE:
        ao = abs(y1 - y0) < abs(x1 - x0)
        if ao != orizz:
            continue
        q = y0 if ao else x0
        if not (0 < (q - c) * dentro <= 45):      # apertura su questo fronte
            continue
        va, vb = (min(x0, x1), max(x0, x1)) if ao else (min(y0, y1), max(y0, y1))
        if vb <= a or va >= b:
            continue
        z0, z1 = VANI[tipo]
        vani.append((max(va, a), min(vb, b), z0, z1))
    for sa, sb in cp.seg_meno(a, b, [(v[0], v[1]) for v in vani]):
        muri.append([sa, sb, cc, orizz, 0, H_INT, sp])
    for va, vb, z0, z1 in vani:                   # fasce sotto e sopra il vano
        if z0 > 0:
            muri.append([va, vb, cc, orizz, 0, z0, sp])
        if z1 < H_INT:
            muri.append([va, vb, cc, orizz, z1, H_INT, sp])

for x, y, w, h, lb in cp.SETTI:
    muri.append([y, y + h, x + w / 2, False, 0, H_INT, w])

# il percorso del battiscopa lo calcola la pianta: vincoli.py ne verifica la contiguita'
for nome, tratti in cp.BATTISCOPA.items():
    for sa, sb, c, orizz, dentro, _lato in tratti:
        batt.append([sa, sb, c + dentro * 0.6, orizz, dentro])

for x0, y0, x1, y1, lb in cp.PILASTRI:
    muri.append([y0, y1, (x0 + x1) / 2, False, 0, H_INT, x1 - x0])
    etichette.append([(x0 + x1) / 2, (y0 + y1) / 2, H_INT + 16,
                      f"{lb} {x1-x0:.0f}x{y1-y0:.0f}", "#5d4037"])

for x0, y0, x1, y1, lb in cp.TRAVI:
    orizz = (x1 - x0) >= (y1 - y0)
    if orizz:
        muri.append([x0, x1, (y0 + y1) / 2, True, cp.H_TRAVE, H_INT, y1 - y0])
    else:
        muri.append([y0, y1, (x0 + x1) / 2, False, cp.H_TRAVE, H_INT, x1 - x0])
    etichette.append([(x0 + x1) / 2, (y0 + y1) / 2, cp.H_TRAVE - 14,
                      f"{lb.split()[0]} h {cp.H_TRAVE:.0f}", "#8e44ad"])

# un tramezzo e' generato da entrambi i locali che divide: due box identici sfarfallano
visti, unici = set(), []
for m in muri:
    k = tuple(round(v, 1) if isinstance(v, float) else v for v in m)
    if k not in visti:
        visti.add(k)
        unici.append(m)
muri[:] = unici

for i, (loc, label, x, y, w, h, tipo) in enumerate(cp.ARREDO):
    if tipo == "cucina":
        continue          # in pianta e' solo il profilo: in 3D ci sono i 5 moduli
    alt, base = cp.altezza(label, tipo)
    if tipo == "muretto":
        muretti.append([x, y, w, h, base, alt])
    else:
        mobili.append([x, y, w, h, base, alt, COL.get(tipo, COL["box"]), tipo])
    etichette.append([x + w / 2, y + h / 2, base + alt + 14,
                      cp.descrizione(i), "#0a6a3a"])

for k, (tipo, x0, y0, x1, y1, lb) in enumerate(cp.APERTURE, 1):
    lw = max(abs(x1 - x0), abs(y1 - y0))
    z0, z1 = VANI[tipo]
    fin = f"  {cp.PORTE_FINITURA}" if tipo in ("porta", "passaggio", "battente") else ""
    etichette.append([(x0 + x1) / 2, (y0 + y1) / 2, z1 + 22,
                      f"{k}: {lw:.0f}x{z1-z0:.0f}{fin}", "#b03020"])

def facce_riv(h_tot):
    """Le facce del rivestimento del bagno fino all'altezza data."""
    out = []
    for a, b, vani, finestre, faccia, orizz, dentro, g in pareti_bagno:
        for sa, sb in seg_meno(a, b, vani):   # tutte le aperture, anche le finestre
            out.append([sa, sb, faccia, orizz, dentro, g, 0, h_tot])
        for va, vb, z0, z1 in finestre:       # fasce sotto e sopra il vano
            if z0 > 1:
                out.append([va, vb, faccia, orizz, dentro, g, 0, min(z0, h_tot)])
            if z1 < h_tot - 1:
                out.append([va, vb, faccia, orizz, dentro, g, z1, h_tot])
    return out


# una configurazione di posa per ogni formato: origine della griglia, modulo e
# rivestimento cambiano insieme, quindi ognuna ha le sue facce e le sue statistiche
POSA = []
for _i, _f in enumerate(cp.FORMATI):
    cp.usa_formato(_i)
    _t = cp.VARIANTI["A"]["tot"]
    POSA.append(dict(
        nome=_f["nome"], piastrella=cp.PIASTRELLA, modulo=cp.MODULO, fuga=cp.FUGA,
        ox=cp.VARIANTI["A"]["o"][0], oy=cp.VARIANTI["A"]["o"][1],
        hriv=cp.H_RIV, corsi=cp.RIV_CORSI, riv=facce_riv(cp.H_RIV),
        texPav=incorpora(BASE_DIR + _f["tex_pav"]),
        texRiv=incorpora(BASE_DIR + _f["tex_riv"]),
        nota=f"{_t['lastre']} lastre, {_t['intere']} intere, "
             f"{_t['sliver']} listelli, sfrido {_t['sfrido']*100:.1f}%"))
cp.usa_formato(0)

DATI = dict(pavimento=pavimento, muri=muri, vetri=vetri, ante=ante, mobili=mobili,
            riv=riv, batt=batt, quote=quote, etichette=etichette, aree=aree,
            muretti=muretti, posa=POSA,
            balconi=BALCONI, box=cp.BOX, contro=cp.CONTROSOFFITTI,
            vicino=BALCONI_VICINO, separe=SEPARE, colring=COL_RING,
            h=H_INT, hbatt=H_BATT, hpar=BALC_P, spanta=SP_ANTA,
            colanta=cp.PORTE_COLORE, start=[1380, 655], guarda=0)

HTML = r"""<!DOCTYPE html>
<html lang="it"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
<title>Appartamento - visita 3D</title>
<style>
  html,body{margin:0;height:100%;overflow:hidden;background:#111;font-family:Arial,Helvetica,sans-serif}
  #hud{position:fixed;left:14px;bottom:14px;color:#fff;font-size:13px;line-height:1.6;
       background:rgba(0,0,0,.45);padding:8px 14px;border-radius:6px;pointer-events:none}
  #leg{position:fixed;right:14px;top:14px;color:#fff;font-size:13px;
       background:rgba(0,0,0,.55);padding:14px 18px 16px;border-radius:8px;pointer-events:none;
       min-width:250px}
  #leg h3{margin:0 0 10px;font-size:13px;letter-spacing:.14em;color:#ffd479}
  #posa{margin:0 0 12px;padding:7px 9px;border-radius:5px;background:rgba(255,212,121,.12);
        border-left:3px solid #ffd479}
  #posa b{display:block;font-size:13px;color:#ffd479;margin-bottom:2px}
  #posa span{color:#cfd8e0;font-size:11.5px;line-height:1.45}
  canvas{touch-action:none}
  /* comandi touch: nascosti su desktop, mostrati se il puntatore e' grosso */
  #touch{display:none;position:fixed;inset:0;pointer-events:none;z-index:5;
         font:600 14px system-ui,Segoe UI,Arial,sans-serif}
  #joy{position:absolute;left:20px;bottom:20px;width:128px;height:128px;border-radius:50%;
       background:rgba(255,255,255,.10);border:1px solid rgba(255,255,255,.28);
       pointer-events:auto;touch-action:none}
  #pomo{position:absolute;left:39px;top:39px;width:50px;height:50px;border-radius:50%;
        background:rgba(255,255,255,.42);box-shadow:0 2px 10px rgba(0,0,0,.4)}
  #bott{position:absolute;right:16px;bottom:20px;display:grid;gap:10px;
        grid-template-columns:56px 56px;pointer-events:auto}
  #bott button{width:56px;height:56px;border-radius:50%;color:#fff;font:600 14px system-ui;
        border:1px solid rgba(255,255,255,.3);background:rgba(0,0,0,.5);touch-action:none}
  #bott button:active{background:rgba(255,212,121,.35)}
  #leg .r{display:flex;align-items:center;gap:8px;margin:6px 0}
  #leg .k{flex:0 0 96px;display:flex;gap:4px}
  kbd{display:inline-block;min-width:15px;text-align:center;font:bold 11px Arial;
      background:#f2f2f2;color:#222;border-radius:4px;padding:3px 5px;
      box-shadow:0 2px 0 #999}
  #leg hr{border:0;border-top:1px solid rgba(255,255,255,.22);margin:11px 0 8px}
  #leg .n{color:#cfd8e0;font-size:12px;line-height:1.5}
  #msg{position:fixed;left:50%;top:62%;transform:translateX(-50%);color:#fff;font-size:15px;
       background:rgba(0,0,0,.55);padding:7px 14px;border-radius:5px;pointer-events:none;opacity:0;
       transition:opacity .15s}
  #start{position:fixed;inset:0;display:flex;align-items:center;justify-content:center;
         background:rgba(0,0,0,.72);color:#fff;cursor:pointer;text-align:center}
  #start div{max-width:480px;font-size:16px;line-height:1.7}
  b{font-size:22px}
</style></head><body>
<div id="hud"><span id="pos"></span></div>
<div id="leg">
  <h3>POSA</h3>
  <div id="posa"></div>
  <h3>COMANDI</h3>
  <div class="r"><span class="k"><kbd>W</kbd><kbd>S</kbd></span>avanti / indietro seguendo lo sguardo</div>
  <div class="r"><span class="k"><kbd>A</kbd><kbd>D</kbd></span>spostarsi di lato</div>
  <div class="r"><span class="k"><kbd>mouse</kbd></span>guardare intorno</div>
  <div class="r"><span class="k"><kbd>&#8592;</kbd><kbd>&#8593;</kbd><kbd>&#8595;</kbd><kbd>&#8594;</kbd></span>muoversi sul piano, a quota fissa</div>
  <div class="r"><span class="k"><kbd>Shift</kbd></span>correre</div>
  <div class="r"><span class="k"><kbd>E</kbd></span>apri / chiudi la porta vicina</div>
  <div class="r"><span class="k"><kbd>Q</kbd></span>quote dei locali</div>
  <div class="r"><span class="k"><kbd>O</kbd></span>ombre accese / spente</div>
  <div class="r"><span class="k"><kbd>L</kbd></span>occlusione ambientale (angoli)</div>
  <div class="r"><span class="k"><kbd>B</kbd></span>cambia formato e corsi del rivestimento</div>
  <div class="r"><span class="k"><kbd>H</kbd></span>mostra / nascondi legenda</div>
  <div class="r"><span class="k"><kbd>Esc</kbd></span>liberare il mouse</div>
  <hr>
  <div class="n">Sopra i 297 cm il soffitto diventa trasparente.<br>
  I numeri rossi identificano gli infissi.<br>
  Trascina qui un png per cambiare la texture.</div>
</div>
<div id="msg"></div>
<div id="touch">
  <div id="joy"><div id="pomo"></div></div>
  <div id="bott">
    <button data-k="KeyE">porta</button><button data-k="KeyQ">quote</button>
    <button data-k="KeyB">posa</button><button data-k="KeyH">menu</button>
  </div>
</div>
<div id="start"><div><b>Appartamento - visita 3D</b><br><br>
  Clicca per entrare.<br>W/S volano nella direzione dello sguardo, A/D e frecce si muovono sul piano.<br>
  <b style="font-size:16px">E</b> apre e chiude la porta vicina,
  <b style="font-size:16px">Q</b> mostra le quote.<br>
  Su telefono e tablet: tocca per entrare, joystick in basso a sinistra per
  muoverti, trascina sulla scena per guardarti attorno.<br>
  Salendo oltre il soffitto questo diventa trasparente.</div></div>
<script type="importmap">
{"imports":{"three":"https://unpkg.com/three@0.161.0/build/three.module.js",
 "three/addons/":"https://unpkg.com/three@0.161.0/examples/jsm/"}}
</script>
<script type="module">
import * as THREE from 'three';
import { PointerLockControls } from 'three/addons/controls/PointerLockControls.js';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { GTAOPass } from 'three/addons/postprocessing/GTAOPass.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';

const D = __DATI__, S = 0.01;
const SP_ANTA = D.spanta*S;

const scene = new THREE.Scene();
// Cartellini, badge e quote stanno in una scena a parte, disegnata dopo il
// post-processing: passando per il composer le loro texture trasparenti
// venivano riscritte come rettangoli neri.
const scenaOver = new THREE.Scene();
scene.background = new THREE.Color(0xbfd8ea);
const camera = new THREE.PerspectiveCamera(72, innerWidth/innerHeight, 0.08, 120);
const renderer = new THREE.WebGLRenderer({antialias:true});
renderer.setPixelRatio(Math.min(devicePixelRatio,1.5));
renderer.setSize(innerWidth, innerHeight);
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.05;
document.body.appendChild(renderer.domElement);

// Un solo canvas per tutte le scritte, convertito subito in immagine: tenendo
// vivi ~50 canvas il browser ne scarta il contenuto e alcune texture arrivano
// alla GPU completamente nere.
const CNV = document.createElement('canvas');
function texTesto(w, h, disegna){
  CNV.width = w; CNV.height = h;
  const k = CNV.getContext('2d');
  k.clearRect(0, 0, w, h);
  disegna(k);
  const img = new Image();
  const t = new THREE.Texture(img);
  t.colorSpace = THREE.SRGBColorSpace;
  t.generateMipmaps = false; t.minFilter = THREE.LinearFilter;
  img.onload = () => { t.needsUpdate = true; };
  img.src = CNV.toDataURL();
  return t;
}

// occlusione ambientale: senza, spigoli, angoli e battiscopa hanno la stessa
// luce delle superfici piane e spariscono. Calcolata a meta' risoluzione:
// e' un effetto a bassa frequenza, la differenza non si vede ma costa la meta'.
const AO_SCALA = 0.5;
const composer = new EffectComposer(renderer);
composer.addPass(new RenderPass(scene, camera));
const ao = new GTAOPass(scene, camera, innerWidth*AO_SCALA, innerHeight*AO_SCALA);
ao.output = GTAOPass.OUTPUT.Default;
ao.blendIntensity = 1.0;
ao.updateGtaoMaterial({radius: 0.6, distanceExponent: 1, thickness: 1,
  distanceFallOff: 1, scale: 2.0, samples: 8, screenSpaceRadius: false});
composer.addPass(ao);
composer.addPass(new OutputPass());

// luce: sole lontanissimo dal lato balconi (Z negativo), piu' cielo diffuso.
// L'ambiente PMREM sostituisce la luce ambientale piatta: pareti con
// orientamenti diversi ricevono luce diversa, quindi gli angoli si leggono.
const pmrem = new THREE.PMREMGenerator(renderer);
scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
scene.environmentIntensity = 0.85;
scene.add(new THREE.HemisphereLight(0xfff6e8, 0xdfe3e6, 0.75));
// rimbalzo del pavimento: alza pareti e soffitto, lascia il pavimento com'e'
scene.add(new THREE.HemisphereLight(0x000000, 0xfff3e2, 0.55));
const sole = new THREE.DirectionalLight(0xfff0d8, 3.6);
sole.position.set(30, 120, -260);
sole.target.position.set(7.3, 0, 2.8);
scene.add(sole.target);
sole.castShadow = true;
sole.shadow.mapSize.set(2048, 2048);
sole.shadow.autoUpdate = false;     // il sole non si muove: la shadow map si calcola una volta
const sc = sole.shadow.camera;
sc.left = -12; sc.right = 12; sc.top = 12; sc.bottom = -12;
sc.near = 150; sc.far = 400;
// bias troppo negativo produce chiazze sulle superfici ampie: normalBias e' piu' stabile
sole.shadow.bias = -0.00015;
sole.shadow.normalBias = 0.05;
scene.add(sole);

// ---------- texture del gres con la fuga reale ----------
function texGres(img, cfg){
  const N = 2048, g = Math.max(2, Math.round(N * cfg.fuga / cfg.modulo));
  const c = document.createElement('canvas'); c.width = c.height = N;
  const k = c.getContext('2d');
  k.fillStyle = '#cdcdc9'; k.fillRect(0,0,N,N);
  if (img) k.drawImage(img, g/2, g/2, N-g, N-g);
  else {
    const gr = k.createLinearGradient(0,0,N,N);
    gr.addColorStop(0,'#f7f7f5'); gr.addColorStop(.5,'#eceae7'); gr.addColorStop(1,'#f5f4f2');
    k.fillStyle = gr; k.fillRect(g/2,g/2,N-g,N-g);
    k.strokeStyle='rgba(165,165,165,.35)'; k.lineWidth=3;
    for(let i=0;i<26;i++){k.beginPath();
      k.moveTo(Math.random()*N,0);
      k.bezierCurveTo(Math.random()*N,N/3,Math.random()*N,2*N/3,Math.random()*N,N);
      k.stroke();}
  }
  const t = new THREE.CanvasTexture(c);
  t.wrapS = t.wrapT = THREE.RepeatWrapping;
  t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = renderer.capabilities.getMaxAnisotropy();
  return t;
}
// un gres per configurazione: formato, fuga e immagine della lastra cambiano insieme
const matPosa = D.posa.map(() => ({
  pav:  new THREE.MeshStandardMaterial({color:0xf3f2ef, roughness:0.26}),
  riv:  new THREE.MeshStandardMaterial({color:0xf3f2ef, roughness:0.22}),
  riv2: new THREE.MeshStandardMaterial({color:0xf3f2ef, roughness:0.22}),
}));

// le immagini sono incorporate come data URI: sono quindi same-origin e WebGL le accetta
function applica(i, imgPav, imgRiv){
  const m = matPosa[i], cfg = D.posa[i];
  m.pav.map  = texGres(imgPav, cfg);
  m.riv.map  = texGres(imgPav, cfg);            // meta' bagno e' lo stesso gres del pavimento
  m.riv2.map = texGres(imgRiv || imgPav, cfg);  // l'altra meta' e' la piastrella dedicata
  // la fuga disegnata nella texture diventa anche un rilievo: cosi' si vede il giunto
  for (const k of ['pav','riv','riv2']){
    m[k].bumpMap = m[k].map; m[k].bumpScale = 0.9; m[k].needsUpdate = true;
  }
}
function caricaSrc(src, cb){
  if (!src){ cb(null); return; }
  const im = new Image();
  im.onload = ()=>cb(im);
  im.onerror = ()=>cb(null);
  im.src = src;
}
D.posa.forEach((cfg, i) => caricaSrc(cfg.texPav, a => caricaSrc(cfg.texRiv, b => {
  applica(i, a, b);
  if (i === 0) dimmi(a ? 'texture incorporate: pavimento + rivestimento'
                       : 'texture procedurale');
})));
// aprendo l'html da file:// il browser puo' bloccare il png: si puo' trascinarlo qui
addEventListener('dragover', e=>e.preventDefault());
addEventListener('drop', e=>{
  e.preventDefault();
  const f = e.dataTransfer.files && e.dataTransfer.files[0];
  if (!f) return;
  const im = new Image();
  im.onload = ()=>{ applica(iPosa, im, null);
                    dimmi('texture caricata su ' + D.posa[iPosa].nome + ': ' + f.name); };
  im.src = URL.createObjectURL(f);
});

// ---------- pavimento e soffitto ----------
function superficie(rects, y, mat, giu, P, dove){
  P = P || D.posa[0];
  const pos=[], uv=[], nor=[], idx=[]; let n=0;
  for (const [x0,y0,x1,y1] of rects){
    for (const [x,z] of [[x0,y0],[x1,y0],[x1,y1],[x0,y1]]){
      pos.push(x*S, y*S, z*S); nor.push(0, giu?-1:1, 0);
      uv.push((x-P.ox)/P.modulo, (z-P.oy)/P.modulo);
    }
    if (giu) idx.push(n,n+1,n+2, n,n+2,n+3); else idx.push(n,n+2,n+1, n,n+3,n+2);
    n += 4;
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(pos,3));
  g.setAttribute('normal', new THREE.Float32BufferAttribute(nor,3));
  g.setAttribute('uv', new THREE.Float32BufferAttribute(uv,2));
  g.setIndex(idx);
  const m = new THREE.Mesh(g, mat); m.receiveShadow = true;
  (dove || scene).add(m); return m;
}
const matSoff = new THREE.MeshStandardMaterial({color:0xf4f2ed, roughness:1,
  emissive:0xfff4e4, emissiveIntensity:0.10,
  transparent:true, opacity:1, side:THREE.DoubleSide});
const soffitto = superficie(D.pavimento, D.h, matSoff, true);
soffitto.castShadow = true;   // senza questo la luce passerebbe e non si vedrebbero i raggi

// ---------- materiali ----------
// bianco di calce, leggermente caldo: il bianco puro appiattisce gli spigoli
const matMuro  = new THREE.MeshStandardMaterial({color:0xf1eee7, roughness:0.96});
const matPvc   = new THREE.MeshStandardMaterial({color:0xf4f3f0, roughness:0.35});
const matAnta  = new THREE.MeshStandardMaterial({color:0xffffff, roughness:0.45});
(function(){            // laminato bianco: venatura verticale e grana, non una tinta piatta
  const N=512, c=document.createElement('canvas'); c.width=c.height=N;
  const k=c.getContext('2d');
  k.fillStyle = D.colanta; k.fillRect(0,0,N,N);
  for(let i=0;i<240;i++){
    k.strokeStyle = Math.random()<0.5 ? 'rgba(255,255,255,.34)' : 'rgba(146,140,128,.10)';
    k.lineWidth = 0.5 + Math.random()*1.8;
    const x = Math.random()*N;
    k.beginPath(); k.moveTo(x, 0);
    k.bezierCurveTo(x+Math.random()*5-2.5, N/3, x+Math.random()*5-2.5, 2*N/3,
                    x+Math.random()*4-2, N);
    k.stroke();
  }
  for(let i=0;i<9000;i++){      // grana: rompe il riflesso uniforme della plastica
    k.fillStyle = Math.random()<0.5 ? 'rgba(255,255,255,.12)' : 'rgba(120,114,104,.07)';
    k.fillRect(Math.random()*N, Math.random()*N, 1, 1);
  }
  const t=new THREE.CanvasTexture(c);
  t.colorSpace=THREE.SRGBColorSpace; t.wrapS=t.wrapT=THREE.RepeatWrapping;
  t.anisotropy = renderer.capabilities.getMaxAnisotropy();
  matAnta.map=t; matAnta.bumpMap=t; matAnta.bumpScale=0.12; matAnta.needsUpdate=true;
})();
const matCls   = new THREE.MeshStandardMaterial({color:0xcfccc6, roughness:0.95});
// la trasmissione fisica rende il vetro quasi invisibile: meglio un azzurro traslucido
const matVetro = new THREE.MeshPhysicalMaterial({color:0x8fd0ea, roughness:0.05,
  metalness:0, transparent:true, opacity:0.34, side:THREE.DoubleSide,
  clearcoat:1, clearcoatRoughness:0.03});

function box(a,b,c,orizz,z0,z1,mat,spes){
  const L=(b-a)*S, alt=(z1-z0)*S, t=spes*S;
  if (L<=0||alt<=0) return null;
  const m = new THREE.Mesh(new THREE.BoxGeometry(orizz?L:t, alt, orizz?t:L), mat);
  m.position.set(orizz?(a+b)/2*S:c*S, (z0+z1)/2*S, orizz?c*S:(a+b)/2*S);
  m.castShadow = mat !== matVetro;      // il vetro non deve fermare il sole
  m.receiveShadow = true; scene.add(m); return m;
}
const SP = __SPESSORE__;
for (const [a,b,c,o,z0,z1,sp] of D.muri) box(a,b,c,o,z0,z1,matMuro,sp||SP);

// ---------- rivestimento bagno e battiscopa (quad con UV in coordinate mondo) ----------
function quad(a,b,c,orizz,dentro,z0,z1,mat,cfg,dove){
  cfg = cfg || D.posa[0];
  const pos=[],uv=[],nor=[],idx=[0,1,2,0,2,3];
  const e = dentro>0 ? 1 : -1;
  const P = orizz ? [[a,c],[b,c],[b,c],[a,c]] : [[c,a],[c,b],[c,b],[c,a]];
  const Z = [z0,z0,z1,z1];
  for (let i=0;i<4;i++){
    pos.push(P[i][0]*S, Z[i]*S, P[i][1]*S);
    nor.push(orizz?0:e, 0, orizz?e:0);
    const s = orizz ? P[i][0]-cfg.ox : P[i][1]-cfg.oy;
    uv.push(s/cfg.modulo, Z[i]/cfg.modulo);
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(pos,3));
  g.setAttribute('normal', new THREE.Float32BufferAttribute(nor,3));
  g.setAttribute('uv', new THREE.Float32BufferAttribute(uv,2));
  g.setIndex(orizz===(dentro>0) ? idx : [0,2,1,0,3,2]);
  const m = new THREE.Mesh(g, mat); m.receiveShadow = true;
  m.material.side = THREE.DoubleSide; (dove || scene).add(m);
  return m;
}

// ---------- configurazioni di posa ----------
// Formato e corsi cambiano insieme modulo, origine della griglia e altezza del
// rivestimento: le UV vanno ricostruite, non riscalate. Un gruppo per ciascuna,
// se ne vede una alla volta e si scorrono con B.
const SP_BATT = 1.0;   // il battiscopa sporge: senza spessore niente spigolo ne' ombra
function costruisciPosa(cfg, i){
  const M = matPosa[i];
  const g = new THREE.Group(); scene.add(g);
  superficie(D.pavimento, 0, M.pav, false, cfg, g);
  for (const [a,b,c,o,dn,gr,z0,z1] of cfg.riv)
    quad(a,b,c,o,dn,z0,z1, gr ? M.riv2 : M.riv, cfg, g);
  for (const [a,b,c,o,dn] of D.batt){
    const c2 = c + (dn>0?1:-1)*SP_BATT;
    quad(a, b, c2, o, dn, 0, D.hbatt, M.riv, cfg, g);
    const lo = Math.min(c,c2), hi = Math.max(c,c2);
    superficie([o ? [a,lo,b,hi] : [lo,a,hi,b]], D.hbatt, M.riv, false, cfg, g);
  }
  // i muretti del bagno sono rivestiti: facce e piano con le UV del rivestimento
  for (const [x,y,w,h,base,alt] of D.muretti){
    const x1 = x+w, y1 = y+h, z1 = base+alt;
    quad(x, x1, y,  true, -1, base, z1, M.riv, cfg, g);
    quad(x, x1, y1, true,  1, base, z1, M.riv, cfg, g);
    quad(y, y1, x,  false, -1, base, z1, M.riv, cfg, g);
    quad(y, y1, x1, false,  1, base, z1, M.riv, cfg, g);
    superficie([[x, y, x1, y1]], z1, M.riv, false, cfg, g);
  }
  return g;
}
let iPosa = 0;
const gPosa = D.posa.map((cfg, i) => {
  const g = costruisciPosa(cfg, i); g.visible = (i === 0); return g;
});
function mostraPosa(){
  const c = D.posa[iPosa];
  document.getElementById('posa').innerHTML =
    '<b>' + c.nome + '</b><span>' + c.nota + '<br>modulo ' + c.modulo.toFixed(2)
    + ' cm &middot; rivestimento h ' + c.hriv.toFixed(0) + ' cm</span>';
}
mostraPosa();

// ---------- infissi ----------
function badge(n, x, y, z){
  if (!n) return;
  const t = texTesto(128, 128, k => {
    k.beginPath(); k.arc(64,64,58,0,7); k.fillStyle='#c0392b'; k.fill();
    k.lineWidth=7; k.strokeStyle='#ffffff'; k.stroke();
    k.fillStyle='#ffffff'; k.font='bold 74px Arial'; k.textAlign='center';
    k.fillText(String(n), 64, 90);
  });
  const sp = new THREE.Sprite(new THREE.SpriteMaterial({map:t,
    depthTest:false, depthWrite:false, transparent:true}));
  sp.position.set(x, y, z); sp.scale.set(0.3, 0.3, 1); scenaOver.add(sp);
}
for (const [a,b,c,o,z0,z1,n] of D.vetri){
  box(a,b,c,o,z0,z1,matVetro,3);
  box(a,a+6,c,o,z0,z1,matPvc,8); box(b-6,b,c,o,z0,z1,matPvc,8);
  box(a,b,c,o,z0,z0+6,matPvc,8); box(a,b,c,o,z1-6,z1,matPvc,8);
  badge(n, o?(a+b)/2*S:c*S, (z1+12)*S, o?c*S:(a+b)/2*S);
}

// ---------- porte e portefinestre apribili ----------
// La porta a scomparsa e' sempre la stessa: un modello unico (anta + coprifilo
// sulle due facce) costruito una volta e clonato. Assi locali: X lungo il vano,
// Y verticale con lo zero in mezzeria, Z attraverso il muro.
const LARG_MOD = 7.0;        // sezione del coprifilo
const modelliPorta = new Map();
function modelloScomparsa(luce, alt, spMuro){
  const k = `${luce}|${alt}|${spMuro}`;
  if (!modelliPorta.has(k)){
    const L = luce*S, A = alt*S, m = LARG_MOD*S, e = SP_BATT*S;
    const tel = new THREE.Object3D();
    const anta = new THREE.Object3D(); anta.name = 'anta'; tel.add(anta);
    const p = new THREE.Mesh(new THREE.BoxGeometry(L, A, 0.045), matAnta);
    p.castShadow = p.receiveShadow = true; anta.add(p);
    // il coprifilo sporge dal filo del muro quanto il battiscopa: le facce coincidono
    for (const lato of [1, -1]){
      const z = lato*(spMuro*S/2 + e/2);
      for (const dx of [-1, 1]){
        const mo = new THREE.Mesh(new THREE.BoxGeometry(m, A + m, e), matAnta);
        mo.position.set(dx*(L + m)/2, m/2, z);
        mo.castShadow = mo.receiveShadow = true; tel.add(mo);
      }
      const tr = new THREE.Mesh(new THREE.BoxGeometry(L + 2*m, m, e), matAnta);
      tr.position.set(0, (A + m)/2, z);
      tr.castShadow = tr.receiveShadow = true; tel.add(tr);
    }
    modelliPorta.set(k, tel);
  }
  return modelliPorta.get(k).clone(true);
}

const porte = [];
for (const [a,b,c,o,z0,z1,tipo,dentro,verso,num,card,spMuro] of D.ante){
  const L=(b-a)*S, alt=(z1-z0)*S;
  const cx = o?(a+b)/2*S:c*S, cz = o?c*S:(a+b)/2*S;
  if (tipo === 'porta'){
    const tel = modelloScomparsa(b-a, z1-z0, spMuro||10);
    tel.position.set(cx, (z0+z1)/2*S, cz);
    tel.rotation.y = o ? 0 : -Math.PI/2;      // X locale sempre lungo il vano
    scene.add(tel);
    const anta = tel.getObjectByName('anta');
    porte.push({og:anta, tipo:'locale', t:0, x:cx, z:cz, corsa:L*verso});
    badge(num, cx, (z1+16)*S, cz);
    continue;
  }
  if (tipo === 'fisar'){
    // due ante a libro: la seconda si ripiega sulla prima
    const base = new THREE.Object3D();
    base.position.set(o?a*S:c*S, (z0+z1)/2*S, o?c*S:a*S);
    base.rotation.y = o ? 0 : -Math.PI/2;
    scene.add(base);
    const half = L/2;
    const p1 = new THREE.Object3D(); base.add(p1);
    const p2 = new THREE.Object3D(); p2.position.set(half, 0, 0); p1.add(p2);
    for (const [pp, off] of [[p1,0],[p2,0]]){
      const m = new THREE.Mesh(new THREE.BoxGeometry(half, alt, 0.035), matAnta);
      m.position.set(half/2 + off, 0, 0); m.castShadow = m.receiveShadow = true; pp.add(m);
    }
    porte.push({tipo:'fisar', p1:p1, p2:p2, t:0, x:cx, z:cz,
                ap: dentro * (o ? -1 : 1) * 1.4});
    badge(num, cx, (z1+16)*S, cz);
    continue;
  }
  const piv = new THREE.Object3D();
  const vetrata = tipo === 'pf';
  const sp = vetrata ? SP_ANTA : 0.045;
  const g = new THREE.BoxGeometry(o?L:sp, alt, o?sp:L);
  const mesh = new THREE.Mesh(g, vetrata ? matVetro : matAnta);
  mesh.castShadow = !vetrata; mesh.receiveShadow = true;
  if (vetrata){
    // telaio in PVC solidale con l'anta
    const tel = [[a,a+7],[b-7,b]];
    for (const [ta,tb] of tel){
      const m = new THREE.Mesh(new THREE.BoxGeometry(o?(tb-ta)*S:0.07, alt, o?0.07:(tb-ta)*S), matPvc);
      m.position.set(o?(ta+tb)/2*S-cx:0, 0, o?0:(ta+tb)/2*S-cz);
      m.castShadow = true; piv.add(m);
    }
    for (const zz of [z0+4, z1-4]){
      const m = new THREE.Mesh(new THREE.BoxGeometry(o?L:0.07, 0.08, o?0.07:L), matPvc);
      m.position.set(0, (zz-(z0+z1)/2)*S, 0); m.castShadow = true; piv.add(m);
    }
  }
  mesh.position.set(0,0,0);
  piv.add(mesh);
  piv.position.set(cx, (z0+z1)/2*S, cz);
  scene.add(piv);
  if (tipo === 'battente' || vetrata){
    // perno su un montante: card=1 sul lato di coordinata maggiore, card=0 sull'altro
    const q = card ? b : a;
    const hx = o ? q*S : cx, hz = o ? cz : q*S;
    const perno = new THREE.Object3D();
    perno.position.set(hx, (z0+z1)/2*S, hz);
    scene.add(perno);
    piv.position.set(cx-hx, 0, cz-hz);
    perno.add(piv);
    const ap = (card ? dentro : -dentro) * (o ? 1 : -1) * Math.PI/2;
    porte.push({og:perno, tipo:'battente', t:0, x:cx, z:cz, ap:ap});
  } else {
    porte.push({og:piv, tipo:'scorrevole', t:0, x:cx, z:cz,
                dx:o?L*verso:0, dz:o?0:L*verso, bx:cx, bz:cz});
  }
  badge(num, cx, (z1+16)*S, cz);
}

// ---------- box doccia: vetro fisso + anta mobile su binario sfalsato ----------
{
  const B = D.box, alt = B.h*S, sp = 0.008;
  function vetro(x0, y, mobile){
    const m = new THREE.Mesh(new THREE.BoxGeometry(B.luce*S, alt, sp), matVetro);
    m.position.set((x0 + B.luce/2)*S, alt/2, y*S);
    m.receiveShadow = true;
    const t = new THREE.Mesh(new THREE.BoxGeometry(B.luce*S, 0.035, 0.035), matPvc);
    t.position.set(0, alt/2 + 0.02, 0); t.castShadow = true; m.add(t);
    for (const dx of [-B.luce*S/2, B.luce*S/2]){     // montanti verticali
      const v = new THREE.Mesh(new THREE.BoxGeometry(0.03, alt, 0.03), matPvc);
      v.position.set(dx, 0, 0); v.castShadow = true; m.add(v);
    }
    scene.add(m);
    return m;
  }
  vetro(B.x0, B.y, false);
  const mob = vetro(B.x0 + B.luce, B.y + B.sfalso, true);
  porte.push({og:mob, tipo:'scorrevole', t:0,
              x:(B.x0 + 1.5*B.luce)*S, z:(B.y + B.sfalso)*S,
              dx:-B.luce*S, dz:0,
              bx:(B.x0 + 1.5*B.luce)*S, bz:(B.y + B.sfalso)*S});
}

// ---------- arredo ----------
for (const [x,y,w,h,base,alt,col,tipo] of D.mobili){
  if (tipo === 'muretto'){
    // rivestito come le pareti: facce e piano con le UV in coordinate mondo,
    // cosi' le fughe proseguono quelle del rivestimento
    const x1 = x+w, y1 = y+h, z1 = base+alt;
    quad(x, x1, y,  true, -1, base, z1, matRiv);
    quad(x, x1, y1, true,  1, base, z1, matRiv);
    quad(y, y1, x,  false, -1, base, z1, matRiv);
    quad(y, y1, x1, false,  1, base, z1, matRiv);
    superficie([[x, y, x1, y1]], z1, matRiv, false);
    continue;
  }
  const mat = tipo === 'specchio'
    ? new THREE.MeshStandardMaterial({color:0xd6e0e6, roughness:0.06, metalness:0.35,
                                      envMapIntensity:2.5})
    : new THREE.MeshStandardMaterial({color:col, roughness:0.82});
  const W = w*S, P = h*S, A = alt*S;
  if (tipo === 'scaffale'){
    // scaffale aperto: montanti agli angoli e ripiani, niente fianchi ne' schiena
    const sp = 0.025, g = new THREE.Object3D();
    g.position.set((x+w/2)*S, base*S, (y+h/2)*S);
    for (const dx of [-1,1]) for (const dz of [-1,1]){
      const m = new THREE.Mesh(new THREE.BoxGeometry(sp, A, sp), mat);
      m.position.set(dx*(W-sp)/2, A/2, dz*(P-sp)/2);
      m.castShadow = m.receiveShadow = true; g.add(m);
    }
    const n = Math.max(2, Math.round(alt/40));
    for (let i=0; i<=n; i++){
      const m = new THREE.Mesh(new THREE.BoxGeometry(W, sp, P), mat);
      m.position.set(0, i*A/n, 0);
      m.castShadow = m.receiveShadow = true; g.add(m);
    }
    scene.add(g);
    continue;
  }
  const m = new THREE.Mesh(new THREE.BoxGeometry(W, A, P), mat);
  m.position.set((x+w/2)*S, (base+alt/2)*S, (y+h/2)*S);
  m.castShadow = m.receiveShadow = true; scene.add(m);
}

// ---------- balconi ----------
const matFerro = new THREE.MeshStandardMaterial({color:new THREE.Color(D.colring),
  roughness:0.55, metalness:0.55});
const matVic = new THREE.MeshStandardMaterial({color:0xb9b6b0, roughness:0.95});
function ringhiera(ax, az, bx, bz, alt){
  const L = Math.hypot(bx-ax, bz-az), P = (alt || D.hpar)*S;
  if (L < 0.05) return;
  const dx = (bx-ax)/L, dz = (bz-az)/L, ang = Math.atan2(-dz, dx);
  for (const [yy, s] of [[P-0.025, 0.05], [0.07, 0.03]]){   // corrimano e traverso
    const m = new THREE.Mesh(new THREE.BoxGeometry(L, s, s), matFerro);
    m.position.set((ax+bx)/2, yy, (az+bz)/2); m.rotation.y = ang;
    m.castShadow = true; scene.add(m);
  }
  const n = Math.max(2, Math.round(L/0.12));               // montanti ogni ~12 cm
  const g = new THREE.BoxGeometry(0.018, P, 0.018);
  for (let i=0; i<=n; i++){
    const m = new THREE.Mesh(g, matFerro);
    m.position.set(ax + dx*L*i/n, P/2, az + dz*L*i/n);
    m.castShadow = true; scene.add(m);
  }
}
function soletta(x0,y0,x1,y1,rN,rO,rE,mat){
  const s = new THREE.Mesh(new THREE.BoxGeometry((x1-x0)*S, 0.16, (y1-y0)*S), mat);
  s.position.set((x0+x1)/2*S, -0.08, (y0+y1)/2*S);
  s.receiveShadow = true; scene.add(s);
  if (rN) ringhiera(x0*S, y0*S, x1*S, y0*S);
  if (rO) ringhiera(x0*S, y0*S, x0*S, y1*S);
  if (rE) ringhiera(x1*S, y0*S, x1*S, y1*S);
}
for (const b of D.balconi) soletta(b[0],b[1],b[2],b[3],b[4],b[5],b[6], matCls);
for (const b of D.vicino)  soletta(b[0],b[1],b[2],b[3],b[4],b[5],b[6], matVic);
for (const [x0,y0,x1,y1,alt] of D.separe) ringhiera(x0*S, y0*S, x1*S, y1*S, alt);

// ---------- controsoffitti con faretti ----------
// chiudono i vuoti a fianco delle travi, che altrimenti restano pozzi profondi
const matFaretto = new THREE.MeshStandardMaterial({color:0xfffaf0,
  emissive:0xfff0d0, emissiveIntensity:1.4, roughness:0.4});
for (const [x0,y0,x1,y1,z,passo,lb] of D.contro){
  const W = (x1-x0)*S, P = (y1-y0)*S;
  const p = new THREE.Mesh(new THREE.BoxGeometry(W, 0.025, P), matMuro);
  p.position.set((x0+x1)/2*S, z*S - 0.0125, (y0+y1)/2*S);
  p.castShadow = p.receiveShadow = true; scene.add(p);
  // faretti equidistanti lungo il lato lungo
  const lungo = Math.max(x1-x0, y1-y0), oriz = (x1-x0) >= (y1-y0);
  const n = Math.max(2, Math.round(lungo/passo));
  for (let i=0; i<n; i++){
    const t = (i + 0.5)/n;
    const fx = oriz ? (x0 + t*(x1-x0))*S : (x0+x1)/2*S;
    const fz = oriz ? (y0+y1)/2*S : (y0 + t*(y1-y0))*S;
    const f = new THREE.Mesh(new THREE.CylinderGeometry(0.045, 0.045, 0.012, 20), matFaretto);
    f.position.set(fx, z*S - 0.028, fz); scene.add(f);
    const l = new THREE.PointLight(0xfff0d8, 1.8, 4, 2);
    l.position.set(fx, z*S - 0.06, fz); scene.add(l);
  }
}

// ---------- quote ----------
const gQuote = new THREE.Group(); gQuote.visible = false; scenaOver.add(gQuote);
function cartello(txt, x, y, z, col){
  const W = 512, H = 64;
  const t = texTesto(W, H, k => {
    let fs = 40;
    k.font = 'bold ' + fs + 'px Arial';
    const larg = k.measureText(txt).width;
    if (larg > W - 20){ fs = Math.floor(fs*(W-20)/larg); k.font = 'bold ' + fs + 'px Arial'; }
    k.textAlign = 'center'; k.textBaseline = 'middle';
    k.lineWidth = Math.max(4, fs/5); k.lineJoin = 'round';
    k.strokeStyle = 'rgba(255,255,255,.92)'; k.strokeText(txt, W/2, H/2);
    k.fillStyle = col; k.fillText(txt, W/2, H/2);
  });
  const sp = new THREE.Sprite(new THREE.SpriteMaterial({map:t,
    depthTest:false, depthWrite:false, transparent:true}));
  sp.position.set(x, y, z);
  sp.scale.set(W/H*0.17, 0.17, 1);
  gQuote.add(sp);
}
const matQ = new THREE.LineBasicMaterial({color:0x000000, depthTest:false, depthWrite:false});
// la quota giace sul pavimento, parallela al lato misurato: niente cartelli girevoli
function quotaPiana(txt, x0, z0, x1, z1, hTesto){
  const W = 256, H = 64;
  const t = texTesto(W, H, k => {
    k.font = 'bold 44px Arial';
    k.fillStyle = '#000000'; k.textAlign = 'center'; k.textBaseline = 'middle';
    k.fillText(txt, W/2, H/2);
  });
  const h = hTesto || 0.13;
  const m = new THREE.Mesh(new THREE.PlaneGeometry(h*W/H, h),
    new THREE.MeshBasicMaterial({map:t, transparent:true, depthTest:false,
                                 depthWrite:false, side:THREE.DoubleSide}));
  let ang = Math.atan2(z1-z0, x1-x0);
  if (ang >  Math.PI/2) ang -= Math.PI;      // il testo non deve leggersi capovolto
  if (ang < -Math.PI/2) ang += Math.PI;
  m.rotation.z = -ang;
  const piano = new THREE.Object3D();
  piano.position.set((x0+x1)/2, 0.02, (z0+z1)/2);
  piano.rotation.x = -Math.PI/2;
  piano.add(m); gQuote.add(piano);
}
for (const [x0,y0,x1,y1,lb] of D.quote){
  const h = 0.015, pts = [new THREE.Vector3(x0*S,h,y0*S), new THREE.Vector3(x1*S,h,y1*S)];
  const vert = Math.abs(x1-x0) < Math.abs(y1-y0);
  for (const [px,pz] of [[x0,y0],[x1,y1]]){          // trattini di estremita'
    const a = vert ? [px-5, pz] : [px, pz-5], b = vert ? [px+5, pz] : [px, pz+5];
    pts.push(new THREE.Vector3(a[0]*S,h,a[1]*S), new THREE.Vector3(b[0]*S,h,b[1]*S));
  }
  gQuote.add(new THREE.LineSegments(new THREE.BufferGeometry().setFromPoints(
    [pts[0],pts[1],pts[2],pts[3],pts[4],pts[5]]), matQ));
  quotaPiana(lb, x0*S, y0*S, x1*S, y1*S);
}
for (const [x,y,txt] of D.aree) quotaPiana(txt, x*S, y*S, (x+1)*S, y*S, 0.20);
for (const [x,y,z,txt,col] of D.etichette) cartello(txt, x*S, z*S, y*S, col);
window.__hs = (t) => { scene.traverse(o=>{ if (o.isSprite) o.visible = !t; });
  gQuote.traverse(o=>{ if (o.isSprite) o.visible = !t; }); };

// ---------- controlli ----------
const controls = new PointerLockControls(camera, renderer.domElement);
const overlay = document.getElementById('start'), msg = document.getElementById('msg');
// su schermo tattile il pointer lock non esiste: si guarda trascinando
const TOCCO = matchMedia('(pointer: coarse)').matches || navigator.maxTouchPoints > 0;
overlay.addEventListener('click', ()=>{
  if (TOCCO) overlay.style.display = 'none'; else controls.lock();
});
controls.addEventListener('lock',   ()=>overlay.style.display='none');
controls.addEventListener('unlock', ()=>{ if (!TOCCO) overlay.style.display='flex'; });
scene.add(controls.getObject());
controls.getObject().position.set(D.start[0]*S, 1.60, D.start[1]*S);
if (D.guarda) controls.getObject().rotation.y = D.guarda;

let avviso = 0;
function dimmi(t){ msg.textContent = t; msg.style.opacity = 1; avviso = performance.now(); }

const tasti = {};
addEventListener('keydown', e=>{
  if (!tasti[e.code]){
    if (e.code === 'KeyQ'){ gQuote.visible = !gQuote.visible;
      dimmi(gQuote.visible ? 'quote visibili' : 'quote nascoste'); }
    if (e.code === 'KeyH'){
      const l = document.getElementById('leg');
      l.style.display = l.style.display === 'none' ? 'block' : 'none';
    }
    if (e.code === 'KeyO'){
      renderer.shadowMap.enabled = !renderer.shadowMap.enabled;
      scene.traverse(o => { if (o.isMesh) o.material.needsUpdate = true; });
      sole.shadow.needsUpdate = true;
      dimmi(renderer.shadowMap.enabled ? 'ombre attive' : 'ombre spente');
    }
    if (e.code === 'KeyL'){
      ao.enabled = !ao.enabled;
      dimmi(ao.enabled ? 'occlusione ambientale attiva' : 'occlusione ambientale spenta');
    }
    if (e.code === 'KeyB'){
      gPosa[iPosa].visible = false;
      iPosa = (iPosa + 1) % gPosa.length;
      gPosa[iPosa].visible = true;
      mostraPosa();
      dimmi(D.posa[iPosa].nome + '  -  ' + D.posa[iPosa].nota);
    }
    if (e.code === 'KeyE'){
      const p = controls.getObject().position;
      let vicine = porte.filter(d => Math.hypot(p.x-d.x, p.z-d.z) < 2.4);
      if (vicine.length){
        const apri = vicine[0].t < 0.5;
        vicine.forEach(d => d.t = apri ? 1 : 0);
        dimmi(apri ? 'porta aperta' : 'porta chiusa');
      } else dimmi('nessuna porta nelle vicinanze');
    }
  }
  tasti[e.code] = true;
  if (e.code.startsWith('Arrow')) e.preventDefault();
});
addEventListener('keyup', e=>tasti[e.code]=false);

// ---------- comandi su schermo tattile ----------
// joystick a sinistra per spostarsi, trascinamento sulla scena per guardarsi
// attorno: la stessa logica dei tasti, ma con valori continui da -1 a 1.
const joy = {x:0, y:0, id:null, cx:0, cy:0};
if (TOCCO){
  document.getElementById('touch').style.display = 'block';
  const base = document.getElementById('joy'), pomo = document.getElementById('pomo');
  const R = 39;
  base.addEventListener('touchstart', e=>{
    const r = base.getBoundingClientRect();
    joy.cx = r.left + r.width/2; joy.cy = r.top + r.height/2;
    joy.id = e.changedTouches[0].identifier; e.preventDefault();
  }, {passive:false});
  base.addEventListener('touchmove', e=>{
    for (const t of e.changedTouches){
      if (t.identifier !== joy.id) continue;
      let dx = t.clientX - joy.cx, dy = t.clientY - joy.cy;
      const d = Math.hypot(dx, dy) || 1;
      if (d > R){ dx *= R/d; dy *= R/d; }
      pomo.style.transform = 'translate(' + dx + 'px,' + dy + 'px)';
      joy.x = dx/R; joy.y = -dy/R;
    }
    e.preventDefault();
  }, {passive:false});
  const molla = ()=>{ joy.id=null; joy.x=joy.y=0; pomo.style.transform=''; };
  base.addEventListener('touchend', molla);
  base.addEventListener('touchcancel', molla);

  // sguardo: yaw e pitch gestiti a mano, PointerLockControls qui non interviene
  const og = controls.getObject();
  og.rotation.order = 'YXZ';
  let look = null, lx = 0, ly = 0;
  renderer.domElement.addEventListener('touchstart', e=>{
    const t = e.changedTouches[0];
    look = t.identifier; lx = t.clientX; ly = t.clientY;
  }, {passive:true});
  renderer.domElement.addEventListener('touchmove', e=>{
    for (const t of e.changedTouches){
      if (t.identifier !== look) continue;
      og.rotation.y -= (t.clientX - lx) * 0.005;
      og.rotation.x = Math.max(-1.5, Math.min(1.5, og.rotation.x - (t.clientY - ly) * 0.005));
      lx = t.clientX; ly = t.clientY;
    }
    e.preventDefault();
  }, {passive:false});
  renderer.domElement.addEventListener('touchend', ()=>{ look = null; });

  for (const b of document.querySelectorAll('#bott button')){
    b.addEventListener('touchstart', e=>{
      const c = b.dataset.k;
      dispatchEvent(new KeyboardEvent('keydown', {code:c}));
      dispatchEvent(new KeyboardEvent('keyup', {code:c}));
      e.preventDefault();
    }, {passive:false});
  }
}
addEventListener('resize', ()=>{
  camera.aspect = innerWidth/innerHeight; camera.updateProjectionMatrix();
  renderer.setSize(innerWidth, innerHeight);
  composer.setSize(innerWidth, innerHeight);
  ao.setSize(innerWidth*AO_SCALA, innerHeight*AO_SCALA);});

const hud = document.getElementById('pos');
const dirW = new THREE.Vector3();
let soffitto_sopra = false;
let t0 = performance.now();
function loop(){
  requestAnimationFrame(loop);
  const t = performance.now(), dt = Math.min((t-t0)/1000, .1); t0 = t;
  const v = (tasti['ShiftLeft']||tasti['ShiftRight'] ? 4.2 : 1.9) * dt;
  if (controls.isLocked || TOCCO){
    const p = controls.getObject().position;
    // avanti segue lo sguardo anche in quota (volo libero), il laterale resta sul piano
    const av = (tasti['KeyW']?1:0) - (tasti['KeyS']?1:0) + joy.y;
    const lat = (tasti['KeyD']?1:0) - (tasti['KeyA']?1:0) + joy.x;
    if (Math.abs(av) > 0.02){
      camera.getWorldDirection(dirW);
      p.addScaledVector(dirW, v * av);
    }
    if (Math.abs(lat) > 0.02) controls.moveRight(v * lat);
    if (tasti['ArrowUp'])    controls.moveForward( v);
    if (tasti['ArrowDown'])  controls.moveForward(-v);
    if (tasti['ArrowRight']) controls.moveRight( v);
    if (tasti['ArrowLeft'])  controls.moveRight(-v);
    p.y = Math.max(p.y, 0.25);
    hud.textContent = `x ${(p.x/S).toFixed(0)}  y ${(p.y/S).toFixed(0)}  z ${(p.z/S).toFixed(0)} cm`
      + (p.y > D.h*S ? '   -  sopra il soffitto' : '');
  }
  // soffitto trasparente quando lo si supera
  const sopra = controls.getObject().position.y > D.h*S;
  matSoff.opacity += ((sopra ? 0.06 : 1) - matSoff.opacity) * Math.min(1, dt*8);
  soffitto.visible = matSoff.opacity > 0.07;
  soffitto.castShadow = !sopra;
  // animazione delle porte
  for (const d of porte){
    const cur = d.cur === undefined ? 0 : d.cur;
    const n = cur + (d.t - cur) * Math.min(1, dt*4.5);
    d.cur = n;
    if (Math.abs(n - cur) > 0.0005) sole.shadow.needsUpdate = true;
    if (d.tipo === 'battente') d.og.rotation.y = n * d.ap;
    else if (d.tipo === 'locale') d.og.position.x = d.corsa * n;
    else if (d.tipo === 'fisar'){ d.p1.rotation.y = n * d.ap; d.p2.rotation.y = -n * 2 * d.ap; }
    else { d.og.position.x = d.bx + d.dx * n; d.og.position.z = d.bz + d.dz * n; }
  }
  if (sopra !== soffitto_sopra){ soffitto_sopra = sopra; sole.shadow.needsUpdate = true; }
  if (avviso && t - avviso > 1400){ msg.style.opacity = 0; avviso = 0; }
  composer.render();
  renderer.autoClear = false;
  renderer.render(scenaOver, camera);
  renderer.autoClear = true;
}
sole.shadow.needsUpdate = true;
loop();
</script></body></html>
"""

HTML = HTML.replace("__DATI__", json.dumps(DATI)).replace("__SPESSORE__", str(cp.SP_EST))
with open(OUT, "w", encoding="utf-8") as f:
    f.write(HTML)

print(f"scritto {OUT}")
print(f"  pavimento     {len(pavimento)} rettangoli")
print(f"  muri          {len(muri)} pannelli")
print(f"  infissi       {len(vetri)} vetrati, {len(ante)} porte apribili")
print(f"  rivestimento  {len(riv)} facce bagno (h {H_RIV:.1f} cm)")
print(f"  battiscopa    {len(batt)} tratti (h {H_BATT:.0f} cm)")
print(f"  balconi       {len(BALCONI)}")
print(f"  arredo        {len(mobili)} volumi")
print(f"  quote         {len(quote)} catene, {len(etichette)} cartellini")
print(f"  griglia       origine {OX:.1f}/{OY:.1f}, modulo {cp.MODULO:.2f}, fuga {cp.FUGA*10:.1f} mm")

print("\nRISCONTRO CON LA PIANTA (valori presi da casa_pianta.py)")
print(f"  altezza interna      {H_INT:.0f} cm")
print(f"  battiscopa           {H_BATT:.0f} cm")
print(f"  rivestimento bagno   {H_RIV:.1f} cm")
print(f"  ringhiera / separe   {cp.H_RING:.0f} / {cp.H_SEPARE:.0f} cm")
print(f"  modulo di posa       {cp.MODULO:.2f} cm (fuga {cp.FUGA*10:.1f} mm)")
print(f"  {'locale':22}{'pianta':>16}{'3D':>16}")
for nome, d in cp.LOCALI.items():
    x0, y0, x1, y1 = d["bb"]
    r = [q for q in d["rect"]]
    sup = sum((q[2] - q[0]) * (q[3] - q[1]) for q in r) / 10000
    print(f"  {nome:22}{x1-x0:7.0f} x{y1-y0:6.0f}{sup:11.2f} mq  = {d['area']:.2f} mq")
sp = sorted({round(m[6]) for m in muri})
print(f"  spessori murari usati in 3D: {sp} cm  (perimetrali {cp.SP_EST:.0f})")
