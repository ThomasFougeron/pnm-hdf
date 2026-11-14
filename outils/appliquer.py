"""Mise à jour hebdomadaire de la page PNM Hauts-de-France, à lancer depuis la racine du dépôt.

usage: python3 outils/appliquer.py teams.txt matchs.txt <maintenant ISO> <veille AAAA-MM-JJ>

teams.txt / matchs.txt : sortie de outils/extract.js (24 et 120 lignes).
Met à jour donnees/ (poules, meta, pronos) et index.html seulement s'il y a du nouveau.
Affiche un résumé JSON ; "ecrit": true quand des fichiers ont changé.
"""
import json, os, shutil, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
O = os.path.join(ROOT, "outils"); D = os.path.join(ROOT, "donnees")


def run(*args):
    r = subprocess.run([sys.executable, *args], capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"échec de {' '.join(args)} :\n{r.stderr}")
    return r.stdout


def main(teams, matchs, now, veille):
    tmp = tempfile.mkdtemp()
    res = json.loads(run(os.path.join(O, "merge.py"), teams, matchs, D, tmp, now, veille))
    res["ecrit"] = False
    if not res["poules_modifiees"]:
        print(json.dumps(res, ensure_ascii=False, indent=1)); return
    for p in res["poules_modifiees"]:
        shutil.copy(os.path.join(tmp, f"poules_{p}.json"), os.path.join(D, "poules", f"{p}.json"))
    meta = json.load(open(os.path.join(D, "meta.json")))
    meta.update(json.load(open(os.path.join(tmp, "meta_etat.json"))))
    json.dump(meta, open(os.path.join(D, "meta.json"), "w"), ensure_ascii=False)
    pr = os.path.join(tmp, "pronos.json")
    res["pronos"] = run(os.path.join(O, "pronos.py"), os.path.join(D, "poules"), os.path.join(D, "equipes"),
                        os.path.join(D, "pronos.json"), pr, now).strip().splitlines()
    shutil.copy(pr, os.path.join(D, "pronos.json"))
    run(os.path.join(O, "build_static.py"), os.path.join(O, "page.html"), os.path.join(D, "poules"),
        os.path.join(D, "equipes"), os.path.join(D, "meta.json"), os.path.join(D, "pronos.json"),
        os.path.join(ROOT, "index.html"))
    res["ecrit"] = True
    print(json.dumps(res, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main(*sys.argv[1:5])
