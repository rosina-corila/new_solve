"""Genera il thesaurus SKOS (Turtle) e il JSON per il sito a partire da vocabolario/temi.csv.

Uso:  python scripts/build_vocabolario.py

Il CSV è la fonte da modificare: una riga per concetto.
- livello: macrotema | sottotema
- padre: id del macrotema (solo per i sottotemi)
- p08, p03, p02: codici del NERC Vocabulary Server (SeaDataNet/EMODnet), separati da spazio
- inspire: codice del tema INSPIRE (es. hy, hb, ps)
"""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "vocabolario" / "temi.csv"
OUT_TTL = ROOT / "vocabolario" / "temi.ttl"
OUT_JSON = ROOT / "vocabolario" / "temi.json"

# Namespace provvisorio: da sostituire con un URI stabile (es. w3id.org) quando lo pubblichiamo
BASE = "https://solve.corila.it/vocabolario/temi/"
NVS = "http://vocab.nerc.ac.uk/collection/{coll}/current/{code}/"
INSPIRE = "http://inspire.ec.europa.eu/theme/{code}"


def esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


def matches(row):
    """Corrispondenze verso i vocabolari standard.

    - P08 (discipline) e temi INSPIRE sono più ampi dei nostri concetti -> skos:broadMatch
    - P03 (gruppi di parametri) ha un dettaglio simile ai sottotemi     -> skos:closeMatch
    - P02 (parametri di ricerca) è più specifico                        -> skos:narrowMatch
    """
    out = []
    for code in row["p08"].split():
        out.append(("broadMatch", NVS.format(coll="P08", code=code)))
    for code in row["p03"].split():
        out.append(("closeMatch", NVS.format(coll="P03", code=code)))
    for code in row["p02"].split():
        out.append(("narrowMatch", NVS.format(coll="P02", code=code)))
    for code in row["inspire"].split():
        out.append(("broadMatch", INSPIRE.format(code=code)))
    return out


def main():
    rows = list(csv.DictReader(SRC.open(encoding="utf-8")))
    ids = {r["id"] for r in rows}
    for r in rows:
        if r["livello"] == "sottotema" and r["padre"] not in ids:
            raise SystemExit(f"Padre mancante per {r['id']}: {r['padre']}")

    children = {}
    for r in rows:
        if r["padre"]:
            children.setdefault(r["padre"], []).append(r["id"])

    ttl = [
        "@prefix skos: <http://www.w3.org/2004/02/skos/core#> .",
        "@prefix dct: <http://purl.org/dc/terms/> .",
        f"@prefix temi: <{BASE}> .",
        "",
        "temi: a skos:ConceptScheme ;",
        '    skos:prefLabel "Temi di SOLVe - Sistema Osservativo della Laguna di Venezia"@it ,',
        '        "SOLVe themes - Venice Lagoon Observing System"@en ;',
        '    dct:publisher "CORILA" ;',
        "    skos:hasTopConcept "
        + " , ".join(f"temi:{r['id']}" for r in rows if r["livello"] == "macrotema")
        + " .",
        "",
    ]
    for r in rows:
        lines = [
            f"temi:{r['id']} a skos:Concept ;",
            "    skos:inScheme temi: ;",
            f'    skos:prefLabel "{esc(r["etichetta_it"])}"@it , "{esc(r["etichetta_en"])}"@en ;',
            f'    skos:definition "{esc(r["definizione"])}"@it ;',
        ]
        if r["livello"] == "macrotema":
            lines.append("    skos:topConceptOf temi: ;")
        else:
            lines.append(f"    skos:broader temi:{r['padre']} ;")
        for kid in children.get(r["id"], []):
            lines.append(f"    skos:narrower temi:{kid} ;")
        for rel, uri in matches(r):
            lines.append(f"    skos:{rel} <{uri}> ;")
        if r["note"]:
            lines.append(f'    skos:editorialNote "{esc(r["note"])}"@it ;')
        lines[-1] = lines[-1][:-2] + " ."
        ttl += lines + [""]
    OUT_TTL.write_text("\n".join(ttl), encoding="utf-8")

    tree = []
    for r in rows:
        if r["livello"] != "macrotema":
            continue
        node = {
            "id": r["id"],
            "uri": BASE + r["id"],
            "label": r["etichetta_it"],
            "label_en": r["etichetta_en"],
            "definizione": r["definizione"],
            "keyword": f"solve-{r['id']}",
            "sottotemi": [],
        }
        for s in rows:
            if s["padre"] == r["id"]:
                node["sottotemi"].append({
                    "id": s["id"],
                    "uri": BASE + s["id"],
                    "label": s["etichetta_it"],
                    "label_en": s["etichetta_en"],
                    "definizione": s["definizione"],
                    "keyword": f"solve-{s['id']}",
                    "match": [{"rel": rel, "uri": uri} for rel, uri in matches(s)],
                })
        tree.append(node)
    OUT_JSON.write_text(json.dumps(tree, ensure_ascii=False, indent=2), encoding="utf-8")

    n_macro = len(tree)
    n_sub = sum(len(n["sottotemi"]) for n in tree)
    print(f"{n_macro} macrotemi, {n_sub} sottotemi -> {OUT_TTL.name}, {OUT_JSON.name}")


if __name__ == "__main__":
    main()
