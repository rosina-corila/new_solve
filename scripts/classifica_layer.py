"""Prima classificazione automatica dei layer pubblici di SOLVe sui sottotemi del vocabolario.

Uso:  python scripts/classifica_layer.py

Legge  dati/catalogo_solve.json   (raccolta delle risorse pubbliche dall'API di SOLVe)
Scrive dati/classificazione.csv   (una riga per layer: sottotemi proposti, regola che li ha scelti, colonna di revisione)
       dati/layer_temi.json       (dati per la home: layer con i loro sottotemi)

Le regole sono espressioni regolari sul titolo, sul nome del layer e sull'abstract.
La colonna "revisione" del CSV, se compilata (id di sottotemi separati da spazio, oppure "escludi"),
prevale sulla proposta automatica: è il modo per correggere a mano senza toccare le regole.
"""
import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAT = ROOT / "dati" / "catalogo_solve.json"
OUT_CSV = ROOT / "dati" / "classificazione.csv"
OUT_JSON = ROOT / "dati" / "layer_temi.json"
VOC = ROOT / "vocabolario" / "temi.json"

# sottotema -> regex (applicata a titolo + nome layer + abstract, in minuscolo)
REGOLE = {
    "idro-livello": r"mareograf|marea|livello del mare|\brmn\b|\brmlv\b|zero idrometrico|meteo-mareograf",
    "idro-correnti": r"corrent|adcp|portat[ae] alle bocche|velocit[aà] della corrente",
    "idro-onde": r"\bond[ae]\b|moto ondoso|wave",
    "idro-opere": r"\bmose\b|bocch[ae] di porto|paratoi|cantier",
    "apporti-fiumi": r"fium|idrometr|livenza|portat[ae]|\bdese\b|osellino|corsi d'acqua",
    "apporti-carichi": r"bacino scolante|carichi|scarich",
    "apporti-falda": r"falda|piezometr|sotterrane|cuneo salino|risalita capillare",
    "apporti-aria": r"\baria\b|atmosfer|polver|pm10|deposimetr|deposizion|samanet|emission|\bco\b -|\bso2\b|\bno2\b|ozono|concentrazione massima|concentrazione media",
    "apporti-rumore": r"rumore|acustic",
    "colonna-ts": r"temperatura|salinit|\bctd\b|sond[ae] multiparametr|traiettoria asv|transetto test",
    "colonna-ossigeno": r"ossigeno|traiettoria asv|transetto test",
    "colonna-nutrienti": r"nutrient|azoto|fosforo|nitrat",
    "colonna-clorofilla": r"clorofill|fitoplancton|traiettoria asv|transetto test",
    "colonna-torbidita": r"torbidit|trasparenz|solidi sospesi|secchi|traiettoria asv|transetto test",
    "colonna-contaminanti": r"contaminant.*acqu|pfas|perfluoro|chimic[oa] acqu|qualit[aà] delle acque|sostanze prioritarie|chimica di supporto|mon_chimico_h2o|monitoraggio chimico acque",
    "colonna-stato": r"stato ecologico|stato chimico|corpi idrici|\bwfd\b|direttiva quadro|msfd|marine waters",
    "sedimenti-granulometria": r"granulometr|sedimenti superficiali",
    "sedimenti-contaminanti": r"sediment.*(chim|contamin|metall)|chem_sed|chimico sedimenti",
    "sedimenti-organica": r"sostanza organica|carbonio organico",
    "sedimenti-stratigrafia": r"carot|trivellat|stratigraf|sondagg",
    "sedimenti-sismica": r"sismic|shallows",
    "sedimenti-dinamica": r"erosion|sedimentazion|risospension|interriment",
    "habitat-morfologia": r"batimetr|morfolog|curve di livello|\bdtm\b|lidar|barene artificiali|velme|conterminazione",
    "habitat-carte": r"habitat|naturalit|zone umide|tegnue",
    "habitat-fanerogame": r"fanerogam|macroalgh|seagrass|zostera|cymodocea",
    "habitat-vegetazione": r"vegetazion|alofil|baccharis|atriplex|cladieto|foreste alluvionali|flora|blackstoni|arenaria|aristoloch|aster noci|anisantha",
    "habitat-protette": r"natura 2000|\bsic\b|\bzps\b|ramsar|aree? protett|aree marine protette|euap|siti protetti|\biba\b|stato conservazione",
    "biologia-avifauna": r"avifauna|uccell|limicoli|charadrius|calidris|himantopus|gulosus|golosus|somateria|nidific|fratino|cavaliere d'italia|marangone|thalasseus|sternula|sterna |sterna$|ichthyaetus|caprimulgus|lanius|dryocopus|\biba\b",
    "biologia-pesci": r"ittiofauna|pesci|ittic|silurus|siluri|bongo net|sciabica|fish",
    "biologia-benthos": r"benthos|bentonic|macrozoobenthos|pinna nobilis|molluschi|bivalv|chamelea|vongol|tapes|cladocora|ostricet|briccole|tegnue",
    "biologia-plancton": r"plancton|zooplancton",
    "biologia-alloctone": r"alloctone|invasiv|baccharis|siluro|silurus",
    "biologia-terrestri": r"coleotter|invertebrati terrestri|insett|canis aureus|sciacallo",
    "clima-meteo": r"meteo|vento|precipitaz|pioggia",
    "clima-scenari": r"scenari|simulat|modell[io]",
    "usi-pesca": r"pesca|acquacoltur|molluschicoltur|allevament|concessioni|lunate",
    "usi-trasporti": r"traffico|\bnavi\b|\bporti\b|portual|navigazion|\bais\b|rotte|compartiment|tracks",
    "usi-energia": r"eolic|energ",
    "usi-turismo": r"turism|fruizion|percors|visitator|pannelli informativi|ecotourism|operatori",
    "usi-patrimonio": r"beni culturali|archeolog|relitt|patrimonio|paesagg|vincol.*1497|mibact|beni e luoghi",
    "usi-pianificazione": r"\bmsp\b|zonizzazion|pianificazion|vincol|ordinanz|interdizion",
    "base-confini": r"confin|\bcomuni\b|regioni|province|limiti amministrativ",
    "base-idrografia": r"idrografi|bacini idrografici|specchi d'acqua|canali|reticolo",
    "base-immagini": r"ortofoto|drone|google|raster di riferimento|immagin",
}
# regole a livello di macrotema: per i layer che appartengono a un tema ma a nessun sottotema esistente
# (segnalano anche possibili lacune del vocabolario, es. mammiferi e rettili marini)
REGOLE_MACRO = {
    "biologia": r"tursiops|caretta|delfin|tartarug|genetica|genotip|monitoraggio biologico|enclosure",
    "colonna": r"aqualab|danubius|qualit[aà] dell'acqua",
    "base": r"edifici|cimiteri|case di riposo|dormitori",
}
COMP = {k: re.compile(v, re.I) for k, v in REGOLE.items()}
COMP.update({k: re.compile(v, re.I) for k, v in REGOLE_MACRO.items()})


