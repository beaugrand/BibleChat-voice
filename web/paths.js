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
  const S = {path: null, step: 0, view: "list", quiz: null, filter: "All"};
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
  /* a group's own Bible (e.g. TS2009) as a link only: BibleChat never copies its text */
  /* ---------- moving pictures: fire flickers, light breathes, mist drifts, the rainbow shimmers, stars twinkle, lightning flashes.
     Only CSS on top of the still picture (light for the phone); "reduce motion" in the phone's settings keeps them still. */
  const STARS = "8 6,22 14,35 4,47 18,58 9,71 15,83 5,93 12,15 27,40 31,64 25,88 30,5 40,28 44,52 38,77 42".split(",").map(x => x.split(" "));
  function picture(p, hero){
    if(!p.image) return `<span class="pv-pc-ph" aria-hidden="true">📜</span>`;
    const a = p.anim || {}, k = a.kind || "", x = a.x == null ? 50 : a.x, y = a.y == null ? 30 : a.y, sz = a.s || 30;
    const yy = hero ? Math.max(-30, Math.min(130, 2 * y - 50)) : y;   // the banner shows the middle third of the picture
    const fx = k === "fire" ? `<i class="pv-fx"></i>${[0, 1, 2, 3, 4, 5, 6].map(i => `<b class="pv-ember" style="--d:${(i * 0.37).toFixed(2)}s;--dx:${(i % 2 ? 1 : -1) * (6 + i * 3)}px"></b>`).join("")}`
      : k === "stars" ? `<i class="pv-fx" style="background-image:${STARS.map(([sx, sy], i) => `radial-gradient(${i % 3 ? 1.2 : 2}px ${i % 3 ? 1.2 : 2}px at ${sx}% ${sy}%, #fff, transparent)`).join(",")}"></i><i class="pv-fx2" style="background-image:${STARS.map(([sx, sy]) => `radial-gradient(1.4px 1.4px at ${(+sx + 11) % 100}% ${(+sy + 7) % 50}%, #fff, transparent)`).join(",")}"></i>`
      : k ? `<i class="pv-fx"></i><i class="pv-fx2"></i>` : "";
    return `<div class="pv-anim${k ? " pv-a-" + k : ""}" style="--x:${x}%;--y:${yy}%;--s:${sz}%"><img src="${esc(A.base + p.image)}" alt="" loading="lazy">${fx}</div>`;
  }
  function readAlong(path, p){ const ra = path && path.read_along; if(!ra) return "";
    return `<a class="pv-niv pv-ra" href="${esc(ra.url.replace("{book}", USFM[p && p.book] || "GEN").replace("{c}", p ? p.c1 : 1))}" target="_blank" rel="noopener" title="Opens on Bible.com; BibleChat doesn't copy this Bible's text">Read in ${esc(ra.label)} ↗</a>`; }
  function nivLink(ref){ return `<a class="pv-niv" href="https://www.biblegateway.com/passage/?search=${encodeURIComponent(ref)}&version=NIV" target="_blank" rel="noopener" title="The NIV is copyrighted; BibleChat links to it on BibleGateway">Open in NIV ↗</a>`; }
  function progress(){ return get("progress", {}); }
  function saveProgress(id, patch){ const p = progress(); p[id] = Object.assign(p[id] || {}, patch); set("progress", p); }
  /* the steps the reader has ticked off (Next ticks the step it leaves; the ✓ boxes on a card tick or untick by hand) */
  function doneSteps(id){ return new Set((progress()[id] || {}).done || []); }
  function markDone(id, step, on){ const d = doneSteps(id); if(on === false) d.delete(step); else d.add(step); saveProgress(id, {done: [...d].sort((a, b) => a - b)}); }
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
      ${S.path && (S.view === "step" || S.view === "quiz") ? `<button class="pv-ib pv-share" title="Share this path">↗</button>` : ""}<button class="pv-ib pv-close" aria-label="Close">✕</button></header><div class="pv-body">${body}</div></div>`;
    root.classList.toggle("pv-wide", S.view === "list");
    root.hidden = false; root.scrollTop = 0; const b = root.querySelector(".pv-body"); if(b) b.scrollTop = 0;
  }
  /* the list of paths: filter chips on top, then a grid of cards, each with the path's own picture, its size and time,
     the steps ticked off so far and the steps themselves (open "Steps" to jump straight to one) */
  const ALL = "All", BUSY = "In progress", YOURS = "Your paths", GROUPS = "Bible Study Groups";
  /* "+ Add your own study path": the request goes to Hans's inbox by FormSubmit.co (no account; his address isn't in the code),
     or as a GitHub issue. The group picks the Bible and the verses; Hans writes the path and it appears in the group's folder. */
  const REQ_URL = "https://formsubmit.co/ajax/56755bcbd30a076dc522b82fa44cf441";
  const REQ_BIBLES = ["The Scriptures 2009 (TS2009)", "King James Version (KJV)", "New King James Version (NKJV)", "New International Version (NIV)", "English Standard Version (ESV)", "Berean Standard Bible (BSB)", "Ethiopian Canon", "Another Bible"];
  function cardInfo(p, g){
    const qs = p.step_questions || (Array.isArray(p.steps) ? p.steps.map(x => x.question) : []), n = qs.length || +p.steps || 0;
    const done = new Set(g.done || []);
    return {qs, n, done, finished: !!g.score, started: g.step != null || done.size > 0 || !!g.score};
  }
  function card(p, g){
    const {qs, n, done, finished, started} = cardInfo(p, g), mineP = p.id.startsWith("mine-");
    const pct = n ? Math.round(100 * (finished ? n : done.size) / n) : 0;
    const status = finished ? `✓ Finished · ${g.score[0]} of ${g.score[1]} right` : done.size ? `${done.size} of ${n} steps done` : g.step != null ? `At step ${g.step + 1} of ${n}` : "Not started";
    const go = finished ? "Do it again" : started ? "Continue" : "Start";
    const img = picture(p, false);
    const dots = qs.map((q, i) => `<i class="${done.has(i) || finished ? "pv-d-ok" : g.step === i ? "pv-d-now" : ""}" title="${esc("Step " + (i + 1))}"></i>`).join("");
    return `<article class="pv-pc${finished ? " pv-pc-fin" : ""}" data-id="${esc(p.id)}">
      <button class="pv-pc-open" data-id="${esc(p.id)}" aria-label="${esc("Open " + p.title)}"><div class="pv-pc-img">${img}<span class="pv-pc-cat">${esc(mineP ? YOURS : p.series ? "Session " + p.series.session + " of " + p.series.of : p.group ? "👥 " + p.group : p.category || "")}</span>${finished ? `<span class="pv-pc-check" title="Finished">✓</span>` : ""}</div>
        <div class="pv-pc-txt"><b class="pvx">${esc(p.title)}</b><span class="pvx">${esc(p.opening_question)}</span></div></button>
      <div class="pv-pc-meta">${p.series ? `<span>📖 ${p.series.session}/${p.series.of}</span>` : ""}${p.minutes ? `<span title="About ${p.minutes} minutes">⏱ ${p.minutes} min</span>` : ""}<span>${n} <span>steps</span></span>${p.verses ? `<span>${p.verses} <span>verses</span></span>` : ""}</div>
      <div class="pv-pc-prog"><div class="pv-dots" aria-hidden="true">${dots}</div><small class="${finished ? "pv-ok" : started ? "pv-busy" : ""}">${esc(status)}</small></div>
      <div class="pv-bar"><i style="width:${pct}%"></i></div>
      <details class="pv-pc-steps"><summary>Steps</summary><ol>${qs.map((q, i) => `<li class="${done.has(i) ? "pv-li-ok" : ""}"><label class="pv-tickl" title="Tick this step as done"><input type="checkbox" class="pv-tick" data-id="${esc(p.id)}" data-step="${i}"${done.has(i) ? " checked" : ""}><span>${i + 1}</span></label><button class="pv-jump pvx" data-id="${esc(p.id)}" data-step="${i}">${esc(mineP ? T(q) : q)}</button></li>`).join("")}
        <li><span class="pv-tickl pv-qa">?</span><button class="pv-jump pv-jumpquiz" data-id="${esc(p.id)}">Questions and answers${finished ? ` · ${g.score[0]} of ${g.score[1]}` : ""}</button></li></ol></details>
      <div class="pv-pc-acts"><button class="pv-btn pv-primary pv-pc-go" data-id="${esc(p.id)}"><span>${esc(go)}</span> ›</button><button class="pv-btn pv-pc-share" data-id="${esc(p.id)}" title="Share this path with someone" aria-label="Share this path with someone">↗</button></div></article>`;
  }
  async function showList(){
    S.view = "list"; S.path = null;
    const L = await loadList(), P = progress(), M = mine();
    const cats = [...new Set(L.map(p => p.category).filter(Boolean))].filter(c => c !== GROUPS);
    const chips = [ALL, BUSY, GROUPS].concat(cats, M.length ? [YOURS] : []);
    if(!chips.includes(S.filter)) S.filter = ALL;
    const busy = p => { const i = cardInfo(p, P[p.id] || {}); return i.started && !i.finished; };
    const keep = p => S.filter === ALL || (S.filter === BUSY ? busy(p) : S.filter === YOURS ? p.id.startsWith("mine-") : p.category === S.filter);
    const shown = L.concat(M).filter(keep);
    const arrivedList = S.arrivedList; S.arrivedList = false;
    frame("📜 Study Paths", (arrivedList ? `<div class="pv-welcome">👋 <b>Someone shared the BibleChat Study Paths with you.</b> Pick a path below and press <b>Start</b>: every step shows the verses, the Hebrew and Greek words, and questions to think about. Free, no sign-up.</div>` : "")
      + `<div class="pv-allshare"><button class="pv-btn pv-shareall">📱 Share all Study Paths · link or QR code</button></div>`
      + `<p class="pv-lead">Each path starts with a question, walks through every main verse on it, including the ones that seem to point the other way, and ends with questions whose answer is always a verse. The path asks; you decide.</p>`
      + `<div class="pv-chips" role="toolbar" aria-label="Show">${chips.map(c => `<button class="pv-chip${c === S.filter ? " pv-chip-on" : ""}" data-f="${esc(c)}" aria-pressed="${c === S.filter}">${c === GROUPS ? "👥 " : ""}${esc(c)}</button>`).join("")}</div>`
      + (S.filter === GROUPS ? groupsView(shown, P)
        : shown.length ? gridWithSeries(shown, P) : `<p class="pv-small pv-empty">${S.filter === BUSY ? "No path started yet. Pick one under All." : "No paths here yet."}</p>`)
      + `<p class="pv-small">Make your own: ask a question, then press 📜 Make a study path under the answer.</p>`
      + `<button class="pv-card pv-quoted"><b>📚 Quoted or named in Scripture</b><span>Verses that quote or name another writing: the Book of Enoch, the Book of Jasher, lost books.</span></button>`
      + `<p class="pv-small">Your progress, notes and scores stay on this device.</p>`);
  }
  /* paths of a series (e.g. the 7 sessions of the mirror prophecies) stand together under the series' title, with its own ↗ / QR code */
  function gridWithSeries(shown, P){
    const out = [], loose = [], seen = {};
    for(const p of shown){ if(p.series){ (seen[p.series.id] = seen[p.series.id] || []).push(p); } else loose.push(p); }
    for(const id in seen){ const ps = seen[id].sort((a, b) => a.series.session - b.series.session), se = ps[0].series;
      out.push(`<div class="pv-series" id="pvSeries-${esc(id)}"><div class="pv-serh"><div><b>📖 <span class="pvx">${esc(se.title)}</span></b><small>${ps.length} of ${se.of} sessions ready${ps.length < se.of ? " · more coming" : ""}</small></div><button class="pv-btn pv-serqr" data-series="${esc(id)}" title="Share this series by link or QR code">↗ QR</button></div><div class="pv-grid">${ps.map(p => card(p, P[p.id] || {})).join("")}</div></div>`); }
    if(loose.length) out.push(`<div class="pv-grid">${loose.map(p => card(p, P[p.id] || {})).join("")}</div>`);
    return out.join("");
  }
  /* 👥 Bible Study Groups: one folder per group, then "+ Add your own study path" */
  function groupsView(shown, P){
    const by = {};
    for(const p of shown) (by[p.group || "Other groups"] = by[p.group || "Other groups"] || []).push(p);
    const reqs = get("requests", []);
    return `<p class="pv-lead">Studies made for Bible study groups: the group picks the Bible and the verses, and the study path is written for them. Share a path with your group (↗) so everyone follows the same verses on their phone during the call or meeting.</p>`
      + Object.keys(by).map((g, i, all) => `<h3 class="pv-grp">👥 <span class="pvx">${esc(g)}</span></h3><div class="pv-grid">${by[g].map(p => card(p, P[p.id] || {})).join("")}${i === all.length - 1 ? ADD_CARD : ""}</div>`).join("")
      + (Object.keys(by).length ? "" : `<div class="pv-grid">${ADD_CARD}</div>`)
      + (reqs.length ? `<h3 class="pv-grp">📨 Your requests</h3>` + reqs.map(r => `<div class="pv-req"><b class="pvx">${esc(r.passage)}</b> <span class="pvx">· ${esc(r.group)} · ${esc(r.bible)}</span><small>Sent ${esc(r.date)}. It will appear in your group's folder here when it's ready.</small></div>`).join("") : "");
  }
  const ADD_CARD = `<button class="pv-pc pv-add"><span class="pv-add-plus" aria-hidden="true">+</span><b>Add your own study path</b><span>For your Bible study group: pick your Bible and the verses, and Hans will write the study path for you.</span></button>`;
  function showRequest(){
    S.view = "request";
    frame("+ Add your own study path", `<p class="pv-lead">Tell Hans what your group is studying. He writes the study path (steps, verses, Hebrew/Greek words, questions) and it appears under 👥 Bible Study Groups in a folder with your group's name.</p>
      <form class="pv-reqf" id="pvReq">
        <label>Your group's name <small>(this becomes your folder)</small><input name="group" required maxlength="80" placeholder="Friday night Bible study"></label>
        <label>The Bible your group reads<select name="bible">${REQ_BIBLES.map(b => `<option>${esc(b)}</option>`).join("")}</select></label>
        <label class="pv-other" hidden>Which Bible?<input name="bible_other" maxlength="80"></label>
        <label>Book, chapter and verses<input name="passage" required maxlength="120" placeholder="Daniel 2, or Acts 1:1-14"></label>
        <label>When does your group meet? <small>(optional)</small><input name="when" maxlength="80" placeholder="Friday 8 pm"></label>
        <label>Questions or topics you want in the study <small>(optional)</small><textarea name="notes" maxlength="2000" rows="4"></textarea></label>
        <label>Your name <small>(optional)</small><input name="name" maxlength="80"></label>
        <label>Your email, so Hans can tell you when it's ready <small>(optional)</small><input name="email" type="email" maxlength="120"></label>
        <div class="pv-nav"><button class="pv-btn pv-primary pv-reqsend" type="submit">📨 Send to Hans</button><button class="pv-btn pv-backlist" type="button">‹ Back</button></div>
        <p class="pv-small" id="pvReqNote">No account needed. Sent by FormSubmit.co to Hans's inbox, only when you press Send. Or <a href="#" class="pv-reqgit">open it on GitHub</a>.</p>
      </form>`, true);
  }
  function reqData(){
    const f = root.querySelector("#pvReq"), v = n => (f.elements[n].value || "").trim();
    const bible = v("bible") === "Another Bible" ? (v("bible_other") || "Another Bible") : v("bible");
    return {group: v("group"), bible, passage: v("passage"), when: v("when"), notes: v("notes"), name: v("name"), email: v("email")};
  }
  function reqText(d){
    return `New study path request for BibleChat\n\nGroup (folder): ${d.group}\nBible: ${d.bible}\nPassage: ${d.passage}\nMeets: ${d.when || "-"}\nFrom: ${d.name || "-"}  ${d.email || ""}\n\nQuestions or topics:\n${d.notes || "-"}`;
  }
  async function sendRequest(){
    const d = reqData(), note = root.querySelector("#pvReqNote"), b = root.querySelector(".pv-reqsend");
    if(!d.group || !d.passage){ note.textContent = T("Fill in your group's name and the verses first."); return; }
    b.disabled = true; b.textContent = T("Sending…");
    try{
      const r = await fetch(REQ_URL, {method: "POST", headers: {"Content-Type": "application/json", "Accept": "application/json"},
        body: JSON.stringify({message: reqText(d), group: d.group, bible: d.bible, passage: d.passage, meets: d.when || "-", name: d.name || "-",
          email: d.email || "(not given)", _replyto: d.email || undefined, _subject: `BibleChat study path request: ${d.passage} (${d.group})`, _template: "box", _captcha: "false"})});
      if(!r.ok) throw new Error(r.status);
      const reqs = get("requests", []); reqs.unshift({group: d.group, bible: d.bible, passage: d.passage, date: new Date().toLocaleDateString()}); set("requests", reqs.slice(0, 20));
      S.filter = GROUPS; await showList(); A.toast(T("Thank you! Your request is on its way to Hans."));
    }catch(e){ note.textContent = T("It couldn't be sent. Check the internet connection and try again, or open it on GitHub."); b.disabled = false; b.textContent = T("📨 Send to Hans"); }
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
    const s = p.steps[S.step], n = p.steps.length, notes = get("notes", {}), mineNote = (notes[p.id] || {})[S.step] || "", done = doneSteps(p.id);
    const arrived = S.arrived; S.arrived = false;
    frame(p.title, `${arrived ? `<div class="pv-welcome">👋 <b>Someone shared this study path with you.</b> Read the question, then the verses of each step, and press <b>Next step</b>. Your notes and answers stay on your device.</div>` : ""}${p.image ? `<div class="pv-hero">${picture(p, true)}<span class="pv-pc-cat">${esc(p.series ? "Session " + p.series.session + " of " + p.series.of : p.group ? "👥 " + p.group : p.category || "")}</span></div>` : ""}${p.series ? `<p class="pv-small pv-serline">📖 <span class="pvx">${esc(p.series.title)}</span></p>` : ""}<div class="pv-open pvx"><small>The question</small>${esc(p.opening_question)}</div>
      <div class="pv-stepno">Step ${S.step + 1} of ${n}</div>
      <div class="pv-track" role="navigation" aria-label="Steps">${p.steps.map((x, i) => `<button class="pv-dot${i === S.step ? " pv-dot-now" : ""}${done.has(i) ? " pv-dot-ok" : ""}" data-step="${i}" title="${esc("Step " + (i + 1) + ": " + x.question)}">${done.has(i) ? "✓" : i + 1}</button>`).join(`<i class="pv-track-line"></i>`)}</div>
      <div class="pv-bar"><i style="width:${Math.round(100 * done.size / n)}%"></i></div>
      <h3 class="pv-q pvx">${esc(p.mine ? T(s.question) : s.question)}</h3>
      <div class="pv-verses${s.side_by_side ? " pv-sbs" : ""}" id="pvVerses"><p class="pv-small">Loading the verses…</p></div>
      ${s.facts ? `<div class="pv-facts"><h4>Facts about the words</h4>${s.facts.map(f => `<p class="pvx">${esc(f.text)}<br><small>${(f.refs || []).map(r => { const q = parseRef(r); return refLink(q.book, q.c1, q.v1, label(r)); }).join(" · ")}${f.refs && f.strongs ? " · " : ""}${(f.strongs || []).map(x => `<button class="pv-sn" data-n="${x}">Strong's ${x}</button>`).join(" ")}</small></p>`).join("")}</div>` : ""}
      ${(s.compare || []).length > 1 ? `<details class="pv-sec" data-sec="compare"><summary>⇄ Compare the translations</summary><div class="pv-secbody"></div></details>` : ""}
      ${(s.look_closer && ((s.look_closer.strongs || []).length || s.look_closer.xref_top)) ? `<details class="pv-sec" data-sec="closer"><summary>🔎 Look closer: the Hebrew/Greek words and cross-references</summary><div class="pv-secbody"></div></details>` : ""}
      ${(s.notes || []).length ? `<details class="pv-sec pv-notesec" data-sec="notes"><summary>📝 Text and notes: what the commentaries say</summary><div class="pv-secbody"></div></details>` : ""}
      <label class="pv-see" for="pvSee">What do you see?</label>
      <textarea id="pvSee" class="pvx" maxlength="4000" placeholder="${esc(T("Your own notes on these verses. They stay on this device."))}">${esc(mineNote)}</textarea>
      <div class="pv-nav"><button class="pv-btn pv-prev"${S.step ? "" : " disabled"}>‹ Previous step</button>${S.step < n - 1 ? `<button class="pv-btn pv-primary pv-next">Next step ›</button>` : `<button class="pv-btn pv-primary pv-toquiz">Questions and answers ›</button>`}</div>
      <button class="pv-btn pv-share pv-sharewide">↗ Share this path with someone</button>
      <p class="pv-small"><span>Sources:</span> <span class="pvx">${esc((p.sources || []).join(" · "))}</span></p>`, true);
    drawVerses(s);
  }
  async function drawVerses(s){
    const box = root.querySelector("#pvVerses"), my = S.step, html = [];
    for(const r of s.refs){
      const {key, vs} = await readVerses(r); if(S.step !== my || !root.contains(box)) return;
      const p = parseRef(r);
      html.push(`<div class="pv-ref"><div class="pv-refh">${refLink(p.book, p.c1, p.v1, label(r))}${key && key !== "reader" ? ` <small class="pv-from">${esc(key === "ETH" ? "Ethiopian Canon" : key)}: not in your Bible</small>` : ""} ${readAlong(S.path, p)}${p.book in BOOKS66 ? nivLink(r) : ""}</div>`
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
  /* ↗ Share a path with someone: one link that opens the path on the phone version of BibleChat (any phone or computer
     browser, no sign-up), at step 1. Send it by the phone's own share sheet, a text message, WhatsApp or email, or show the
     QR code to someone next to you. */
  function shareText(t){ return t.kind === "all" ? "Have a look at the BibleChat Study Paths (free, no sign-up): guided Bible studies with the verses side by side, the Hebrew and Greek words, and questions. Pick one and start."
    : t.kind === "series" ? `Let's study "${t.title}" together in BibleChat (free, no sign-up): ${t.question}`
    : `Let's study "${t.title}" together in BibleChat (free, no sign-up): ${t.opening_question || t.question}`; }
  /* what is shared: one path (step 1), a whole series, or the page with all the Study Paths */
  function target(kind, p){
    if(kind === "all") return {kind, title: "BibleChat Study Paths", question: "Every path starts with a question and walks through the verses.", hash: "#/paths", image: null};
    if(kind === "series") return {kind, title: p.series.title, question: `${p.series.of} sessions, Daniel and Revelation side by side.`, hash: "#/paths/series/" + p.series.id, image: p.image};
    return Object.assign({kind: "path", hash: shareHash(p, 0), question: p.opening_question}, p);
  }
  function share(p, from, kind){
    p = p || S.path; if(!p && kind !== "all") return;
    const t = target(kind || "path", p), url = A.shareUrl(t.hash), text = shareText(t), both = text + "\n" + url;
    const what = t.kind === "all" ? "the page with all the Study Paths" : t.kind === "series" ? "this series of study paths" : "this study path, at step 1";
    S.shareFrom = from || "path"; S.shareP = t; S.view = "share";
    const back = S.shareFrom === "list" ? `<button class="pv-btn pv-backlist">‹ Back to the paths</button>` : `<button class="pv-btn pv-backpath">‹ Back to the path</button>`;
    const wide = matchMedia("(min-width: 760px)").matches;   // on a computer the QR code comes first: hold the phone up to the screen
    const qr = `<div class="pv-qrbox"><p class="pv-small">${wide ? "Point a phone camera at the screen:" : "Or let them scan this code with their phone camera:"}</p><div class="pv-qr"></div><button class="pv-btn pv-qrbig">⛶ Show the QR code big (for a TV or projector)</button></div>`;
    frame(t.kind === "all" ? "↗ Share the Study Paths" : t.kind === "series" ? "↗ Share this series" : "↗ Share this path", `<div class="pv-shead">${t.image ? `<img src="${esc(A.base + t.image)}" alt="">` : `<span class="pv-shico">📜</span>`}<div><b class="pvx">${esc(t.title)}</b><span class="pvx">${esc(t.question || "")}</span></div></div>
      <p class="pv-small">Send this link to someone. It opens ${what} in BibleChat on their phone or computer. No sign-up, nothing to install.</p>
      ${wide ? qr : ""}
      <div class="pv-shbtns">${navigator.share ? `<button class="pv-btn pv-primary pv-sys">📤 Send to someone</button>` : ""}
        <a class="pv-btn" href="sms:?&body=${encodeURIComponent(both)}">💬 Text message</a>
        <a class="pv-btn" href="https://wa.me/?text=${encodeURIComponent(both)}" target="_blank" rel="noopener">🟢 WhatsApp</a>
        <a class="pv-btn" href="mailto:?subject=${encodeURIComponent("Bible study: " + t.title)}&body=${encodeURIComponent(both)}">✉ Email</a>
        <button class="pv-btn pv-copy">⧉ Copy link</button></div>
      <p class="pv-small pv-socl">Post it on social media:</p>
      <div class="pv-social">
        <a class="pv-btn pv-so-fb" href="https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(url)}" target="_blank" rel="noopener">Facebook</a>
        <a class="pv-btn pv-so-x" href="https://x.com/intent/post?text=${encodeURIComponent(text)}&url=${encodeURIComponent(url)}" target="_blank" rel="noopener">X</a>
        <a class="pv-btn pv-so-tg" href="https://t.me/share/url?url=${encodeURIComponent(url)}&text=${encodeURIComponent(text)}" target="_blank" rel="noopener">Telegram</a>
        <a class="pv-btn pv-so-pin" href="https://pinterest.com/pin/create/button/?url=${encodeURIComponent(url)}&media=${encodeURIComponent(absImg(t))}&description=${encodeURIComponent(text)}" target="_blank" rel="noopener">Pinterest</a>
        <a class="pv-btn pv-so-li" href="https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(url)}" target="_blank" rel="noopener">LinkedIn</a>
        <a class="pv-btn pv-so-rd" href="https://www.reddit.com/submit?url=${encodeURIComponent(url)}&title=${encodeURIComponent(t.title)}" target="_blank" rel="noopener">Reddit</a>
        <button class="pv-btn pv-so-tt">TikTok</button>
        <button class="pv-btn pv-so-tt pv-so-ig">Instagram</button>
        <button class="pv-btn pv-card-dl">🖼 Picture to post</button>
      </div>
      <p class="pv-small pv-tthint" hidden>TikTok and Instagram don't take links from websites. Post the picture (it has the QR code and the address on it), and paste the link in your caption, bio or story link: it is copied.</p>
      <input class="pv-url" readonly value="${esc(url)}">
      ${wide ? "" : qr}
      <div class="pv-nav">${back}</div>`, true);
    const cv = A.qr(url, wide ? 280 : 220); if(cv) root.querySelector(".pv-qr").appendChild(cv);
  }
  function absImg(t){ return t.image ? new URL("paths/" + t.image, A.shareUrl("")).href : new URL("paths/img/og-studypaths.jpg", A.shareUrl("")).href; }
  /* 🖼 a picture to post (TikTok, Instagram, Facebook, a status): the path's picture, its title and question, and a QR code with the address */
  async function shareCard(t){
    const W = 1080, H = 1350, c = document.createElement("canvas"); c.width = W; c.height = H; const g = c.getContext("2d");
    g.fillStyle = "#16191d"; g.fillRect(0, 0, W, H);
    const src = t.image ? A.base + t.image : A.base + "img/og-studypaths.jpg";
    const img = await new Promise(res => { const i = new Image(); i.onload = () => res(i); i.onerror = () => res(null); i.src = src; });
    if(img){ const h = 720, sc = Math.max(W / img.width, h / img.height), w2 = img.width * sc, h2 = img.height * sc; g.drawImage(img, (W - w2) / 2, (h - h2) / 2, w2, h2);
      const gr = g.createLinearGradient(0, 520, 0, 720); gr.addColorStop(0, "rgba(22,25,29,0)"); gr.addColorStop(1, "#16191d"); g.fillStyle = gr; g.fillRect(0, 520, W, 200); }
    const wrap = (text, x, y, maxW, lh, maxLines) => {   // lines that fit; the last one ends in … if the text is longer
      const words = String(text).split(/\s+/), lines = []; let line = "";
      for(const w of words){ const tt = line ? line + " " + w : w; if(g.measureText(tt).width > maxW && line){ lines.push(line); line = w; } else line = tt; }
      if(line) lines.push(line);
      const out = lines.slice(0, maxLines);
      if(lines.length > maxLines){ let l = out[maxLines - 1]; while(g.measureText(l + "…").width > maxW && l.length > 3) l = l.slice(0, -1); out[maxLines - 1] = l + "…"; }
      out.forEach((l, i) => g.fillText(l, x, y + i * lh)); return y + out.length * lh; };
    g.fillStyle = "#d9b44a"; g.font = "bold 64px Georgia, serif"; let y = wrap(t.title, 70, 790, W - 140, 74, 2);
    g.fillStyle = "#e9ecef"; g.font = "36px system-ui, sans-serif"; y = wrap(t.question || "", 70, y + 20, W - 140, 48, 3);
    const qr = A.qr(A.shareUrl(t.hash), 260); if(qr) g.drawImage(qr, W - 330, H - 330, 260, 260);
    g.fillStyle = "#e9ecef"; g.font = "bold 40px system-ui, sans-serif"; g.fillText("Study it free in BibleChat", 70, H - 210);
    g.fillStyle = "#9aa3ad"; g.font = "30px system-ui, sans-serif"; g.fillText("Scan the code, or open", 70, H - 160); g.fillText("beaugrand.github.io/BibleChat-voice", 70, H - 118); g.fillText("No sign-up · no app needed", 70, H - 76);
    const blob = await new Promise(r => c.toBlob(r, "image/png")), name = "BibleChat-" + (t.id || t.kind || "study").replace(/[^a-z0-9-]/gi, "") + ".png";
    const file = typeof File === "function" ? new File([blob], name, {type: "image/png"}) : null;
    if(file && navigator.canShare && navigator.canShare({files: [file]})){ try{ await navigator.share({files: [file], title: t.title, text: shareText(t) + "\n" + A.shareUrl(t.hash)}); return; }catch(e){ if(e && e.name === "AbortError") return; } }
    const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = name; document.body.appendChild(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(a.href), 4000);
    A.toast(T("Picture saved. Post it with the link."));
  }
  /* the QR code over the whole screen, as big as it fits: for a TV, a projector or a room */
  function bigQr(){
    const t = S.shareP; if(!t) return;
    const url = A.shareUrl(t.hash), px = Math.max(220, Math.min(innerWidth, innerHeight) - 250);
    const o = document.createElement("div"); o.className = "pv-qrfull";
    o.innerHTML = `<div class="pv-qrf-in"><b class="pvx">${esc(t.title)}</b><div class="pv-qrf-code"></div><span>Scan with your phone camera · BibleChat</span><button class="pv-btn pv-qrclose">✕ Close</button></div>`;
    const cv = A.qr(url, px); if(cv) o.querySelector(".pv-qrf-code").appendChild(cv);
    o.addEventListener("click", e => { if(e.target === o || e.target.closest(".pv-qrclose")) o.remove(); });
    root.appendChild(o);
  }
  async function shareFromCard(id){
    let p = (await loadList()).find(x => x.id === id) || mine().find(x => x.id === id);
    if(!p) return; share(p, "list", "path");
  }
  /* a link "#/path/<id>/<step>" or "#/path/mine/<data>" */
  async function openHash(h){
    const all = /^#\/paths(?:\/series\/([a-z0-9-]+))?\/?$/.exec(h || "");
    if(all){
      S.arrivedList = true; S.filter = ALL;
      if(all[1]){ const L = await loadList(), p = L.find(x => x.series && x.series.id === all[1]); if(p) S.filter = p.category; }
      await showList();
      if(all[1]){ const el = root.querySelector("#pvSeries-" + all[1]); if(el) el.scrollIntoView({block: "start"}); }
      return true;
    }
    const m = /^#\/path\/([^/]+)(?:\/([^/]+))?/.exec(h || ""); if(!m) return false;
    if(m[1] === "mine" && m[2]){
      try{
        const d = JSON.parse(decodeURIComponent(escape(atob(m[2].replace(/-/g, "+").replace(/_/g, "/")))));
        const refs = (d.r || []).filter(r => parseRef(r)).slice(0, 8);
        if(refs.length){ await fromAnswer(String(d.t || "A shared study path").slice(0, 300), refs); return true; }
      }catch(e){}
      return false;
    }
    S.arrived = true;   // came by a shared link: say so once on the first page
    await open(decodeURIComponent(m[1]), m[2] ? Math.max(0, +m[2] - 1) : null); return true;
  }

  /* ---------- events ---------- */
  function onClick(e){
    const t = e.target;
    if(t.closest(".pv-close")){ close(); return; }
    if(t.closest(".pv-back")){ if(S.view === "request" || (S.view === "share" && S.shareFrom === "list")) showList(); else if(S.view === "word" || S.view === "share") showPath(S.path.id, S.step); else if(S.view === "step" || S.view === "quiz" || S.view === "quoted") showList(); else close(); return; }
    const sc = t.closest(".pv-pc-share"); if(sc){ shareFromCard(sc.dataset.id); return; }
    if(t.closest(".pv-add")){ showRequest(); return; }
    if(t.closest(".pv-shareall")){ share(null, "list", "all"); return; }
    const sq = t.closest(".pv-serqr"); if(sq){ loadList().then(L => { const p = L.find(x => x.series && x.series.id === sq.dataset.series); if(p) share(p, "list", "series"); }); return; }
    if(t.closest(".pv-qrbig")){ bigQr(); return; }
    if(t.closest(".pv-card-dl")){ shareCard(S.shareP).catch(() => A.toast(T("Couldn't make the picture."))); return; }
    if(t.closest(".pv-so-tt")){ const u = root.querySelector(".pv-url").value, h = root.querySelector(".pv-tthint"); if(h) h.hidden = false;
      (navigator.clipboard ? navigator.clipboard.writeText(u) : Promise.reject()).then(() => A.toast(T("Link copied")), () => {});
      if(navigator.share){ const p = S.shareP; navigator.share({title: p.title, text: shareText(p), url: u}).catch(() => {}); } return; }
    if(t.closest(".pv-reqgit")){ e.preventDefault(); const d = reqData();
      window.open("https://github.com/beaugrand/BibleChat-voice/issues/new?title=" + encodeURIComponent("Study path request: " + (d.passage || "?") + " (" + (d.group || "?") + ")") + "&body=" + encodeURIComponent(reqText(d)), "_blank", "noopener"); return; }
    if(t.closest(".pv-share")){ share(); return; }
    if(t.closest(".pv-backlist")){ showList(); return; }
    if(t.closest(".pv-backpath")){ showPath(S.path.id, S.step); return; }
    if(t.closest(".pv-copy")){ const i = root.querySelector(".pv-url"); i.select(); (navigator.clipboard ? navigator.clipboard.writeText(i.value) : Promise.reject()).then(() => A.toast("Link copied"), () => { document.execCommand("copy"); A.toast("Link copied"); }); return; }
    if(t.closest(".pv-sys")){ const p = S.shareP || target("path", S.path); navigator.share({title: p.title, text: shareText(p), url: root.querySelector(".pv-url").value}).catch(() => {}); return; }
    const c = t.closest(".pv-card"); if(c){ if(c.classList.contains("pv-quoted")) showQuoted(); else open(c.dataset.id); return; }
    const chip = t.closest(".pv-chip"); if(chip){ S.filter = chip.dataset.f; showList(); return; }
    const jq = t.closest(".pv-jumpquiz"); if(jq){ loadPath(jq.dataset.id).then(p => { S.path = p; S.step = p.steps.length - 1; S.quiz = null; showQuiz(false); }).catch(() => open(jq.dataset.id)); return; }
    const j = t.closest(".pv-jump"); if(j){ open(j.dataset.id, +j.dataset.step); return; }
    const pc = t.closest(".pv-pc-open, .pv-pc-go"); if(pc){ const g = progress()[pc.dataset.id] || {}; open(pc.dataset.id, g.score ? 0 : null); return; }
    const dot = t.closest(".pv-dot"); if(dot){ showPath(S.path.id, +dot.dataset.step); return; }
    if(t.closest(".pv-prev")){ showPath(S.path.id, S.step - 1); return; }
    if(t.closest(".pv-next")){ markDone(S.path.id, S.step); showPath(S.path.id, S.step + 1); return; }
    if(t.closest(".pv-toquiz")){ markDone(S.path.id, S.step); showQuiz(false); return; }
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
    if(e.target.id === "pvReq"){ e.preventDefault(); sendRequest(); return; }
    const f = e.target.closest(".pv-find"); if(!f) return; e.preventDefault();
    const q = S.path.quiz[+f.dataset.q]; q.i = +f.dataset.q;
    const v = f.querySelector("input").value; if(!v.trim()) return;
    answer(q, await checkFind(q, v));
  }
  function onInput(e){
    if(e.target.name === "bible" && e.target.closest("#pvReq")){ root.querySelector(".pv-other").hidden = e.target.value !== "Another Bible"; return; }
    if(e.type === "change" && e.target.classList.contains("pv-tick")){ const t = e.target, li = t.closest("li");
      markDone(t.dataset.id, +t.dataset.step, t.checked); if(li) li.classList.toggle("pv-li-ok", t.checked);
      const top = root.scrollTop, open = [...root.querySelectorAll(".pv-pc-steps")].filter(d => d.open).map(d => d.closest(".pv-pc").dataset.id);
      showList().then(() => { open.forEach(id => { const d = root.querySelector(`.pv-pc[data-id="${id}"] .pv-pc-steps`); if(d) d.open = true; }); root.scrollTop = top; });
      return; }
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
    root.classList.add("pv", "pv-dark"); root.hidden = true;
    root.addEventListener("click", onClick); root.addEventListener("toggle", onToggle, true);
    root.addEventListener("submit", onSubmit); root.addEventListener("input", onInput); root.addEventListener("change", onInput);
    addEventListener("keydown", e => { if(e.key === "Escape" && !root.hidden) close(); });
    if(!document.getElementById("pvStyle")){ const st = document.createElement("style"); st.id = "pvStyle"; st.textContent = CSS; document.head.appendChild(st); }
  }
  const USFM = Object.fromEntries(("Genesis GEN|Exodus EXO|Leviticus LEV|Numbers NUM|Deuteronomy DEU|Joshua JOS|Judges JDG|Ruth RUT|1 Samuel 1SA|2 Samuel 2SA|1 Kings 1KI|2 Kings 2KI|1 Chronicles 1CH|2 Chronicles 2CH|Ezra EZR|Nehemiah NEH|Esther EST|Job JOB|Psalms PSA|Proverbs PRO|Ecclesiastes ECC|Song of Solomon SNG|Isaiah ISA|Jeremiah JER|Lamentations LAM|Ezekiel EZK|Daniel DAN|Hosea HOS|Joel JOL|Amos AMO|Obadiah OBA|Jonah JON|Micah MIC|Nahum NAM|Habakkuk HAB|Zephaniah ZEP|Haggai HAG|Zechariah ZEC|Malachi MAL|"
    + "Matthew MAT|Mark MRK|Luke LUK|John JHN|Acts ACT|Romans ROM|1 Corinthians 1CO|2 Corinthians 2CO|Galatians GAL|Ephesians EPH|Philippians PHP|Colossians COL|1 Thessalonians 1TH|2 Thessalonians 2TH|1 Timothy 1TI|2 Timothy 2TI|Titus TIT|Philemon PHM|Hebrews HEB|James JAS|1 Peter 1PE|2 Peter 2PE|1 John 1JN|2 John 2JN|3 John 3JN|Jude JUD|Revelation REV").split("|").map(x => { const i = x.lastIndexOf(" "); return [x.slice(0, i), x.slice(i + 1)]; }));
  const BOOKS66 = Object.fromEntries("Genesis Exodus Leviticus Numbers Deuteronomy Joshua Judges Ruth|1 Samuel|2 Samuel|1 Kings|2 Kings|1 Chronicles|2 Chronicles|Ezra Nehemiah Esther Job Psalms Proverbs Ecclesiastes|Song of Solomon|Isaiah Jeremiah Lamentations Ezekiel Daniel Hosea Joel Amos Obadiah Jonah Micah Nahum Habakkuk Zephaniah Haggai Zechariah Malachi Matthew Mark Luke John Acts Romans|1 Corinthians|2 Corinthians|Galatians Ephesians Philippians Colossians|1 Thessalonians|2 Thessalonians|1 Timothy|2 Timothy|Titus Philemon Hebrews James|1 Peter|2 Peter|1 John|2 John|3 John|Jude Revelation"
    .split("|").flatMap(x => /^\d/.test(x) ? [x] : x.trim().split(" ")).filter(Boolean).map(b => [b, 1]));
  const CSS = `
.pv-dark{--bg:#16191d;--card:#1e2228;--panel:#191c21;--panel2:#262b32;--line:#2e343c;--text:#e9ecef;--muted:#9aa3ad;--accent:#d9b44a;--accent-text:#1a1606;--ok:#4ade80;--danger:#f08070;--hl:rgba(255,205,60,.25);color-scheme:dark}
.pv-dark a{color:#8cc4ff}
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
.pv-chips{display:flex;gap:8px;overflow-x:auto;padding:2px 0 12px;margin:0 0 4px;scrollbar-width:none;-webkit-overflow-scrolling:touch}.pv-chips::-webkit-scrollbar{display:none}
.pv-chip{flex:none;border:1px solid var(--line);background:var(--card);color:var(--muted);border-radius:99px;padding:7px 15px;font:inherit;font-size:14px;font-weight:600;cursor:pointer;white-space:nowrap}
.pv-chip-on{background:var(--accent);border-color:var(--accent);color:var(--accent-text)}
.pv-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;margin:0 0 16px}
@media (min-width:760px){.pv-grid{grid-template-columns:repeat(3,minmax(0,1fr));gap:16px}}
@media (min-width:1060px){.pv-grid{grid-template-columns:repeat(4,minmax(0,1fr))}}
@media (max-width:340px){.pv-grid{grid-template-columns:1fr}}
.pv-grid .pv-pc:has(.pv-pc-steps[open]){grid-column:1/-1}
@media (max-width:560px){.pv-grid{gap:10px}.pv-pc{border-radius:14px}.pv-pc-txt{padding:8px 10px 0}.pv-pc-txt b{font-size:14.5px}.pv-pc-txt span{font-size:12.5px;-webkit-line-clamp:2}
  .pv-pc-meta{padding:6px 10px 0;gap:4px}.pv-pc-meta>span{font-size:10.5px;padding:1px 6px}.pv-pc-prog{padding:7px 10px 0}.pv-pc-prog small{font-size:11px}
  .pv-dots i{width:7px;height:7px}.pv-pc .pv-bar,.pv-pc-steps{margin-left:10px;margin-right:10px}.pv-pc-acts{margin:auto 10px 10px}.pv-pc-go{padding:7px 8px;font-size:13.5px}.pv-pc-share{padding:7px 9px}.pv-pc-cat{font-size:10.5px;left:6px;top:6px}}
.pv-pc{display:flex;flex-direction:column;background:var(--card);border:1px solid var(--line);border-radius:16px;overflow:hidden;box-shadow:0 6px 18px rgba(0,0,0,.28);min-width:0}
.pv-pc-fin{border-color:rgba(74,222,128,.45)}
.pv-pc-open{display:block;width:100%;border:0;background:none;padding:0;text-align:left;color:inherit;font:inherit;cursor:pointer}
.pv-pc-img{position:relative;aspect-ratio:3/2;background:linear-gradient(135deg,#2b3240,#1b1f26);overflow:hidden}
.pv-pc-img img{width:100%;height:100%;object-fit:cover;display:block;transition:transform .35s}.pv-pc-open:hover .pv-pc-img img{transform:scale(1.04)}
.pv-pc-img:after{content:"";position:absolute;inset:auto 0 0 0;height:45%;background:linear-gradient(transparent,rgba(22,25,29,.85))}
.pv-pc-ph{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;font-size:44px}
.pv-pc-cat{position:absolute;z-index:1;left:8px;top:8px;max-width:calc(100% - 50px);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;background:rgba(15,17,20,.72);color:#f3e2a6;font-size:11.5px;font-weight:700;letter-spacing:.03em;border-radius:99px;padding:3px 9px;backdrop-filter:blur(4px)}
.pv-pc-check{position:absolute;z-index:1;right:8px;top:8px;width:26px;height:26px;border-radius:50%;background:var(--ok);color:#0b2414;display:flex;align-items:center;justify-content:center;font-weight:800}
.pv-pc-txt{padding:10px 12px 0}
.pv-pc-txt b{display:block;font-size:16px;line-height:1.25}
.pv-pc-txt span{display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden;color:var(--muted);font-size:13.5px;line-height:1.35;margin-top:4px}
.pv-pc-meta{display:flex;flex-wrap:wrap;gap:5px;padding:8px 12px 0}
.pv-pc-meta>span{font-size:11.5px;font-weight:650;color:var(--text);background:var(--panel2);border-radius:99px;padding:2px 8px}
.pv-pc-prog{display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:4px 8px;padding:9px 12px 0}
.pv-pc-prog small{font-size:12px;font-weight:650;color:var(--muted)}.pv-pc-prog small.pv-ok{color:var(--ok)}.pv-pc-prog small.pv-busy{color:var(--accent)}
.pv-dots{display:flex;gap:4px;flex-wrap:wrap}.pv-dots i{width:9px;height:9px;border-radius:50%;background:var(--line)}
.pv-dots i.pv-d-ok{background:var(--ok)}.pv-dots i.pv-d-now{background:var(--accent);box-shadow:0 0 0 2px rgba(217,180,74,.3)}
.pv-pc .pv-bar{margin:8px 12px 0;height:4px}.pv-pc-fin .pv-bar i{background:var(--ok)}
.pv-pc-steps{margin:8px 12px 0;border-top:1px solid var(--line)}
.pv-pc-steps>summary{cursor:pointer;padding:8px 0 4px;font-size:13.5px;font-weight:650;color:var(--accent);list-style:none}
.pv-pc-steps>summary::-webkit-details-marker{display:none}.pv-pc-steps>summary:after{content:" ▾"}.pv-pc-steps[open]>summary:after{content:" ▴"}
.pv-pc-steps ol{list-style:none;margin:0;padding:0 0 4px}
.pv-pc-steps li{display:flex;gap:8px;align-items:flex-start;padding:5px 0;border-bottom:1px dashed var(--line)}.pv-pc-steps li:last-child{border-bottom:0}
.pv-tickl{flex:none;position:relative;width:22px;height:22px;border-radius:50%;border:2px solid var(--line);display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:700;color:var(--muted);cursor:pointer}
.pv-tickl input{position:absolute;opacity:0;inset:0;margin:0;cursor:pointer}
.pv-li-ok .pv-tickl{background:var(--ok);border-color:var(--ok)}.pv-li-ok .pv-tickl span{display:none}.pv-li-ok .pv-tickl:after{content:"✓";color:#0b2414;font-size:13px}
.pv-tickl input:focus-visible+span{outline:2px solid var(--accent)}
.pv-qa{border-style:dashed;cursor:default}
.pv-jump{flex:1;min-width:0;border:0;background:none;padding:1px 0;text-align:left;color:inherit;font:inherit;font-size:13px;line-height:1.35;cursor:pointer}.pv-jump:hover{color:var(--accent)}
.pv-li-ok .pv-jump{color:var(--muted)}
.pv-pc-steps{margin-bottom:10px}
.pv-pc-acts{display:flex;gap:6px;margin:auto 12px 12px}
.pv-pc-go{flex:1;font-size:14px;font-weight:650}
.pv-pc-share{flex:none;padding:7px 12px;font-weight:700}
.pv-sharewide{display:block;width:100%;margin:4px 0 12px;font-weight:650}
.pv-shead{display:flex;gap:12px;align-items:center;background:var(--card);border:1px solid var(--line);border-radius:14px;padding:10px;margin:4px 0 10px}
.pv-shead img{width:96px;height:64px;object-fit:cover;border-radius:10px;flex:none}.pv-shead b{display:block;font-size:16px}.pv-shead span{display:block;color:var(--muted);font-size:13.5px;margin-top:2px}
.pv-shbtns{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:10px 0}.pv-shbtns .pv-btn{text-align:center;text-decoration:none;font-weight:650}.pv-shbtns .pv-primary{grid-column:1/-1}
.pv-welcome{background:rgba(217,180,74,.14);border:1px solid rgba(217,180,74,.45);border-radius:12px;padding:10px 12px;margin:6px 0 10px;font-size:14.5px;line-height:1.45}
.pv-empty{padding:20px 0}
.pv-anim{position:absolute;inset:0;overflow:hidden}.pv-anim img{width:100%;height:100%;object-fit:cover;display:block;animation:pvKB 24s ease-in-out infinite alternate;transform-origin:var(--x,50%) var(--y,40%)}
@keyframes pvKB{from{transform:scale(1)}to{transform:scale(1.07)}}
.pv-anim .pv-fx,.pv-anim .pv-fx2{position:absolute;inset:0;pointer-events:none}
.pv-a-light .pv-fx{background:radial-gradient(circle at var(--x) var(--y),rgba(255,236,170,.75),rgba(255,214,120,.25) calc(var(--s) * .6),transparent var(--s));mix-blend-mode:screen;animation:pvBreathe 5s ease-in-out infinite}
.pv-a-light .pv-fx2{background:conic-gradient(from 180deg at var(--x) var(--y),transparent 0 20deg,rgba(255,240,190,.16) 24deg,transparent 30deg 60deg,rgba(255,240,190,.12) 66deg,transparent 72deg 110deg,rgba(255,240,190,.14) 116deg,transparent 122deg 160deg,rgba(255,240,190,.12) 166deg,transparent 172deg);mix-blend-mode:screen;animation:pvRays 9s ease-in-out infinite alternate}
@keyframes pvBreathe{0%,100%{opacity:.45}50%{opacity:1}}
@keyframes pvRays{from{opacity:.4;transform:rotate(-2deg)}to{opacity:1;transform:rotate(2deg)}}
.pv-a-fire .pv-fx{background:radial-gradient(ellipse calc(var(--s) * .7) var(--s) at var(--x) var(--y),rgba(255,170,40,.75),rgba(255,90,0,.25) 55%,transparent 75%);mix-blend-mode:screen;animation:pvFlicker 1.6s infinite}
@keyframes pvFlicker{0%{opacity:.55}12%{opacity:.95}20%{opacity:.6}35%{opacity:1}48%{opacity:.7}60%{opacity:.9}72%{opacity:.5}85%{opacity:1}100%{opacity:.55}}
.pv-ember{position:absolute;left:var(--x);top:var(--y);width:3px;height:3px;border-radius:50%;background:#ffd27a;box-shadow:0 0 6px 2px rgba(255,150,40,.85);opacity:0;animation:pvEmber 2.6s ease-out infinite;animation-delay:var(--d)}
@keyframes pvEmber{0%{opacity:0;transform:translate(0,0) scale(1)}15%{opacity:1}100%{opacity:0;transform:translate(var(--dx),-70px) scale(.4)}}
.pv-a-mist .pv-fx,.pv-a-mist .pv-fx2{background:radial-gradient(ellipse 40% 22% at 25% 70%,rgba(255,255,255,.55),transparent 70%),radial-gradient(ellipse 35% 18% at 70% 62%,rgba(255,255,255,.45),transparent 70%),radial-gradient(ellipse 45% 20% at 50% 85%,rgba(255,255,255,.5),transparent 70%);filter:blur(6px);animation:pvMist 18s ease-in-out infinite alternate}
.pv-a-mist .pv-fx2{opacity:.7;animation-duration:27s;animation-direction:alternate-reverse;transform:scaleX(-1)}
@keyframes pvMist{from{transform:translateX(-12%)}to{transform:translateX(12%)}}
.pv-a-rainbow .pv-fx{background:linear-gradient(110deg,transparent 35%,rgba(255,255,255,.32) 48%,rgba(255,255,255,.08) 54%,transparent 62%);background-size:260% 100%;mix-blend-mode:screen;animation:pvSweep 6.5s ease-in-out infinite}
.pv-a-rainbow img{animation:pvKB 24s ease-in-out infinite alternate,pvSat 4s ease-in-out infinite}
@keyframes pvSweep{from{background-position:120% 0}to{background-position:-20% 0}}
@keyframes pvSat{0%,100%{filter:saturate(1)}50%{filter:saturate(1.45) brightness(1.06)}}
.pv-a-stars .pv-fx{animation:pvTwinkle 2.8s ease-in-out infinite}.pv-a-stars .pv-fx2{animation:pvTwinkle 3.9s ease-in-out infinite reverse}
@keyframes pvTwinkle{0%,100%{opacity:.2}50%{opacity:1}}
.pv-a-storm .pv-fx{background:radial-gradient(ellipse 60% 45% at 70% 15%,rgba(220,230,255,.9),transparent 70%);mix-blend-mode:screen;opacity:0;animation:pvFlash 7s infinite}
.pv-a-storm .pv-fx2{background:linear-gradient(transparent 62%,rgba(200,225,255,.18) 75%,transparent 90%);background-size:100% 200%;animation:pvWaves 5s ease-in-out infinite alternate}
@keyframes pvFlash{0%,60%,64%,67%,100%{opacity:0}61%{opacity:.9}62%{opacity:.2}65%{opacity:1}}
@keyframes pvWaves{from{background-position:0 0}to{background-position:0 18%}}
@media (prefers-reduced-motion:reduce){.pv-anim img,.pv-anim .pv-fx,.pv-anim .pv-fx2,.pv-ember{animation:none!important}.pv-ember{display:none}}
.pv-allshare{display:flex;justify-content:flex-end;margin:8px 0 0}
.pv-shareall{font-weight:650}
.pv-series{margin:0 0 14px}.pv-serh{display:flex;gap:10px;align-items:center;justify-content:space-between;margin:6px 0 10px}
.pv-serh b{display:block;font-size:16px;color:var(--accent)}.pv-serh small{color:var(--muted)}.pv-serqr{flex:none;font-weight:700}
.pv-serline{margin:-4px 0 8px;color:var(--accent)}
.pv-shico{font-size:40px;width:96px;text-align:center}
.pv-socl{margin:12px 0 6px}.pv-social{display:grid;grid-template-columns:repeat(4,1fr);gap:6px}.pv-social .pv-btn{text-align:center;text-decoration:none;font-weight:650;font-size:14px;padding:8px 4px;color:#fff;border:0}
@media (max-width:560px){.pv-social{grid-template-columns:repeat(3,1fr)}}
.pv-so-fb{background:#1877f2}.pv-so-x{background:#000}.pv-so-tg{background:#229ed9}.pv-so-pin{background:#e60023}.pv-so-li{background:#0a66c2}.pv-so-rd{background:#ff4500}
.pv-so-tt{background:linear-gradient(90deg,#25f4ee,#000 30%,#000 70%,#fe2c55)}.pv-so-ig{background:linear-gradient(45deg,#f09433,#dc2743 50%,#bc1888)}.pv-card-dl{grid-column:1/-1;background:var(--accent)!important;color:var(--accent-text)!important}
.pv-tthint{margin-top:6px}
.pv-qrbox{text-align:center;margin:6px 0 10px}.pv-qrbig{margin-top:6px}
.pv-qrfull{position:fixed;inset:0;z-index:60;background:rgba(10,12,15,.94);display:flex;align-items:center;justify-content:center}
.pv-qrf-in{display:flex;flex-direction:column;align-items:center;gap:12px;color:#fff;text-align:center;padding:16px}.pv-qrf-in b{font-size:clamp(18px,3vw,30px)}
.pv-qrf-code canvas,.pv-qrf-code img{background:#fff;padding:14px;border-radius:14px;max-width:92vw}
.pv-grp{font-size:16px;margin:14px 0 10px;color:var(--accent)}
.pv-add{align-items:center;justify-content:center;text-align:center;gap:6px;padding:22px 14px;border:2px dashed var(--line);background:transparent;box-shadow:none;cursor:pointer;color:inherit;font:inherit;min-height:200px}
.pv-add:hover{border-color:var(--accent)}.pv-add b{font-size:16px}.pv-add span:last-child{color:var(--muted);font-size:13.5px;line-height:1.4}
.pv-add-plus{width:54px;height:54px;border-radius:50%;background:var(--accent);color:var(--accent-text);font-size:36px;font-weight:700;line-height:54px}
.pv-req{border:1px solid var(--line);background:var(--card);border-radius:12px;padding:9px 12px;margin:0 0 8px}.pv-req span{color:var(--muted)}.pv-req small{display:block;color:var(--muted);margin-top:3px}
.pv-reqf label{display:block;font-weight:650;margin:0 0 12px}.pv-reqf small{font-weight:400;color:var(--muted)}
.pv-reqf input,.pv-reqf select,.pv-reqf textarea{display:block;width:100%;margin-top:5px;border:1px solid var(--line);border-radius:10px;padding:9px 11px;background:var(--card);color:inherit;font:inherit;font-weight:400}
.pv-ra{color:#f3d77a !important}
.pv-hero{position:relative;border-radius:14px;overflow:hidden;aspect-ratio:3/1;max-height:190px;width:100%;margin:2px 0 10px;background:var(--card)}
.pv-hero img{width:100%;height:100%;object-fit:cover;display:block}
.pv-track{display:flex;align-items:center;margin:6px 0 8px;overflow-x:auto;padding:3px 1px}
.pv-dot{flex:none;width:30px;height:30px;border-radius:50%;border:2px solid var(--line);background:var(--card);color:var(--muted);font:inherit;font-size:13px;font-weight:700;cursor:pointer;padding:0}
.pv-dot-ok{background:var(--ok);border-color:var(--ok);color:#0b2414}
.pv-dot-now{border-color:var(--accent);color:var(--accent);box-shadow:0 0 0 3px rgba(217,180,74,.25)}.pv-dot-ok.pv-dot-now{color:#0b2414}
.pv-track-line{flex:1 1 8px;min-width:6px;max-width:40px;height:2px;background:var(--line)}
.pv-wide .pv-in{max-width:1100px}
.pv-tag{font-size:11.5px;font-weight:700;border-radius:99px;padding:1px 8px;background:var(--line)}
.pv-st-text{background:#d9ecd9}.pv-st-lost{background:#efd9d4}.pv-st-disputed{background:#f3e7c4}
:root[data-theme="dark"] .pv-tag,.pv-dark .pv-tag{color:#1f1e1b}
.pv-dark .pnote{background:#191c21}`;
  return {mount, open, close, reopen, openHash, fromAnswer, choose, parseRef, label: LABEL, isOpen: () => root && !root.hidden};
})();
if(typeof module !== "undefined") module.exports = BCPaths;
