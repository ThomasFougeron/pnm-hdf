"""Pronostics de montée PNM HdF — modèle de notes (écart de points) + Monte-Carlo.

usage: python3 pronos.py <dossier_poules> <dossier_equipes> <ancien_pronos.json|-> <sortie.json> <maintenant_iso>
- dossier_poules : A.json..D.json (documents "poules" de la base, avec ou sans enveloppe {"data": ...})
- dossier_equipes : un fichier JSON par équipe (documents "equipes", champ n1 = saison 2025-26)
Python pur (aucune dépendance), résultat reproductible (graine fixe).
"""
import json, os, sys, glob, math, random

HYP = dict(off_nm3=8.0, off_rm2=-10.0, w=0.6, tau=6.0, sigma=12.0, home=3.0, nsim=20000, montees=3,
           format="2 premiers de chaque poule -> poule d'accession à 8 (aller-retour), 3 premiers montent")


def load(path):
    d = json.load(open(path))
    return d.get("data", d) if isinstance(d, dict) and "data" in d and isinstance(d["data"], dict) else d


def inverse(m):
    n = len(m); a = [row[:] + [1.0 if i == j else 0.0 for j in range(n)] for i, row in enumerate(m)]
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(a[r][c])); a[c], a[p] = a[p], a[c]
        pv = a[c][c]; a[c] = [x / pv for x in a[c]]
        for r in range(n):
            if r != c and a[r][c]:
                f = a[r][c]; a[r] = [x - f * y for x, y in zip(a[r], a[c])]
    return [row[n:] for row in a]


def cholesky(m):
    n = len(m); L = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1):
            s = sum(L[i][k] * L[j][k] for k in range(j))
            L[i][j] = math.sqrt(max(m[i][i] - s, 1e-12)) if i == j else (m[i][j] - s) / L[j][j]
    return L


def main(pdir, edir, old_path, out_path, now):
    P = {p: load(os.path.join(pdir, f"{p}.json")) for p in "ABCD"}
    E = {}
    for f in glob.glob(os.path.join(edir, "*.json")):
        d = load(f); eid = os.path.basename(f)[:-5].replace("equipes_", "")
        E[eid] = d
    ids = sorted(E); ix = {t: i for i, t in enumerate(ids)}; N = len(ids)
    h = HYP
    # 1. note de départ (saison 2025-26, ajustée par division, régressée vers la moyenne)
    mu = [0.0] * N
    for t, e in E.items():
        n1 = e.get("n1") or {}
        g = (n1.get("v", 0) + n1.get("d", 0)) or 1
        m = n1.get("ecart", 0) / g
        m += h["off_nm3"] if n1.get("division") == "NM3" else h["off_rm2"] if n1.get("division") == "RM2" else 0.0
        mu[ix[t]] = h["w"] * m
    avg = sum(mu) / N; mu = [x - avg for x in mu]
    # 2. régression bayésienne sur les matchs joués : écart = note_dom - note_ext + avantage terrain
    prec = [[(1 / h["tau"] ** 2 if i == j else 0.0) for j in range(N)] for i in range(N)]
    rhs = [x / h["tau"] ** 2 for x in mu]
    joues = 0
    for p in P.values():
        for m in p["matchs"]:
            if not m.get("joue") or m.get("s1") is None or m["s1"] == m["s2"]: continue  # 0-0 = pénalité, pas un vrai score
            a, b = ix[m["eq1"]], ix[m["eq2"]]; y = m["s1"] - m["s2"] - h["home"]; s2 = h["sigma"] ** 2
            prec[a][a] += 1 / s2; prec[b][b] += 1 / s2; prec[a][b] -= 1 / s2; prec[b][a] -= 1 / s2
            rhs[a] += y / s2; rhs[b] -= y / s2; joues += 1
    cov = inverse(prec)
    post = [sum(cov[i][k] * rhs[k] for k in range(N)) for i in range(N)]
    sd = [math.sqrt(cov[i][i]) for i in range(N)]
    L = cholesky(cov)
    # 3. Monte-Carlo : fin de saison régulière + phase d'accession supposée
    rnd = random.Random(20261012)
    first = [0] * N; top2 = [0] * N; promo = [0] * N
    for _ in range(h["nsim"]):
        z = [rnd.gauss(0, 1) for _ in range(N)]
        r = [post[i] + sum(L[i][k] * z[k] for k in range(i + 1)) for i in range(N)]
        qual = []
        for p in P.values():
            teams = [c["id"] for c in p["classement"]]
            w = {t: 0 for t in teams}; d = {t: 0.0 for t in teams}
            for m in p["matchs"]:
                a, b = m["eq1"], m["eq2"]
                if m.get("joue") and m.get("s1") is not None:
                    mg = m["s1"] - m["s2"]
                    if mg == 0: continue  # défaite des deux équipes (pénalité) : pas de victoire
                else:
                    mg = r[ix[a]] - r[ix[b]] + h["home"] + rnd.gauss(0, h["sigma"])
                    if mg == 0: mg = 1
                w[a if mg > 0 else b] += 1; d[a] += mg; d[b] -= mg
            order = sorted(teams, key=lambda t: (w[t], d[t]), reverse=True)
            first[ix[order[0]]] += 1
            for t in order[:2]: top2[ix[t]] += 1
            qual += order[:2]
        wq = {t: 0 for t in qual}; dq = {t: 0.0 for t in qual}
        for a in qual:
            for b in qual:
                if a == b: continue
                mg = r[ix[a]] - r[ix[b]] + h["home"] + rnd.gauss(0, h["sigma"])
                if mg == 0: mg = 1
                wq[a if mg > 0 else b] += 1; dq[a] += mg; dq[b] -= mg
        for t in sorted(qual, key=lambda t: (wq[t], dq[t]), reverse=True)[:h["montees"]]:
            promo[ix[t]] += 1
    n = h["nsim"]
    lastj = max([m["j"] for p in P.values() for m in p["matchs"] if m.get("joue")] or [0])
    equipes = sorted(({"id": t, "note": round(post[ix[t]], 1), "sd": round(sd[ix[t]], 1),
                       "prior": round(mu[ix[t]], 1), "p1": round(100 * first[ix[t]] / n, 1),
                       "p2": round(100 * top2[ix[t]] / n, 1), "pm": round(100 * promo[ix[t]] / n, 1)} for t in ids),
                     key=lambda e: -e["pm"])
    hist = []
    if old_path and old_path != "-" and os.path.exists(old_path):
        hist = (load(old_path) or {}).get("historique", [])
    hist = [x for x in hist if x.get("journee") != lastj]
    hist.append({"date": now[:10], "journee": lastj, "pm": {e["id"][-2:]: e["pm"] for e in equipes}})
    out = {"calcule_le": now, "apres_journee": lastj, "matchs_joues": joues, "hypotheses": HYP,
           "equipes": equipes, "historique": hist[-12:]}
    json.dump(out, open(out_path, "w"), ensure_ascii=False)
    for e in equipes[:6]:
        print(f"{E[e['id']].get('court', e['id']):34s} montée {e['pm']:5.1f}%  1er {e['p1']:5.1f}%  top2 {e['p2']:5.1f}%")
    print("total montée", round(sum(e["pm"] for e in equipes), 1), "| après J", lastj, "|", joues, "matchs")


if __name__ == "__main__":
    main(*sys.argv[1:6])
