/* BibleChat 📜 Study Paths: a starting question, steps through the text, then questions and answers.
   Shared by the phone (web/index.html) and the computer (bibleask/web/index.html). Each page hands in an
   adapter (BCPaths.mount) that loads Bible chapters and the study data its own way.

   The rules (packaging/build_paths.py and tests/test_paths.py check them):
   - Scripture only comes from the Bible files. A path holds references; this file never writes a verse.
   - Every step, question, fact and answer points to a verse. The answer to a question is the verse itself.
   - The notes of men (Scofield, Matthew Henry) only appear through noteBlock(), under their label and apart
     from the text, so the reader can judge whether the note matches the text.
   - The path asks; the reader concludes. No verdict anywhere.
   - Progress, notes, answers and scores stay on this device (localStorage). Nothing is sent anywhere. */
"use strict";
const BCPaths = (() => {
  const LABEL = {scofield: "Commentary (Scofield, 1917)", henry: "Commentary (Matthew Henry, Concise)"};
  const NAMES = {KJV: "King James Version", ETH: "Ethiopian Canon", BSB: "Berean Standard Bible", JASHER: "Book of Jasher (1840)"};
  const STOP_STRONGS = new Set("H853 H5921 H413 H834 H3588 H3605 H5973 H4480 H3808 H1961 H559 H3651 H1931 H2088 G3588 G2532 G1161 G846 G1722 G1519 G3754 G1063 G3756 G2076 G1510 G3739 G3778 G1537 G4314 G5100 G3361 G3767 G2443 G235 G1909 G1223 G3004 G2036".split(" "));
  let A = null, root = null, list = null, quoted = null;
  const cache = {};
  const S = {path: null, step: 0, view: "list", quiz: null};
  let lastView = null;   // where the reader was when a verse link took them to Read: "← Back to Study Paths" returns there
  const esc = s => String(s == null ? "" : s).replace(/[&<>"']/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]));
  const T = x => (typeof tr === "function" ? tr(x) : x);   // the phone's app language (web/i18n.js), where there is one
  const get = (k, d) => A.get("paths." + k, d), set = (k, v) => A.set("paths." + k, v);

  /* ---------- references ---------- */
  const REF = /^(.+?) (\d+)(?::(\d+))?(?:-(\d+)(?::(\d+))?)?$/;
  function parseRef(r){
    const m = REF.exec(String(r).trim()); if(!m) return null;
    const [, book, c1, v1, x, y] = m;
    if(v1 === undefined) return {book, c1: +c1, v1: null, c2: x ? +x : +c1, v2: null};
    if(x === undefined) return {book, c1: +c1, v1: +v1, c2: +c1, v2: +v1};
    if(y === undefined) return {book, c1: +c1, v1: +v1, c2: +c1, v2: +x};
    return {book, c1: +c1, v1: +v1, c2: +x, v2: +y};
  }
  const label = r => String(r).replace(/-/g, "–");
  function inRef(p, c, v){ return p.v1 === null ? c >= p.c1 && c <= p.c2 : (c > p.c1 || (c === p.c1 && v >= p.v1)) && (c < p.c2 || (c === p.c2 && v <= p.v2)); }
  /* the verses of a reference in one Bible: [[book, ch, v, text], ...]; null if that Bible lacks the book */
  async function versesOf(key, ref){
    const p = parseRef(ref); if(!p) return null;
    const out = [];
    for(let c = p.c1; c <= p.c2; c++){
      const vs = await A.chapter(key, p.book, c);
      if(!vs){ if(c === p.c1) return null; break; }
      for(const [v, t] of vs) if(inRef(p, c, v)) out.push([p.book, c, v, t]);
    }
    return out.length ? out : null;
  }
  /* the reader's Bible first; a verse it doesn't have comes from the Bible that does (and says so) */
  async function readVerses(ref){
    const r = await versesOf("reader", ref).catch(() => null);
    if(r) return {key: "reader", vs: r};
    for(const k of ["KJV", "ETH", "BSB", "JASHER"]){ const x = await versesOf(k, ref).catch(() => null); if(x) return {key: k, vs: x}; }
    return {key: null, vs: []};
  }

  /* ---------- small helpers ---------- */
  const norm = s => String(s).toLowerCase().replace(/[’‘]/g, "'").replace(/[“”]/g, '"');
  const wordsOf = s => norm(s).match(/[a-z0-9']+/g) || [];
  function hasWord(text, w){ return new RegExp("(^|[^a-z])" + norm(w).replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + "(?![a-z])").test(norm(text)); }
  function bookIndex(book){ return A.books().then(b => b.indexOf(book)); }
  function refLink(book, c, v, text){ return `<a href="#" class="pv-go" data-b="${esc(book)}" data-c="${c}" data-v="${v || ""}">${esc(text || A.bookName(book) + " " + c + (v ? ":" + v : ""))}</a>`; }
  function nivLink(ref){ return `<a class="pv-niv" href="https://www.biblegateway.com/passage/?search=${encodeURIComponent(ref)}&version=NIV" target="_blank" rel="noopener" title="The NIV is copyrighted; BibleChat links to it on BibleGateway">Open in NIV ↗</a>`; }
  function progress(){ return get("progress", {}); }
  function saveProgress(id, patch){ const p = progress(); p[id] = Object.assign(p[id] || {}, patch); set("progress", p); }
  function mine(){ return get("mine", []); }

  /* ---------- loading ---------- */
  async function loadList(){
    if(!list){ try{ list = await (await fetch(A.base + "index.json")).json(); }catch(e){ list = []; } }
    return list;
  }
  async function loadPath(id){
    if(id.startsWith("mine-")){ const p = mine().find(x => x.id === id); if(p) return p; throw new Error("not found"); }
    if(!cache[id]) cache[id] = fetch(A.base + encodeURIComponent(id) + ".json").then(r => { if(!r.ok) throw new Error(r.status); return r.json(); });
    return cache[id];
  }
  async function loadQuoted(){
    if(!quoted){ try{ quoted = await (await fetch(A.quotedUrl)).json(); }catch(e){ quoted = {items: []}; } }
    return quoted;
  }

  /* ---------- drawing ---------- */
  function frame(title, body, back){
    root.innerHTML = `<div class="pv-in"><header class="pv-head">${back ? `<button class="pv-ib pv-back" aria-label="Back">‹</button>` : ""}<h2 class="pvx">${esc(title)}</h2>
      ${S.path && S.view !== "list" && S.view !== "quoted" ? `<button class="pv-ib pv-share" title="Share this path">↗</button>` : ""}<button class="pv-ib pv-close" aria-label="Close">✕</button></header><div class="pv-body">${body}</div></div>`;
    root.hidden = false; root.scrollTop = 0; const b = root.querySelector(".pv-body"); if(b) b.scrollTop = 0;
  }
  async function showList(){
    S.view = "list"; S.path = null;
    const L = await loadList(), P = progress(), M = mine();
    const card = p => { const g = P[p.id] || {};
      const st = g.score ? `Finished · ${g.score[0]} of ${g.score[1]}` : g.step != null ? `Step ${g.step + 1} of ${p.steps.length || p.steps}` : "Not started";
      return `<button class="pv-card" data-id="${esc(p.id)}"><b class="pvx">${esc(p.title)}</b><span class="pvx">${esc(p.opening_question)}</span><small>${esc(st)}</small></button>`; };
    frame("📜 Study Paths", `<p class="pv-lead">Each path starts with a question, walks through every main verse on it, including the ones that seem to point the other way, and ends with questions whose answer is always a verse. The path asks; you decide.</p>`
      + L.map(card).join("")
      + (M.length ? `<h3>Your paths</h3>` + M.map(p => card(Object.assign({}, p, {steps: p.steps}))).join("") : "")
      + `<p class="pv-small">Make your own: ask a question, then press 📜 Make a study path under the answer.</p>`
      + `<button class="pv-card pv-quoted"><b>📚 Quoted or named in Scripture</b><span>Verses that quote or name another writing: the Book of Enoch, the Book of Jasher, lost books.</span></button>`
      + `<p class="pv-small">Your progress, notes and scores stay on this device.</p>`);
  }
  async function showQuoted(){
    S.view = "quoted";
    const q = await loadQuoted(), st = {text: "In BibleChat", disputed: "Disputed", lost: "Lost", "not-in-biblechat": "Not in BibleChat"};
    frame("📚 Quoted or named in Scripture", `<p class="pv-lead pvx">${esc(q.about || "")}</p>` + q.items.map(it => { const p = parseRef(it.ref), t = it.target && parseRef(it.target.ref);
      return `<div class="pv-qd"><div class="pv-qh">${refLink(p.book, p.c1, p.v1, label(it.ref))} <span class="pv-tag pv-st-${esc(it.status)}">${esc(st[it.status] || it.status)}</span></div>
        <b class="pvx">${esc(it.writing)}</b><p class="pvx">${esc(it.note)}</p>${t ? `<p><span>${it.status === "text" ? "Read it:" : "See:"}</span> ${refLink(t.book, t.c1, t.v1, label(it.target.ref))}${it.target.bible === "ETH" ? " <small>(Ethiopian Canon)</small>" : it.target.bible === "JASHER" ? " <small>(the 1840 English Jasher)</small>" : ""}</p>` : ""}
        <small><span>Source:</span> <span class="pvx">${esc(it.source)}</span></small></div>`; }).join(""), true);
  }
  async function showPath(id, step){
    let p;
    try{ p = await loadPath(id); }catch(e){ frame("📜 Study Paths", `<p class="pv-err">That study path isn't available. Check the internet connection, or pick another path.</p>`, true); return; }
    S.path = p; S.view = "step";
    const g = progress()[p.id] || {};
    S.step = Math.max(0, Math.min(p.steps.length - 1, step != null ? step : g.step || 0));
    saveProgress(p.id, {step: S.step});
    const s = p.steps[S.step], n = p.steps.length, notes = get("notes", {}), mineNote = (notes[p.id] || {})[S.step] || "";
    frame(p.title, `<div class="pv-open pvx"><small>The question</small>${esc(p.opening_question)}</div>
      <div class="pv-stepno">Step ${S.step + 1} of ${n}</div><div class="pv-bar"><i style="width:${Math.round(100 * (S.step + 1) / n)}%"></i></div>
      <h3 class="pv-q pvx">${esc(p.mine ? T(s.question) : s.question)}</h3>
      <div class="pv-verses${s.side_by_side ? " pv-sbs" : ""}" id="pvVerses"><p class="pv-small">Loading the verses…</p></div>
      ${s.facts ? `<div class="pv-facts"><h4>Facts about the words</h4>${s.facts.map(f => `<p class="pvx">${esc(f.text)}<br><small>${(f.refs || []).map(r => { const q = parseRef(r); return refLink(q.book, q.c1, q.v1, label(r)); }).join(" · ")}${f.refs && f.strongs ? " · " : ""}${(f.strongs || []).map(x => `<button class="pv-sn" data-n="${x}">Strong's ${x}</button>`).join(" ")}</small></p>`).join("")}</div>` : ""}
      ${(s.compare || []).length > 1 ? `<details class="pv-sec" data-sec="compare"><summary>⇄ Compare the translations</summary><div class="pv-secbody"></div></details>` : ""}
      ${(s.look_closer && ((s.look_closer.strongs || []).length || s.look_closer.xref_top)) ? `<details class="pv-sec" data-sec="closer"><summary>🔎 Look closer: the Hebrew/Greek words and cross-references</summary><div class="pv-secbody"></div></details>` : ""}
      ${(s.notes || []).length ? `<details class="pv-sec pv-notesec" data-sec="notes"><summary>📝 Text and notes: what the commentaries say</summary><div class="pv-secbody"></div></details>` : ""}
      <label class="pv-see" for="pvSee">What do you see?</label>
      <textarea id="pvSee" class="pvx" maxlength="4000" placeholder="${esc(T("Your own notes on these verses. They stay on this device."))}">${esc(mineNote)}</textarea>
      <div class="pv-nav"><button class="pv-btn pv-prev"${S.step ? "" : " disabled"}>‹ Previous step</button>${S.step < n - 1 ? `<button class="pv-btn pv-primary pv-next">Next step ›</button>` : `<button class="pv-btn pv-primary pv-toquiz">Questions and answers ›</button>`}</div>
      <p class="pv-small"><span>Sources:</span> <span class="pvx">${esc((p.sources || []).join(" · "))}</span></p>`, true);
    drawVerses(s);
  }
  async function drawVerses(s){
    const box = root.querySelector("#pvVerses"), my = S.step, html = [];
    for(const r of s.refs){
      const {key, vs} = await readVerses(r); if(S.step !== my || !root.contains(box)) return;
      const p = parseRef(r);
      html.push(`<div class="pv-ref"><div class="pv-refh">${refLink(p.book, p.c1, p.v1, label(r))}${key && key !== "reader" ? ` <small class="pv-from">${esc(key === "ETH" ? "Ethiopian Canon" : key)}: not in your Bible</small>` : ""} ${p.book in BOOKS66 ? nivLink(r) : ""}</div>`
        + (vs.length ? `<div class="pvx pv-text">${vs.map(([b, c, v, t]) => `<span class="pv-v"><sup>${p.c1 !== p.c2 || p.v1 === null ? c + ":" : ""}${v}</sup>${esc(t)} </span>`).join("")}</div>` : `<p class="pv-err">This passage isn't in the Bibles available here.</p>`) + `</div>`);
    }
    box.innerHTML = html.join("");
  }

  /* ⇄ Compare: the same verses side by side, words that differ highlighted */
  async function drawCompare(s, el){
    const keys = s.compare, rows = [];
    let missing = [];
    for(const r of s.refs){
      const per = await Promise.all(keys.map(k => versesOf(k, r).catch(() => null)));
      per.forEach((x, i) => { if(!x && !missing.includes(keys[i])) missing.push(keys[i]); });
      const base = per.find(x => x); if(!base) continue;
      for(const [b, c, v] of base.slice(0, 60)){
        const texts = per.map(x => { const e = x && x.find(y => y[1] === c && y[2] === v); return e ? e[3] : null; });
        rows.push({b, c, v, texts});
      }
    }
    const cols = keys.length;
    const mark = (t, others) => { if(t == null) return `<i class="pv-none">not in this Bible</i>`;
      const sets = others.filter(o => o != null).map(o => new Set(wordsOf(o)));
      if(!sets.length) return esc(t);
      return t.split(/(\s+)/).map(w => { const k = (wordsOf(w)[0] || ""); return k && sets.every(st => !st.has(k)) ? `<mark class="pv-diff">${esc(w)}</mark>` : esc(w); }).join(""); };
    el.innerHTML = rows.length ? `<div class="pv-cmp" style="--cols:${cols}">${keys.map(k => `<div class="pv-ch">${esc(NAMES[k] || k)}</div>`).join("")}`
      + rows.map(r => r.texts.map((t, i) => `<div class="pv-cc pvx"><sup>${esc(A.bookName(r.b))} ${r.c}:${r.v}</sup> ${mark(t, r.texts.filter((_, j) => j !== i))}</div>`).join("")).join("") + `</div>`
      + `<p class="pv-small"><mark class="pv-diff">Highlighted words are not in the other columns.</mark></p><p class="pv-small">In the 66 books BibleChat's Ethiopian Canon uses the World English Bible text; 1 Enoch and Jubilees are R. H. Charles's 1917 translation.</p><p class="pv-small">The NIV is copyrighted, so BibleChat opens it on BibleGateway (Open in NIV ↗). The Berean Standard Bible is the modern column here.</p>`
      + (missing.length ? missingNote(missing) : "")
      : `<p class="pv-small">Nothing to compare for these verses.</p>` + missingNote(missing);
  }
  function missingNote(keys){
    if(!keys.length) return "";
    return `<p class="pv-small"><span class="pvx">${keys.map(k => esc(NAMES[k] || k)).join(", ")}:</span> <span>${A.canGet ? "Not on this device yet." : "Doesn't have these verses."}</span>${A.canGet ? ` <button class="pv-btn pv-get">⬇ Get free Bibles</button>` : ""}</p>`;
  }

  /* 🔎 Look closer: the Strong's words (meaning, every verse with it, letter by letter) and the strongest cross-references */
  async function pathKeys(){
    const books = await A.books(), keys = new Set();
    for(const st of S.path.steps) for(const r of st.refs){ const p = parseRef(r); if(!p) continue;
      if(p.v1 !== null && p.c1 === p.c2) for(let v = p.v1; v <= p.v2; v++) keys.add(books.indexOf(p.book) + ":" + p.c1 + ":" + v);
      else for(let c = p.c1; c <= p.c2; c++) keys.add(books.indexOf(p.book) + ":" + c + ":*"); }
    return keys;
  }
  async function wordCard(n, lettersOpen){
    const books = await A.books(), keys = await pathKeys(), L = n[0], num = +n.slice(1);
    const [d, w] = await Promise.all([A.study("dict/" + L + Math.floor(num / 500) + ".json"), A.study("where/" + L + Math.floor(num / 100) + ".json")]);
    const e = d[n]; if(!e) return `<p class="pv-err">No Strong's entry ${esc(n)}.</p>`;
    const uses = w[n] || [], inPath = uses.filter(([b, c, v]) => keys.has(b + ":" + c + ":" + v) || keys.has(b + ":" + c + ":*")), he = L === "H";
    return `<div class="pv-word"><div class="pv-orig${he ? " pv-he" : ""}" lang="${he ? "he" : "el"}">${esc(e.w)}</div>
      <div><b>Strong's ${n}</b> · <span>${he ? "Hebrew" : "Greek"}</span> · <i class="pvx">${esc(e.t)}</i> · <span class="pvx">“${esc(e.p)}”</span></div>
      <p class="pvx">${esc(e.d)}</p>${e.k ? `<p class="pv-small"><span>King James renders it:</span> <span class="pvx">${esc(e.k)}</span></p>` : ""}
      <p class="pv-small"><span>${uses.length} verses use it</span>${inPath.length ? ` · <span>${inPath.length} of them in this path</span>` : ""}</p>
      <details class="pv-sub"${lettersOpen ? " open" : ""}><summary>${he ? "א" : "α"} Letter by letter${he ? ", with Paleo-Hebrew" : ""}</summary><div>${A.letters(e.w, he)}</div></details>
      <details class="pv-sub"><summary>Every verse with this word (${uses.length})</summary><div class="pv-uses">${uses.slice(0, 400).map(([b, c, v, kw]) => `<div>${refLink(books[b], c, v)} <span class="pvx">${esc(kw || "")}</span></div>`).join("")}${uses.length > 400 ? `<p class="pv-small">…and ${uses.length - 400} more.</p>` : ""}</div></details></div>`;
  }
  /* the original line of each verse: Hebrew (Westminster Leningrad Codex) or Greek (Textus Receptus) */
  async function originalLines(refs, books){
    const rows = [];
    for(const r of refs){
      const p = parseRef(r), bi = books.indexOf(p.book); if(bi < 0) continue;
      const d = await A.study("orig/" + bi + ".json").catch(() => ({}));
      Object.keys(d).map(k => k.split(":").map(Number)).filter(([c, v]) => inRef(p, c, v)).sort((a, b) => a[0] - b[0] || a[1] - b[1])
        .forEach(([c, v]) => rows.push([p.book, c, v, d[c + ":" + v], bi < 39]));
    }
    if(!rows.length) return "";
    return `<h4>The original line</h4>` + rows.slice(0, 12).map(([b, c, v, x, he]) => { const t = Array.isArray(x) ? x[0] : x, num = Array.isArray(x) ? x[1] : null;
        return `<div class="pv-ol"><small>${refLink(b, c, v)}${num ? ` <span>(Hebrew numbering: ${esc(num)})</span>` : ""}</small><div class="pvx pv-oline" dir="${he ? "rtl" : "ltr"}" lang="${he ? "he" : "grc"}">${esc(t)}</div></div>`; }).join("")
      + (rows.length > 12 ? `<p class="pv-small">…and ${rows.length - 12} more verses.</p>` : "")
      + `<p class="pv-small">Hebrew: Westminster Leningrad Codex. Greek: Textus Receptus (Stephanus 1550, Elzevir 1624 and Scrivener 1881, collated). Both public domain, from eBible.org. Where the Hebrew numbers a verse differently, its own number is shown; a verse that couldn't be lined up for certain has no line.</p>`;
  }
  async function showWord(n){
    S.view = "word";
    frame("Strong's " + n, `<p class="pv-small">Loading…</p>`, true);
    let h; try{ h = await wordCard(n, true); }catch(e){ h = `<p class="pv-err">Couldn't load Strong's ${esc(n)}.</p>`; }
    root.querySelector(".pv-body").innerHTML = h + `<div class="pv-nav"><button class="pv-btn pv-backpath">‹ Back to the path</button></div>`;
  }
  async function drawCloser(s, el){
    const lc = s.look_closer || {}, parts = [], books = await A.books();
    parts.push(await originalLines(s.refs, books));
    for(const n of lc.strongs || []){
      try{ parts.push(await wordCard(n, lc.letters === n)); }catch(err){ parts.push(`<p class="pv-err">Couldn't load Strong's ${esc(n)}.</p>`); }
    }
    if(lc.xref_top){
      const links = [];
      for(const r of s.refs){
        const p = parseRef(r), bi = books.indexOf(p.book); if(bi < 0 || p.v1 === null) continue;
        const xr = await A.study("xref/" + bi + ".json").catch(() => ({}));
        for(let c = p.c1; c <= p.c2; c++) for(const k in xr){ const [kc, kv] = k.split(":").map(Number);
          if(kc === c && inRef(p, kc, kv)) for(const x of xr[k]) links.push({from: [p.book, kc, kv], to: x}); }
      }
      links.sort((a, b) => b.to[5] - a.to[5]);
      const top = [], seen = new Set();
      for(const l of links){ const k = l.to.slice(0, 5).join("."); if(seen.has(k)) continue; seen.add(k); top.push(l); if(top.length >= lc.xref_top) break; }
      const rows = [];
      for(const {from, to} of top){
        const [b, c, v, c2, v2, votes] = to, book = books[b], ref = book + " " + c + ":" + v + (c2 === c && v2 > v ? "-" + v2 : c2 !== c ? "-" + c2 + ":" + v2 : "");
        const got = await readVerses(c2 === c ? ref : book + " " + c + ":" + v).catch(() => ({vs: []}));
        rows.push(`<div class="pv-x"><div>${refLink(from[0], from[1], from[2], A.bookName(from[0]) + " " + from[1] + ":" + from[2])} → ${refLink(book, c, v, label(A.bookName(book) + ref.slice(book.length)))} <small>${votes} votes</small></div><div class="pvx pv-text">${esc(got.vs.slice(0, 3).map(x => x[3]).join(" ") + (got.vs.length > 3 ? " …" : ""))}</div></div>`);
      }
      parts.push(`<h4>The strongest cross-references</h4>` + (rows.length ? rows.join("") + `<p class="pv-small">From OpenBible.info (CC BY), ranked by readers' votes.</p>` : `<p class="pv-small">No cross-references for these verses.</p>`));
    }
    el.innerHTML = parts.join("") || `<p class="pv-small">Nothing more to show for these verses.</p>`;
  }

  /* 📝 Text and notes. The ONLY place commentary is shown: always under its label, apart from Scripture. */
  function noteBlock(kind, items){
    return `<section class="pnote"><h4>${esc(LABEL[kind])}</h4><p class="pnote-why">The notes of a man, not Scripture. Read the text above first, then judge for yourself whether the note matches it.</p>`
      + (items.length ? items.map(([ref, t]) => { const fmt = x => esc(x).replace(/\*\*(.+?)\*\*/g, "<b>$1</b>").replace(/\n\n+/g, "<br><br>");
          const long = t.length > 900, cut = long ? t.slice(0, t.lastIndexOf(" ", 700)) : t;
          return `<div class="pnote-item"><b>On <span class="pvx">${esc(ref)}</span></b><div class="pvx">${fmt(cut)}${long ? `… <details class="pv-sub"><summary>Read the whole note</summary>${fmt(t.slice(cut.length))}</details>` : ""}</div></div>`; }).join("")
        : `<p class="pv-small">No note on these verses.</p>`) + `</section>`;
  }
  async function drawNotes(s, el){
    const books = await A.books(), out = [];
    for(const kind of s.notes){
      if(!LABEL[kind]) continue;   // only labelled commentary, never anything else
      const items = [];
      for(const r of s.refs){
        const p = parseRef(r), bi = books.indexOf(p.book); if(bi < 0) continue;
        const d = await A.study(kind + "/" + bi + ".json").catch(() => ({}));
        const keys = Object.keys(d).map(k => k.split(":").map(Number)).filter(([c, v]) => inRef(p, c, v)).sort((a, b) => a[0] - b[0] || a[1] - b[1]);
        if(kind === "henry" && p.v1 !== null && !keys.some(([c, v]) => c === p.c1 && v === p.v1)){   // the note on the passage the first verse belongs to
          let v = p.v1; while(v > 0 && !d[p.c1 + ":" + v]) v--; if(v > 0) keys.unshift([p.c1, v]);
        }
        for(const [c, v] of keys) items.push([A.bookName(p.book) + " " + c + ":" + v, d[c + ":" + v]]);
      }
      out.push(noteBlock(kind, items));
    }
    el.innerHTML = out.join("");
  }

  /* ---------- questions and answers ---------- */
  function choose(p, extra){
    const bank = p.quiz.map((q, i) => Object.assign({i, rank: q.score || 0}, q));
    if(extra) bank.forEach(q => { q.rank += extra[q.i] || 0; });
    bank.sort((a, b) => b.rank - a.rank);
    const show = Math.min(p.show || 8, bank.length), pick = [];
    for(const t of ["find_the_verse", "multiple_choice", "fill_word", "which_translation"]){ const q = bank.find(x => x.type === t); if(q && pick.length < show) pick.push(q); }
    for(const q of bank){ if(pick.length >= show) break; if(!pick.includes(q)) pick.push(q); }
    pick.sort((a, b) => b.rank - a.rank);
    return {pick, rest: bank.filter(q => !pick.includes(q))};
  }
  async function closeness(p){
    // optional, off by default, on the device only: how close each question is to what this reader asked before
    if(!get("prefs", {}).past || !A.similar) return null;
    const past = (A.pastQuestions ? A.pastQuestions() : []).slice(-40); if(!past.length) return null;
    try{ const sims = await A.similar(p.quiz.map(q => q.q), past); return sims ? sims.map(x => 0.3 * Math.max(0, x)) : null; }catch(e){ return null; }
  }
  async function showQuiz(more){
    const p = S.path; S.view = "quiz";
    if(!more || !S.quiz){ const extra = await closeness(p); S.quiz = Object.assign(choose(p, extra), {answers: {}, past: !!extra}); }
    else { const add = S.quiz.rest.splice(0, Math.min(p.show || 8, S.quiz.rest.length)); S.quiz.pick = S.quiz.pick.concat(add); }
    const prefs = get("prefs", {});
    frame(p.title, `<div class="pv-open pvx"><small>The question</small>${esc(p.opening_question)}</div><h3>Questions and answers</h3>
      <p class="pv-small">The answer to every question is a verse.</p>
      ${A.similar ? `<label class="pv-opt"><input type="checkbox" id="pvPast"${prefs.past ? " checked" : ""}> Put questions close to what I asked before first (uses the meaning search on this device; off unless you tick it)</label>` : ""}
      <div id="pvQs">${S.quiz.pick.map((q, n) => qCard(q, n)).join("")}</div>
      <div id="pvScore"></div>
      <div class="pv-nav"><button class="pv-btn pv-backsteps">‹ Back to the steps</button>${S.quiz.rest.length ? `<button class="pv-btn pv-more">More questions (${S.quiz.rest.length})</button>` : ""}</div>`, true);
    for(const q of S.quiz.pick) if(q.type === "fill_word") fillText(q);
    score();
  }
  function qCard(q, n){
    const why = (q.why || []).length ? `<div class="pv-why"><b>Why this question?</b> ${q.why.map(w => `<span>${esc(w)}</span>`).join(" · ")}</div>` : "";
    let body = "";
    if(q.type === "find_the_verse") body = `<form class="pv-find" data-q="${q.i}"><input class="pvx" type="text" placeholder="${esc(T("Book chapter:verse, e.g. " + label(q.answer_refs[0]).replace(/\d+(–\d+)?$/, "1")))}" autocomplete="off"><button class="pv-btn">Check</button></form>`;
    if(q.type === "multiple_choice") body = `<div class="pv-opts">${shuffle(q.options.map((o, i) => [o, i]), q.i).map(([o, i]) => `<button class="pv-btn pv-o pvx" data-q="${q.i}" data-o="${i}">${esc(o)}</button>`).join("")}</div>`;
    if(q.type === "fill_word") body = `<div class="pv-fill pvx" id="pvFill${q.i}">…</div><form class="pv-find" data-q="${q.i}"><input class="pvx" type="text" placeholder="${esc(T("The missing word"))}" autocomplete="off"><button class="pv-btn">Check</button></form>`;
    if(q.type === "which_translation") body = `<div class="pv-opts">${["KJV", "ETH", "BSB"].map(k => `<button class="pv-btn pv-o" data-q="${q.i}" data-t="${k}">${esc(NAMES[k])}</button>`).join("")}</div>`;
    return `<div class="pv-qc" id="pvQ${q.i}"><div class="pv-qn">${n + 1}</div><div class="pv-qb"><p class="pvx"><b>${esc(q.q)}</b></p>${why}${body}
      <button class="pv-link pv-reveal" data-q="${q.i}">Show the answer</button><div class="pv-ans" hidden></div></div></div>`;
  }
  function shuffle(a, seed){ const r = a.slice(); let s = seed * 9301 + 49297; for(let i = r.length - 1; i > 0; i--){ s = (s * 9301 + 49297) % 233280; const j = Math.floor(s / 233280 * (i + 1)); [r[i], r[j]] = [r[j], r[i]]; } return r; }
  async function fillText(q){
    const el = root.querySelector("#pvFill" + q.i); if(!el) return;
    const vs = await versesOf(q.bible || "KJV", q.ref).catch(() => null), t = vs && vs[0] ? vs[0][3] : "";
    const re = new RegExp("(^|[^A-Za-z])(" + q.word.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + ")(?![A-Za-z])", "i");
    el.innerHTML = t && re.test(t) ? esc(t.replace(re, "$1\u0000")).replace("\u0000", `<span class="pv-blank">______</span>`) + ` <small>(${esc(q.bible || "KJV")})</small>` : `<small>${esc(label(q.ref))}</small>`;
  }
  async function answer(q, ok){
    const card = root.querySelector("#pvQ" + q.i); if(!card) return;
    if(ok !== null && !(q.i in S.quiz.answers)) S.quiz.answers[q.i] = ok;
    const box = card.querySelector(".pv-ans"), parts = [];
    const keys = q.type === "which_translation" ? ["KJV", "ETH", "BSB"] : q.type === "fill_word" ? [q.bible || "KJV"] : [null];
    for(const r of q.answer_refs){
      const p = parseRef(r);
      for(const k of keys){
        const got = k ? {key: k, vs: await versesOf(k, r).catch(() => null) || []} : await readVerses(r);
        parts.push(`<div class="pv-av"><div>${refLink(p.book, p.c1, p.v1, label(r))}${k ? ` <small>${esc(NAMES[k])}</small>` : ""}</div><div class="pvx pv-text">${got.vs.map(x => `<sup>${x[2]}</sup>${esc(x[3])}`).join(" ") || "<i>not in this Bible</i>"}</div></div>`);
      }
    }
    box.innerHTML = (ok === true ? `<p class="pv-ok">✓ Yes. Here is the verse:</p>` : ok === false ? `<p class="pv-no">Not quite. Here is the verse:</p>` : `<p>The answer is the verse:</p>`) + parts.join("");
    box.hidden = false; card.querySelector(".pv-reveal").hidden = true;
    card.querySelectorAll("button.pv-o, .pv-find button, .pv-find input").forEach(b => b.disabled = true);
    score();
  }
  function score(){
    const a = S.quiz.answers, n = Object.keys(a).length, right = Object.values(a).filter(Boolean).length, total = S.quiz.pick.length;
    const el = root.querySelector("#pvScore"); if(!el) return;
    el.innerHTML = n ? `<p class="pv-scoreline"><span>${right} of ${n} answered right</span>${n < total ? ` · <span>${total - n} to go</span>` : ""}</p><p class="pv-small">Your score stays on this device.</p>` : "";
    if(n >= total && total) saveProgress(S.path.id, {score: [right, total]});
  }
  async function checkFind(q, text){
    if(q.type === "fill_word") return norm(text).trim() === norm(q.word);
    const books = await A.books(), t = text.trim().replace(/\s+/g, " ");
    const m = /^(.+?)\s*(\d+)\s*[:.]\s*(\d+)/.exec(t); if(!m) return false;
    const typed = norm(m[1]).replace(/[^a-z0-9]/g, "");
    const all = books.concat(["1 Enoch", "Jubilees"]);
    const book = all.find(b => norm(b).replace(/[^a-z0-9]/g, "") === typed) || all.find(b => typed.length >= 2 && norm(b).replace(/[^a-z0-9]/g, "").startsWith(typed))
      || all.find(b => norm(A.bookName(b)).replace(/[^a-z0-9]/g, "") === typed);
    if(!book) return false;
    return q.answer_refs.some(r => { const p = parseRef(r); return p.book === book && inRef(p, +m[2], +m[3]); });
  }

  /* ---------- 📜 Make a study path from a chat answer ---------- */
  async function fromAnswer(question, refs){
    refs = [...new Set(refs)].slice(0, 8); if(!refs.length) return;
    const books = await A.books(), counts = {}, perVerse = {};
    for(const r of refs){
      const p = parseRef(r), bi = books.indexOf(p.book); if(bi < 0 || p.v1 === null) continue;
      const kjv = await A.study("kjv/" + bi + ".json").catch(() => ({})), nums = new Set();
      for(let v = p.v1; v <= p.v2; v++) for(const w of kjv[p.c1 + ":" + v] || []) if(typeof w !== "string") for(const n of w[1].split(" ")) if(/^[HG]\d+$/.test(n) && !STOP_STRONGS.has(n)) nums.add(n);
      perVerse[r] = [...nums]; for(const n of nums) counts[n] = (counts[n] || 0) + 1;
    }
    const steps = refs.map(r => ({question: `What does ${label(r)} say about your question?`, refs: [r],
      look_closer: {strongs: (perVerse[r] || []).sort((a, b) => counts[b] - counts[a]).slice(0, 2), xref_top: 5}, compare: ["KJV", "ETH", "BSB"], notes: ["scofield", "henry"]}));
    const quiz = [];
    for(const r of refs){
      const {vs} = await readVerses(r); if(!vs.length) continue;
      const w = vs[0][3].split(/\s+/), start = w.slice(0, Math.min(10, w.length)).join(" ");
      quiz.push({q: `Which verse says: “${start}${w.length > 10 ? " …" : ""}”?`, type: "find_the_verse", answer_refs: [r], why: ["A verse found for your question"], score: 0});
    }
    const p = {id: "mine-" + Date.now().toString(36), title: question.length > 70 ? question.slice(0, 67) + "…" : question, opening_question: question,
      steps, quiz, show: Math.min(10, Math.max(quiz.length, 1)), sources: ["Your question", "the verses BibleChat found", "Strong's", "OpenBible cross-references"], mine: true};
    const M = mine(); M.unshift(p); set("mine", M.slice(0, 30));
    open(p.id, 0);
  }
  function shareHash(p, step){
    if(p.mine){ const data = btoa(unescape(encodeURIComponent(JSON.stringify({t: p.opening_question, r: p.steps.map(s => s.refs[0])})))).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, ""); return "#/path/mine/" + data; }
    return "#/path/" + encodeURIComponent(p.id) + "/" + (step + 1);
  }
  function share(){
    const p = S.path; if(!p) return;
    const url = A.shareUrl(shareHash(p, S.view === "step" ? S.step : 0));
    const cv = A.qr(url, 220);
    frame("Share this path", `<p class="pvx"><b>${esc(p.title)}</b></p><div class="pv-qr"></div><p class="pv-small">Scan the code or send the link. It opens this path on the phone version of BibleChat.</p>
      <input class="pv-url" readonly value="${esc(url)}"><div class="pv-nav"><button class="pv-btn pv-primary pv-copy">⧉ Copy link</button>${navigator.share ? `<button class="pv-btn pv-sys">↗ Share</button>` : ""}<button class="pv-btn pv-backpath">‹ Back to the path</button></div>`, false);
    if(cv) root.querySelector(".pv-qr").appendChild(cv);
    S.view = "share";
  }
  /* a link "#/path/<id>/<step>" or "#/path/mine/<data>" */
  async function openHash(h){
    const m = /^#\/path\/([^/]+)(?:\/([^/]+))?/.exec(h || ""); if(!m) return false;
    if(m[1] === "mine" && m[2]){
      try{
        const d = JSON.parse(decodeURIComponent(escape(atob(m[2].replace(/-/g, "+").replace(/_/g, "/")))));
        const refs = (d.r || []).filter(r => parseRef(r)).slice(0, 8);
        if(refs.length){ await fromAnswer(String(d.t || "A shared study path").slice(0, 300), refs); return true; }
      }catch(e){}
      return false;
    }
    await open(decodeURIComponent(m[1]), m[2] ? Math.max(0, +m[2] - 1) : null); return true;
  }

  /* ---------- events ---------- */
  function onClick(e){
    const t = e.target;
    if(t.closest(".pv-close")){ close(); return; }
    if(t.closest(".pv-back")){ if(S.view === "word" || S.view === "share") showPath(S.path.id, S.step); else if(S.view === "step" || S.view === "quiz" || S.view === "quoted") showList(); else close(); return; }
    if(t.closest(".pv-share")){ share(); return; }
    if(t.closest(".pv-backpath")){ showPath(S.path.id, S.step); return; }
    if(t.closest(".pv-copy")){ const i = root.querySelector(".pv-url"); i.select(); (navigator.clipboard ? navigator.clipboard.writeText(i.value) : Promise.reject()).then(() => A.toast("Link copied"), () => { document.execCommand("copy"); A.toast("Link copied"); }); return; }
    if(t.closest(".pv-sys")){ navigator.share({title: S.path.title, url: root.querySelector(".pv-url").value}).catch(() => {}); return; }
    const c = t.closest(".pv-card"); if(c){ if(c.classList.contains("pv-quoted")) showQuoted(); else open(c.dataset.id); return; }
    if(t.closest(".pv-prev")){ showPath(S.path.id, S.step - 1); return; }
    if(t.closest(".pv-next")){ showPath(S.path.id, S.step + 1); return; }
    if(t.closest(".pv-toquiz")){ showQuiz(false); return; }
    if(t.closest(".pv-backsteps")){ showPath(S.path.id, S.step); return; }
    if(t.closest(".pv-more")){ showQuiz(true); return; }
    if(t.closest(".pv-get")){ A.getBibles(); return; }
    const sn = t.closest(".pv-sn"); if(sn){ showWord(sn.dataset.n); return; }
    const go = t.closest(".pv-go"); if(go){ e.preventDefault();
      lastView = {view: S.view === "quiz" || S.view === "word" || S.view === "share" ? "step" : S.view, id: S.path && S.path.id, step: S.step, top: root.scrollTop};
      close(); A.openVerse(go.dataset.b, +go.dataset.c, go.dataset.v ? +go.dataset.v : null); return; }
    const o = t.closest(".pv-o"); if(o){ const q = S.path.quiz[+o.dataset.q]; q.i = +o.dataset.q;
      const ok = o.dataset.t ? o.dataset.t === q.bible : +o.dataset.o === q.answer; o.classList.add(ok ? "pv-right" : "pv-wrong"); answer(q, ok); return; }
    const rv = t.closest(".pv-reveal"); if(rv){ const q = S.path.quiz[+rv.dataset.q]; q.i = +rv.dataset.q; answer(q, (q.i in S.quiz.answers) ? null : false); return; }
  }
  function onToggle(e){
    const d = e.target; if(!d.matches || !d.matches("details.pv-sec") || !d.open || d.dataset.done) return;
    d.dataset.done = "1"; const el = d.querySelector(".pv-secbody"), s = S.path.steps[S.step];
    el.innerHTML = `<p class="pv-small">Loading…</p>`;
    const f = {compare: drawCompare, closer: drawCloser, notes: drawNotes}[d.dataset.sec];
    f(s, el).catch(() => { el.innerHTML = `<p class="pv-err">Couldn't load this. Check the internet connection and try again.</p>`; delete d.dataset.done; });
  }
  async function onSubmit(e){
    const f = e.target.closest(".pv-find"); if(!f) return; e.preventDefault();
    const q = S.path.quiz[+f.dataset.q]; q.i = +f.dataset.q;
    const v = f.querySelector("input").value; if(!v.trim()) return;
    answer(q, await checkFind(q, v));
  }
  function onInput(e){
    if(e.target.id === "pvSee"){ const n = get("notes", {}); (n[S.path.id] = n[S.path.id] || {})[S.step] = e.target.value; set("notes", n); }
    if(e.target.id === "pvPast"){ const p = get("prefs", {}); p.past = e.target.checked; set("prefs", p); showQuiz(false); }
  }

  /* ---------- public ---------- */
  async function open(id, step){ if(!root) return; if(id) await showPath(id, step); else await showList(); }
  async function reopen(){
    const v = lastView; if(!v){ await showList(); return; }
    if(v.view === "quoted") await showQuoted(); else if(v.id && v.view === "step") await showPath(v.id, v.step); else await showList();
    if(v.top) root.scrollTop = v.top;
  }
  function close(){ if(root){ root.hidden = true; root.innerHTML = ""; S.view = "list"; if(A.onClose) A.onClose(); } }
  function mount(adapter){
    A = adapter; root = adapter.container;
    root.classList.add("pv"); root.hidden = true;
    root.addEventListener("click", onClick); root.addEventListener("toggle", onToggle, true);
    root.addEventListener("submit", onSubmit); root.addEventListener("input", onInput); root.addEventListener("change", onInput);
    addEventListener("keydown", e => { if(e.key === "Escape" && !root.hidden) close(); });
    if(!document.getElementById("pvStyle")){ const st = document.createElement("style"); st.id = "pvStyle"; st.textContent = CSS; document.head.appendChild(st); }
  }
  const BOOKS66 = Object.fromEntries("Genesis Exodus Leviticus Numbers Deuteronomy Joshua Judges Ruth|1 Samuel|2 Samuel|1 Kings|2 Kings|1 Chronicles|2 Chronicles|Ezra Nehemiah Esther Job Psalms Proverbs Ecclesiastes|Song of Solomon|Isaiah Jeremiah Lamentations Ezekiel Daniel Hosea Joel Amos Obadiah Jonah Micah Nahum Habakkuk Zephaniah Haggai Zechariah Malachi Matthew Mark Luke John Acts Romans|1 Corinthians|2 Corinthians|Galatians Ephesians Philippians Colossians|1 Thessalonians|2 Thessalonians|1 Timothy|2 Timothy|Titus Philemon Hebrews James|1 Peter|2 Peter|1 John|2 John|3 John|Jude Revelation"
    .split("|").flatMap(x => /^\d/.test(x) ? [x] : x.trim().split(" ")).filter(Boolean).map(b => [b, 1]));
  const CSS = `
.pv{position:fixed;inset:0;z-index:35;background:var(--bg);color:var(--text);overflow:auto;-webkit-overflow-scrolling:touch}
.pv-in{max-width:760px;margin:0 auto;padding:0 16px calc(28px + env(safe-area-inset-bottom))}
.pv-head{position:sticky;top:0;z-index:2;background:var(--bg);display:flex;align-items:center;gap:8px;padding:calc(10px + env(safe-area-inset-top)) 0 10px;border-bottom:1px solid var(--line)}
.pv-head h2{flex:1;margin:0;font-size:18px;line-height:1.25}
.pv-ib{border:0;background:none;font-size:20px;padding:6px 8px;border-radius:9px;color:inherit;cursor:pointer}
.pv-body{padding-top:10px}
.pv-lead{color:var(--muted);margin:6px 0 14px}
.pv-small{color:var(--muted);font-size:13.5px}
.pv-err{color:var(--danger,#b3382c)}
.pv-card{display:block;width:100%;text-align:left;border:1px solid var(--line);background:var(--card);border-radius:12px;padding:12px 14px;margin:0 0 10px;color:inherit;cursor:pointer;font:inherit}
.pv-card b{display:block;font-size:16.5px}.pv-card span{display:block;color:var(--muted);font-size:14.5px;margin:2px 0}.pv-card small{color:var(--accent);font-weight:600}
.pv-open{border-left:4px solid #c9a227;background:var(--card);padding:9px 12px;border-radius:8px;margin:4px 0 12px;font-style:italic}
.pv-open small{display:block;font-style:normal;color:var(--muted);font-size:12px;text-transform:uppercase;letter-spacing:.06em}
.pv-stepno{font-weight:650;color:var(--accent);font-size:14px}
.pv-bar{height:5px;background:var(--line);border-radius:9px;overflow:hidden;margin:4px 0 8px}.pv-bar i{display:block;height:100%;background:var(--accent)}
.pv-q{font-size:18px;margin:8px 0 10px}
.pv-ref{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px 12px;margin:0 0 10px}
.pv-refh{display:flex;flex-wrap:wrap;gap:8px;align-items:baseline;font-weight:650;margin-bottom:4px}
.pv-text{font-family:Georgia,"Times New Roman",serif;font-size:17px;line-height:1.6}
.pv-text sup{font-family:system-ui,sans-serif;font-size:.62em;color:var(--muted);margin-right:2px}
.pv-from{font-weight:400;color:var(--muted)}
.pv-niv{font-weight:400;font-size:13px;margin-left:auto}
@media (min-width:700px){.pv-sbs{display:grid;grid-template-columns:1fr 1fr;gap:10px}}
.pv-facts{border:1px dashed var(--line);border-radius:10px;padding:4px 12px;margin:0 0 10px}
.pv-facts h4{margin:8px 0 4px}
.pv-sn{border:1px solid var(--line);background:var(--card);border-radius:7px;font-size:12.5px;padding:1px 6px;color:inherit;cursor:pointer}
.pv-sec{border:1px solid var(--line);border-radius:10px;margin:0 0 10px;background:var(--card)}
.pv-sec>summary{cursor:pointer;padding:10px 12px;font-weight:600}
.pv-secbody{padding:0 12px 10px}
.pv-cmp{display:grid;grid-template-columns:repeat(var(--cols),minmax(0,1fr));gap:6px 10px;font-size:14.5px}
.pv-cmp .pv-text,.pv-cc{font-family:Georgia,serif;line-height:1.5}
.pv-ch{font-weight:700;font-size:12.5px;color:var(--muted);border-bottom:1px solid var(--line);padding-bottom:3px}
.pv-cc sup{color:var(--muted);font-family:system-ui,sans-serif}
@media (max-width:520px){.pv-cmp{font-size:13px;gap:4px 6px}}
mark.pv-diff{background:var(--hl,rgba(255,205,60,.35));color:inherit;border-radius:3px}
.pv-none{color:var(--muted)}
.pv-word{border-top:1px solid var(--line);padding:8px 0}
.pv-orig{font-size:30px;line-height:1.2}.pv-he{direction:rtl;text-align:left}
.pv-sub>summary{cursor:pointer;color:var(--accent);margin:4px 0}
.pv-uses{max-height:260px;overflow:auto;font-size:14px}
.pv-x{border-top:1px solid var(--line);padding:6px 0}
.pv-ol{border-top:1px solid var(--line);padding:5px 0}.pv-oline{font-size:20px;line-height:1.6;font-family:"SBL Hebrew","Ezra SIL","Times New Roman",serif}.pv-x small{color:var(--muted)}
.pnote{background:var(--panel,#f1efea);border-left:4px solid var(--muted);border-radius:8px;padding:8px 12px;margin:8px 0;font-family:system-ui,sans-serif;font-size:14.5px}
.pnote h4{margin:2px 0 2px;font-size:14px;text-transform:uppercase;letter-spacing:.05em;color:var(--muted)}
.pnote-why{font-style:italic;color:var(--muted);font-size:13px;margin:0 0 6px}
.pnote-item{margin:6px 0}
.pv-see{display:block;font-weight:650;margin:14px 0 4px}
#pvSee{width:100%;min-height:90px;border:1px solid var(--line);border-radius:10px;padding:10px;background:var(--card);color:inherit;font:inherit;resize:vertical}
.pv-nav{display:flex;gap:8px;flex-wrap:wrap;justify-content:space-between;margin:14px 0}
.pv-btn{border:1px solid var(--line);background:var(--card);border-radius:10px;padding:8px 13px;color:inherit;font:inherit;font-size:15px;cursor:pointer}
.pv-btn:disabled{opacity:.45;cursor:default}
.pv-primary{background:var(--accent);border-color:var(--accent);color:var(--accent-text,#fff)}
.pv-link{border:0;background:none;color:var(--accent);padding:4px 0;font:inherit;font-size:14px;cursor:pointer;text-decoration:underline}
.pv-qc{display:flex;gap:10px;border:1px solid var(--line);background:var(--card);border-radius:12px;padding:10px 12px;margin:0 0 10px}
.pv-qn{flex:none;width:26px;height:26px;border-radius:50%;background:var(--accent);color:var(--accent-text,#fff);display:flex;align-items:center;justify-content:center;font-weight:700;font-size:14px}
.pv-qb{flex:1;min-width:0}.pv-qb p{margin:2px 0 6px}
.pv-why{font-size:12.5px;color:var(--muted);margin:0 0 8px}
.pv-opts{display:flex;flex-wrap:wrap;gap:6px}
.pv-right{border-color:var(--ok,#2f7d4f);box-shadow:inset 0 0 0 2px var(--ok,#2f7d4f)}.pv-wrong{border-color:var(--danger,#b3382c);box-shadow:inset 0 0 0 2px var(--danger,#b3382c)}
.pv-find{display:flex;gap:6px}.pv-find input{flex:1;min-width:0;border:1px solid var(--line);border-radius:9px;padding:7px 10px;background:var(--bg);color:inherit;font:inherit}
.pv-fill{font-family:Georgia,serif;margin:0 0 6px}.pv-blank{border-bottom:2px solid var(--accent);padding:0 6px}
.pv-ans{border-top:1px solid var(--line);margin-top:8px;padding-top:6px}
.pv-av{margin:4px 0 8px}
.pv-ok{color:var(--ok,#2f7d4f);font-weight:650;margin:2px 0}.pv-no{color:var(--danger,#b3382c);font-weight:650;margin:2px 0}
.pv-scoreline{font-weight:650}
.pv-opt{display:flex;gap:8px;align-items:flex-start;font-size:13.5px;color:var(--muted);margin:0 0 10px}
.pv-qr{display:flex;justify-content:center;margin:10px 0}.pv-qr canvas,.pv-qr img{background:#fff;padding:10px;border-radius:10px;max-width:240px}
.pv-url{width:100%;border:1px solid var(--line);border-radius:9px;padding:8px;background:var(--card);color:inherit;font-size:13px}
.pv-qd{border:1px solid var(--line);background:var(--card);border-radius:10px;padding:10px 12px;margin:0 0 10px}
.pv-qd p{margin:4px 0}.pv-qh{display:flex;gap:8px;align-items:center;font-weight:650}
.pv-tag{font-size:11.5px;font-weight:700;border-radius:99px;padding:1px 8px;background:var(--line)}
.pv-st-text{background:#d9ecd9}.pv-st-lost{background:#efd9d4}.pv-st-disputed{background:#f3e7c4}
:root[data-theme="dark"] .pv-tag{color:#1f1e1b}`;
  return {mount, open, close, reopen, openHash, fromAnswer, choose, parseRef, label: LABEL, isOpen: () => root && !root.hidden};
})();
if(typeof module !== "undefined") module.exports = BCPaths;
