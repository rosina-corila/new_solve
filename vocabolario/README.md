# Vocabolario dei temi di SOLVe

Thesaurus SKOS dei macrotemi e sottotemi usati dal grafo e dai filtri della nuova SOLVe.
Guida completa ai vocabolari standard: documento "Vocabolari standard per SOLVe - guida".

## File

| File | Cosa contiene | Si modifica? |
|---|---|---|
| `temi.csv` | Una riga per concetto: etichette, definizione, parametri P02, agganci manuali, correlati | **Sì, è la fonte** |
| `nvs_cache.json` | Mappature lette dal NERC Vocabulary Server per i P02 usati | No, generato da `scripts/aggiorna_nvs.py` |
| `temi.ttl` | Thesaurus SKOS in Turtle, da caricare in GeoNode (`load_thesaurus`) o in uno strumento SKOS | No, generato |
| `temi.json` | Albero completo con classificazione standard per il sito | No, generato |
| `temi_grafo.json` | Versione compatta per `sito/vocabolario.html` | No, generato |

Dopo ogni modifica al CSV:

```bash
python scripts/aggiorna_nvs.py        # solo se hai aggiunto o cambiato codici P02 / P03 (serve internet)
python scripts/build_vocabolario.py
```

Per vedere il grafo in locale: `python -m http.server` nella cartella del repository, poi apri `http://localhost:8000/sito/vocabolario.html`.

## Il modello

- **9 macrotemi** (8 componenti ecosistemiche + "Base cartografica") e **44 sottotemi**, con identificativo fisso e parola chiave `solve-<id>`.
- **Un solo aggancio standard scritto a mano: la colonna `p02`** (parametri di ricerca SeaDataNet/EMODnet).
- **Tutto il resto è ricavato dal NERC Vocabulary Server**: gruppo SeaDataNet (P03), disciplina (P08), tema INSPIRE (collezione P22), categoria ISO 19115 (P05), indicatori della Strategia Marina (C47).
- **`p03_manuale` e `inspire_manuale`** solo per i sottotemi senza un P02 adatto (falda, opere MOSE, stato WFD, rilievi sismici, usi…), con una nota che lo spiega. Regola: meglio nessun aggancio che un aggancio forzato.
- **`correlati`**: legami "vedi anche" tra nostri sottotemi (`skos:related`), simmetrici, si scrivono una volta sola. Sono gli unici legami trasversali che il sito usa per la navigazione.

## Cosa determina cosa

| Relazione | Dove | Effetto nel sito |
|---|---|---|
| `skos:broader` / `narrower` | gerarchia macrotema → sottotema | Il clic sul macrotema include i layer dei sottotemi |
| `skos:related` | colonna `correlati` | Riquadro "vedi anche", mai nei risultati |
| `skos:narrowMatch` (P02), `closeMatch` (P03 manuale), `broadMatch` (INSPIRE manuale) | agganci standard | Nessuno sui risultati: riquadro "classificazione standard", metadati RNDT, collocazione dei layer esterni |

Il file `temi.ttl` contiene solo le nostre affermazioni; le classificazioni derivate dall'NVS stanno in `temi.json`.

## Namespace

`https://solve.corila.it/vocabolario/temi/` è provvisorio. Prima della pubblicazione va scelto un URI stabile (es. un redirect w3id.org) e rigenerato il TTL.
