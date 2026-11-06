/* 🕊 What would Jesus do? (web/situations.json, written by hand in packaging/situations.json and checked by
   packaging/build_situations.py). Someone types their situation under the search field; BibleChat recognises it from
   its words and answers with Scripture only: what Jesus said (His words in red), what Jesus did, and more verses.
   Everything happens on this phone: nothing typed here is sent anywhere or kept.
   This file only finds the situation and colours the words of Jesus; web/index.html draws the answer with the verses
   of the Bible being read. tests/test_situations.py runs it with Node.js. Nothing here writes a verse. */
"use strict";
const BCSituations = (() => {
  let D = null, P = null;
  const esc = s => String(s).replace(/[&<>"']/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]));
  function use(d){ D = d; return D; }
  /* load once; offline before the first visit the box simply says it can't load yet */
  function load(url){
    if(!P) P = (typeof fetch === "function" ? fetch(url || "situations.json").then(r => { if(!r.ok) throw new Error(r.status); return r.json(); }) : Promise.reject(new Error("no fetch")))
      .then(use).catch(e => { P = null; return null; });
    return P;
  }
  const list = () => D ? D.situations : [];
  const byId = id => list().find(s => s.id === id) || null;

  /* ---------- the words of what someone typed: lower case, ’ as ', letters, digits and ' only ---------- */
  function norm(t){ return " " + String(t).toLowerCase().replace(/[’‘`]/g, "'").replace(/[^a-z0-9']+/g, " ").trim() + " "; }
  /* a word also stands in its simple forms: worry → worries, worried; fire → fired; hurt → hurting */
  function forms(w){
    const f = [w, w + "s", w + "es", w + "ed", w + "d", w + "ing"];
    if(/e$/.test(w)) f.push(w.slice(0, -1) + "ing");
    if(/y$/.test(w)) f.push(w.slice(0, -1) + "ies", w.slice(0, -1) + "ied");
    return f;
  }
  /* how strongly one situation fits: a phrase ("laid off") counts 3, a word 2. Phrases are read first, longest first,
     and every word found is taken out, so "passed away" does not count "passed" a second time. */
  function score(s, text){
    let n = 0; const hit = [];
    const ws = s.words.slice().sort((a, b) => (b.includes(" ") - a.includes(" ")) || b.length - a.length);
    for(const w of ws){
      if(w.includes(" ")){
        if(!text.includes(" " + w + " ")) continue;
        text = text.split(" " + w + " ").join("  "); n += 3; hit.push(w);
      }else{
        const f = forms(w).find(f => text.includes(" " + f + " ")); if(!f) continue;
        text = text.split(" " + f + " ").join("  "); n += 2; hit.push(w);   // "worried" counts once, not for "worry" and "worried"
      }
    }
    return {n, hit};
  }
  /* the situations that fit, best first: the best one, and up to two more that fit nearly as well */
  function match(text, max){
    const t = norm(text); if(t.trim().length < 2) return [];
    const out = list().map(s => Object.assign({id: s.id, title: s.title}, score(s, t))).filter(x => x.n > 0)
      .sort((a, b) => b.n - a.n || list().findIndex(s => s.id === a.id) - list().findIndex(s => s.id === b.id));
    if(!out.length) return [];
    const top = out[0].n;
    return out.filter((x, i) => i === 0 || x.n * 2 >= top).slice(0, max || 3);
  }

  /* 🔴 the words of Jesus in red, only where the verse text is exactly the one the marks were made for
     (the same rule as the Study Paths, web/paths.js redHtml) */
  function fnv(t){ let h = 0x811c9dc5; for(let i = 0; i < t.length; i++){ h ^= t.charCodeAt(i); h = Math.imul(h, 16777619) >>> 0; } return h; }
  function redHtml(ref, t){
    const marks = D && D.red && D.red[ref];
    const m = marks && marks.find(x => x.n === t.length && x.h === fnv(t));
    if(!m) return esc(t);
    let out = "", at = 0;
    for(const [a, z] of m.s){ if(a < at || z > t.length) return esc(t); out += esc(t.slice(at, a)) + `<span class="wj-red">${esc(t.slice(a, z))}</span>`; at = z; }
    return out + esc(t.slice(at));
  }
  /* "Matthew 6:31-34" → {book, c, v1, v2} */
  function parseRef(r){ const m = /^(.+?)\s+(\d+):(\d+)(?:-(\d+))?$/.exec(String(r).trim()); return m ? {book: m[1], c: +m[2], v1: +m[3], v2: m[4] ? +m[4] : +m[3]} : null; }

  return {load, use, list, byId, match, norm, redHtml, parseRef, fnv, esc, about: () => D && D.about};
})();
if(typeof module !== "undefined") module.exports = BCSituations;
