"""Genera i dati compatti per la home di test (sito/data/temi.json, sito/data/layer.json)."""
import json, pathlib
R = pathlib.Path(__file__).resolve().parent.parent
t = json.load(open(R / 'vocabolario/temi.json'))
temi = [{"id": m["id"], "l": m["label"], "d": m.get("definizione", ""),
         "s": [{"id": s["id"], "l": s["label"], "d": s.get("definizione", ""), "r": [c["id"] for c in s.get("correlati", [])]}
               for s in m["sottotemi"]]} for m in t["temi"]]
lay = [{k: l[k] for k in ("pk", "t", "ti", "ab", "dt", "sub", "mac")}
       for l in json.load(open(R / 'dati/layer_temi.json')) if l["mac"]]
(R / 'sito/data').mkdir(exist_ok=True)
json.dump(temi, open(R / 'sito/data/temi.json', 'w'), ensure_ascii=False)
json.dump(lay, open(R / 'sito/data/layer.json', 'w'), ensure_ascii=False)
print(len(temi), 'temi,', len(lay), 'risorse classificate')
