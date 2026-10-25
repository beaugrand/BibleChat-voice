/* BibleChat 🙏 Prayers: a prayer library, today's prayer, a prayer for the chapter you read, a closing prayer after
   each Study Path, and "Pray about this" under a search or chat answer.
   Shared by the phone (web/index.html) and the computer (bibleask/web/index.html), like paths.js. It borrows the
   Study Paths adapter (Bible chapters, the reader's Bible, voice, highlights), so each page only hands in a few extras.

   The rules (tests/test_prayers.py checks them):
   - The prayers live in web/prayers.json. Every prayer names the verses it is drawn from; this file shows those
     verses from the reader's own Bible, never typed-in Scripture.
   - A written prayer is the words of a man, not Scripture, and says so. The "Prayers of the Bible" have no written
     text: the verses themselves are the prayer.
   - A prayer the AI writes is labelled as the AI's, with the verses it was given under it.
   - Nothing is sent anywhere. "Ask an AI" only opens the AI the person picks, as everywhere else in BibleChat. */
"use strict";
const BCPrayers = (() => {
  let P = null, A = null, root = null, data = null, loading = null;
  const S = {view: "list", cat: "all", q: "", id: null, back: null, about: null, arrived: false};
  const esc = s => String(s == null ? "" : s).replace(/[&<>"']/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]));
  const T = x => (typeof tr === "function" ? tr(x) : x);
  const WRITTEN_NOTE = "A prayer written for BibleChat from these verses. The prayer is the words of a man, not Scripture; the verses are Scripture.";
  const BIBLE_NOTE = "A prayer the Bible itself records. These are the verses, in the Bible you are reading.";
  const AI_NOTE = "Written by an AI from the verses below. It is not Scripture: read it against them.";

  /* ---------- the data ---------- */
  function load(){
    if(data) return Promise.resolve(data);
    return loading || (loading = fetch(P.url).then(r => { if(!r.ok) throw new Error(r.status); return r.json(); })
      .then(d => { data = d; d.byId = {}; for(const p of d.prayers){ d.byId[p.id] = p; p._refs = p.refs.map(r => parse(r)).filter(Boolean); } return d; })
      .catch(e => { loading = null; throw e; }));
  }
  const parse = r => BCPaths.parseRef(r);
  const label = r => String(r).replace(/-/g, "–");
  const cat = id => (data.categories.find(c => c.id === id) || {id, icon: "🙏", name: id});
  const written = p => !!p.text;
  const kindRank = p => p.category === "bible" ? 1 : p.category === "paths" ? 2 : 0;   // written library prayers first
  function hasVerse(r, c, v){ return r.v1 === null ? c >= r.c1 && c <= r.c2 : (c > r.c1 || (c === r.c1 && v >= r.v1)) && (c < r.c2 || (c === r.c2 && v <= r.v2)); }
  const touchesChapter = (r, c) => c >= r.c1 && c <= r.c2;

  /* 🙏 for a chapter in Read: the prayers drawn from that chapter (written ones, then the Bible's own), then the book's
     own prayer, then the closing prayers of Study Paths that read this chapter, then a general one */
  function forChapter(book, ch){
    const hits = data.prayers.filter(p => p._refs.some(r => r.book === book && touchesChapter(r, ch)))
      .sort((a, b) => kindRank(a) - kindRank(b));
    const out = hits.filter(p => p.category !== "paths"), add = p => { if(p && !out.includes(p)) out.push(p); };
    add(data.byId[data.books[book]]); hits.forEach(add); add(data.byId[data.fallback]);
    return out;
  }
  /* ☀ today's prayer: the one drawn from the verse of the day if there is one, else from its chapter, else the next
     prayer in the library (the same for everyone on that date) */
  function today(votd, date){
    const lib = data.prayers.filter(p => written(p) && p.category !== "paths");
    if(votd){
      const v = lib.find(p => p._refs.some(r => r.book === votd.book && hasVerse(r, votd.ch, votd.v)));
      if(v) return v;
      const c = lib.find(p => p._refs.some(r => r.book === votd.book && touchesChapter(r, votd.ch)));
      if(c) return c;
    }
    const d = date || new Date(), day = Math.floor((Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()) - Date.UTC(2026, 0, 1)) / 864e5);
    return lib[((day % lib.length) + lib.length) % lib.length];
  }
  /* 🙏 Pray about this: the library prayers closest to an answer, by its verses and its words */
  const WORD = /[a-z']+/g, STOP = new Set("the and for that with this what does say about from are was who how why when his her their they them you your our not but all any can will shall unto thee thou thy have has had into upon".split(" "));
  function forAnswer(question, refs, n){
    const rs = (refs || []).map(parse).filter(Boolean), words = new Set((String(question || "").toLowerCase().match(WORD) || []).filter(w => w.length > 2 && !STOP.has(w)));
    const scored = data.prayers.filter(p => p.category !== "paths").map(p => {
      let s = 0, chap = false, book = false;   // the same verse counts most; one chapter or book in common counts once
      for(const q of rs) for(const r of p._refs){ if(r.book !== q.book) continue; book = true;
        if(q.v1 !== null && hasVerse(r, q.c1, q.v1)) s += 4; else if(touchesChapter(r, q.c1)) chap = true; }
      s += (chap ? 1.5 : 0) + (book ? 0.3 : 0);
      const hay = (p.title + " " + (p.tags || []).join(" ")).toLowerCase();
      for(const w of words) if(new RegExp("(^|[^a-z])" + w.replace(/'/g, "") + "(s|es|ed|ing)?([^a-z]|$)").test(hay)) s += 3;
      return [s + (written(p) ? 0.2 : 0), p];
    }).filter(x => x[0] >= 1).sort((a, b) => b[0] - a[0]);
    return scored.slice(0, n || 3).map(x => x[1]);
  }
  function forPath(path){
    if(!data || !path) return null;
    const own = data.prayers.find(p => (p.paths || []).includes(path.id));
    if(own) return own;
    const refs = (path.steps || []).flatMap(s => s.refs || []);   // a path someone made: the library prayer closest to it
    return forAnswer(path.title, refs, 1)[0] || null;
  }
  function search(q){
    const w = String(q || "").toLowerCase().trim(); if(!w) return data.prayers;
    return data.prayers.filter(p => (p.title + " " + (p.by || "") + " " + (p.tags || []).join(" ") + " " + p.refs.join(" ") + " " + (p.text || []).join(" ") + " " + cat(p.category).name).toLowerCase().includes(w));
  }

  /* ---------- 🔊 Listen: the prayer read aloud (computer: the cloned voice or the computer's voice; phone: its own) ---------- */
  const LS = {ctl: null, btn: null};
  function sayOne(text, kind, ctl){
    if(A.speak) return A.speak(text, kind, ctl);
    if(!("speechSynthesis" in window)) return Promise.reject(new Error(T("This device has no voice for reading aloud.")));
    const v = A.voice ? A.voice(kind, text) : null;
    return new Promise((res, rej) => { const u = new SpeechSynthesisUtterance(text); u.lang = (v && v.lang) || "en-US"; try{ if(v && v.voice) u.voice = v.voice; }catch(e){}
      u.rate = .92; u.onend = res; u.onerror = e => (ctl.stop || e.error === "interrupted" || e.error === "canceled") ? res() : rej(new Error(T("The voice couldn't read that."))); speechSynthesis.speak(u); });
  }
  function stopListen(){
    const c = LS.ctl; if(c){ c.stop = true; if(c.audio) try{ c.audio.pause(); }catch(e){} }
    if(A && A.speakCancel) A.speakCancel(); try{ speechSynthesis.cancel(); }catch(e){}
    if(LS.btn) LS.btn.textContent = LS.btn.dataset.label || "🔊 Listen";
    LS.ctl = null; LS.btn = null;
  }
  async function listen(parts, btn){
    if(LS.btn === btn && LS.ctl){ stopListen(); return; }
    stopListen(); if(A.onListen) A.onListen();
    const ctl = {stop: false}; LS.ctl = ctl; LS.btn = btn;
    if(btn){ btn.dataset.label = btn.dataset.label || btn.textContent; btn.textContent = "■ " + T("Stop"); }
    try{ for(const [text, kind] of parts){ if(ctl.stop) break; if(String(text).trim()) await sayOne(text, kind, ctl); } }
    catch(e){ toast(e.message); }
    if(LS.ctl === ctl) stopListen();
  }
  async function partsOf(p, verses){
    const out = [[p.title + ".", "app"]];
    if(written(p)) for(const t of p.text) out.push([t, "app"]);
    else for(const v of (verses || await versesFor(p))) out.push([v.vs.map(x => x[3]).join(" "), "reader"]);
    return out;
  }

  /* ---------- verses from the reader's Bible ---------- */
  async function versesFor(p){
    const out = [];
    for(const r of p.refs){ const got = await BCPaths.readVerses(r).catch(() => ({key: null, vs: []})); out.push({ref: r, key: got.key, vs: got.vs}); }
    return out;
  }
  const NAMES = {KJV: "King James Version", ETH: "Ethiopian Canon", BSB: "Berean Standard Bible", JASHER: "Book of Jasher (1840)"};
  function versesHtml(list){
    return list.map(x => { const r = parse(x.ref);
      return `<div class="pr-v"><a href="#" class="pr-go" data-b="${esc(r.book)}" data-c="${r.c1}" data-v="${r.v1 || ""}">${esc(A.bookName(r.book) + " " + label(x.ref.slice(r.book.length + 1)))}</a>${x.key && x.key !== "reader" ? ` <small>(${esc(T("from the") + " " + (NAMES[x.key] || x.key))})</small>` : ""}
        <div class="pvx pr-vt">${x.vs.length ? x.vs.map(v => `<sup>${v[2]}</sup>${esc(v[3])}`).join(" ") : `<i>${esc(T("Not in this Bible"))}</i>`}</div></div>`; }).join("");
  }
  function toast(m){ if(P && P.toast) P.toast(m); else if(A && A.toast) A.toast(m); }

  /* ---------- drawing ---------- */
  function frame(title, body, back){
    root.innerHTML = `<div class="pv-in"><header class="pv-head">${back ? `<button class="pv-ib pr-back" aria-label="Back">‹</button>` : ""}<h2 class="pvx">${esc(title)}</h2><button class="pv-ib pr-close" aria-label="Close">✕</button></header><div class="pv-body">${body}</div></div>`;
    root.hidden = false; root.scrollTop = 0;
    if(P.onOpen) P.onOpen();
  }
  function cardHtml(p){
    const c = cat(p.category), first = written(p) ? p.text[0] : (p.by ? T("Prayed by:") + " " + p.by : "");
    return `<button class="pr-card" data-id="${esc(p.id)}"><span class="pr-ci" aria-hidden="true">${c.icon}</span><span class="pr-cb"><b class="pvx">${esc(p.title)}</b><small class="pvx">${esc(p.refs.map(label).join(" · "))}</small><span class="pr-snip pvx">${esc(first)}</span></span></button>`;
  }
  async function showList(){
    S.view = "list"; S.id = null;
    const d = await load(), t = today(P.votd ? P.votd() : null);
    const chips = [{id: "all", icon: "", name: "All"}].concat(d.categories).map(c => `<button class="pv-chip${S.cat === c.id ? " pv-chip-on" : ""}" data-cat="${esc(c.id)}">${c.icon ? c.icon + " " : ""}${esc(T(c.name))}</button>`).join("");
    const list = (S.q ? search(S.q) : d.prayers).filter(p => S.cat === "all" || p.category === S.cat);
    const groups = d.categories.filter(c => S.cat === "all" || c.id === S.cat).map(c => { const ps = list.filter(p => p.category === c.id); return ps.length ? `<h3 class="pr-grp">${c.icon} ${esc(T(c.name))}</h3><div class="pr-grid">${ps.map(cardHtml).join("")}</div>` : ""; }).join("");
    const arrived = S.arrived; S.arrived = false;
    frame("🙏 " + T("Prayers"), `${arrived ? `<div class="pv-welcome">👋 <b>${esc(T("Someone shared the BibleChat Prayers with you."))}</b> ${esc(T("Tap a prayer to pray it, listen to it, or read the verses it comes from. Free, no sign-up."))}</div>` : ""}<p class="pv-lead">${esc(T("Prayers drawn from the Bible, and the prayers the Bible itself records. Tap one to pray it, listen to it or share it."))}</p>
      <div class="pv-allshare"><button class="pv-btn pr-shareall">↗ ${esc(T("Share the Prayers · link or QR code"))}</button></div>
      ${!S.q && S.cat === "all" ? `<div class="pr-today"><div class="pr-lab">☀ ${esc(T("Today's prayer"))}</div>${cardHtml(t)}</div>` : ""}
      <input type="search" class="pr-find" placeholder="${esc(T("Find a prayer: fear, sleep, children, Psalm 91…"))}" value="${esc(S.q)}" aria-label="${esc(T("Find a prayer"))}">
      <div class="pv-chips">${chips}</div>
      ${groups || `<p class="pv-small">${esc(T("No prayer has these words. Try another word."))}</p>`}
      <p class="pv-small">${esc(T(d.about))}</p>`, false);
  }
  async function showPrayer(id, opts){
    const d = await load(), p = d.byId[id];
    if(!p){ frame("🙏 " + T("Prayers"), `<p class="pv-err">${esc(T("That prayer isn't in this version of BibleChat."))}</p>`, true); S.back = null; return; }
    S.view = "prayer"; S.id = id; if(opts && "back" in opts) S.back = opts.back;
    const arrived = S.arrived; S.arrived = false;
    const c = cat(p.category), more = (opts && opts.more) || d.prayers.filter(x => x.category === p.category && x !== p).slice(0, 6);
    const pathTitle = p.paths && P.pathTitle ? P.pathTitle(p.paths[0]) : "";
    frame(p.title, `<div class="pr-cat">${c.icon} ${esc(T(c.name))}${p.by ? ` · <span class="pvx">${esc(p.by)}</span>` : ""}${pathTitle ? ` · <a href="#" class="pr-path" data-path="${esc(p.paths[0])}">📜 <span class="pvx">${esc(pathTitle)}</span></a>` : ""}</div>
      ${arrived ? `<div class="pv-welcome">👋 <b>${esc(T("Someone shared this prayer with you."))}</b> ${esc(T("Pray it, listen to it, or read the verses it comes from. Free, no sign-up."))}</div>` : ""}
      ${opts && opts.intro ? `<p class="pv-lead">${esc(opts.intro)}</p>` : ""}
      ${written(p) ? `<div class="pr-text pvx">${p.text.map(t => `<p>${esc(t)}</p>`).join("")}</div>` : ""}
      <div class="pr-acts"><button class="pv-btn pr-listen">🔊 ${esc(T("Listen"))}</button><button class="pv-btn pr-share">↗ ${esc(T("Share"))}</button><button class="pv-btn pr-copy">⧉ ${esc(T("Copy"))}</button></div>
      <h3 class="pr-h">${esc(T(written(p) ? "Drawn from these verses" : "The prayer"))}</h3>
      <div class="pr-verses${written(p) ? "" : " pr-big"}" id="prVerses"><p class="pv-small">${esc(T("Loading the verses…"))}</p></div>
      <p class="pr-note">${esc(T(written(p) ? WRITTEN_NOTE : BIBLE_NOTE))}</p>
      ${opts && opts.list && opts.list.length ? `<h3 class="pr-h">${esc(opts.listTitle || T("More prayers"))}</h3><div class="pr-grid">${opts.list.map(cardHtml).join("")}</div>` : ""}
      ${more.length ? `<h3 class="pr-h">${esc(T("More prayers:"))} ${c.icon} ${esc(T(c.name))}</h3><div class="pr-grid">${more.map(cardHtml).join("")}</div>` : ""}
      <p><button class="pv-btn pr-all">🙏 ${esc(T("All prayers"))}</button></p>`, true);
    const my = S.id, vs = await versesFor(p); if(S.id !== my || root.hidden) return;
    const box = root.querySelector("#prVerses"); if(box) box.innerHTML = versesHtml(vs);
    S.verses = vs;
  }
  /* 🙏 in Read: the prayer for this chapter, with the others drawn from it */
  async function openChapter(book, ch){
    await load(); P.ensure && P.ensure();
    const list = forChapter(book, ch), first = list[0], name = A.bookName(book) + " " + ch;
    const fromChapter = first && first._refs.some(r => r.book === book && touchesChapter(r, ch));
    S.back = null;
    await showPrayer(first.id, {intro: fromChapter ? T("A prayer drawn from") + " " + name + "." : T("A prayer for reading") + " " + A.bookName(book) + ".",
      list: list.slice(1, 5), listTitle: T("More prayers for") + " " + name});
  }
  /* 🙏 Pray about this (under a search or chat answer): the closest prayers, and an AI prayer from the answer's verses */
  async function prayAbout(question, passages){
    await load(); P.ensure && P.ensure();
    const ps = (passages || []).filter(x => x && x.ref).slice(0, 8), hits = forAnswer(question, ps.map(x => x.ref), 4);
    S.view = "about"; S.id = null; S.back = null; S.about = {question, passages: ps};
    frame("🙏 " + T("Pray about this"), `<div class="pv-open pvx"><small>${esc(T("You asked"))}</small>${esc(question)}</div>
      ${hits.length ? `<h3 class="pr-h">${esc(T("Prayers that share these verses or words"))}</h3><div class="pr-grid">${hits.map(cardHtml).join("")}</div>` : `<p class="pv-small">${esc(T("No prayer in the library matches this yet."))}</p>`}
      ${ps.length ? `<h3 class="pr-h">✍ ${esc(T("A prayer from these verses"))}</h3>
      <p class="pv-small">${esc(T("An AI can write a prayer from the verses of this answer. It is told to use only these verses and to name each one."))}</p>
      <div class="pr-acts">${P.aiReady && P.aiReady() ? `<button class="pv-btn pv-primary pr-aiwrite">✍ ${esc(T("Write it here (the AI on this computer)"))}</button>` : ""}<button class="pv-btn pr-aiask">✨ ${esc(T("Ask an AI to write one"))}</button></div>
      <div id="prAi" hidden></div>
      <h3 class="pr-h">${esc(T("The verses"))}</h3><div class="pr-verses">${ps.map(x => { const r = parse(x.ref);
        return `<div class="pr-v"><a href="#" class="pr-go" data-b="${esc(r ? r.book : "")}" data-c="${r ? r.c1 : 1}" data-v="${r && r.v1 ? r.v1 : ""}">${esc(r ? A.bookName(r.book) + " " + label(x.ref.slice(r.book.length + 1)) : x.ref)}</a><div class="pvx pr-vt">${esc(x.text || "")}</div></div>`; }).join("")}</div>` : ""}
      <p><button class="pv-btn pr-all">🙏 ${esc(T("All prayers"))}</button></p>`, false);
  }
  function aiPrompt(){
    const a = S.about;
    return `Write a short prayer (about 150 words) about: "${a.question}".\n\nBuild it only on these Bible verses${P.bibleName ? " (" + P.bibleName() + ")" : ""}, and name the reference in brackets after each line that uses one:\n`
      + a.passages.map(x => `${x.ref} ${x.text || ""}`.trim()).join("\n")
      + "\n\nDo not quote any verse that is not in this list, and do not change the words of the ones you quote. Speak to God reverently, in plain words, and end in Jesus' name.";
  }
  async function aiWrite(btn){
    const box = root.querySelector("#prAi"); if(!box || !P.aiWrite) return;
    box.hidden = false; btn.disabled = true;
    box.innerHTML = `<div class="pr-ai"><div class="pr-text pvx" id="prAiText"><p class="pv-small">${esc(T("Writing…"))}</p></div><p class="pr-note">${esc(T(AI_NOTE))}</p><div class="pr-acts"><button class="pv-btn pr-ailisten">🔊 ${esc(T("Listen"))}</button><button class="pv-btn pr-aicopy">⧉ ${esc(T("Copy"))}</button></div></div>`;
    let text = "";
    const paint = () => { const el = root.querySelector("#prAiText"); if(el) el.innerHTML = text.split(/\n{2,}|\n/).filter(x => x.trim()).map(x => `<p>${esc(x)}</p>`).join(""); };
    try{ await P.aiWrite(S.about.question, S.about.passages.map(x => [x.ref, x.text || ""]), piece => { text += piece; paint(); }); }
    catch(e){ const el = root.querySelector("#prAiText"); if(el) el.innerHTML = `<p class="pv-err">${esc(e.message || String(e))}</p>`; }
    btn.disabled = false; S.aiText = text;
  }
  function shareText(p){
    const head = written(p) ? p.text.join("\n\n") : p.title;
    return `${p.title}\n\n${head}\n\n(${p.refs.map(label).join("; ")})`;
  }
  /* ↗ Share a prayer (or the whole Prayers page): one link that opens it in BibleChat on any phone or computer, no sign-up.
     Its own short page (pray/<id>/) shows the prayer's title when the link is posted. Send it by the phone's share sheet, a
     text message, WhatsApp, email or social media, show the QR code, or copy the whole prayer as text. */
  const linkFor = id => BCPaths.linkOf ? BCPaths.linkOf(id ? "#/prayers/" + id : "#/prayers") : A.shareUrl(id ? "#/prayers/" + id : "#/prayers");
  function inviteText(p){
    return p ? `${T("A prayer for you")}: "${p.title}" (${p.refs.map(label).join("; ")}). ${T("Pray it in BibleChat (free, no sign-up):")}`
      : T("Prayers drawn from the Bible, and the prayers the Bible itself records. In BibleChat, free, no sign-up:");
  }
  function share(p, back){
    stopListen();
    const url = linkFor(p && p.id), text = inviteText(p), both = text + "\n" + url, wide = matchMedia("(min-width: 760px)").matches, e = encodeURIComponent;
    S.view = "share"; S.id = p ? p.id : null; S.shareP = p || null; S.shareUrl = url; S.back = back || (p ? () => showPrayer(p.id) : () => showList());
    const qr = `<div class="pv-qrbox"><p class="pv-small">${esc(T(wide ? "Point a phone camera at the screen:" : "Or let them scan this code with their phone camera:"))}</p><div class="pv-qr"></div></div>`;
    frame(p ? "↗ " + T("Share this prayer") : "↗ " + T("Share the Prayers"), `<div class="pv-shead"><span class="pv-shico">🙏</span><div><b class="pvx">${esc(p ? p.title : T("BibleChat Prayers"))}</b><span class="pvx">${esc(p ? p.refs.map(label).join(" · ") : T("Prayers drawn from the Bible, and the prayers the Bible itself records."))}</span></div></div>
      <p class="pv-small">${esc(T(p ? "Send this link to someone. It opens this prayer in BibleChat on their phone or computer, with the verses it comes from. No sign-up, nothing to install." : "Send this link to someone. It opens all the prayers in BibleChat on their phone or computer. No sign-up, nothing to install."))}</p>
      ${wide ? qr : ""}
      <div class="pv-shbtns">${navigator.share ? `<button class="pv-btn pv-primary pr-sys">📤 ${esc(T("Send to someone"))}</button>` : ""}
        <a class="pv-btn" href="sms:?&body=${e(both)}">💬 ${esc(T("Text message"))}</a>
        <a class="pv-btn" href="https://wa.me/?text=${e(both)}" target="_blank" rel="noopener">🟢 WhatsApp</a>
        <a class="pv-btn" href="mailto:?subject=${e((p ? T("A prayer") + ": " + p.title : "BibleChat " + T("Prayers")))}&body=${e(both)}">✉ ${esc(T("Email"))}</a>
        <button class="pv-btn pr-copylink">⧉ ${esc(T("Copy link"))}</button>${p ? `<button class="pv-btn pr-copyall">📋 ${esc(T("Copy the whole prayer"))}</button>` : ""}</div>
      <p class="pv-small pv-socl">${esc(T("Post it on social media:"))}</p>
      <div class="pv-social">
        <a class="pv-btn pv-so-fb" href="https://www.facebook.com/sharer/sharer.php?u=${e(url)}" target="_blank" rel="noopener">Facebook</a>
        <a class="pv-btn pv-so-x" href="https://x.com/intent/post?text=${e(text)}&url=${e(url)}" target="_blank" rel="noopener">X</a>
        <a class="pv-btn pv-so-tg" href="https://t.me/share/url?url=${e(url)}&text=${e(text)}" target="_blank" rel="noopener">Telegram</a>
        <a class="pv-btn pv-so-li" href="https://www.linkedin.com/sharing/share-offsite/?url=${e(url)}" target="_blank" rel="noopener">LinkedIn</a>
      </div>
      <input class="pv-url" readonly value="${esc(url)}">
      ${wide ? "" : qr}`, true);
    const cv = A.qr ? A.qr(url, wide ? 260 : 210) : null, box = root.querySelector(".pv-qr"); if(cv && box) box.appendChild(cv); else if(box) box.parentNode.hidden = true;
  }
  /* from Home (today's prayer) or the end of a Study Path: open the share screen over the page; Back returns there */
  function shareFrom(p, from){
    P.ensure && P.ensure();
    const fromPath = BCPaths.isOpen && BCPaths.isOpen(); if(fromPath){ BCPaths.remember && BCPaths.remember(); BCPaths.close(); }
    share(p, fromPath ? () => { close(); BCPaths.reopen && BCPaths.reopen(); } : () => close());
  }
  async function sysShare(){
    const p = S.shareP;
    try{ await navigator.share({title: p ? p.title : "BibleChat " + T("Prayers"), text: inviteText(p), url: S.shareUrl}); }catch(e){ if(!(e && e.name === "AbortError")) copy(inviteText(p) + "\n" + S.shareUrl); }
  }
  function copy(text){
    const done = () => toast(T("Copied"));
    if(navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(text).then(done, () => fallbackCopy(text, done)); else fallbackCopy(text, done);
  }
  function fallbackCopy(text, done){ const t = document.createElement("textarea"); t.value = text; document.body.appendChild(t); t.select(); try{ document.execCommand("copy"); done(); }catch(e){} t.remove(); }

  function onClick(e){
    const t = e.target;
    if(t.closest(".pr-close")){ close(); return; }
    if(t.closest(".pr-back")){ if(S.back){ const b = S.back; S.back = null; b(); } else showList(); return; }
    const card = t.closest(".pr-card"); if(card){ const from = S.view === "about" ? (q => () => prayAbout(q.question, q.passages))(S.about) : S.view === "prayer" ? (id => () => showPrayer(id))(S.id) : null; stopListen(); showPrayer(card.dataset.id, {back: from}); return; }
    const ch = t.closest(".pv-chip[data-cat]"); if(ch){ S.cat = ch.dataset.cat; showList(); return; }
    if(t.closest(".pr-all")){ stopListen(); S.cat = "all"; S.q = ""; showList(); return; }
    const go = t.closest(".pr-go"); if(go){ e.preventDefault(); stopListen(); close(); (P.openVerse || A.openVerse)(go.dataset.b, +go.dataset.c, go.dataset.v ? +go.dataset.v : null); return; }
    const pa = t.closest(".pr-path"); if(pa){ e.preventDefault(); stopListen(); close(); BCPaths.open(pa.dataset.path); return; }
    const p = S.id && data.byId[S.id];
    if(t.closest(".pr-listen") && p){ const b = t.closest(".pr-listen"); partsOf(p, S.verses).then(parts => listen(parts, b)); return; }
    if(t.closest(".pr-share") && p){ const id = p.id, prev = S.back; share(p, () => showPrayer(id, {back: prev})); return; }
    if(t.closest(".pr-shareall")){ share(null, () => showList()); return; }
    if(t.closest(".pr-sys")){ sysShare(); return; }
    if(t.closest(".pr-copylink") && S.shareUrl){ copy(S.shareUrl); return; }
    if(t.closest(".pr-copyall") && S.shareP){ copy(shareText(S.shareP) + "\n\nBibleChat: " + S.shareUrl); return; }
    if(t.closest(".pv-url")){ t.closest(".pv-url").select(); return; }
    if(t.closest(".pr-copy") && p){ copy(shareText(p)); return; }
    if(t.closest(".pr-aiask")){ if(P.askAI) P.askAI(aiPrompt()); return; }
    if(t.closest(".pr-aiwrite")){ aiWrite(t.closest(".pr-aiwrite")); return; }
    if(t.closest(".pr-ailisten") && S.aiText){ listen([[S.aiText, "app"]], t.closest(".pr-ailisten")); return; }
    if(t.closest(".pr-aicopy") && S.aiText){ copy(S.aiText + "\n\n(" + T("Written by an AI from") + " " + S.about.passages.map(x => x.ref).join("; ") + ")"); return; }
  }
  let findTimer = null;
  function onInput(e){
    if(!e.target.classList.contains("pr-find")) return;
    clearTimeout(findTimer); const v = e.target.value;
    findTimer = setTimeout(() => { S.q = v; showList().then(() => { const f = root.querySelector(".pr-find"); if(f){ f.focus(); f.setSelectionRange(v.length, v.length); } }); }, 250);
  }

  /* ---------- the pieces other screens show ---------- */
  /* ☀ Today's prayer card (phone: Home, under the verse of the day; computer: the chat's start page) */
  let pendingCard = null;
  async function todayCard(el){
    if(!el) return;
    if(!P){ pendingCard = el; return; }   // the page asked before mount(): drawn as soon as it mounts
    try{ await load(); }catch(e){ el.hidden = true; return; }
    const p = today(P.votd ? P.votd() : null); if(!p){ el.hidden = true; return; }
    el.innerHTML = `<div class="lab">🙏 ${esc(T("Today's prayer"))}</div><b class="pr-tt pvx">${esc(p.title)}</b><div class="vt pvx">${esc(written(p) ? p.text[0] : p.by || "")}</div><div class="rf">${esc(p.refs.map(label).join(" · "))}</div>
      <div class="alt row"><button class="btn" data-prt="open">🙏 ${esc(T("Pray it"))}</button><button class="btn" data-prt="listen">🔊 ${esc(T("Listen"))}</button><button class="btn" data-prt="share">↗ ${esc(T("Share"))}</button><button class="btn" data-prt="all">${esc(T("All prayers"))}</button></div>`;
    el.hidden = false;
    el.onclick = e => { const b = e.target.closest("[data-prt]"); if(!b) return;
      if(b.dataset.prt === "open") open(p.id); else if(b.dataset.prt === "all") open(); else if(b.dataset.prt === "share") shareFrom(p);
      else partsOf(p).then(parts => listen(parts, b)); };
  }
  /* 📜 the closing prayer at the end of a Study Path (paths.js calls this under Questions and answers) */
  async function closing(el, path){
    if(!el || !path) return;
    try{ await load(); }catch(e){ return; }
    const p = forPath(path); if(!p || !document.body.contains(el)) return;
    el.innerHTML = `<div class="pr-close-box"><h3>🙏 ${esc(T("A closing prayer"))}</h3><b class="pvx">${esc(p.title)}</b>
      ${written(p) ? `<div class="pr-text pvx">${p.text.map(t => `<p>${esc(t)}</p>`).join("")}</div>` : `<p class="pv-small pvx">${esc(p.by || "")}</p>`}
      <p class="pv-small">${p.refs.map(r => { const q = parse(r); return `<a href="#" class="pv-go" data-b="${esc(q.book)}" data-c="${q.c1}" data-v="${q.v1 || ""}">${esc(A.bookName(q.book) + " " + label(r.slice(q.book.length + 1)))}</a>`; }).join(" · ")}</p>
      <p class="pr-note">${esc(T(written(p) ? WRITTEN_NOTE : BIBLE_NOTE))}</p>
      <div class="pr-acts"><button class="pv-btn pr-cl-listen">🔊 ${esc(T("Listen to the prayer"))}</button><button class="pv-btn pr-cl-open">🙏 ${esc(T("Open in Prayers"))}</button><button class="pv-btn pr-cl-share">↗ ${esc(T("Share the prayer"))}</button></div></div>`;
    el.querySelector(".pr-cl-listen").onclick = ev => { ev.stopPropagation(); partsOf(p).then(parts => listen(parts, ev.target.closest("button"))); };
    el.querySelector(".pr-cl-open").onclick = ev => { ev.stopPropagation(); stopListen(); open(p.id, {back: null}); };
    el.querySelector(".pr-cl-share").onclick = ev => { ev.stopPropagation(); stopListen(); shareFrom(p); };
  }

  /* ---------- open / close ---------- */
  async function open(id, opts){
    P.ensure && P.ensure();
    if(BCPaths.isOpen && BCPaths.isOpen()) BCPaths.close();
    try{ if(id) await showPrayer(id, Object.assign({back: null}, opts || {})); else await showList(); }
    catch(e){ frame("🙏 " + T("Prayers"), `<p class="pv-err">${esc(T("The prayers couldn't load. Check the internet connection and try again."))}</p>`, false); }
  }
  function close(){ stopListen(); if(root){ root.hidden = true; root.innerHTML = ""; } if(P && P.onClose) P.onClose(); }
  /* a shared link "#/prayers/<id>" or "#/prayers" (the tracking Facebook and others add on the end is cut off first);
     an unknown prayer opens the list. The person who opens it is told someone shared it with them. */
  async function openHash(h){
    h = BCPaths.cleanHash ? BCPaths.cleanHash(h) : String(h || "");
    const m = /^#\/prayers?(?:\/([a-z0-9-]+))?/.exec(h); if(!m) return false;
    let id = m[1] || null;
    try{ const d = await load(); if(id && !d.byId[id]) id = null; }catch(e){}
    S.arrived = true; await open(id); return true;
  }
  function mount(opts){
    P = opts; A = BCPaths.adapter(); root = opts.container;
    root.classList.add("pv", "pv-dark", "pr"); root.hidden = true;
    root.addEventListener("click", onClick); root.addEventListener("input", onInput);
    addEventListener("keydown", e => { if(e.key === "Escape" && !root.hidden) close(); });
    if(!document.getElementById("prStyle")){ const st = document.createElement("style"); st.id = "prStyle"; st.textContent = CSS; document.head.appendChild(st); }
    load().catch(() => {});
    if(pendingCard){ const el = pendingCard; pendingCard = null; todayCard(el); }
  }
  const CSS = `
.pr-today{margin:0 0 12px}.pr-lab{font:700 12px system-ui,sans-serif;letter-spacing:.06em;text-transform:uppercase;color:var(--accent);margin:0 0 6px}
.pr-find{display:block;width:100%;margin:0 0 10px;border:1px solid var(--line);border-radius:10px;padding:10px 12px;background:var(--card);color:inherit;font:inherit}
.pr-grp{font-size:16px;margin:16px 0 8px;color:var(--accent)}
.pr-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:8px}
.pr-card{display:flex;gap:10px;align-items:flex-start;width:100%;text-align:left;border:1px solid var(--line);background:var(--card);border-radius:12px;padding:11px 12px;color:inherit;cursor:pointer;font:inherit}
.pr-card:hover{border-color:var(--accent)}
.pr-ci{font-size:22px;line-height:1.2}.pr-cb{display:flex;flex-direction:column;gap:2px;min-width:0}.pr-cb small{color:var(--accent);font-size:12.5px}
.pr-snip{color:var(--muted);font-size:13.5px;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.pr-cat{color:var(--muted);font-size:13.5px;margin:2px 0 10px}
.pr-text{font-family:Georgia,serif;font-size:18px;line-height:1.65;background:linear-gradient(135deg,rgba(217,180,74,.10),rgba(217,180,74,.03));border:1px solid rgba(217,180,74,.35);border-radius:14px;padding:6px 16px;margin:0 0 10px}
.pr-text p{margin:10px 0}
.pr-acts{display:flex;gap:8px;flex-wrap:wrap;margin:8px 0 12px}.pr-acts .pv-btn{flex:0 1 auto}
.pr-h{font-size:15.5px;margin:16px 0 8px}
.pr-v{border-left:3px solid var(--accent);padding:4px 0 4px 10px;margin:0 0 10px}.pr-vt{font-family:Georgia,serif;font-size:16.5px;line-height:1.55;margin-top:3px}
.pr-big .pr-vt{font-size:18.5px;line-height:1.65}.pr-vt sup{color:var(--muted);font-size:.65em;margin-right:2px}
.pr-note{color:var(--muted);font-size:12.5px;font-style:italic;margin:6px 0 10px}
.pr-ai{border:1px dashed var(--line);border-radius:14px;padding:8px 12px;margin:6px 0 10px}
.pr-close-box{margin:22px 0 8px;border-top:1px solid var(--line);padding-top:12px}.pr-close-box h3{margin:0 0 4px;color:var(--accent)}.pr-close-box>b{display:block;margin:0 0 8px}`;
  return {mount, open, close, openChapter, prayAbout, todayCard, closing, openHash, share: shareFrom, isOpen: () => !!root && !root.hidden,
    load, forChapter: (b, c) => data ? forChapter(b, c) : [], forAnswer: (q, r, n) => data ? forAnswer(q, r, n) : [], today: (v, d) => data ? today(v, d) : null,
    forPath: p => forPath(p), _data: () => data, _setData: d => { data = d; d.byId = {}; for(const p of d.prayers){ d.byId[p.id] = p; p._refs = p.refs.map(r => parse(r)).filter(Boolean); } }};
})();
if(typeof module !== "undefined") module.exports = BCPrayers;
