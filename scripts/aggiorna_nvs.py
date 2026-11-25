"""Aggiorna vocabolario/nvs_cache.json interrogando il NERC Vocabulary Server (SPARQL).

Uso:  python scripts/aggiorna_nvs.py      (serve accesso a internet; nessuna dipendenza esterna)

Per ogni P02 citato in vocabolario/temi.csv legge: gruppi P03, temi INSPIRE (P22), categorie ISO (P05),
indicatori MSFD (C47); per ogni P03 coinvolto (anche quelli di p03_manuale) legge le discipline P08.
Segnala i codici inesistenti o deprecati.
"""
import csv
import json
import re
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "vocabolario" / "temi.csv"
CACHE = ROOT / "vocabolario" / "nvs_cache.json"
ENDPOINT = "https://vocab.nerc.ac.uk/sparql/sparql"
PFX = "PREFIX skos:<http://www.w3.org/2004/02/skos/core#> PREFIX owl:<http://www.w3.org/2002/07/owl#> "


def sparql(q):
    url = ENDPOINT + "?" + urllib.parse.urlencode({"query": PFX + q, "output": "json"})
    req = urllib.request.Request(url, headers={"Accept": "application/sparql-results+json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)["results"]["bindings"]


def uri(coll, code):
    return f"<http://vocab.nerc.ac.uk/collection/{coll}/current/{code}/>"


def parse(u):
    m = re.search(r"collection/(\w+)/current/([^/]+)/", u)
    return m.group(1), m.group(2)


def main():
    rows = list(csv.DictReader(SRC.open(encoding="utf-8")))
    p02 = sorted({c for r in rows for c in r["p02"].split()})
    p03_man = sorted({c for r in rows for c in r["p03_manuale"].split()})

    vals = " ".join(uri("P02", c) for c in p02)
    status = sparql(f"SELECT ?c ?l ?d WHERE {{ VALUES ?c {{ {vals} }} ?c skos:prefLabel ?l . "
                    f"OPTIONAL {{ ?c owl:deprecated ?d }} }}")
    found = {parse(b["c"]["value"])[1]: b for b in status}
    errori = [c for c in p02 if c not in found]
    errori += [c for c, b in found.items() if b.get("d", {}).get("value") == "true"]
    if errori:
        raise SystemExit(f"Codici P02 inesistenti o deprecati: {', '.join(sorted(set(errori)))}")

    out = {c: {"l": found[c]["l"]["value"], "P03": [], "P22": [], "P05": [], "C47": []} for c in p02}
    lab = {"P03": {}, "P22": {}, "P05": {}, "C47": {}, "P08": {}}
    for b in sparql(f"SELECT ?c ?b ?bl WHERE {{ VALUES ?c {{ {vals} }} ?c skos:broader ?b . ?b skos:prefLabel ?bl . "
                    "FILTER(lang(?bl)='en' || lang(?bl)='') FILTER(REGEX(STR(?b),'/(P03|P22|P05|C47)/')) }"):
        c = parse(b["c"]["value"])[1]
        coll, code = parse(b["b"]["value"])
        if code not in out[c][coll]:
            out[c][coll].append(code)
        lab[coll][code] = b["bl"]["value"]

    p03 = sorted({g for v in out.values() for g in v["P03"]} | set(p03_man))
    vals3 = " ".join(uri("P03", c) for c in p03)
    p03_out = {c: [] for c in p03}
    for b in sparql(f"SELECT ?c ?cl ?b ?bl WHERE {{ VALUES ?c {{ {vals3} }} ?c skos:prefLabel ?cl . "
                    "OPTIONAL { ?c skos:broader ?b . ?b skos:prefLabel ?bl . FILTER(REGEX(STR(?b),'/P08/')) } }"):
        c = parse(b["c"]["value"])[1]
        lab["P03"][c] = b["cl"]["value"]
        if "b" in b:
            d = parse(b["b"]["value"])[1]
            if d not in p03_out[c]:
                p03_out[c].append(d)
            lab["P08"][d] = b["bl"]["value"]
    mancanti = [c for c in p03_man if c not in lab["P03"]]
    if mancanti:
        raise SystemExit(f"Codici P03 manuali inesistenti: {', '.join(mancanti)}")

    cache = {"_info": {"fonte": ENDPOINT, "letto_il": date.today().isoformat(),
                       "contenuto": "Mappature NVS dei P02 e P03 usati in temi.csv"},
             "p02": out, "p03": p03_out, "lab": lab}
    CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(out)} P02 e {len(p03_out)} P03 aggiornati in {CACHE.name}")


if __name__ == "__main__":
    main()
