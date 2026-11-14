window.__pnm = await (async () => {
  const PH = '200000002897554', PA = '200000003055243';
  const grab = (txt, key) => { const h = txt.replace(/\\\\/g, '\\').replace(/\\"/g, '"'); const out = []; let from = 0;
    while (true) { const i = h.indexOf('"' + key + '":[', from); if (i < 0) break; const st = i + key.length + 3; let j = st + 1, d = 1, s = false;
      for (; j < h.length && d > 0; j++) { const c = h[j]; if (s) { if (c === '\\') { j++; continue } if (c === '"') s = false; continue }
        if (c === '"') s = true; else if (c === '[' || c === '{') d++; else if (c === ']' || c === '}') d--; }
      try { out.push(JSON.parse(h.slice(st, j))) } catch (e) {} from = j; } return out; };
  const get = async u => { const r = await fetch(u, { credentials: 'include' }); if (!r.ok) throw new Error('HTTP ' + r.status); return r.text(); };
  const tc = await get('/ligues/hdf/competitions/pnm/classement?phase=' + PH + '&poule=' + PA);
  const tr = await get('/ligues/hdf/competitions/pnm?phase=' + PH + '&poule=' + PA);
  const P = grab(tc, 'poules').filter(Array.isArray).sort((a, b) => b.reduce((s, x) => s + (x.classements || []).length, 0) - a.reduce((s, x) => s + (x.classements || []).length, 0))[0] || [];
  const map = {}, tl = [], bad = [];
  for (const p of P) { const L = p.nom.replace('Poule ', ''); for (const c of (p.classements || [])) { const e = c.idEngagement; map[e.id] = L;
    if (!e.id.startsWith('2000000053397')) bad.push(e.id + ' ' + e.nom);
    tl.push([e.id.slice(-2), L, c.position, c.points, c.matchJoues, c.gagnes, c.perdus, c.paniersMarques, c.paniersEncaisses, c.penalites || 0].join('|')); } }
  const seen = new Set(), ml = [];
  for (const r of grab(tr, 'rencontres').flat()) { if (!r || !r.id || seen.has(r.id)) continue; seen.add(r.id);
    const a = r.idEngagementEquipe1?.id, b = r.idEngagementEquipe2?.id;
    if (!r.id.startsWith('200000014')) bad.push('match ' + r.id);
    const sc = v => (v === null || v === undefined || v === '') ? '' : v;
    ml.push([r.id.slice(-6), map[a] || map[b] || '?', r.numeroJournee, String(r.date_rencontre).slice(0, 16), r.joue ? 1 : 0, (a || '').slice(-2), (b || '').slice(-2), sc(r.resultatEquipe1), sc(r.resultatEquipe2)].join('|')); }
  ml.sort();
  return { tl, ml, bad };
})();
'equipes ' + __pnm.tl.length + ' | matchs ' + __pnm.ml.length + ' | joues ' + __pnm.ml.filter(l => l.split('|')[4] === '1').length + ' | anomalies ' + __pnm.bad.length + (__pnm.bad.length ? ' : ' + __pnm.bad.slice(0, 5).join(' ; ') : '')
