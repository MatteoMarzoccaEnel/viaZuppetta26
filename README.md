# via Zuppetta 26

Progetto di ristrutturazione di un appartamento: rilievo, pianta di posa del
gres, modello 3D navigabile e computo dei materiali.

Tutto nasce da **un solo file di dati**, [`casa_pianta.py`](casa_pianta.py): i
poligoni dei locali, le aperture, la struttura in c.a. e l'arredo. Ogni altro
script legge da lì e non duplica nessuna misura, così pianta, modello 3D e
computo non possono divergere.

## Script

| file | cosa produce |
|---|---|
| `casa_pianta.py` | pianta di posa del gres (SVG/PDF/PNG), analisi lastra per lastra, elenco infissi e arredi |
| `casa_3d.py` | `casa_3d.html`, visita in prima persona con Three.js |
| `vincoli.py` | verifica i vincoli tecnici e blocca le modifiche silenziose ai dati immutabili |
| `report.py` | un computo tecnico in PDF per ogni formato di piastrella |
| `computo.py` | riepilogo del fabbisogno rispetto al preventivo |
| `battiscopa.py` | metri di battiscopa ricavati dalle stesse lastre |
| `bagno_pianta.py` | tavola di dettaglio del bagno in scala |
| `bagno_rivestimento.py` | rivestimento del bagno diviso per prodotto |
| `muri_nuovi.py`, `muro_disimpegno.py`, `muro_ingresso.py` | studi parametrici sulla posizione dei muri di progetto |

## Configurazioni di posa

I formati messi a confronto sono dichiarati in `casa_pianta.FORMATI`. Cambiare
formato rifà l'ottimizzazione della griglia, non solo il disegno.

```
python casa_pianta.py --posa=2     # elaborati con il formato indicato
python report.py                   # un PDF di computo per ogni formato
```

Nel modello 3D il tasto **B** scorre le configurazioni mostrando lastre,
listelli e sfrido di ciascuna.

## Vincoli

`vincoli.py` verifica a ogni esecuzione perimetro, struttura, muri esistenti,
tasche delle porte a scomparsa, spallette, incassi e continuità del battiscopa.
Perimetro, pilastri e travi sono protetti da una firma: si possono correggere,
ma non per sbaglio.

```
python vincoli.py            # esegue i controlli
python vincoli.py --firme    # rigenera le firme dopo un rilievo più accurato
```

## Requisiti

Python 3 con `pymupdf`, `pillow`, `reportlab`, `svglib`. Il modello 3D si apre
in qualsiasi browser, senza server.
