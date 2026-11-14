import json, sys, os
# usage: python3 merge.py teams.txt matchs.txt old_dir out_dir now_iso yesterday(YYYY-MM-DD)
PRE_E, PRE_M = "2000000053397", "200000014"
tf, mf, old_dir, out, now, veille = sys.argv[1:7]
os.makedirs(out, exist_ok=True)
cls = {p: [] for p in "ABCD"}; mt = {p: [] for p in "ABCD"}
for l in open(tf).read().splitlines():
    if not l.strip(): continue
    s, p, pos, pts, j, v, d, pm, pe, pen = l.split("|")
    cls[p].append(dict(id=PRE_E + s, pos=int(pos), pts=int(pts), j=int(j), v=int(v), d=int(d),
                       pm=int(pm), pe=int(pe), pen=int(pen or 0)))
for l in open(mf).read().splitlines():
    if not l.strip(): continue
    mid, p, j, date, joue, e1, e2, s1, s2 = l.split("|")
    mt[p].append(dict(id=PRE_M + mid, j=int(j), date=date + ":00", joue=joue == "1",
                      eq1=PRE_E + e1, eq2=PRE_E + e2,
                      s1=int(s1) if s1 not in ("", "null") else None,
                      s2=int(s2) if s2 not in ("", "null") else None))
problems = []
for p in "ABCD":
    if len(cls[p]) != 6: problems.append(f"poule {p}: {len(cls[p])} équipes au classement (6 attendues)")
    if len(mt[p]) != 30: problems.append(f"poule {p}: {len(mt[p])} matchs (30 attendus)")
    calc = {}
    for m in mt[p]:
        if m["joue"] and m["s1"] is not None and m["s2"] is not None and m["s1"] != m["s2"]:
            w, lo = (m["eq1"], m["eq2"]) if m["s1"] > m["s2"] else (m["eq2"], m["eq1"])
            calc[w] = calc.get(w, 0) + 2; calc[lo] = calc.get(lo, 0) + 1
    for c in cls[p]:
        if calc.get(c["id"], 0) != c["pts"]:
            problems.append(f"poule {p}: points FFBB {c['pts']} != recalcul {calc.get(c['id'], 0)} pour {c['id']} (forfait ou pénalité ?)")
    mt[p].sort(key=lambda m: (m["j"], m["date"], m["id"])); cls[p].sort(key=lambda c: c["pos"])

def load_old(p):
    for cand in (f"{old_dir}/poules/{p}.json", f"{old_dir}/{p}.json"):
        if os.path.exists(cand):
            d = json.load(open(cand)); return d.get("data", d)
    return {}

changed, new_results, played_yesterday = [], [], []
for p in "ABCD":
    old = load_old(p)
    om = {m["id"]: m for m in old.get("matchs", [])}
    for m in mt[p]:
        o = om.get(m["id"])
        if m["joue"] and m["date"].startswith(veille): played_yesterday.append(m["id"])
        if not o or (o.get("joue"), o.get("s1"), o.get("s2"), o.get("date")) != (m["joue"], m["s1"], m["s2"], m["date"]):
            if m["joue"] and (not o or not o.get("joue") or (o.get("s1"), o.get("s2")) != (m["s1"], m["s2"])):
                new_results.append(f"{p} J{m['j']} {m['eq1'][-2:]}-{m['eq2'][-2:]} {m['s1']}-{m['s2']}")
            changed.append(p)
    if [ (c["id"], c["pos"], c["pts"], c["v"], c["d"], c["pm"], c["pe"]) for c in cls[p] ] != \
       [ (c.get("id"), c.get("pos"), c.get("pts"), c.get("v"), c.get("d"), c.get("pm"), c.get("pe")) for c in old.get("classement", []) ]:
        changed.append(p)
changed = sorted(set(changed))
for p in changed:
    json.dump(dict(nom=f"Poule {p}", classement=cls[p], matchs=mt[p], maj_le=now),
              open(f"{out}/poules_{p}.json", "w"), ensure_ascii=False)
lastj = max([m["j"] for p in mt for m in mt[p] if m["joue"]] or [0])
json.dump(dict(maj_le=now, derniere_journee=lastj), open(f"{out}/meta_etat.json", "w"), ensure_ascii=False)
print(json.dumps(dict(match_la_veille=len(played_yesterday), poules_modifiees=changed,
                      nouveaux_resultats=new_results, derniere_journee=lastj, problemes=problems), ensure_ascii=False, indent=1))
