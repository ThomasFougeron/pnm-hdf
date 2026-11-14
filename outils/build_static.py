"""Génère la version publique autonome de la page PNM (données intégrées, aucune base requise).

usage: python3 build_static.py <page.html> <dossier_poules> <dossier_equipes> <meta.json> <pronos.json> <sortie/index.html>
"""
import json, os, sys, glob


def load(path):
    d = json.load(open(path))
    return d["data"] if isinstance(d, dict) and isinstance(d.get("data"), dict) else d


def main(page, pdir, edir, meta, pronos, out):
    html = open(page, encoding="utf-8").read()
    data = {
        "poules": {p: load(os.path.join(pdir, f"{p}.json")) for p in "ABCD"},
        "equipes": {os.path.basename(f)[:-5].replace("equipes_", ""): load(f) for f in glob.glob(os.path.join(edir, "*.json"))},
        "meta": load(meta) if os.path.exists(meta) else None,
        "pronos": load(pronos) if os.path.exists(pronos) else None,
    }
    blob = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    marker = "<!--PNM_DATA-->"
    assert marker in html, "marqueur <!--PNM_DATA--> absent de la page"
    body = html.replace(marker, f"<script>window.__PNM_DATA={blob};</script>")
    doc = ("<!doctype html><html lang=\"fr\"><head><meta charset=\"utf-8\">"
           "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1,viewport-fit=cover\">"
           "<meta name=\"description\" content=\"Classement, résultats et course à la montée de la Pré-Nationale Masculine Hauts-de-France 2026-2027.\">"
           "<style>:root{color-scheme:light}body{margin:0;font:14px system-ui,-apple-system,sans-serif}img{max-width:100%}[hidden]{display:none!important}</style>"
           "</head><body>" + body + "</body></html>")
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    open(out, "w", encoding="utf-8").write(doc)
    print(out, len(doc), "octets |", len(data["equipes"]), "équipes |",
          sum(len(p["matchs"]) for p in data["poules"].values()), "matchs | pronos:", bool(data["pronos"]))


if __name__ == "__main__":
    main(*sys.argv[1:7])
