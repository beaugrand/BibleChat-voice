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
  const S = {path: null, step: 0, view: "list", quiz: null, filter: "All", section: "paths", draft: null};
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
  /* 🖍 a verse the reader highlighted in Read keeps its colour here (the page hands in A.highlight) */
  const hlClass = (b, c, v) => { const k = A.highlight && A.highlight(b, c, v); return k ? " hl-" + k : ""; };
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
    if(LS.on && !LS.moving) lsStop();
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
  function card(p, g, isNext){
    const {qs, n, done, finished, started} = cardInfo(p, g), mineP = p.id.startsWith("mine-");
    const pct = n ? Math.round(100 * (finished ? n : done.size) / n) : 0;
    const status = finished ? `✓ Finished · ${g.score[0]} of ${g.score[1]} right` : done.size ? `${done.size} of ${n} steps done` : g.step != null ? `At step ${g.step + 1} of ${n}` : "Not started";
    const go = finished ? "Do it again" : started ? "Continue" : "Start";
    const img = picture(p, false);
    const dots = qs.map((q, i) => `<i class="${done.has(i) || finished ? "pv-d-ok" : g.step === i ? "pv-d-now" : ""}" title="${esc("Step " + (i + 1))}"></i>`).join("");
    return `<article class="pv-pc${finished ? " pv-pc-fin" : ""}" data-id="${esc(p.id)}">
      <button class="pv-pc-open" data-id="${esc(p.id)}" aria-label="${esc("Open " + p.title)}"><div class="pv-pc-img">${img}<span class="pv-pc-cat">${esc(mineP ? (p.group ? "👥 " + p.group : YOURS) : p.series ? "Session " + p.series.session + " of " + p.series.of : p.group ? "👥 " + p.group : p.category || "")}</span>${finished ? `<span class="pv-pc-check" title="Finished">✓</span>` : ""}</div>
        <div class="pv-pc-txt"><b class="pvx">${esc(p.title)}</b><span class="pvx">${esc(p.opening_question)}</span></div></button>
      <div class="pv-pc-meta">${p.study_date ? `<span class="${isNext ? "pv-next" : ""}">📅 ${esc(dayLabel(p.study_date))}${isNext ? " · " + esc(T("next")) : ""}</span>` : ""}${p.series ? `<span>📖 ${p.series.session}/${p.series.of}</span>` : ""}${p.minutes ? `<span title="About ${p.minutes} minutes">⏱ ${p.minutes} min</span>` : ""}<span>${n} <span>steps</span></span>${p.verses ? `<span>${p.verses} <span>verses</span></span>` : ""}</div>
      <div class="pv-pc-prog"><div class="pv-dots" aria-hidden="true">${dots}</div><small class="${finished ? "pv-ok" : started ? "pv-busy" : ""}">${esc(status)}</small></div>
      <div class="pv-bar"><i style="width:${pct}%"></i></div>
      <details class="pv-pc-steps"><summary>Steps</summary><ol>${qs.map((q, i) => `<li class="${done.has(i) ? "pv-li-ok" : ""}"><label class="pv-tickl" title="Tick this step as done"><input type="checkbox" class="pv-tick" data-id="${esc(p.id)}" data-step="${i}"${done.has(i) ? " checked" : ""}><span>${i + 1}</span></label><button class="pv-jump pvx" data-id="${esc(p.id)}" data-step="${i}">${esc(mineP ? T(q) : q)}</button></li>`).join("")}
        <li><span class="pv-tickl pv-qa">?</span><button class="pv-jump pv-jumpquiz" data-id="${esc(p.id)}">Questions and answers${finished ? ` · ${g.score[0]} of ${g.score[1]}` : ""}</button></li></ol></details>
      ${mineP ? `<div class="pv-pc-mine"><span class="pv-vis">${esc(VIS[p.visibility || "private"] || VIS.private)}${p.community ? " · " + esc(T("sent")) + " " + esc(p.community) : ""}</span><button class="pv-link pv-edit" data-id="${esc(p.id)}">✏️ Edit</button></div>` : ""}
      <div class="pv-pc-acts"><button class="pv-btn pv-primary pv-pc-go" data-id="${esc(p.id)}"><span>${esc(go)}</span> ›</button><button class="pv-btn pv-pc-share" data-id="${esc(p.id)}" title="Share this path with someone" aria-label="Share this path with someone">↗</button></div></article>`;
  }
  async function showList(){
    S.view = "list"; S.path = null;
    const L = await loadList(), P = progress(), M = mine();
    const cats = [...new Set(L.map(p => p.category).filter(Boolean))].filter(c => c !== GROUPS);
    const chips = [ALL, BUSY, GROUPS].concat(cats.filter(c => c !== COMMUNITY));
    if(!chips.includes(S.filter)) S.filter = ALL;
    const busy = p => { const i = cardInfo(p, P[p.id] || {}); return i.started && !i.finished; };
    const keep = p => S.filter === ALL || (S.filter === BUSY ? busy(p) : S.filter === YOURS ? p.id.startsWith("mine-") : p.category === S.filter);
    const shown = L.filter(p => p.category !== COMMUNITY).filter(keep);
    const arrivedList = S.arrivedList; S.arrivedList = false;
    const sections = `<div class="pv-seg" role="tablist"><button class="pv-segb${S.section === "paths" ? " pv-segon" : ""}" data-sec="paths" role="tab">📖 Study Paths</button><button class="pv-segb${S.section === "community" ? " pv-segon" : ""}" data-sec="community" role="tab">👥 Community</button></div>`;
    if(S.section === "community"){ frame("📜 Study Paths / Community", sections + communityView(L, M, P)); return; }
    frame("📜 Study Paths / Community", sections + (arrivedList ? `<div class="pv-welcome">👋 <b>Someone shared the BibleChat Study Paths with you.</b> Pick a path below and press <b>Start</b>: every step shows the verses, the Hebrew and Greek words, and questions to think about. Free, no sign-up.</div>` : "")
      + `<div class="pv-allshare"><button class="pv-btn pv-shareall">📱 Share all Study Paths · link or QR code</button></div>`
      + `<p class="pv-lead">Each path starts with a question, walks through every main verse on it, including the ones that seem to point the other way, and ends with questions whose answer is always a verse. The path asks; you decide.</p>`
      + `<div class="pv-chips" role="toolbar" aria-label="Show">${chips.map(c => `<button class="pv-chip${c === S.filter ? " pv-chip-on" : ""}" data-f="${esc(c)}" aria-pressed="${c === S.filter}">${c === GROUPS ? "👥 " : ""}${esc(c)}</button>`).join("")}</div>`
      + (S.filter === GROUPS ? groupsView(shown, P)
        : shown.length ? gridWithSeries(shown, P) : `<p class="pv-small pv-empty">${S.filter === BUSY ? "No path started yet. Pick one under All." : "No paths here yet."}</p>`)
      + `<p class="pv-small">Make your own: open <b>👥 Community</b> and press <b>＋ Make your own study path</b>, or ask a question and press 📜 Make a study path under the answer.</p>`
      + `<button class="pv-card pv-quoted"><b>📚 Quoted or named in Scripture</b><span>Verses that quote or name another writing: the Book of Enoch, the Book of Jasher, lost books.</span></button>`
      + `<p class="pv-small">Your progress, notes and scores stay on this device.</p>`);
  }
  /* ---------- 🔊 Listen: every Study Path screen can be read aloud ----------
     A step: "Step 2 of 7", its question, every passage (in the reader's own Bible, with its own voice), the facts about the
     words, the maker's note and any commentary that is open; then it goes on to the next step. The questions page reads
     the questions and their choices. The voice is the one BibleChat already reads with (the phone's or computer's own
     voice, or the computer's cloned voice when it runs); nothing is recorded or sent anywhere.
     ⏸ Pause / ▶ Resume, ⏭ Skip and ■ Stop in the bar at the bottom; the part being read is highlighted. */
  const LS = {on: false, paused: false, tok: 0, segs: [], i: 0, kind: "step", ctl: null, moving: false};
  const sayRef = r => { const p = parseRef(r); if(!p) return r; const b = A.bookName(p.book);
    if(p.v1 === null) return b + " " + p.c1 + (p.c2 !== p.c1 ? " to " + p.c2 : "");
    return b + " " + p.c1 + (p.c2 !== p.c1 ? ", verse " + p.v1 + ", to chapter " + p.c2 + ", verse " + p.v2 : p.v2 > p.v1 ? ", verses " + p.v1 + " to " + p.v2 : ", verse " + p.v1); };
  const plain = el => (el ? el.textContent : "").replace(/\s+/g, " ").trim();
  function speakOne(text, kind, ctl){
    if(A.speak) return A.speak(text, kind, ctl);
    if(!("speechSynthesis" in window)) return Promise.reject(new Error(T("This device has no voice for reading aloud.")));
    const v = A.voice ? A.voice(kind, text) : null;
    return new Promise((res, rej) => { const u = new SpeechSynthesisUtterance(text); u.lang = (v && v.lang) || "en-US"; try{ if(v && v.voice) u.voice = v.voice; }catch(e){}
      u.rate = .95; u.onend = res; u.onerror = e => (ctl.stop || e.error === "interrupted" || e.error === "canceled") ? res() : rej(new Error(T("The voice couldn't read that."))); speechSynthesis.speak(u); });
  }
  function speakCancel(){ const c = LS.ctl; if(c){ c.stop = true; if(c.audio) try{ c.audio.pause(); }catch(e){} } if(A.speakCancel) A.speakCancel(); try{ speechSynthesis.cancel(); }catch(e){} }
  function lsSegments(kind){
    const segs = [], add = (text, el, voice) => { text = String(text || "").trim(); if(text) segs.push({text, el, kind: voice || "path"}); };
    if(kind === "quiz"){
      add(T("Questions and answers. The answer to every question is a verse."), root.querySelector(".pv-in h3"));
      root.querySelectorAll(".pv-qc").forEach((c, i) => { const q = plain(c.querySelector(".pv-qb p")), opts = [...c.querySelectorAll(".pv-opts .pv-o")].map(plain);
        add((i + 1) + ". " + q + (opts.length ? " " + opts.join(", or ") + "?" : ""), c); });
      return segs;
    }
    const p = S.path, st = p.steps[S.step];
    add(`${T("Step")} ${S.step + 1} ${T("of")} ${p.steps.length}. ${p.mine ? T(st.question) : st.question}`, root.querySelector(".pv-q"));
    root.querySelectorAll("#pvVerses .pv-ref").forEach(r => {
      const voice = r.dataset.key === "reader" ? "reader" : "path", vs = [...r.querySelectorAll(".pv-v")];
      add(sayRef(r.dataset.ref) + ".", r.querySelector(".pv-refh"));
      vs.forEach(v => add([...v.childNodes].filter(n => !(n.nodeName === "SUP")).map(n => n.textContent).join("").trim(), v, voice));
    });
    const facts = root.querySelectorAll(".pv-facts p"); if(facts.length){ add(T("Facts about the words."), root.querySelector(".pv-facts h4")); facts.forEach(f => add(plain(f.firstChild && f.firstChild.nodeType === 3 ? f.firstChild : f).replace(/\s+·.*$/, ""), f)); }
    const cn = root.querySelector(".pv-cnote"); if(cn) add(plain(cn.querySelector("h4")) + ". " + plain(cn.querySelector("div.pvx")), cn);
    root.querySelectorAll("details.pv-notesec[open] .pnote").forEach(n => { add(plain(n.querySelector("h4")) + ". " + T("The notes of a man, not Scripture."), n.querySelector("h4"));
      n.querySelectorAll(".pnote-item").forEach(it => add(plain(it), it)); });
    return segs;
  }
  async function lsStart(kind){
    if(A.onListen) A.onListen();   // the Bible reader's own Listen stops
    speakCancel(); LS.tok++;
    Object.assign(LS, {on: true, paused: false, kind, i: 0, segs: []});
    lsBar(T("Getting ready…"));
    if(kind === "step" && S.versesP) await S.versesP;
    if(!LS.on) return;
    LS.segs = lsSegments(kind); lsRun(LS.tok);
  }
  async function lsRun(tok){
    while(LS.on && !LS.paused && tok === LS.tok && LS.i < LS.segs.length){
      const sg = LS.segs[LS.i];
      root.querySelectorAll(".pv-saying").forEach(x => x.classList.remove("pv-saying"));
      if(sg.el){ sg.el.classList.add("pv-saying"); sg.el.scrollIntoView({block: "center", behavior: "smooth"}); }
      lsBar();
      const ctl = LS.ctl = {stop: false};
      try{ await speakOne(sg.text, sg.kind, ctl); }catch(e){ if(tok === LS.tok){ lsStop(); A.toast(e.message || T("The voice couldn't read that.")); } return; }
      if(tok !== LS.tok || ctl.stop) return;
      LS.i++;
    }
    if(tok !== LS.tok || !LS.on || LS.paused) return;
    if(LS.kind === "step" && S.path && S.step < S.path.steps.length - 1){   // on to the next step, still listening
      markDone(S.path.id, S.step); LS.moving = true; S.lsAuto = true;
      try{ await showPath(S.path.id, S.step + 1); }finally{ LS.moving = false; }
      return;
    }
    if(LS.kind === "step"){ LS.segs.push({text: T("That was the last step. The questions and answers come next."), kind: "path"}); const t2 = ++LS.tok; LS.kind = "end"; return lsRun(t2); }
    lsStop();
  }
  function lsPause(){ if(!LS.on) return; if(LS.paused){ LS.paused = false; LS.tok++; lsRun(LS.tok); } else { LS.paused = true; LS.tok++; speakCancel(); } lsBar(); }
  function lsSkip(){ if(!LS.on) return; LS.tok++; speakCancel(); LS.i++; LS.paused = false; lsRun(LS.tok); }
  function lsStop(){ if(!LS.on && !root) return; LS.on = false; LS.paused = false; LS.tok++; speakCancel();
    if(root){ root.querySelectorAll(".pv-saying").forEach(x => x.classList.remove("pv-saying")); const b = root.querySelector(".pv-player"); if(b) b.remove(); } }
  function lsBar(msg){
    let b = root.querySelector(".pv-player");
    if(!b){ b = document.createElement("div"); b.className = "pv-player"; b.setAttribute("role", "region"); b.setAttribute("aria-label", "Listen");
      b.innerHTML = `<span class="pv-plw"></span><button class="pv-btn pv-lspause"></button><button class="pv-btn pv-lsskip" title="Skip this part">⏭</button><button class="pv-btn pv-lsstop" title="Stop">■</button>`; root.appendChild(b); }
    const sg = LS.segs[LS.i], where = msg || (LS.kind === "quiz" ? T("Questions") + " · " + Math.min(LS.i + 1, LS.segs.length) + "/" + LS.segs.length
      : S.path ? T("Step") + " " + (S.step + 1) + " · " + Math.min(LS.i + 1, LS.segs.length) + "/" + LS.segs.length : "");
    b.querySelector(".pv-plw").textContent = "🔊 " + where;
    b.querySelector(".pv-lspause").textContent = LS.paused ? "▶ " + T("Resume") : "⏸ " + T("Pause");
  }

  /* ---------- 👥 Community: your own study paths, the ones readers sent in (checked by Hans), and the Bible study groups ---------- */
  const COMMUNITY = "Community";
  const VIS = {private: "🔒 Only you", link: "🔗 Anyone with the link", community: "👥 Community"};
  function communityView(L, M, P){
    const comm = L.filter(p => p.category === COMMUNITY), groups = L.filter(p => p.category === GROUPS);
    return `<p class="pv-lead">Study paths made by BibleChat readers. Pick the verses, the questions, the commentaries and the Hebrew/Greek words yourself.</p>
      <div class="pv-who"><b>Who can see a path you make?</b><span>🔒 <b>Only you</b>: it stays on this device.</span><span>🔗 <b>Anyone with the link</b>: send the link or QR code; the whole path travels inside the link, nothing is stored on a server.</span><span>👥 <b>Community</b>: send it to Hans; once he has checked that every verse and word is right, it appears here for everyone.</span></div>
      <button class="pv-btn pv-primary pv-new">＋ Make your own study path</button>
      <h3 class="pv-grp">✍ Your study paths</h3>`
      + (M.length ? gridWithSeries(M, P) : `<p class="pv-small">None yet. Press ＋ Make your own study path, or 📜 Make a study path under a search or chat answer.</p>`)
      + `<h3 class="pv-grp">👥 Community study paths</h3>`
      + (comm.length ? gridWithSeries(comm, P) : `<p class="pv-small">Paths readers send in appear here after Hans has checked them. Be the first: make one and choose 👥 Community.</p>`)
      + (groups.length ? `<h3 class="pv-grp">👥 Bible Study Groups</h3>` + groupsView(groups, P) : "");
  }
  function blankStep(){ return {question: "", refs: [], notes: ["scofield", "henry"], compare: ["KJV", "ETH", "BSB"], look_closer: {strongs: [], xref_top: 5}, my_note: ""}; }
  function editPath(p){
    S.draft = p ? JSON.parse(JSON.stringify(p)) : {id: "mine-" + Date.now().toString(36), title: "", opening_question: "", author: get("author", ""), category: "", visibility: "private", steps: [blankStep()], mine: true, isNew: true};
    if(!S.draft.steps.length) S.draft.steps.push(blankStep());
    S.draft.steps.forEach(st => { st.look_closer = st.look_closer || {strongs: [], xref_top: 0}; st.look_closer.strongs = st.look_closer.strongs || []; st.notes = st.notes || []; st.compare = st.compare || []; st.my_note = st.my_note || ""; });
    S.view = "edit"; edRender(true);
  }
  const CAT_CHOICES = ["Creation", "Prophecy", "Gospel", "Marriage", "Freedom", "Body & Life", "Name & Word", "Covenant", "Bible study group", "Other"];
  function edRender(top){
    const d = S.draft, keep = top ? 0 : root.scrollTop, cb = (on, opt, i, lab) => `<label class="pv-edck"><input type="checkbox" data-opt="${opt}" data-s="${i}"${on ? " checked" : ""}> ${lab}</label>`;
    frame(d.isNew ? "＋ Make your own study path" : "✏️ Edit your study path", `<form class="pv-reqf pv-ed" id="pvEd" autocomplete="off">
      <label>Title<input data-f="title" maxlength="90" value="${esc(d.title)}" placeholder="The serpent in the garden"></label>
      <label>The starting question <small>(what the path asks; the verses answer)</small><textarea data-f="opening_question" maxlength="400" rows="2" placeholder="What does the text say about the serpent, Eve and Cain?">${esc(d.opening_question)}</textarea></label>
      <div class="pv-edrow"><label>Topic<select data-f="category">${["", ...CAT_CHOICES].map(c => `<option${c === d.category ? " selected" : ""} value="${esc(c)}">${esc(c || "Choose…")}</option>`).join("")}</select></label>
        <label>Your name <small>(optional)</small><input data-f="author" maxlength="60" value="${esc(d.author || "")}"></label></div>
      <label>Your group <small>(optional: your Bible study group's name; its studies are kept together in one folder)</small><input data-f="group" maxlength="80" list="pvGroups" value="${esc(d.group || "")}" placeholder="Friday night Bible study"><datalist id="pvGroups">${[...new Set((list || []).concat(mine()).map(p => p.group).filter(Boolean))].map(g => `<option value="${esc(g)}">`).join("")}</datalist></label>
      <label>Date of the study <small>(optional: the day your group studies it)</small><input data-f="study_date" type="date" value="${esc(d.study_date || "")}"></label>
      ${d.steps.map((st, i) => `<div class="pv-eds" data-i="${i}">
        <div class="pv-edsh"><b>Step ${i + 1}</b><span><button type="button" class="pv-ib" data-ed="up" data-s="${i}" title="Move up"${i ? "" : " disabled"}>↑</button><button type="button" class="pv-ib" data-ed="down" data-s="${i}" title="Move down"${i < d.steps.length - 1 ? "" : " disabled"}>↓</button><button type="button" class="pv-ib" data-ed="delstep" data-s="${i}" title="Remove this step"${d.steps.length > 1 ? "" : " disabled"}>🗑</button></span></div>
        <label>Question for this step<input data-k="question" data-s="${i}" maxlength="240" value="${esc(st.question)}" placeholder="What did the serpent say to the woman?"></label>
        <div class="pv-edrefs">${st.refs.length ? st.refs.map((r, j) => `<div class="pv-edref"><div><b>${esc(label(r))}</b> <button type="button" class="pv-link" data-ed="delref" data-s="${i}" data-j="${j}">remove</button></div><div class="pv-edprev pvx" data-ref="${esc(r)}">…</div></div>`).join("") : `<p class="pv-small">No verses yet. Add one or more below.</p>`}</div>
        <div class="pv-edadd"><input class="pv-edin" data-s="${i}" maxlength="60" placeholder="Add verses, e.g. Genesis 3:1-6 or John 3:16"><button type="button" class="pv-btn" data-ed="addref" data-s="${i}">＋ Add</button></div>
        <p class="pv-small pv-edmsg" data-s="${i}"></p>
        ${A.findVerses ? `<details class="pv-edfind"><summary>🔎 Find verses by words</summary><div class="pv-edadd"><input class="pv-edq" data-s="${i}" maxlength="80" placeholder="e.g. serpent beguiled"><button type="button" class="pv-btn" data-ed="find" data-s="${i}">Search</button></div><div class="pv-edhits" data-s="${i}"></div></details>` : ""}
        <div class="pv-edopts">${cb(st.compare.length > 1, "compare", i, "⇄ Compare KJV · Ethiopian Canon · BSB")}${cb(st.notes.includes("scofield"), "scofield", i, "📝 Scofield notes (1917)")}${cb(st.notes.includes("henry"), "henry", i, "📝 Matthew Henry notes")}${cb(st.look_closer.xref_top, "xref", i, "🔗 Strongest cross-references")}</div>
        <div class="pv-edwords"><div><b>🔎 Hebrew/Greek words</b> <small>tap a word to put it in Look closer: its meaning, every verse with it and, for Hebrew, the Paleo-Hebrew letters one by one</small></div>
          <div class="pv-edwl" data-s="${i}">${st.look_closer.strongs.map(n => `<button type="button" class="pv-edw pv-edw-on" data-ed="word" data-s="${i}" data-n="${n}">${esc(n)} ✓</button>`).join("")}</div>
          <button type="button" class="pv-btn" data-ed="words" data-s="${i}"${st.refs.length ? "" : " disabled"}>Show the words of these verses</button></div>
        <label>Your note for this step <small>(shown under your name, clearly not Scripture)</small><textarea data-k="my_note" data-s="${i}" maxlength="1500" rows="2">${esc(st.my_note)}</textarea></label>
      </div>`).join("")}
      <button type="button" class="pv-btn" data-ed="addstep">＋ Add a step</button>
      <fieldset class="pv-edvis"><legend>Who can see it?</legend>${Object.keys(VIS).map(v => `<label class="pv-edck"><input type="radio" name="vis" value="${v}"${(d.visibility || "private") === v ? " checked" : ""}> ${VIS[v]}<small>${v === "private" ? " stays on this device" : v === "link" ? " send the link or QR code" : " sent to Hans; after his check it is listed here for everyone"}</small></label>`).join("")}</fieldset>
      <div class="pv-nav"><button type="submit" class="pv-btn pv-primary">💾 Save${d.isNew ? "" : " changes"}</button>${d.isNew ? "" : `<button type="button" class="pv-btn pv-eddel">🗑 Delete</button>`}<button type="button" class="pv-btn pv-backlist">‹ Back</button></div>
      <p class="pv-small" id="pvEdNote">Every verse comes from the Bibles in BibleChat; your questions and notes are shown as yours. The questions at the end ("Which verse says …?") are made from your verses.</p>
    </form>`, true);
    if(keep) root.scrollTop = keep;
    root.querySelectorAll(".pv-edprev").forEach(async el => { const {vs} = await readVerses(el.dataset.ref).catch(() => ({vs: []}));
      const t = vs.map(x => x[3]).join(" "); el.textContent = t ? (t.length > 220 ? t.slice(0, 217) + "…" : t) : T("Not in the Bibles here."); });
  }
  /* "gen 3:1-6", "1 cor 13", "Psalm 23", "Song of Solomon 2:1" -> "Genesis 3:1-6" ... (any book name BibleChat knows) */
  async function normRef(text){
    const books = await A.books(), t = String(text).trim().replace(/\s+/g, " ").replace(/[–—]/g, "-");
    const m = /^(.+?)\s*(\d+)(?:\s*[:.]\s*(\d+)(?:\s*-\s*(\d+)(?:\s*[:.]\s*(\d+))?)?)?\s*$/.exec(t); if(!m) return null;
    const key = x => norm(x).replace(/[^a-z0-9]/g, ""), typed = key(m[1]), all = books.concat(["1 Enoch", "Jubilees"]);
    const book = all.find(b => key(b) === typed) || all.find(b => key(A.bookName(b)) === typed) || all.find(b => typed.length >= 2 && key(b).startsWith(typed))
      || all.find(b => typed.length >= 2 && key(A.bookName(b)).startsWith(typed)) || (typed === "psalm" ? "Psalms" : null);
    if(!book) return null;
    const c = +m[2], v1 = m[3] ? +m[3] : null, x = m[4] ? +m[4] : null, y = m[5] ? +m[5] : null;
    return book + " " + c + (v1 == null ? "" : ":" + v1 + (x == null ? "" : y == null ? (x > v1 ? "-" + x : "") : "-" + x + ":" + y));
  }
  async function edAddRef(i, text){
    const msg = root.querySelector(`.pv-edmsg[data-s="${i}"]`), parts = String(text).split(/[;,]\s*(?=[1-4]?\s*[A-Za-z])/).filter(x => x.trim());
    for(const part of parts){
      const r = await normRef(part); if(!r){ msg.textContent = T("Not a verse BibleChat knows. Try e.g. Genesis 3:1-6."); return; }
      const {vs} = await readVerses(r).catch(() => ({vs: []})); if(!vs.length){ msg.textContent = r + ": " + T("not in the Bibles here."); return; }
      const st = S.draft.steps[i]; if(!st.refs.includes(r)) st.refs.push(r);
    }
    edRender();
  }
  /* the Hebrew/Greek words of a step's verses (from the King James with Strong's numbers) as chips to tap */
  async function edWords(i){
    const st = S.draft.steps[i], books = await A.books(), seen = new Map(), box = root.querySelector(`.pv-edwl[data-s="${i}"]`);
    box.innerHTML = `<span class="pv-small">Loading…</span>`;
    for(const r of st.refs){ const p = parseRef(r), bi = books.indexOf(p.book); if(bi < 0) continue;
      const kjv = await A.study("kjv/" + bi + ".json").catch(() => ({}));
      for(const k of Object.keys(kjv)){ const [c, v] = k.split(":").map(Number); if(!inRef(p, c, v)) continue;
        for(const w of kjv[k]) if(typeof w !== "string") for(const n of w[1].split(" ")) if(/^[HG]\d+$/.test(n) && !STOP_STRONGS.has(n) && !seen.has(n)) seen.set(n, w[0].trim()); }
      if(seen.size > 60) break; }
    const nums = [...seen.keys()].slice(0, 40), out = [];
    for(const n of nums){ const d = await A.study("dict/" + n[0] + Math.floor(+n.slice(1) / 500) + ".json").catch(() => ({})), e = d[n] || {};
      out.push(`<button type="button" class="pv-edw${st.look_closer.strongs.includes(n) ? " pv-edw-on" : ""}" data-ed="word" data-s="${i}" data-n="${n}"><span class="pvx" lang="${n[0] === "H" ? "he" : "el"}">${esc(e.w || "")}</span> <i class="pvx">${esc(e.t || "")}</i> “${esc(seen.get(n))}”${st.look_closer.strongs.includes(n) ? " ✓" : ""}</button>`); }
    box.innerHTML = out.join("") || `<span class="pv-small">No Hebrew/Greek words found for these verses.</span>`;
  }
  async function edFind(i, q){
    const box = root.querySelector(`.pv-edhits[data-s="${i}"]`); if(!q.trim()) return;
    box.innerHTML = `<p class="pv-small">Searching…</p>`;
    let hits = []; try{ hits = await A.findVerses(q); }catch(e){}
    box.innerHTML = hits.length ? hits.slice(0, 15).map(h => `<div class="pv-edhit"><button type="button" class="pv-btn" data-ed="hit" data-s="${i}" data-ref="${esc(h.ref)}">＋</button> <b>${esc(label(h.ref))}</b> <span class="pvx">${esc(h.text.length > 160 ? h.text.slice(0, 157) + "…" : h.text)}</span></div>`).join("") : `<p class="pv-small">Nothing found. Try other words.</p>`;
  }
  /* quiz from the path's own verses: "Which verse says …?" (the answer is always the verse) */
  async function autoQuiz(steps){
    const quiz = [];
    for(const st of steps) for(const r of st.refs){
      const p = parseRef(r); if(!p || p.v1 === null) continue;
      const first = p.book + " " + p.c1 + ":" + p.v1, {vs} = await readVerses(first).catch(() => ({vs: []})); if(!vs.length) continue;
      const w = vs[0][3].split(/\s+/), start = w.slice(0, Math.min(10, w.length)).join(" ");
      quiz.push({q: `Which verse says: “${start}${w.length > 10 ? " …" : ""}”?`, type: "find_the_verse", answer_refs: [first], why: ["A verse of this path"], score: 0});
    }
    return quiz.slice(0, 20);
  }
  async function edSave(){
    const d = S.draft, note = root.querySelector("#pvEdNote");
    d.title = (d.title || "").trim(); d.opening_question = (d.opening_question || "").trim();
    const steps = d.steps.filter(st => st.refs.length);
    if(!d.title || !d.opening_question){ note.textContent = T("Give the path a title and a starting question."); note.classList.add("pv-err"); return; }
    if(!steps.length){ note.textContent = T("Add at least one verse."); note.classList.add("pv-err"); return; }
    steps.forEach((st, i) => { if(!st.question.trim()) st.question = `What does ${label(st.refs[0])} say?`; st.look_closer.xref_top = st.look_closer.xref_top ? 5 : 0;
      const he = st.look_closer.strongs.find(n => n[0] === "H"); if(he) st.look_closer.letters = he; else delete st.look_closer.letters; });
    const vis = (root.querySelector('input[name="vis"]:checked') || {}).value || "private";
    const quiz = await autoQuiz(steps);
    const p = {id: d.id, title: d.title, opening_question: d.opening_question, author: (d.author || "").trim(), category: d.category || "", visibility: vis, steps, quiz,
      group: (d.group || "").trim() || undefined, study_date: /^\d{4}-\d{2}-\d{2}$/.test(d.study_date || "") ? d.study_date : undefined,
      show: Math.min(10, Math.max(quiz.length, 1)), mine: true, updated: new Date().toISOString().slice(0, 10),
      sources: ["Made by " + ((d.author || "").trim() || "a BibleChat reader"), "KJV", "ETH", "BSB", "Strong's", "OpenBible cross-references"]};
    if(d.author) set("author", d.author.trim());
    const M = mine().filter(x => x.id !== p.id); M.unshift(p); set("mine", M.slice(0, 50));
    S.draft = null; S.section = "community";
    if(vis === "community"){ await sendToCommunity(p); }
    else if(vis === "link"){ share(p, "list", "path"); A.toast(T("Saved. Send the link or QR code.")); }
    else { await showList(); A.toast(T("Saved on this device.")); }
  }
  /* 👥 Community: the path goes to Hans (FormSubmit, no account); he checks every verse and word, then lists it for everyone */
  async function sendToCommunity(p){
    const url = A.shareUrl(shareHash(p, 0)), body = {message: `A reader sent a study path for the Community.\n\nTitle: ${p.title}\nQuestion: ${p.opening_question}\nBy: ${p.author || "-"}\nTopic: ${p.category || "-"}\n\nOpen it: ${url}\n\n` + p.steps.map((st, i) => `Step ${i + 1}: ${st.question}\n  ${st.refs.join("; ")}${st.my_note ? "\n  Note: " + st.my_note : ""}`).join("\n") + "\n\nThe whole path (JSON):\n" + JSON.stringify(p),
      _subject: "BibleChat Community study path: " + p.title, _template: "box", _captcha: "false"};
    try{ const r = await fetch(REQ_URL, {method: "POST", headers: {"Content-Type": "application/json", "Accept": "application/json"}, body: JSON.stringify(body)}); if(!r.ok) throw new Error(r.status);
      const M = mine(); const x = M.find(y => y.id === p.id); if(x){ x.community = new Date().toLocaleDateString(); set("mine", M); }
      await showList(); A.toast(T("Sent to Hans for the Community. Until then anyone with the link can use it."));
    }catch(e){ await showList(); A.toast(T("Saved, but it couldn't be sent. Check the internet connection and choose 👥 Community again.")); }
  }
  /* 📜 Study Paths about a search or chat question ("Adam Eve" finds The Garden, the serpent and Cain) */
  const FIND_STOP = new Set("the and for with that this what does about from into have was were his her him she they them who whom which when where why how are you your our not but all any can will shall bible say says said".split(" "));
  function findPaths(q, n){
    const toks = [...new Set((norm(q).match(/[a-z0-9']+/g) || []).map(w => w.replace(/'s$/, "")).filter(w => w.length > 2 && !FIND_STOP.has(w)))];
    if(!toks.length) return [];
    const hay = p => norm([p.title, p.opening_question, p.category, p.group, p.series && p.series.title, (p.step_questions || (p.steps || []).map(s => s.question) || []).join(" "), (p.books || []).join(" "), (p.steps && p.steps.map ? p.steps.map(s => (s.refs || []).join(" ")).join(" ") : "")].filter(Boolean).join(" "));
    const scored = (list || []).concat(mine()).map(p => { const h = hay(p); let sc = 0;
      for(const t of toks){ const st = t.replace(/s$/, ""); if(new RegExp("(^|[^a-z])" + st.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "").test(h)) sc += norm(p.title).includes(st) ? 2 : 1; }
      return {p, sc}; }).filter(x => x.sc >= Math.min(2, toks.length));
    return scored.sort((a, b) => b.sc - a.sc).slice(0, n || 4).map(x => x.p);
  }
  /* paths of a series (e.g. the 7 sessions of the mirror prophecies) stand together under the series' title, with its own ↗ / QR code */
  /* 📂 a series (e.g. the 7 sessions of Revelation & Daniel) is ONE folder card in the list; tapping it opens the folder
     with its sessions. Any future series made of several sessions ("series" in a path) works the same way. */
  /* folders: a series' sessions, and a Bible study group's studies (official ones and the ones readers make in Community),
     each become ONE folder card; Open shows what is inside. */
  const slug = x => norm(x || "").replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 60);
  function folderOf(p){ return p.series ? {kind: "series", id: p.series.id} : p.group ? {kind: "group", id: slug(p.group)} : null; }
  const day = d => { const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(d || ""); return m ? new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3])) : null; };
  const today = () => { const t = new Date(); return new Date(t.getFullYear(), t.getMonth(), t.getDate()); };
  const dayLabel = d => { const x = day(d); return x ? x.toLocaleDateString(undefined, {weekday: "short", month: "short", day: "numeric"}) : ""; };
  /* a group's studies: the next one (today or later) first, then the later ones, then the past ones newest first */
  function groupOrder(ps){
    const t = today(), up = ps.filter(p => day(p.study_date) && day(p.study_date) >= t).sort((a, b) => day(a.study_date) - day(b.study_date));
    const past = ps.filter(p => !up.includes(p)).sort((a, b) => (day(b.study_date) || 0) - (day(a.study_date) || 0) || String(a.title).localeCompare(b.title));
    return {list: up.concat(past), next: up[0] || null};
  }
  function gridWithSeries(shown, P){
    const cards = [], seen = {}, order = [];
    for(const p of shown){ const f = folderOf(p);
      if(f){ const k = f.kind + ":" + f.id; if(!seen[k]){ seen[k] = []; order.push({folder: k, kind: f.kind}); } seen[k].push(p); } else order.push(p); }
    order.sort((a, b) => (b.folder ? 1 : 0) - (a.folder ? 1 : 0));   // folders first, then the single paths in their usual order
    for(const x of order) cards.push(x.folder ? folderCard(seen[x.folder], P, x.kind) : card(x, P[x.id] || {}));
    return cards.length ? `<div class="pv-grid">${cards.join("")}</div>` : "";
  }
  function folderCard(ps, P, kind){
    const isG = kind === "group";
    if(!isG) ps = ps.slice().sort((a, b) => a.series.session - b.series.session);
    const g = isG ? groupOrder(ps) : null; if(isG) ps = g.list;
    const id = isG ? slug(ps[0].group) : ps[0].series.id, title = isG ? ps[0].group : ps[0].series.title, word = isG ? (ps.length === 1 ? "study" : "studies") : "sessions";
    const info = ps.map(p => cardInfo(p, P[p.id] || {})), fin = info.filter(i => i.finished).length, busy = info.filter(i => i.started && !i.finished).length;
    const mins = ps.reduce((a, p) => a + (p.minutes || 0), 0), status = isG && g.next ? `📅 Next: ${g.next.title.replace(/:.*$/, "")} · ${dayLabel(g.next.study_date)}`
      : fin === ps.length ? `✓ All ${ps.length} ${word} finished` : fin || busy ? `${fin} of ${ps.length} ${word} finished` : "Not started";
    const lead = isG ? ps.map(p => p.title).join(" · ") : ps.map(p => p.title.replace(/^Session \d+:\s*/, "")).join(" · ");
    return `<article class="pv-pc pv-folder" data-${isG ? "group" : "series"}="${esc(id)}">
      <button class="pv-pc-open pv-sopen" data-kind="${isG ? "group" : "series"}" data-series="${esc(id)}" aria-label="${esc("Open " + title)}"><div class="pv-pc-img">${picture(ps[0], false)}<span class="pv-pc-cat">${isG ? "👥" : "📂"} ${ps.length} ${word}</span></div>
        <div class="pv-pc-txt"><b class="pvx">${isG ? "👥 " : ""}${esc(title)}</b><span class="pvx">${esc(lead)}</span></div></button>
      <div class="pv-pc-meta"><span>${isG ? "👥" : "📂"} ${ps.length}${!isG && ps.length < ps[0].series.of ? " of " + ps[0].series.of : ""} ${word}</span>${mins ? `<span title="About ${mins} minutes in all">⏱ ${mins} min</span>` : ""}</div>
      <div class="pv-pc-prog"><div class="pv-dots" aria-hidden="true">${info.map(i => `<i class="${i.finished ? "pv-d-ok" : i.started ? "pv-d-now" : ""}"></i>`).join("")}</div><small class="${isG && g.next ? "pv-busy" : fin === ps.length ? "pv-ok" : fin || busy ? "pv-busy" : ""}">${esc(status)}</small></div>
      <div class="pv-pc-acts"><button class="pv-btn pv-primary pv-sopen" data-kind="${isG ? "group" : "series"}" data-series="${esc(id)}"><span>Open</span> ›</button><button class="pv-btn pv-serqr" data-kind="${isG ? "group" : "series"}" data-series="${esc(id)}" title="Share this folder by link or QR code" aria-label="Share this folder">↗</button></div></article>`;
  }
  /* inside a folder: a series' sessions in order, or a group's studies (the next one first) */
  async function folderPaths(kind, id){
    const L = await loadList();
    return kind === "group" ? groupOrder(L.concat(mine()).filter(p => p.group && slug(p.group) === id)) : {list: L.filter(p => p.series && p.series.id === id).sort((a, b) => a.series.session - b.series.session), next: null};
  }
  async function showSeries(id){ return showFolder("series", id); }
  async function showFolder(kind, id){
    const {list: ps, next} = await folderPaths(kind, id);
    if(!ps.length){ await showList(); return; }
    const isG = kind === "group", P = progress(), arrived = S.arrivedList; S.arrivedList = false;
    S.view = "series"; S.series = id; S.folderKind = kind; S.path = null;
    const title = isG ? ps[0].group : ps[0].series.title, ra = ps.find(p => p.read_along);
    frame((isG ? "👥 " : "📂 ") + title, (arrived ? `<div class="pv-welcome">👋 <b>Someone shared ${isG ? "this Bible study group" : "these study sessions"} with you.</b> ${isG ? "The next study is first: read it ahead and come prepared." : "Start with Session 1 and press <b>Start</b>."} Free, no sign-up.</div>` : "")
      + (isG ? `<p class="pv-lead">The chapters this group studies${next ? ", the next one first" : ""}. Read ahead to come prepared: every study has the verses, the Hebrew and Greek words and questions${ra ? `, and <b>Read in ${esc(ra.read_along.label)} ↗</b> next to every passage to read it in the group's own Bible` : ""}.</p>`
        : `<p class="pv-lead">${ps.length}${ps.length < ps[0].series.of ? " of " + ps[0].series.of : ""} sessions, one after another. Each starts with a question and walks through the verses; the questions at the end are answered with a verse.</p>`)
      + `<button class="pv-btn pv-serqr pv-sharewide" data-kind="${kind}" data-series="${esc(id)}">↗ Share ${isG ? "this group" : "these sessions"} · link or QR code</button>`
      + `<div class="pv-grid">${ps.map(p => card(p, P[p.id] || {}, next && p.id === next.id)).join("")}${isG && ps.some(p => p.category === GROUPS) ? ADD_CARD : ""}</div>`
      + `<div class="pv-nav"><button class="pv-btn pv-backlist">‹ All Study Paths</button></div>`, true);
  }
  /* 👥 Bible Study Groups: one folder per group, then "+ Add your own study path" */
  function groupsView(shown, P){
    const reqs = get("requests", []);
    return `<p class="pv-lead">Studies made for Bible study groups: the group picks the Bible and the verses, and the study path is written for them. Each group has its own folder, the next study first, so everyone can read ahead. Share the folder or a study with your group (↗).</p>`
      + `<div class="pv-grid">${(gridWithSeries(shown, P).replace(/^<div class="pv-grid">|<\/div>$/g, ""))}${ADD_CARD}</div>`
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
      <button class="pv-btn pv-listen" data-ls="step">🔊 Listen to this step</button>
      <div class="pv-stepno">Step ${S.step + 1} of ${n}</div>
      <div class="pv-track" role="navigation" aria-label="Steps">${p.steps.map((x, i) => `<button class="pv-dot${i === S.step ? " pv-dot-now" : ""}${done.has(i) ? " pv-dot-ok" : ""}" data-step="${i}" title="${esc("Step " + (i + 1) + ": " + x.question)}">${done.has(i) ? "✓" : i + 1}</button>`).join(`<i class="pv-track-line"></i>`)}</div>
      <div class="pv-bar"><i style="width:${Math.round(100 * done.size / n)}%"></i></div>
      <h3 class="pv-q pvx">${esc(p.mine ? T(s.question) : s.question)}</h3>
      <div class="pv-verses${s.side_by_side ? " pv-sbs" : ""}" id="pvVerses"><p class="pv-small">Loading the verses…</p></div>
      ${p.mine && s.my_note ? `<div class="pv-cnote"><h4>✍ Note from <span class="pvx">${esc(p.author || T("the maker of this path"))}</span></h4><p class="pv-cnote-why">Written by the person who made this path: not Scripture, and not checked by BibleChat.</p><div class="pvx">${esc(s.my_note)}</div></div>` : ""}
      ${s.facts ? `<div class="pv-facts"><h4>Facts about the words</h4>${s.facts.map(f => `<p class="pvx">${esc(f.text)}<br><small>${(f.refs || []).map(r => { const q = parseRef(r); return refLink(q.book, q.c1, q.v1, label(r)); }).join(" · ")}${f.refs && f.strongs ? " · " : ""}${(f.strongs || []).map(x => `<button class="pv-sn" data-n="${x}">Strong's ${x}</button>`).join(" ")}</small></p>`).join("")}</div>` : ""}
      ${(s.compare || []).length > 1 ? `<details class="pv-sec" data-sec="compare"><summary>⇄ Compare the translations</summary><div class="pv-secbody"></div></details>` : ""}
      ${(s.look_closer && ((s.look_closer.strongs || []).length || s.look_closer.xref_top)) ? `<details class="pv-sec" data-sec="closer"><summary>🔎 Look closer: the Hebrew/Greek words and cross-references</summary><div class="pv-secbody"></div></details>` : ""}
      ${(s.notes || []).length ? `<details class="pv-sec pv-notesec" data-sec="notes"><summary>📝 Text and notes: what the commentaries say</summary><div class="pv-secbody"></div></details>` : ""}
      <label class="pv-see" for="pvSee">What do you see?</label>
      <textarea id="pvSee" class="pvx" maxlength="4000" placeholder="${esc(T("Your own notes on these verses. They stay on this device."))}">${esc(mineNote)}</textarea>
      <div class="pv-nav"><button class="pv-btn pv-prev"${S.step ? "" : " disabled"}>‹ Previous step</button>${S.step < n - 1 ? `<button class="pv-btn pv-primary pv-next">Next step ›</button>` : `<button class="pv-btn pv-primary pv-toquiz">Questions and answers ›</button>`}</div>
      <button class="pv-btn pv-share pv-sharewide">↗ Share this path with someone</button>
      ${p.mine ? `<button class="pv-btn pv-sharewide pv-edit" data-id="${esc(p.id)}">✏️ ${p.received ? "Make it your own (edit a copy)" : "Edit this path"}</button>` : ""}
      <p class="pv-small"><span>Sources:</span> <span class="pvx">${esc((p.sources || []).join(" · "))}</span></p>`, true);
    S.versesP = drawVerses(s);
    if(S.lsAuto){ S.lsAuto = false; lsStart("step"); }   // 🔊 Listen goes on into the next step
  }
  async function drawVerses(s){
    const box = root.querySelector("#pvVerses"), my = S.step, html = [];
    for(const r of s.refs){
      const {key, vs} = await readVerses(r); if(S.step !== my || !root.contains(box)) return;
      const p = parseRef(r);
      html.push(`<div class="pv-ref" data-ref="${esc(r)}" data-key="${esc(key || "")}"><div class="pv-refh">${refLink(p.book, p.c1, p.v1, label(r))}${key && key !== "reader" ? ` <small class="pv-from">${esc(key === "ETH" ? "Ethiopian Canon" : key)}: not in your Bible</small>` : ""} ${readAlong(S.path, p)}${p.book in BOOKS66 ? nivLink(r) : ""}</div>`
        + (vs.length ? `<div class="pvx pv-text">${vs.map(([b, c, v, t]) => `<span class="pv-v${hlClass(b, c, v)}"><sup>${p.c1 !== p.c2 || p.v1 === null ? c + ":" : ""}${v}</sup>${esc(t)} </span>`).join("")}</div>` : `<p class="pv-err">This passage isn't in the Bibles available here.</p>`) + `</div>`);
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
    frame(p.title, `<div class="pv-open pvx"><small>The question</small>${esc(p.opening_question)}</div><h3>Questions and answers</h3><button class="pv-btn pv-listen" data-ls="quiz">🔊 Listen to the questions</button>
      <p class="pv-small">The answer to every question is a verse.</p>
      ${A.similar ? `<label class="pv-opt"><input type="checkbox" id="pvPast"${prefs.past ? " checked" : ""}> Put questions close to what I asked before first (uses the meaning search on this device; off unless you tick it)</label>` : ""}
      <div id="pvQs">${S.quiz.pick.map((q, n) => qCard(q, n)).join("")}</div>
      <div id="pvScore"></div>
      <div class="pv-nav"><button class="pv-btn pv-backsteps">‹ Back to the steps</button>${S.quiz.rest.length ? `<button class="pv-btn pv-more">More questions (${S.quiz.rest.length})</button>` : ""}</div>
      <div id="pvPrayer"></div>`, true);
    if(typeof BCPrayers !== "undefined") BCPrayers.closing(root.querySelector("#pvPrayer"), p);   // 🙏 a closing prayer (web/prayers.js)
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
  /* Links come back from Facebook, Messenger, Instagram, email and text messages with extra bits on the end: the app's own
     tracking (?fbclid=…, &utm_source=…), sometimes put after the "#", and the full stop or bracket of the sentence the link
     ended. cleanHash cuts that off, so the link still opens what was shared instead of falling back to Home. */
  function cleanHash(h){ return String(h || "").replace(/(%3F|%26|[?&]).*$/i, "").replace(/[\s.,;:!)\]}'"»”’]+$/, ""); }
  /* The address to send. A path, a series, a prayer and the two lists each have a short page of their own on the phone site
     (p/<id>/, series/<id>/, pray/<id>/, p/, pray/; web/build_study.py writes them). A posted link then shows that path's or
     prayer's own picture, title and question, and the page opens it in BibleChat. A path someone made travels in the link. */
  const SHORT = [[/^#\/path\/(?!mine\/)([a-z0-9-]+)\/1$/, "p/$1/"], [/^#\/paths\/?$/, "p/"], [/^#\/paths\/series\/([a-z0-9-]+)\/?$/, "series/$1/"],
    [/^#\/prayers\/([a-z0-9-]+)$/, "pray/$1/"], [/^#\/prayers\/?$/, "pray/"]];
  function shortPath(hash){
    const g = /^#\/paths\/group\/([a-z0-9-]+)\/?$/.exec(hash);   // a Bible study group: a short page only for the groups on the site
    if(g) return (list || []).some(p => p.group && slug(p.group) === g[1]) ? "group/" + g[1] + "/" : null;
    for(const [re, to] of SHORT) if(re.test(hash)) return hash.replace(re, to); return null; }
  function linkOf(hash){ const sp = shortPath(hash); return sp ? A.shareUrl("") + sp : A.shareUrl(hash); }
  function shareHash(p, step){
    if(p.mine){   // version 2: the whole path travels in the link (title, question, steps, options, words, notes); nothing is stored on a server
      const o = st => (st.compare && st.compare.length > 1 ? 1 : 0) | ((st.notes || []).includes("scofield") ? 2 : 0) | ((st.notes || []).includes("henry") ? 4 : 0) | (st.look_closer && st.look_closer.xref_top ? 8 : 0);
      const d = {v: 2, ti: p.title, q: p.opening_question, a: p.author || undefined, c: p.category || undefined, g: p.group || undefined, dt: p.study_date || undefined,
        s: p.steps.map(st => ({q: st.question, r: st.refs, o: o(st), w: (st.look_closer || {}).strongs || [], n: st.my_note ? String(st.my_note).slice(0, 800) : undefined}))};
      const data = btoa(unescape(encodeURIComponent(JSON.stringify(d)))).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, ""); return "#/path/mine/" + data; }
    return "#/path/" + encodeURIComponent(p.id) + "/" + (step + 1);
  }
  /* ↗ Share a path with someone: one link that opens the path on the phone version of BibleChat (any phone or computer
     browser, no sign-up), at step 1. Send it by the phone's own share sheet, a text message, WhatsApp or email, or show the
     QR code to someone next to you. */
  function shareText(t){ return t.kind === "all" ? "Have a look at the BibleChat Study Paths (free, no sign-up): guided Bible studies with the verses side by side, the Hebrew and Greek words, and questions. Pick one and start."
    : t.kind === "group" ? `Join "${t.title}" in BibleChat (free, no sign-up): ${t.question}`
    : t.kind === "series" ? `Let's study "${t.title}" together in BibleChat (free, no sign-up): ${t.question}`
    : `Let's study "${t.title}" together in BibleChat (free, no sign-up): ${t.opening_question || t.question}`; }
  /* what is shared: one path (step 1), a whole series, or the page with all the Study Paths */
  function target(kind, p){
    if(kind === "all") return {kind, title: "BibleChat Study Paths", question: "Every path starts with a question and walks through the verses.", hash: "#/paths", image: null};
    if(kind === "group") return {kind, title: p.group, question: "The chapters this Bible study group studies, the next one first: read ahead and come prepared.", hash: "#/paths/group/" + slug(p.group), image: p.image};
    if(kind === "series") return {kind, title: p.series.title, question: `${p.series.of} sessions, Daniel and Revelation side by side.`, hash: "#/paths/series/" + p.series.id, image: p.image};
    return Object.assign({kind: "path", hash: shareHash(p, 0), question: p.opening_question}, p);
  }
  function share(p, from, kind){
    p = p || S.path; if(!p && kind !== "all") return;
    const t = target(kind || "path", p), url = linkOf(t.hash), text = shareText(t), both = text + "\n" + url;
    const what = t.kind === "all" ? "the page with all the Study Paths" : t.kind === "group" ? "this Bible study group's folder" : t.kind === "series" ? "this series of study paths" : "this study path, at step 1";
    S.shareFrom = from || "path"; S.shareP = t; S.view = "share";
    const back = S.shareFrom === "list" || S.shareFrom === "series" ? `<button class="pv-btn pv-backlist">‹ Back to the paths</button>` : `<button class="pv-btn pv-backpath">‹ Back to the path</button>`;
    const wide = matchMedia("(min-width: 760px)").matches;   // on a computer the QR code comes first: hold the phone up to the screen
    const qr = `<div class="pv-qrbox"><p class="pv-small">${wide ? "Point a phone camera at the screen:" : "Or let them scan this code with their phone camera:"}</p><div class="pv-qr"></div><button class="pv-btn pv-qrbig">⛶ Show the QR code big (for a TV or projector)</button></div>`;
    frame(t.kind === "all" ? "↗ Share the Study Paths" : t.kind === "series" ? "↗ Share this series" : "↗ Share this path", `<div class="pv-shead"><img class="pv-shimg" src="${esc(A.base + (t.image || "img/thumb-studypaths.jpg"))}" alt="" onerror="this.outerHTML='<span class=&quot;pv-shico&quot;>📜</span>'"><div><b class="pvx">${esc(t.title)}</b><span class="pvx">${esc(t.question || "")}</span></div></div>
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
        <a class="pv-btn pv-so-x" href="https://x.com/intent/post?text=${encodeURIComponent(text)}&url=${encodeURIComponent(url)}" target="_blank" rel="noopener" aria-label="X (Twitter)">X (Twitter)</a>
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
    const qr = A.qr(linkOf(t.hash), 260); if(qr) g.drawImage(qr, W - 330, H - 330, 260, 260);
    g.fillStyle = "#e9ecef"; g.font = "bold 40px system-ui, sans-serif"; g.fillText("Study it free in BibleChat", 70, H - 210);
    g.fillStyle = "#9aa3ad"; g.font = "30px system-ui, sans-serif"; g.fillText("Scan the code, or open", 70, H - 160); g.fillText("beaugrand.github.io/BibleChat-voice", 70, H - 118); g.fillText("No sign-up · no app needed", 70, H - 76);
    const blob = await new Promise(r => c.toBlob(r, "image/png")), name = "BibleChat-" + (t.id || t.kind || "study").replace(/[^a-z0-9-]/gi, "") + ".png";
    const file = typeof File === "function" ? new File([blob], name, {type: "image/png"}) : null;
    if(file && navigator.canShare && navigator.canShare({files: [file]})){ try{ await navigator.share({files: [file], title: t.title, text: shareText(t) + "\n" + linkOf(t.hash)}); return; }catch(e){ if(e && e.name === "AbortError") return; } }
    const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = name; document.body.appendChild(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(a.href), 4000);
    A.toast(T("Picture saved. Post it with the link."));
  }
  /* the QR code over the whole screen, as big as it fits: for a TV, a projector or a room */
  function bigQr(){
    const t = S.shareP; if(!t) return;
    const url = linkOf(t.hash), px = Math.max(220, Math.min(innerWidth, innerHeight) - 250);
    const o = document.createElement("div"); o.className = "pv-qrfull";
    o.innerHTML = `<div class="pv-qrf-in"><b class="pvx">${esc(t.title)}</b><div class="pv-qrf-code"></div><span>Scan with your phone camera · BibleChat</span><button class="pv-btn pv-qrclose">✕ Close</button></div>`;
    const cv = A.qr(url, px); if(cv) o.querySelector(".pv-qrf-code").appendChild(cv);
    o.addEventListener("click", e => { if(e.target === o || e.target.closest(".pv-qrclose")) o.remove(); });
    root.appendChild(o);
  }
  async function shareFromCard(id){
    let p = (await loadList()).find(x => x.id === id) || mine().find(x => x.id === id);
    if(!p) return; share(p, S.view === "series" ? "series" : "list", "path");
  }
  /* a path someone made and sent by link: kept on this device under ✍ Your study paths (once), then opened */
  async function openShared(d){
    const str = x => String(x == null ? "" : x).slice(0, 1500);
    const steps = d.s.slice(0, 30).map(x => ({question: str(x.q).slice(0, 240), refs: (x.r || []).filter(r => parseRef(r)).slice(0, 12),
      compare: x.o & 1 ? ["KJV", "ETH", "BSB"] : [], notes: [x.o & 2 ? "scofield" : null, x.o & 4 ? "henry" : null].filter(Boolean),
      look_closer: {strongs: (x.w || []).filter(n => /^[HG]\d{1,4}$/.test(n)).slice(0, 8), xref_top: x.o & 8 ? 5 : 0}, my_note: str(x.n)})).filter(st => st.refs.length);
    steps.forEach(st => { const he = st.look_closer.strongs.find(n => n[0] === "H"); if(he) st.look_closer.letters = he; });
    if(!steps.length) return;
    const sig = JSON.stringify([d.ti, d.q, steps.map(s => s.refs)]), M = mine(), have = M.find(x => x.sig === sig);
    if(have){ await open(have.id, 0); return; }
    const quiz = await autoQuiz(steps);
    const p = {id: "mine-" + Date.now().toString(36), sig, group: str(d.g).slice(0, 80) || undefined, study_date: /^\d{4}-\d{2}-\d{2}$/.test(d.dt || "") ? d.dt : undefined, title: str(d.ti).slice(0, 90) || "A shared study path", opening_question: str(d.q).slice(0, 400), author: str(d.a).slice(0, 60), category: str(d.c).slice(0, 40),
      steps, quiz, show: Math.min(10, Math.max(quiz.length, 1)), mine: true, received: true, visibility: "link",
      sources: ["Made by " + (str(d.a) || "a BibleChat reader"), "KJV", "ETH", "BSB", "Strong's", "OpenBible cross-references"]};
    M.unshift(p); set("mine", M.slice(0, 50)); await open(p.id, 0);
  }
  /* a link "#/path/<id>/<step>" or "#/path/mine/<data>" */
  async function openHash(h){
    h = cleanHash(h);
    const all = /^#\/paths(?:\/(series|group)\/([a-z0-9-]+))?\/?$/.exec(h || "");
    if(all){
      S.arrivedList = true; S.filter = ALL; S.section = "paths";
      if(all[2]) await showFolder(all[1], all[2]); else await showList();
      return true;
    }
    const m = /^#\/path\/([^/]+)(?:\/([^/]+))?/.exec(h || ""); if(!m) return false;
    if(m[1] === "mine" && m[2]){
      try{
        const d = JSON.parse(decodeURIComponent(escape(atob(m[2].replace(/-/g, "+").replace(/_/g, "/")))));
        if(d.v === 2 && Array.isArray(d.s)){ S.arrived = true; await openShared(d); return true; }
        const refs = (d.r || []).filter(r => parseRef(r)).slice(0, 8);
        if(refs.length){ await fromAnswer(String(d.t || "A shared study path").slice(0, 300), refs); return true; }
      }catch(e){}
      return false;
    }
    let id = m[1]; try{ id = decodeURIComponent(id); }catch(e){}
    const L = await loadList();
    if(L.length && !L.some(x => x.id === id) && !mine().some(x => x.id === id)){   // an old or mistyped link: show all the paths instead
      S.arrivedList = true; S.filter = ALL; S.section = "paths"; await showList(); return true; }
    const n = parseInt(m[2], 10);   // the step number; anything else on the end is ignored
    S.arrived = true;   // came by a shared link: say so once on the first page
    await open(id, n > 0 ? n - 1 : null); return true;
  }

  /* ---------- events ---------- */
  function onClick(e){
    const t = e.target;
    if(t.closest(".pv-close")){ close(); return; }
    if(t.closest(".pv-back")){ if(S.view === "edit"){ S.draft = null; showList(); return; } if(S.view === "share" && S.shareFrom === "series" && S.series) showFolder(S.folderKind || "series", S.series); else if(S.view === "request" || (S.view === "share" && S.shareFrom === "list")) showList(); else if(S.view === "word" || S.view === "share") showPath(S.path.id, S.step); else if((S.view === "step" || S.view === "quiz") && S.path && S.path.series) showSeries(S.path.series.id); else if((S.view === "step" || S.view === "quiz") && S.path && S.path.group) showFolder("group", slug(S.path.group)); else if(S.view === "step" || S.view === "quiz" || S.view === "quoted" || S.view === "series") showList(); else close(); return; }
    const sc = t.closest(".pv-pc-share"); if(sc){ shareFromCard(sc.dataset.id); return; }
    if(t.closest(".pv-add")){ showRequest(); return; }
    const lb = t.closest(".pv-listen"); if(lb){ if(LS.on && LS.kind === lb.dataset.ls && !LS.paused) lsPause(); else lsStart(lb.dataset.ls); return; }
    if(t.closest(".pv-lspause")){ lsPause(); return; }
    if(t.closest(".pv-lsskip")){ lsSkip(); return; }
    if(t.closest(".pv-lsstop")){ lsStop(); return; }
    const sg = t.closest(".pv-segb"); if(sg){ S.section = sg.dataset.sec; showList(); return; }
    if(t.closest(".pv-new")){ editPath(null); return; }
    const ed = t.closest(".pv-edit"); if(ed){ const p = mine().find(x => x.id === ed.dataset.id); if(p){ const c = JSON.parse(JSON.stringify(p)); if(c.received){ c.id = "mine-" + Date.now().toString(36); delete c.received; delete c.sig; c.isNew = true; } editPath(c); } return; }
    if(t.closest(".pv-eddel")){ if(confirm(T("Delete this study path from this device?"))){ set("mine", mine().filter(x => x.id !== S.draft.id)); S.draft = null; showList(); } return; }
    const eb = t.closest("[data-ed]"); if(eb && S.view === "edit"){ e.preventDefault(); edAction(eb); return; }
    if(t.closest(".pv-shareall")){ share(null, "list", "all"); return; }
    const so = t.closest(".pv-sopen"); if(so){ showFolder(so.dataset.kind || "series", so.dataset.series); return; }
    const sq = t.closest(".pv-serqr"); if(sq){ const kind = sq.dataset.kind || "series"; folderPaths(kind, sq.dataset.series).then(({list}) => { if(list[0]) share(list[0], S.view === "series" ? "series" : "list", kind); }); return; }
    if(t.closest(".pv-qrbig")){ bigQr(); return; }
    if(t.closest(".pv-card-dl")){ shareCard(S.shareP).catch(() => A.toast(T("Couldn't make the picture."))); return; }
    if(t.closest(".pv-so-tt")){ const u = root.querySelector(".pv-url").value, h = root.querySelector(".pv-tthint"); if(h) h.hidden = false;
      (navigator.clipboard ? navigator.clipboard.writeText(u) : Promise.reject()).then(() => A.toast(T("Link copied")), () => {});
      if(navigator.share){ const p = S.shareP; navigator.share({title: p.title, text: shareText(p), url: u}).catch(() => {}); } return; }
    if(t.closest(".pv-reqgit")){ e.preventDefault(); const d = reqData();
      window.open("https://github.com/beaugrand/BibleChat-voice/issues/new?title=" + encodeURIComponent("Study path request: " + (d.passage || "?") + " (" + (d.group || "?") + ")") + "&body=" + encodeURIComponent(reqText(d)), "_blank", "noopener"); return; }
    if(t.closest(".pv-share")){ share(); return; }
    if(t.closest(".pv-backlist")){ if(S.view === "share" && S.shareFrom === "series" && S.series) showFolder(S.folderKind || "series", S.series); else showList(); return; }
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
  function edAction(b){
    const d = S.draft, i = +b.dataset.s, st = d.steps[i], a = b.dataset.ed;
    if(a === "addstep"){ d.steps.push(blankStep()); edRender(); setTimeout(() => { const el = root.querySelector(`.pv-eds[data-i="${d.steps.length - 1}"]`); if(el) el.scrollIntoView({block: "start"}); }, 30); return; }
    if(a === "delstep"){ d.steps.splice(i, 1); edRender(); return; }
    if(a === "up" && i > 0){ [d.steps[i - 1], d.steps[i]] = [d.steps[i], d.steps[i - 1]]; edRender(); return; }
    if(a === "down" && i < d.steps.length - 1){ [d.steps[i + 1], d.steps[i]] = [d.steps[i], d.steps[i + 1]]; edRender(); return; }
    if(a === "delref"){ st.refs.splice(+b.dataset.j, 1); edRender(); return; }
    if(a === "addref"){ const inp = root.querySelector(`.pv-edin[data-s="${i}"]`); if(inp && inp.value.trim()) edAddRef(i, inp.value); return; }
    if(a === "hit"){ if(!st.refs.includes(b.dataset.ref)) st.refs.push(b.dataset.ref); b.disabled = true; b.textContent = "✓"; const box = root.querySelector(`.pv-edrefs`); edRender(); return; }
    if(a === "find"){ const inp = root.querySelector(`.pv-edq[data-s="${i}"]`); if(inp) edFind(i, inp.value); return; }
    if(a === "words"){ edWords(i); return; }
    if(a === "word"){ const n = b.dataset.n, L = st.look_closer.strongs, k = L.indexOf(n); if(k >= 0) L.splice(k, 1); else if(L.length < 8) L.push(n);
      b.classList.toggle("pv-edw-on", L.includes(n)); b.innerHTML = b.innerHTML.replace(/ ✓$/, "") + (L.includes(n) ? " ✓" : ""); return; }
  }
  async function onSubmit(e){
    if(e.target.id === "pvEd"){ e.preventDefault(); const f = document.activeElement;
      if(f && f.classList && f.classList.contains("pv-edin")){ edAddRef(+f.dataset.s, f.value); return; }   // Enter in "Add verses" adds them
      if(f && f.classList && f.classList.contains("pv-edq")){ edFind(+f.dataset.s, f.value); return; }
      edSave(); return; }
    if(e.target.id === "pvReq"){ e.preventDefault(); sendRequest(); return; }
    const f = e.target.closest(".pv-find"); if(!f) return; e.preventDefault();
    const q = S.path.quiz[+f.dataset.q]; q.i = +f.dataset.q;
    const v = f.querySelector("input").value; if(!v.trim()) return;
    answer(q, await checkFind(q, v));
  }
  function onInput(e){
    if(S.view === "edit" && S.draft && e.target.closest && e.target.closest("#pvEd")){ const el = e.target, d = S.draft;
      if(el.dataset.f){ d[el.dataset.f] = el.value; return; }
      if(el.dataset.k){ d.steps[+el.dataset.s][el.dataset.k] = el.value; return; }
      if(el.dataset.opt && e.type === "change"){ const st = d.steps[+el.dataset.s], o = el.dataset.opt;
        if(o === "compare") st.compare = el.checked ? ["KJV", "ETH", "BSB"] : [];
        if(o === "scofield" || o === "henry"){ st.notes = st.notes.filter(x => x !== o); if(el.checked) st.notes.push(o); }
        if(o === "xref") st.look_closer.xref_top = el.checked ? 5 : 0; return; }
      if(el.name === "vis") d.visibility = el.value; return; }
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
    if(v.view === "quoted") await showQuoted(); else if(v.id && v.view === "step") await showPath(v.id, v.step);
    else if(v.id && v.view === "quiz"){ await showPath(v.id, v.step); await showQuiz(); } else await showList();
    if(v.top) root.scrollTop = v.top;
  }
  function close(){ lsStop(); if(root){ root.hidden = true; root.innerHTML = ""; S.view = "list"; S.draft = null; if(A.onClose) A.onClose(); } }
  function mount(adapter){
    A = adapter; root = adapter.container;
    root.classList.add("pv", "pv-dark"); root.hidden = true;
    root.addEventListener("click", onClick); root.addEventListener("toggle", onToggle, true);
    root.addEventListener("submit", onSubmit); root.addEventListener("input", onInput); root.addEventListener("change", onInput);
    addEventListener("keydown", e => { if(e.key === "Escape" && !root.hidden) close(); });
    loadList().catch(() => {});   // so a search can show the Study Paths about it at once
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
.pv-listen{display:block;width:100%;margin:2px 0 10px;font-weight:700;font-size:15.5px;padding:11px;background:rgba(217,180,74,.14);border-color:rgba(217,180,74,.55)}
.pv-player{position:sticky;bottom:0;z-index:5;display:flex;align-items:center;gap:6px;max-width:760px;margin:0 auto;padding:8px 12px calc(8px + env(safe-area-inset-bottom));background:#0f1215;border-top:1px solid var(--line);box-shadow:0 -6px 18px rgba(0,0,0,.35)}
.pv-plw{flex:1;min-width:0;font-size:13.5px;font-weight:650;color:var(--accent);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.pv-player .pv-btn{padding:7px 11px;font-weight:700}
.pv-saying{background:rgba(217,180,74,.22)!important;border-radius:6px;box-shadow:0 0 0 2px rgba(217,180,74,.35)}
.pv-seg{display:flex;gap:6px;background:var(--card);border:1px solid var(--line);border-radius:14px;padding:4px;margin:10px 0 6px}
.pv-segb{flex:1;border:0;background:none;color:var(--muted);font:inherit;font-weight:700;font-size:15px;padding:9px 6px;border-radius:10px;cursor:pointer}.pv-segon{background:var(--accent);color:var(--accent-text)}
.pv-who{display:flex;flex-direction:column;gap:4px;border:1px solid var(--line);background:var(--card);border-radius:12px;padding:10px 12px;margin:0 0 12px;font-size:14px}.pv-who span{color:var(--muted)}
.pv-new{display:block;width:100%;font-weight:700;font-size:16px;padding:12px;margin:0 0 6px}
.pv-pc-mine{display:flex;justify-content:space-between;align-items:center;gap:6px;padding:6px 12px 0;font-size:12px}.pv-vis{color:var(--muted)}
.pv-cnote{border:1px solid rgba(140,196,255,.35);background:rgba(140,196,255,.08);border-radius:10px;padding:8px 12px;margin:0 0 10px}.pv-cnote h4{margin:2px 0}.pv-cnote-why{font-size:12.5px;color:var(--muted);font-style:italic;margin:0 0 6px}
.pv-ed .pv-edrow{display:grid;grid-template-columns:1fr 1fr;gap:10px}@media (max-width:520px){.pv-ed .pv-edrow{grid-template-columns:1fr}}
.pv-eds{border:1px solid var(--line);background:var(--card);border-radius:14px;padding:10px 12px;margin:0 0 12px}.pv-edsh{display:flex;justify-content:space-between;align-items:center;margin:0 0 6px}.pv-edsh b{color:var(--accent);font-size:16px}
.pv-ed .pv-eds input,.pv-ed .pv-eds textarea{background:var(--bg)}
.pv-edref{border-left:3px solid var(--accent);padding:4px 8px;margin:0 0 6px}.pv-edprev{font-family:Georgia,serif;font-size:14px;color:var(--muted)}
.pv-edadd{display:flex;gap:6px;align-items:center}.pv-edadd input{flex:1;min-width:0;margin:0!important}
.pv-edfind summary{cursor:pointer;color:var(--accent);margin:6px 0}.pv-edhit{font-size:13.5px;padding:4px 0;border-top:1px dashed var(--line)}.pv-edhit .pv-btn{padding:2px 9px}
.pv-edopts{display:grid;grid-template-columns:1fr 1fr;gap:2px 10px;margin:8px 0}@media (max-width:520px){.pv-edopts{grid-template-columns:1fr}}
.pv-ed .pv-edck{display:flex;gap:6px;align-items:baseline;font-weight:500;margin:2px 0}.pv-ed .pv-edck input{display:inline;width:auto;margin:0}
.pv-edwords{border-top:1px dashed var(--line);padding:8px 0 4px;margin:4px 0 8px}.pv-edwords small{color:var(--muted);display:block}
.pv-edwl{display:flex;flex-wrap:wrap;gap:5px;margin:6px 0}.pv-edw{border:1px solid var(--line);background:var(--bg);color:inherit;border-radius:99px;padding:3px 10px;font:inherit;font-size:13px;cursor:pointer}.pv-edw-on{border-color:var(--accent);background:rgba(217,180,74,.18)}
.pv-edvis{border:1px solid var(--line);border-radius:12px;padding:6px 12px;margin:10px 0}.pv-edvis legend{font-weight:700;padding:0 6px}.pv-edvis small{color:var(--muted)}
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
.pv-folder{border-color:rgba(217,180,74,.55)}
.pv-pc-meta>span.pv-next{background:rgba(217,180,74,.25);color:var(--accent)}
.pv-shead .pv-shico{display:block;font-size:40px;line-height:64px;width:96px;margin:0;text-align:center;color:inherit;flex:none}
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
  async function openCommunity(){ S.section = "community"; await open(); }
  /* remember where the reader is before another screen covers the path (🙏 sharing the closing prayer), so reopen() returns there */
  function remember(){ if(root && !root.hidden) lastView = {view: S.view === "quiz" ? "quiz" : S.view === "word" || S.view === "share" ? "step" : S.view, id: S.path && S.path.id, step: S.step, top: root.scrollTop}; }
  return {mount, open, close, reopen, remember, openHash, cleanHash, shortPath, linkOf, fromAnswer, choose, parseRef, label: LABEL, isOpen: () => root && !root.hidden,
    findPaths, openCommunity, preload: () => loadList(), normRef,
    adapter: () => A, readVerses, title: id => { const x = (list || []).find(q => q.id === id); return x ? x.title : ""; }};   // 🙏 Prayers (web/prayers.js) borrow these
})();
if(typeof module !== "undefined") module.exports = BCPaths;
