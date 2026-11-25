"""Genera il thesaurus SKOS (Turtle) e il JSON per il sito a partire da vocabolario/temi.csv.

Uso:  python scripts/build_vocabolario.py

Modello (vedi vocabolario/README.md):
- l'unico aggancio standard scritto a mano è la colonna p02 (parametri SeaDataNet/EMODnet);
- gruppo SeaDataNet (P03), disciplina (P08), tema INSPIRE (P22), categoria ISO (P05) e
  indicatori MSFD (C47) sono ricavati dal NERC Vocabulary Server, letti da vocabolario/nvs_cache.json
  (aggiornabile con scripts/aggiorna_nvs.py);
- p03_manuale e inspire_manuale servono solo per i sottotemi senza un P02 adatto;
- correlati = legami "vedi anche" tra nostri sottotemi (simmetrici, si scrivono una volta sola).
"""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VOC = ROOT / "vocabolario"
SRC = VOC / "temi.csv"
CACHE = VOC / "nvs_cache.json"
OUT_TTL = VOC / "temi.ttl"
OUT_JSON = VOC / "temi.json"

# Namespace provvisorio: da sostituire con un URI stabile (es. w3id.org) prima della pubblicazione
BASE = "https://solve.corila.it/vocabolario/temi/"
NVS = "http://vocab.nerc.ac.uk/collection/{coll}/current/{code}/"
INSPIRE = "http://inspire.ec.europa.eu/theme/{code}"

# Collezione NVS P22 (GEMET - INSPIRE themes): id numerico -> codice del registro INSPIRE
P22_INSPIRE = {"10": "el", "11": "lc", "13": "ge", "16": "so", "18": "hh", "20": "ef", "26": "ac",
               "27": "mf", "28": "of", "31": "hb", "32": "sd", "34": "mr", "163": "hy"}
INSPIRE_IT = {
    "rs": "Sistemi di coordinate", "gg": "Sistemi di griglie geografiche", "gn": "Nomi geografici",
    "au": "Unità amministrative", "ad": "Indirizzi", "cp": "Parcelle catastali", "tn": "Reti di trasporto",
    "hy": "Idrografia", "ps": "Siti protetti", "el": "Elevazione", "lc": "Copertura del suolo",
    "oi": "Orto immagini", "ge": "Geologia", "su": "Unità statistiche", "bu": "Edifici", "so": "Suolo",
    "lu": "Utilizzo del territorio", "hh": "Salute umana e sicurezza", "us": "Servizi di pubblica utilità",
    "ef": "Impianti di monitoraggio ambientale", "pf": "Produzione e impianti industriali",
    "af": "Impianti agricoli e di acquacoltura", "pd": "Distribuzione della popolazione",
    "am": "Zone sottoposte a gestione e limitazioni", "nz": "Zone a rischio naturale",
    "ac": "Condizioni atmosferiche", "mf": "Elementi geografici meteorologici",
    "of": "Elementi geografici oceanografici", "sr": "Regioni marine", "br": "Regioni biogeografiche",
    "hb": "Habitat e biotopi", "sd": "Distribuzione delle specie", "er": "Risorse energetiche",
    "mr": "Risorse minerarie",
}


def esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


def add(d, key, code, label, origine):
    """Aggiunge una voce di classificazione senza duplicati, ricordando se è derivata o manuale."""
    for x in d[key]:
        if x["code"] == code:
            return
    d[key].append({"code": code, "label": label, "origine": origine})


def classifica(row, nvs):
    """Classificazione standard di un sottotema: derivata dai P02 + agganci manuali."""
    c = {k: [] for k in ("p02", "p03", "p08", "inspire", "iso", "msfd")}
    lab = nvs["lab"]
    for code in row["p02"].split():
        if code not in nvs["p02"]:
            raise SystemExit(f"{row['id']}: {code} non è in nvs_cache.json -> lancia scripts/aggiorna_nvs.py")
        p = nvs["p02"][code]
        add(c, "p02", code, p["l"], "manuale")
        for g in p["P03"]:
            add(c, "p03", g, lab["P03"].get(g, g), "NVS")
        for t in p["P22"]:
            ins = P22_INSPIRE.get(t)
            if ins:
                add(c, "inspire", ins, INSPIRE_IT[ins], "NVS")
        for i in p["P05"]:
            add(c, "iso", i, lab["P05"].get(i, i), "NVS")
        for m in p["C47"]:
            add(c, "msfd", m, lab["C47"].get(m, m), "NVS")
    for g in row["p03_manuale"].split():
        add(c, "p03", g, lab["P03"].get(g, g), "manuale")
    for ins in row["inspire_manuale"].split():
        add(c, "inspire", ins, INSPIRE_IT[ins], "manuale")
    for g in c["p03"]:
        for d in nvs["p03"].get(g["code"], []):
            add(c, "p08", d, lab["P08"].get(d, d), "NVS")
    return c


