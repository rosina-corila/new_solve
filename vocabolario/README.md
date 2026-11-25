# Vocabolario dei temi di SOLVe

Thesaurus SKOS dei macrotemi e sottotemi usati dal grafo e dai filtri della nuova SOLVe.

## File

| File | Cosa contiene | Si modifica? |
|---|---|---|
| `temi.csv` | Una riga per concetto: etichette, definizione, codici dei vocabolari standard | **Sì, è la fonte** |
| `temi.ttl` | Thesaurus SKOS in Turtle, da caricare in GeoNode (`load_thesaurus`) o in qualsiasi strumento SKOS | No, generato |
| `temi.json` | Albero macrotemi → sottotemi per il sito | No, generato |

Dopo ogni modifica al CSV:

```bash
python scripts/build_vocabolario.py
```

## Struttura

- **9 macrotemi**: le 8 componenti ecosistemiche più "Base cartografica" (nodo trasversale).
- **44 sottotemi**, 4–7 per macrotema.
- Ogni concetto ha un identificativo fisso (`id`) e una parola chiave derivata (`solve-<id>`) per i filtri.

## Agganci ai vocabolari standard

I nostri concetti restano nostri (etichette in italiano, taglio lagunare) ma sono collegati ai vocabolari ufficiali con le relazioni SKOS di corrispondenza:

| Colonna | Vocabolario | Relazione | Perché |
|---|---|---|---|
| `p08` | SeaDataNet P08 – discipline (NERC Vocabulary Server) | `skos:broadMatch` | La disciplina è più ampia del nostro tema |
| `p03` | SeaDataNet P03 – gruppi di parametri concordati | `skos:closeMatch` | Livello di dettaglio simile ai sottotemi |
| `p02` | SeaDataNet/EMODnet P02 – parametri di ricerca | `skos:narrowMatch` | Il parametro è più specifico del sottotema |
| `inspire` | Temi INSPIRE (registro INSPIRE) | `skos:broadMatch` | Tema di direttiva, molto ampio |

Tutti i codici NVS usati sono stati verificati come esistenti e non deprecati il 25/11/2026 (SPARQL su vocab.nerc.ac.uk).

Da aggiungere in un secondo passo: GEMET (parole chiave RNDT), EUNIS (habitat), WoRMS (specie).

## Namespace

`https://solve.corila.it/vocabolario/temi/` è provvisorio. Prima della pubblicazione va scelto un URI stabile (es. un redirect w3id.org) e rigenerato il TTL.