def main():
    cat = json.loads(CAT.read_text(encoding="utf-8"))
    voc = json.loads(VOC.read_text(encoding="utf-8"))
    sub2mac = {s["id"]: m["id"] for m in voc["temi"] for s in m["sottotemi"]}

    revisioni = {}
    if OUT_CSV.exists():
        for r in csv.DictReader(OUT_CSV.open(encoding="utf-8")):
            if r.get("revisione", "").strip():
                revisioni[r["pk"]] = r["revisione"].strip()

    righe, layer = [], []
    for r in cat:
        testo_titolo = f"{r['ti']} {r.get('alt') or ''}"
        testo = f"{testo_titolo} {r.get('ab') or ''}"
        # prima il titolo; l'abstract solo se il titolo non basta
        trovati = [k for k, rx in COMP.items() if rx.search(testo_titolo)]
        fonte = "titolo"
        if not trovati:
            trovati = [k for k, rx in COMP.items() if rx.search(testo)]
            fonte = "abstract" if trovati else ""
        rev = revisioni.get(str(r["pk"]), "")
        finali = trovati
        if rev:
            finali = [] if rev == "escludi" else rev.split()
            fonte = "revisione"
        righe.append({
            "pk": r["pk"], "tipo": r["t"], "titolo": r["ti"], "proposta": " ".join(trovati),
            "fonte": fonte, "revisione": rev,
            "link": f"https://solve.corila.it/catalogue/#/{r['t']}/{r['pk']}",
        })
        if finali:
            layer.append({
                "pk": r["pk"], "t": r["t"], "ti": r["ti"], "ab": r.get("ab") or "", "dt": r.get("dt") or "",
                "sub": [s for s in finali if s in sub2mac], "mac": sorted({sub2mac.get(s, s) for s in finali}),
            })

    with OUT_CSV.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["pk", "tipo", "titolo", "proposta", "fonte", "revisione", "link"])
        w.writeheader()
        w.writerows(righe)
    OUT_JSON.write_text(json.dumps(layer, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    n = len(righe)
    k = sum(1 for x in righe if x["proposta"] or x["revisione"])
    print(f"{n} risorse pubbliche, {k} classificate ({k * 100 // n}%), {n - k} da classificare")


if __name__ == "__main__":
    main()