def main():
    nvs = json.loads(CACHE.read_text(encoding="utf-8"))
    rows = list(csv.DictReader(SRC.open(encoding="utf-8")))
    ids = {r["id"] for r in rows}
    for r in rows:
        if r["livello"] == "sottotema" and r["padre"] not in ids:
            raise SystemExit(f"Padre mancante per {r['id']}: {r['padre']}")
        for ins in r["inspire_manuale"].split():
            if ins not in INSPIRE_IT:
                raise SystemExit(f"{r['id']}: tema INSPIRE sconosciuto {ins}")

    # correlati simmetrici
    rel = {r["id"]: set() for r in rows}
    for r in rows:
        for o in r["correlati"].split():
            if o not in ids:
                raise SystemExit(f"{r['id']}: correlato sconosciuto {o}")
            rel[r["id"]].add(o)
            rel[o].add(r["id"])

    children = {}
    for r in rows:
        if r["padre"]:
            children.setdefault(r["padre"], []).append(r["id"])
    cls = {r["id"]: classifica(r, nvs) for r in rows}

    # --- Turtle: solo le nostre affermazioni (gerarchia, correlati, agganci scritti da noi)
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
        for o in sorted(rel[r["id"]]):
            lines.append(f"    skos:related temi:{o} ;")
        for code in r["p02"].split():
            lines.append(f"    skos:narrowMatch <{NVS.format(coll='P02', code=code)}> ;")
        for code in r["p03_manuale"].split():
            lines.append(f"    skos:closeMatch <{NVS.format(coll='P03', code=code)}> ;")
        for code in r["inspire_manuale"].split():
            lines.append(f"    skos:broadMatch <{INSPIRE.format(code=code)}> ;")
        if r["note"]:
            lines.append(f'    skos:editorialNote "{esc(r["note"])}"@it ;')
        lines[-1] = lines[-1][:-2] + " ."
        ttl += lines + [""]
    OUT_TTL.write_text("\n".join(ttl), encoding="utf-8")

    # --- JSON per il sito: albero, correlati, classificazione standard (derivata + manuale)
    label = {r["id"]: r["etichetta_it"] for r in rows}
    tree = []
    for r in rows:
        if r["livello"] != "macrotema":
            continue
        subs = []
        for s in rows:
            if s["padre"] != r["id"]:
                continue
            subs.append({
                "id": s["id"], "uri": BASE + s["id"], "label": s["etichetta_it"], "label_en": s["etichetta_en"],
                "definizione": s["definizione"], "keyword": f"solve-{s['id']}",
                "correlati": [{"id": o, "label": label[o]} for o in sorted(rel[s["id"]])],
                "classificazione": cls[s["id"]], "note": s["note"],
            })
        # il macrotema eredita l'unione delle classificazioni dei figli (solo P03, P08, INSPIRE, ISO)
        agg = {k: [] for k in ("p03", "p08", "inspire", "iso")}
        for s in subs:
            for k in agg:
                for x in s["classificazione"][k]:
                    if all(y["code"] != x["code"] for y in agg[k]):
                        agg[k].append({"code": x["code"], "label": x["label"]})
        tree.append({
            "id": r["id"], "uri": BASE + r["id"], "label": r["etichetta_it"], "label_en": r["etichetta_en"],
            "definizione": r["definizione"], "keyword": f"solve-{r['id']}", "note": r["note"],
            "classificazione": agg, "sottotemi": subs,
        })
    OUT_JSON.write_text(json.dumps({"nvs_letto_il": nvs["_info"]["letto_il"], "temi": tree},
                                   ensure_ascii=False, indent=2), encoding="utf-8")

    # --- JSON compatto per il grafo (sito/vocabolario.html); '*' = aggancio scritto a mano
    def comp(xs):
        return [x["code"] + "|" + x["label"] + ("*" if x.get("origine") == "manuale" else "") for x in xs]
    grafo = [{
        "id": m["id"], "l": m["label"], "d": m["definizione"],
        "s": [{"id": s["id"], "l": s["label"], "d": s["definizione"], "r": [x["id"] for x in s["correlati"]],
               "p02": comp(s["classificazione"]["p02"]), "p03": comp(s["classificazione"]["p03"]),
               "p08": comp(s["classificazione"]["p08"]), "in": comp(s["classificazione"]["inspire"]),
               "iso": comp(s["classificazione"]["iso"]), "ms": len(s["classificazione"]["msfd"]), "n": s["note"]}
              for s in m["sottotemi"]],
    } for m in tree]
    (VOC / "temi_grafo.json").write_text(json.dumps(grafo, ensure_ascii=False, separators=(",", ":")),
                                         encoding="utf-8")

    n_sub = sum(len(n["sottotemi"]) for n in tree)
    n_rel = sum(len(v) for v in rel.values()) // 2
    print(f"{len(tree)} macrotemi, {n_sub} sottotemi, {n_rel} correlazioni -> {OUT_TTL.name}, {OUT_JSON.name}")


if __name__ == "__main__":
    main()
