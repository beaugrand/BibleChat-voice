/* BibleChat search guide (web/guide.json), shared by the phone (web/index.html), the computer page
   (bibleask/web/index.html) and the Study Paths (web/paths.js). The computer's Python twin is bibleask/guide.py;
   tests/test_guide.py runs this file with Node.js and checks both give the same answers.

   - Key passages: for a broad topic ("women", "prayer", "money") every side the Bible shows, grouped by theme,
     shown above the search results, so the best word matches can't tell only half the story.
   - Which Bibles a book is in: "In Catholic and Orthodox Bibles" next to Sirach, "Ethiopian Bible only" next to 1 Enoch.
   - "In the original": where the Hebrew or Greek says more than the translation (Psalm 68:11).
   - "In context": who wrote a hard verse, to whom, and the verses around it (1 Corinthians 14:34).
   - Spread: for a broad question, the first answers come from several parts of the Bible, not one.
   Notes are BibleChat's, never Scripture, and every box says so. Nothing here writes a verse. */
"use strict";
const BCGuide = (() => {
  let D = null, P = null, NOTES = new Map(), SECTION = new Map();
  const REF = /^(.+?)\s+(\d+):(\d+)(?:-(\d+))?$/;
  const esc = s => String(s).replace(/[&<>"']/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]));
  function parseRef(r){ const m = REF.exec(String(r).trim()); return m ? {book: m[1], c: +m[2], v1: +m[3], v2: m[4] ? +m[4] : +m[3]} : null; }
  function use(d){
    D = d; NOTES = new Map(); SECTION = new Map();
    for(const [key, n] of Object.entries(d.notes || {})){
      const p = parseRef(key); if(!p) continue;
      for(let v = p.v1; v <= p.v2; v++){ const k = p.book + "|" + p.c + "|" + v, cur = NOTES.get(k) || {};
        for(const [kind, val] of Object.entries(n)) if(!cur[kind]) cur[kind] = Object.assign({key}, val);
        NOTES.set(k, cur); }
    }
    for(const [name, books] of d.sections || []) for(const b of books) SECTION.set(b, name);
    return D;
  }
  /* load once; a page that can't load it (offline before the first visit) simply shows no guide */
  function load(url){
    if(!P) P = (typeof fetch === "function" ? fetch(url || "guide.json").then(r => { if(!r.ok) throw new Error(r.status); return r.json(); }) : Promise.reject(new Error("no fetch")))
      .then(use).catch(e => { P = null; return null; });
    return P;
  }

  /* ---------- words: letters a-z only, lower case (bibleask/guide.py words) ---------- */
  const words = t => String(t).toLowerCase().replace(/’/g, "'").match(/[a-z]+/g) || [];
  const contentWords = t => { const stop = new Set((D && D.stop) || []); return words(t).filter(w => !stop.has(w)); };
  function topicFor(q){
    if(!D) return null;
    const ws = words(q); if(!ws.length) return null;
    const hay = " " + ws.join(" ") + " "; let best = null, bestN = 0;
    for(const t of D.topics || []){ const n = (t.words || []).filter(w => hay.includes(" " + w + " ")).length; if(n > bestN){ best = t; bestN = n; } }
    return best;
  }
  const broad = q => !!topicFor(q) || (contentWords(q).length > 0 && contentWords(q).length <= 2);
  function canon(book){ if(!D) return null; const g = (D.canon.books || {})[book]; return g ? Object.assign({group: g}, D.canon.groups[g]) : null; }
  const notesFor = (book, c, v) => NOTES.get(book + "|" + c + "|" + v) || {};
  const sectionOf = book => SECTION.get(book) || (D && D.other_section) || "Other books";
  /* the first k with at most `cap` from one part of the Bible, best first; the rest after them (bibleask/guide.py spread) */
  function spread(items, bookOf, k = 8, cap = 3){
    const picked = [], skipped = [], count = new Map();
    for(let i = 0; i < items.length && picked.length < k; i++){
      const s = sectionOf(bookOf(items[i]));
      if((count.get(s) || 0) < cap){ picked.push(i); count.set(s, (count.get(s) || 0) + 1); } else skipped.push(i);
    }
    for(const i of skipped){ if(picked.length >= k) break; picked.push(i); }
    const chosen = new Set(picked);
    return picked.map(i => items[i]).concat(items.filter((_, i) => !chosen.has(i)));
  }

  /* ---------- what the pages show (one look on phone and computer; styles below) ---------- */
  const CSS = `.bc-canon{display:inline-block;font:600 11.5px system-ui,sans-serif;color:var(--muted);border:1px solid var(--line);border-radius:999px;padding:1px 8px;margin:0 6px 2px 0;vertical-align:middle;white-space:nowrap;cursor:help}
.bc-note{font:13.5px/1.45 system-ui,sans-serif;color:var(--text);background:var(--panel2);border-left:3px solid var(--accent);border-radius:6px;padding:7px 10px;margin:6px 0 2px}
.bc-note b{font-weight:650}.bc-note .bc-by{display:block;font-size:11.5px;color:var(--muted);margin-top:3px}
.bc-note a,.bc-keys a{font-weight:600;text-decoration:none;color:var(--accent);white-space:nowrap}
.bc-keys{border:1px solid var(--accent);border-radius:10px;padding:8px 12px;margin:0 0 12px;background:var(--panel2)}
.bc-keys>summary{cursor:pointer;font:650 15px system-ui,sans-serif;list-style-position:outside}
.bc-keys .bc-lead{font:13px/1.45 system-ui,sans-serif;color:var(--muted);margin:6px 0}
.bc-th{padding:7px 0;border-top:1px solid var(--line)}.bc-th:first-of-type{border-top:0}
.bc-th>b{display:block;font:650 14px/1.35 system-ui,sans-serif;margin-bottom:3px}
.bc-kv{font:15px/1.5 Georgia,"Times New Roman",serif;margin:3px 0}.bc-kv a{font:600 13px system-ui,sans-serif;margin-right:6px}
.bc-keys .bc-path{margin-top:8px}
.bc-parts{display:flex;flex-wrap:wrap;gap:6px;margin:4px 0 8px;font:12.5px system-ui,sans-serif;color:var(--muted);align-items:center}
.bc-parts button{font:600 12.5px system-ui,sans-serif;border:1px solid var(--line);background:var(--panel2);color:var(--text);border-radius:999px;padding:3px 10px;cursor:pointer}
.bc-parts button[aria-pressed=true]{border-color:var(--accent);color:var(--accent)}`;
  function style(){ if(typeof document === "undefined" || document.getElementById("bcGuideCss")) return; const s = document.createElement("style"); s.id = "bcGuideCss"; s.textContent = CSS; document.head.appendChild(s); }
  const plainLink = (book, c, v1, v2, label) => esc(label);
  const refLabel = (p, name) => (name ? name(p.book) : p.book) + " " + p.c + ":" + p.v1 + (p.v2 > p.v1 ? "–" + p.v2 : "");

  /* 📚 the tag beside a book that isn't in every Bible */
  function tagHtml(book){ const c = canon(book); style(); return c ? `<span class="bc-canon" title="${esc(c.long)}">📚 ${esc(c.short)}</span>` : ""; }

  /* 🔤 In the original / 🧭 In context, under a verse. o.link(book, c, v1, v2, label) makes a reference a link. */
  function block(kind, x, o, where){
    const link = o.link || plainLink, name = o.name;
    const by = `<span class="bc-by">${esc(o.byLabel || "A BibleChat note, not Scripture.")}${where ? " (" + esc(where) + ")" : ""}</span>`;
    if(kind === "original") return `<div class="bc-note bc-orig"><b>🔤 ${esc(o.originalLabel || "In the original")}:</b> ${esc(x.text)}${by}</div>`;
    const refs = (x.refs || []).map(parseRef).filter(Boolean).map(p => link(p.book, p.c, p.v1, p.v2, refLabel(p, name)));
    return `<div class="bc-note bc-ctx"><b>🧭 ${esc(o.contextLabel || "In context")}:</b> ${esc(x.text)}${refs.length ? ` <span class="bc-read">${esc(o.readWith || "Read with")}: ${refs.join(" · ")}</span>` : ""}${by}</div>`;
  }
  function notesHtml(book, c, v, o = {}){
    const n = notesFor(book, c, v); style();
    return (n.original ? block("original", n.original, o) : "") + (n.context ? block("context", n.context, o) : "");
  }
  /* the notes of every verse in a passage, each once (a note on 1 Timothy 2:11-12 shows once, not twice) */
  function passageNotesHtml(book, c, v1, v2, o = {}){
    const seen = new Set(); let h = ""; style();
    for(let v = v1; v <= v2; v++){ const n = notesFor(book, c, v);
      for(const kind of ["original", "context"]) if(n[kind] && !seen.has(kind + n[kind].key)){
        seen.add(kind + n[kind].key);
        h += block(kind, n[kind], o, v2 > v1 ? (o.name ? o.name(book) : book) + " " + n[kind].key.replace(/^.+?\s(\d+:)/, "$1").replace("-", "–") : "");
      }
    }
    return h;
  }
  /* 📌 Key passages for a broad topic, by theme. verse(book, c, v1, v2) -> the reader's text or "" (then the reference
     alone shows). o.open: start unfolded; o.path: {id, title} of its Study Path (the page wires data-guidepath). */
  function keysHtml(t, verse, o = {}){
    if(!t) return ""; style();
    const link = o.link || plainLink, name = o.name;
    const th = t.themes.map(x => `<div class="bc-th"><b>${esc(x.point)}</b>${x.refs.map(parseRef).filter(Boolean).map(p => {
      const txt = verse ? verse(p.book, p.c, p.v1, p.v2) : ""; const short = txt && txt.length > 220 ? txt.slice(0, 217).replace(/\s+\S*$/, "") + " …" : txt;
      return `<div class="bc-kv">${link(p.book, p.c, p.v1, p.v2, refLabel(p, name))}${short ? esc(short) : ""}</div>`; }).join("")}</div>`).join("");
    return `<details class="bc-keys"${o.open ? " open" : ""}><summary>📌 ${esc(o.title || "Key passages")}: ${esc(t.title)}</summary>`
      + `<p class="bc-lead">${esc(o.lead || "Every side the Bible shows on this topic, grouped by theme. Hard verses are listed too; tap one to read it in its chapter.")}</p>${th}`
      + (o.path ? `<div class="bc-path"><button class="${esc(o.pathClass || "btn")}" data-guidepath="${esc(o.path.id)}">📜 ${esc(o.pathLabel || "Study Path")}: ${esc(o.path.title)}</button></div>` : "")
      + `</details>`;
  }
  /* what an AI gets besides the verses: the key passages by theme, the notes on the verses, and how to answer */
  function aiText(q, refs, o = {}){
    const t = topicFor(q), parts = [];
    if(t) parts.push("Key passages on " + t.title.toLowerCase() + " (from BibleChat's guide, by theme):\n" + t.themes.map(x => "- " + x.point + ": " + x.refs.join("; ")).join("\n"));
    const notes = [];
    for(const r of refs || []){ const p = parseRef(r); if(!p) continue; const c = canon(p.book), n = notesFor(p.book, p.c, p.v1);
      if(c) notes.push("- " + r + ": " + c.long);
      if(n.original) notes.push("- " + r + " (in the original): " + n.original.text);
      if(n.context) notes.push("- " + r + " (in context): " + n.context.text); }
    if(notes.length) parts.push("Notes from BibleChat (not Scripture):\n" + [...new Set(notes)].join("\n"));
    parts.push("Group the answer by theme. If the verses lean one way, say so, and use the key passages so every side the Bible shows is heard. Explain hard verses in their context. Say which verse supports each point." + (o.extra ? " " + o.extra : ""));
    return parts.join("\n\n");
  }

  return {load, use, ready: () => !!D, parseRef, words, contentWords, topicFor, broad, canon, notesFor, sectionOf, spread,
          sections: () => ((D && D.sections) || []).map(s => s[0]).concat([(D && D.other_section) || "Other books"]),
          tagHtml, notesHtml, passageNotesHtml, keysHtml, aiText, esc};
})();
if(typeof module !== "undefined") module.exports = BCGuide;
