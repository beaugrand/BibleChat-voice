/* BibleChat 📘 "Walking with Yeshua": the printed book for a US Letter ring binder (handover of 22 November 2026).
   The 📘 Export the book button (Study Paths list) and 🖨 Print this path (first screen of a path) open it. The page
   lays out the binder pages on screen; the reader prints them or saves them as a PDF with the phone's own Print.

   The rules:
   - Verse text comes from the Yahweh Edition (based on the World Messianic Bible), word for word, as the app has it.
     A book the Yahweh Edition doesn't have (1 Enoch, Jasher, ...) comes from the Bible that has it, and says so.
     "Lord*" with its note where the Yahweh Edition writes "Lord" for the Name (packaging/build_yahweh.py AWKWARD).
   - Nothing is written by an AI. Questions, "For me" lines and prayers are the paths' and prayers' own words, with
     "Yeshua" for "Jesus" outside the verses.
   - No page numbers. Every page has a small corner label ("Forgiveness, step 3 of 9") so a loose page can be re-filed.
   - QR codes are plain links to the phone site. Nothing about the reader is saved or sent.
   - The Love Donations note and the credit to Hans W. Beaugrand and the licenses stay in the book.
   It borrows the Study Paths adapter (BCPaths.adapter()) for the Bible chapters, like web/prayers.js. Phone only. */
"use strict";
const BCBook = (() => {
  const SITE = "https://beaugrand.github.io/BibleChat-voice/";
  const TITLE = "Walking with Yeshua", SUBTITLE = "Study paths, scripture and prayers", AUTHOR = "Hans W. Beaugrand";
  const WELCOME = "I made this book because I wanted to go back to the roots of Scripture. I wanted to use today's technology to look at the original languages, down to the letters themselves, like Paleo Hebrew and Ge'ez. This study holds the 66 books we have all been handed, and it also makes room for the books of the Ethiopian canon, because both are dear to my heart. Walk with me, and let's go back to the source.";
  const CASHAPP = "https://cash.app/$HansBeaugrand", VENMO = "https://venmo.com/u/Hans-Beaugrand";
  const COMMUNITY = "Community", GROUPS = "Bible Study Groups";
  /* where the Bible text comes from, in order; the first is the book's own Bible */
  const SOURCES = [["YAHWEH", "Yahweh Edition"], ["ETH", "Ethiopian Canon"], ["JASHER", "Book of Jasher (1840)"], ["KJV", "King James Version"]];
  /* the places where the Yahweh Edition says "Lord" for the Name (packaging/build_yahweh.py AWKWARD); the app leaves
     footnotes out, so the book puts the asterisk and the note back */
  const AWKWARD = {"Numbers 14:14": /\byou Lord\b/g, "2 Chronicles 30:18": /\bgood Lord\b/g};
  const AWKWARD_NOTE = "* Hebrew יהוה (YHWH), God’s Proper Name, “Yahweh” (Strong’s H3068). Written “Lord” here because “Yahweh” reads awkwardly in this sentence.";

  const esc = s => String(s == null ? "" : s).replace(/[&<>"']/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]));
  /* "Yeshua, not Jesus" in the book's own words (questions, notes, prayers); never in the verses */
  const yeshua = s => String(s == null ? "" : s).replace(/\bJesus\b/g, "Yeshua");
  const REF = /^(.+?) (\d+)(?::(\d+))?(?:-(\d+)(?::(\d+))?)?$/;
  function parseRef(r){
    const m = REF.exec(String(r).trim()); if(!m) return null;
    const [, book, c1, v1, x, y] = m;
    if(v1 === undefined) return {book, c1: +c1, v1: null, c2: x ? +x : +c1, v2: null};
    if(x === undefined) return {book, c1: +c1, v1: +v1, c2: +c1, v2: +v1};
    if(y === undefined) return {book, c1: +c1, v1: +v1, c2: +c1, v2: +x};
    return {book, c1: +c1, v1: +v1, c2: +x, v2: +y};
  }
  const inRef = (p, c, v) => p.v1 === null ? c >= p.c1 && c <= p.c2 : (c > p.c1 || (c === p.c1 && v >= p.v1)) && (c < p.c2 || (c === p.c2 && v <= p.v2));
  const label = r => String(r).replace(/-/g, "–");
  /* the short name in the corner label: "Forgiveness: seventy times seven" → "Forgiveness" */
  const shortName = t => yeshua(String(t || "").split(/:\s/)[0]).trim();
  function corner(name, part){ return name + ", " + part; }
  /* a session of a series says which series: "Revelation & Daniel: the mirror prophecies – Session 1: The four beasts" */
  const fullTitle = p => yeshua(p.series && /^Session \d/.test(p.title) ? p.series.title + " – " + p.title : p.title);
  const cornerName = p => p.series ? shortName(p.series.title) + ", session " + p.series.session : shortName(p.title);

  /* ---------- which paths go into the book ---------- */
  function choose(list, o){
    o = o || {};
    if(o.only) return list.filter(p => p.id === o.only);
    return list.filter(p => p.category === GROUPS ? !!o.daniel : p.category === COMMUNITY ? o.community !== false : true);
  }

  /* ---------- the plan: every page group of the book, as plain data (no screen needed; tests/test_book.py runs it) ----------
     data = {paths: [full path JSON], prayers: prayers.json, verses: {ref: {src, vs: [[book, ch, v, text], ...]}}, qr: text => svg}
     Each group: {label, kind, blocks: [html], lines: bool}. The page code splits a group over as many pages as it needs. */
  function versesHtml(ref, data){
    const got = data.verses[ref];
    const head = `<h4 class="bk-ref">${esc(label(ref))}${got && got.src !== "YAHWEH" ? ` <small>(${esc((SOURCES.find(s => s[0] === got.src) || [, got.src])[1])})</small>` : ""}</h4>`;
    if(!got || !got.vs.length) return [head + `<p class="bk-miss">This passage isn't in the Bibles the book uses.</p>`];
    const out = [head], notes = [];
    for(const [b, c, v, t] of got.vs){
      let text = t; const aw = AWKWARD[b + " " + c + ":" + v];
      if(aw){ text = text.replace(aw, m => m + "*"); notes.push(AWKWARD_NOTE); }
      out.push(`<p class="bk-v"><sup>${c}:${v}</sup> ${esc(text)}</p>`);
    }
    return out.concat(notes.map(n => `<p class="bk-fn">${esc(n)}</p>`));
  }
  function qrBox(data, url, cls){ return `<span class="bk-qr${cls ? " " + cls : ""}">${data.qr(url)}</span>`; }
  const pathUrl = id => SITE + "p/" + encodeURIComponent(id) + "/";
  const prayerUrl = id => SITE + "pray/" + encodeURIComponent(id) + "/";
  function closingPrayer(prayers, id){ return (prayers.prayers || []).find(x => (x.paths || []).includes(id)) || null; }
  function prayerBlocks(pr, data){
    const out = [`<h3 class="bk-ptitle">${esc(yeshua(pr.title))}</h3>`];
    if(pr.by) out.push(`<p class="bk-by">${esc(yeshua(pr.by))}</p>`);
    if(Array.isArray(pr.text) && pr.text.length){
      pr.text.forEach(t => out.push(`<p class="bk-pray">${esc(yeshua(t))}</p>`));
      if((pr.refs || []).length) out.push(`<p class="bk-prefs">${pr.refs.map(r => esc(label(r))).join(" · ")}</p>`);
    }else (pr.refs || []).forEach(r => out.push(...versesHtml(r, data)));   // a prayer of the Bible: its verses are the prayer
    return out;
  }
  function plan(o, data){
    o = o || {};
    const groups = [], paths = data.paths, prayers = data.prayers || {};
    if(!o.only){
      groups.push({kind: "cover", label: "", blocks: [
        `<div class="bk-cover-top"><h1>${esc(TITLE)}</h1><p class="bk-sub">${esc(SUBTITLE)}</p></div>`
        + `<div class="bk-cover-foot"><p class="bk-author">${esc(AUTHOR)}</p>${qrBox(data, SITE, "bk-qr-cover")}</div>`]});
      groups.push({kind: "welcome", label: "Welcome", blocks: [
        `<h2>Welcome</h2>`, `<p class="bk-note">${esc(WELCOME)}</p>`, `<p class="bk-sign">${esc(AUTHOR)}</p>`,
        `<div class="bk-love"><h3>♥ Love Donations</h3><p>BibleChat and this book are free. If they bless you, you can help keep them free.</p>`
        + `<div class="bk-qrs"><figure>${qrBox(data, CASHAPP)}<figcaption>Cash App<br><b>$HansBeaugrand</b></figcaption></figure>`
        + `<figure>${qrBox(data, VENMO)}<figcaption>Venmo<br><b>@Hans-Beaugrand</b></figcaption></figure></div></div>`,
        `<div class="bk-about"><p>The verses are from the Yahweh Edition, based on the World Messianic Bible (public domain): God's Name is written “Yahweh” instead of “LORD”. Where “Yahweh” reads awkwardly, it says “Lord*” with a note. A passage from a book outside the 66 (such as 1 Enoch) comes from the Ethiopian Canon or the Book of Jasher, and says so. No verse in this book is written by an AI: every verse is copied word for word from the Bible file.</p>`
        + `<p>Each QR code opens the same study or prayer in the free BibleChat app, ${esc(SITE.replace(/^https:\/\//, ""))}. The codes are plain links: nothing about you is saved, no account, no tracking.</p>`
        + `<p>Made with BibleChat by ${esc(AUTHOR)}. BibleChat is free and open source under the Apache License 2.0; keep this credit (NOTICE). Every page has a small label in the top corner, so a loose page can be put back in its place.</p></div>`]});
      const toc = [`<h2>Contents</h2>`, `<h3 class="bk-tochead">Study paths</h3>`]
        .concat(paths.map(p => `<div class="bk-toc">${qrBox(data, pathUrl(p.id))}<span>${esc(fullTitle(p))}</span></div>`));
      if(o.prayers !== false){
        toc.push(`<h3 class="bk-tochead">Prayers</h3>`);
        libraryPrayers(prayers, paths).forEach(x => toc.push(`<div class="bk-toc">${qrBox(data, prayerUrl(x.id))}<span>${esc(yeshua(x.title))}</span></div>`));
      }
      groups.push({kind: "toc", label: "Contents", blocks: toc});
    }
    for(const p of paths){
      const name = cornerName(p), n = (p.steps || []).length;
      const byStep = (p.steps || []).map((s, i) => ({n: i + 1, refs: (s.refs || []).filter(r => parseRef(r))})).filter(g => g.refs.length);
      groups.push({kind: "path-title", label: corner(name, "start"), blocks: [
        `<h2 class="bk-ptop">${esc(fullTitle(p))}</h2>`,
        (p.image ? `<img class="bk-pic" src="${esc(data.base + p.image)}" alt="">` : ""),
        `<div class="bk-open">${qrBox(data, pathUrl(p.id))}<p>${esc(yeshua(p.opening_question))}</p></div>`,
        `<h3>Scriptures in this path</h3>`]
        .concat(byStep.map(g => `<p class="bk-scrip"><b>Step ${g.n}</b> ${g.refs.map(r => esc(label(r))).join(" · ")}</p>`))});
      (p.steps || []).forEach((s, i) => {
        const blocks = [`<p class="bk-stepno">Step ${i + 1} of ${n}</p>`];
        if(s.intro) blocks.push(`<p class="bk-intro">${esc(yeshua(s.intro))}</p>`);
        blocks.push(`<p class="bk-q">${esc(yeshua(s.question))}</p>`);
        (s.outside || []).forEach(x => blocks.push(`<p class="bk-out">In the app this step also shows ${esc(x)} beside the Bible, marked “not Scripture”.</p>`));
        (s.refs || []).forEach(r => blocks.push(...versesHtml(r, data)));
        if(s.apply) blocks.push(`<p class="bk-apply"><b>For me:</b> ${esc(yeshua(s.apply))}</p>`);
        groups.push({kind: "step", label: corner(name, `step ${i + 1} of ${n}`), blocks, lines: o.lines !== false});
      });
      const pr = closingPrayer(prayers, p.id);
      if(pr) groups.push({kind: "prayer", label: corner(name, "closing prayer"), blocks: [`<h2>Closing prayer</h2>`].concat(prayerBlocks(pr, data))});
      const rem = [...new Set((p.remember || []).flatMap(x => (x && x.refs) || []))];
      groups.push({kind: "living", label: corner(name, "living it out"), lines: o.lines !== false,
        blocks: [`<h2>Living it out</h2>`, `<p class="bk-lead">Verses to remember from this path:</p>`]
          .concat(rem.flatMap(r => versesHtml(r, data)))});
    }
    if(!o.only && o.prayers !== false){
      const cats = prayers.categories || [], lib = libraryPrayers(prayers, paths);
      for(const c of cats){
        const these = lib.filter(x => x.category === c.id); if(!these.length) continue;
        groups.push({kind: "library", label: corner("Prayers", c.name), blocks: [`<h2>Prayers: ${esc(c.name)}</h2>`]
          .concat(these.flatMap(x => [`<div class="bk-gap"></div>`].concat(prayerBlocks(x, data))))});
      }
    }
    if(o.spine && !o.only) groups.push({kind: "spine", label: "Spine label", blocks: [
      `<h2>Spine label (optional)</h2><p class="bk-lead">Measure the clear spine sleeve of your binder, cut out the strip that fits and slide it in.</p>`
      + `<div class="bk-spines">${["1", "1.5", "2"].map(w => `<div class="bk-spine" style="width:${w}in"><b>${esc(TITLE)}</b><small>${esc(AUTHOR)}</small><i>${w} inch</i></div>`).join("")}</div>`]});
    return groups;
  }
  /* the prayer library at the back: every prayer, except the closing prayers of paths left out of this book */
  function libraryPrayers(prayers, paths){
    const ids = new Set(paths.map(p => p.id));
    return (prayers.prayers || []).filter(x => !(x.paths && x.paths.length) || x.paths.some(id => ids.has(id)));
  }
  /* every reference the book needs the verse text of */
  function refsOf(o, paths, prayers){
    const out = new Set();
    for(const p of paths){
      (p.steps || []).forEach(s => (s.refs || []).forEach(r => out.add(r)));
      (p.remember || []).forEach(x => ((x && x.refs) || []).forEach(r => out.add(r)));
    }
    if(!o.only && o.prayers !== false) libraryPrayers(prayers, paths).forEach(x => { if(!(x.text && x.text.length)) (x.refs || []).forEach(r => out.add(r)); });
    paths.forEach(p => { const pr = closingPrayer(prayers, p.id); if(pr && !(pr.text && pr.text.length)) (pr.refs || []).forEach(r => out.add(r)); });
    return [...out].filter(r => parseRef(r));
  }

  /* ---------- the screen: options, gathering the verses, laying out the pages ---------- */
  let box = null, A = null;
  async function versesOf(key, ref){
    const p = parseRef(ref), out = [];
    for(let c = p.c1; c <= p.c2; c++){
      const vs = await A.chapter(key, p.book, c);
      if(!vs){ if(c === p.c1) return null; break; }
      for(const [v, t] of vs) if(inRef(p, c, v)) out.push([p.book, c, v, t]);
    }
    return out.length ? out : null;
  }
  async function fetchJson(u){ const r = await fetch(u); if(!r.ok) throw new Error(u + ": " + r.status); return r.json(); }
  function qrSvg(text){
    if(typeof qrcode !== "function") return "";
    const q = qrcode(0, "M"); q.addData(text); q.make();
    return q.createSvgTag({cellSize: 2, margin: 0, scalable: true});
  }
  function shell(){
    if(box) return box;
    box = document.createElement("div"); box.id = "bcBook"; box.setAttribute("role", "dialog"); box.setAttribute("aria-label", TITLE);
    document.body.appendChild(box);
    const st = document.createElement("style"); st.textContent = CSS; document.head.appendChild(st);
    box.addEventListener("click", e => {
      const t = e.target;
      if(t.closest(".bk-close")){ close(); return; }
      if(t.closest(".bk-print")){ window.print(); return; }
      if(t.closest(".bk-back")){ options(box.dataset.only || ""); return; }
      if(t.closest(".bk-make")){ make(); return; }
    });
    return box;
  }
  function close(){ if(box){ box.hidden = true; box.innerHTML = ""; } document.documentElement.classList.remove("bk-open-doc"); }
  async function open(only){
    A = (typeof BCPaths !== "undefined" && BCPaths.adapter()) || null;
    if(!A) return;
    shell(); box.hidden = false; document.documentElement.classList.add("bk-open-doc");
    await options(only || "");
  }
  let LIST = null;
  async function options(only){
    box.dataset.only = only;
    box.innerHTML = `<div class="bk-bar"><b>📘 ${esc(TITLE)}</b><button class="bk-btn bk-close">✕ Close</button></div><div class="bk-opts"><p>Loading…</p></div>`;
    try{ LIST = LIST || await fetchJson(A.base + "index.json"); }catch(e){ box.querySelector(".bk-opts").innerHTML = `<p>The study paths didn't load. Check the internet connection and try again.</p>`; return; }
    const nComm = LIST.filter(p => p.category === COMMUNITY).length;
    box.querySelector(".bk-opts").innerHTML = `
      <h2>${esc(TITLE)}</h2><p class="bk-lead">${esc(SUBTITLE)}. The book for a US Letter ring binder: print it at home or have a print shop print and punch it. The verses are from the Yahweh Edition.</p>
      <label class="bk-o"><span>What to print</span><select id="bkOnly"><option value="">The whole book</option>${LIST.map(p => `<option value="${esc(p.id)}"${p.id === only ? " selected" : ""}>Only: ${esc(fullTitle(p))}</option>`).join("")}</select></label>
      <p class="bk-small">“Only” prints one study path by itself, to add new pages to your binder.</p>
      <label class="bk-c"><input type="checkbox" id="bkComm" checked> Community study paths (${nComm || "none yet"})</label>
      <label class="bk-c"><input type="checkbox" id="bkDan"> The Friday night Bible study (Daniel 2 to 5)</label>
      <label class="bk-c"><input type="checkbox" id="bkLines" checked> Lines to write notes on</label>
      <label class="bk-c"><input type="checkbox" id="bkPray" checked> The prayer library at the back</label>
      <label class="bk-c"><input type="checkbox" id="bkSpine"> A spine label to cut out</label>
      <button class="bk-btn bk-main bk-make">📘 Make the book</button>
      <p class="bk-small">Then press 🖨 Print or save as PDF. Choose US Letter, one-sided, 100% size (not “fit to page”), and switch off headers and footers. The whole book has several hundred pages and takes a moment to make.</p>`;
  }
  async function make(){
    const v = id => box.querySelector(id), o = {only: v("#bkOnly").value, community: v("#bkComm").checked, daniel: v("#bkDan").checked,
      lines: v("#bkLines").checked, prayers: v("#bkPray").checked, spine: v("#bkSpine").checked};
    box.dataset.only = o.only;
    const say = m => { box.querySelector(".bk-opts").innerHTML = `<p class="bk-wait">${esc(m)}</p>`; };
    say("Loading the Yahweh Edition…");
    const ok = await A.chapter("YAHWEH", "John", 1).catch(() => null);
    if(!ok){ say("The Yahweh Edition didn't load. Check the internet connection and try again."); return; }
    const chosen = choose(LIST, o), paths = [];
    try{
      for(let i = 0; i < chosen.length; i++){ say(`Loading the study paths… ${i + 1} of ${chosen.length}`); paths.push(Object.assign({}, chosen[i], await fetchJson(A.base + chosen[i].id + ".json"))); }   // the list entry adds the series
    }catch(e){ say("A study path didn't load. Check the internet connection and try again."); return; }
    let prayers = {};
    try{ prayers = await fetchJson("prayers.json"); }catch(e){ say("The prayers didn't load. Check the internet connection and try again."); return; }
    const refs = refsOf(o, paths, prayers), verses = {};
    for(let i = 0; i < refs.length; i++){
      if(i % 20 === 0) say(`Gathering the verses… ${i} of ${refs.length}`);
      for(const [key] of SOURCES){ const vs = await versesOf(key, refs[i]).catch(() => null); if(vs){ verses[refs[i]] = {src: key, vs}; break; } }
    }
    say("Laying out the pages…");
    const groups = plan(o, {paths, prayers, verses, qr: qrSvg, base: A.base});
    box.innerHTML = `<div class="bk-bar"><button class="bk-btn bk-back">‹ Options</button><button class="bk-btn bk-main bk-print">🖨 Print or save as PDF</button><button class="bk-btn bk-close">✕</button></div>`
      + `<p class="bk-hint">US Letter, one-sided, 100% size, headers and footers off.</p><div class="bk-pages"></div>`;
    const host = box.querySelector(".bk-pages");
    host.style.setProperty("--z", String(Math.min(1, (window.innerWidth - 24) / 816)));
    layout(groups, host);
    box.querySelector(".bk-hint").textContent = `${host.children.length} pages. US Letter, one-sided, 100% size, headers and footers off.`;
  }
  /* split each group over pages: blocks go in one by one; a block that doesn't fit starts a new page with the same label */
  function layout(groups, host){
    const page = (g, more) => {
      const pg = document.createElement("section"); pg.className = "bk-page bk-k-" + g.kind;
      if(g.kind === "cover"){ const im = document.createElement("img"); im.className = "bk-coverimg"; im.src = "book-cover.jpg"; im.alt = ""; pg.appendChild(im); }
      if(g.label){ const c = document.createElement("div"); c.className = "bk-corner"; c.textContent = g.label + (more ? " (continued)" : ""); pg.appendChild(c); }
      const body = document.createElement("div"); body.className = "bk-body"; pg.appendChild(body);
      host.appendChild(pg); return body;
    };
    const over = b => b.scrollHeight > b.clientHeight + 1;
    for(const g of groups){
      let body = page(g, false);
      for(const html of g.blocks){
        if(!html) continue;
        const t = document.createElement("template"); t.innerHTML = html.trim();
        const els = [...t.content.childNodes];
        els.forEach(el => body.appendChild(el));
        if(over(body) && body.childNodes.length > els.length){ els.forEach(el => el.remove()); body = page(g, true); els.forEach(el => body.appendChild(el)); }
      }
      if(g.lines){
        const lineH = 0.34 * 96, room = () => { const l = body.lastElementChild; return body.clientHeight - (l ? l.offsetTop + l.offsetHeight : 0); };   // scrollHeight is never below the box's own height
        if(room() < lineH * 4){ body = page(g, true); }
        const w = document.createElement("div"); w.className = "bk-lines"; body.appendChild(w);
        const n = Math.max(0, Math.floor((body.clientHeight - w.offsetTop - 8) / lineH));   // the page body is the lines' offsetParent
        w.innerHTML = `<p class="bk-notes">Notes</p>` + "<i></i>".repeat(Math.max(0, n - 1));
        while(over(body) && w.lastChild && w.lastChild.tagName === "I") w.lastChild.remove();
      }
    }
  }

  const CSS = `
#bcBook{position:fixed;inset:0;z-index:9999;overflow:auto;background:#e9e6df;color:#222;-webkit-overflow-scrolling:touch}
html.bk-open-doc,html.bk-open-doc body{overflow:hidden}
.bk-bar{position:sticky;top:0;z-index:2;display:flex;gap:8px;align-items:center;padding:8px 12px;background:#2d2a26;color:#fff}
.bk-bar b{flex:1}
.bk-btn{font:inherit;padding:8px 12px;border-radius:8px;border:1px solid #888;background:#fff;color:#222;cursor:pointer}
.bk-main{background:#7a4b16;color:#fff;border-color:#7a4b16;font-weight:600}
.bk-bar .bk-main{flex:1}
.bk-opts{max-width:560px;margin:0 auto;padding:16px}
.bk-opts h2{margin:.2em 0}
.bk-o{display:block;margin:14px 0 4px}.bk-o span{display:block;font-weight:600;margin-bottom:4px}.bk-o select{width:100%;font:inherit;padding:8px}
.bk-c{display:block;margin:10px 0}
.bk-small{font-size:.88em;color:#555}
.bk-opts .bk-make{width:100%;margin:14px 0 6px;padding:12px}
.bk-wait{font-size:1.1em;padding:30px 0;text-align:center}
.bk-hint{text-align:center;font-size:.9em;margin:8px}
.bk-pages{zoom:var(--z,1);padding:8px 0 40px}
.bk-page{position:relative;width:8.5in;height:11in;margin:0 auto 16px;background:#fff;box-shadow:0 1px 6px rgba(0,0,0,.25);overflow:hidden;
  font-family:Georgia,"Times New Roman",serif;font-size:11.5pt;line-height:1.45;color:#111;break-after:page;page-break-after:always}
.bk-body{position:absolute;top:.75in;bottom:.6in;left:1.15in;right:.65in;overflow:hidden}
.bk-corner{position:absolute;top:.32in;right:.65in;font:8.5pt/1 Helvetica,Arial,sans-serif;color:#666;letter-spacing:.02em}
.bk-page h2{font-size:20pt;margin:0 0 .15in;font-weight:normal;color:#5a3610}
.bk-page h3{font-size:13pt;margin:.18in 0 .06in;color:#5a3610}
.bk-qr{display:inline-block;width:.85in;height:.85in;background:#fff}.bk-qr svg{width:100%;height:100%;display:block}
.bk-k-cover .bk-body{top:0;bottom:0;left:0;right:0}
.bk-coverimg{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}
.bk-cover-top{position:absolute;top:0;left:0;right:0;padding:.7in .8in 1.2in;text-align:center;background:linear-gradient(rgba(255,250,240,.82),rgba(255,250,240,0))}
.bk-k-cover h1{font-size:40pt;font-weight:normal;margin:0;color:#3d2508;letter-spacing:.01em}
.bk-sub{font-size:15pt;margin:.08in 0 0;color:#3d2508;font-style:italic}
.bk-cover-foot{position:absolute;left:0;right:0;bottom:0;display:flex;align-items:flex-end;justify-content:space-between;padding:.6in .8in .6in 1.15in;background:linear-gradient(rgba(0,0,0,0),rgba(0,0,0,.45))}
.bk-author{margin:0;font-size:18pt;color:#fff;text-shadow:0 1px 4px rgba(0,0,0,.6)}
.bk-qr-cover{width:.95in;height:.95in;padding:.06in;border-radius:4px}
.bk-note{font-size:13pt;line-height:1.6;font-style:italic}
.bk-sign{text-align:right;font-size:13pt;margin-top:0}
.bk-love{border:1px solid #d8c7ad;border-radius:8px;padding:.12in .2in;margin:.2in 0}
.bk-love h3{margin-top:0}
.bk-qrs{display:flex;gap:.6in}.bk-qrs figure{margin:0;text-align:center;font-size:10pt}
.bk-about{font-size:9.5pt;color:#444;margin-top:.2in}.bk-about p{margin:.05in 0}
.bk-tochead{width:100%}
.bk-toc{display:inline-flex;align-items:center;gap:.1in;width:49%;margin:0 0 .08in;vertical-align:top;font-size:10.5pt;line-height:1.25}
.bk-toc .bk-qr{flex:none;width:.6in;height:.6in}
.bk-ptop{font-size:22pt!important}
.bk-pic{width:100%;height:3.2in;object-fit:cover;border-radius:6px;display:block}
.bk-open{display:flex;gap:.15in;align-items:flex-start;margin:.15in 0}.bk-open .bk-qr{flex:none}.bk-open p{margin:0;font-style:italic}
.bk-scrip{margin:.03in 0;font-size:10.5pt}
.bk-stepno{font:600 10pt Helvetica,Arial,sans-serif;color:#7a4b16;text-transform:uppercase;letter-spacing:.08em;margin:0 0 .05in}
.bk-intro{font-style:italic;margin:.04in 0}
.bk-q{font-weight:bold;font-size:12.5pt;margin:.06in 0 .12in}
.bk-ref{font:600 10.5pt Helvetica,Arial,sans-serif;margin:.12in 0 .03in;color:#333}.bk-ref small{font-weight:normal;color:#777}
.bk-v{margin:0 0 .03in}.bk-v sup{font:7.5pt Helvetica,Arial,sans-serif;color:#7a4b16}
.bk-fn{font-size:8.5pt;color:#555;margin:.03in 0}
.bk-miss,.bk-out{font-size:9.5pt;color:#666;font-style:italic}
.bk-apply{margin:.14in 0 .05in;padding:.06in .12in;border-left:3px solid #c9a46a;background:#faf6ef}
.bk-lead{color:#444}
.bk-ptitle{margin-top:.08in!important}.bk-by{font-style:italic;color:#555;margin:0 0 .05in}
.bk-pray{margin:0 0 .07in}.bk-prefs{font-size:9.5pt;color:#666}
.bk-gap{height:.05in}
.bk-lines{margin-top:.12in}.bk-lines i{display:block;height:.34in;border-bottom:1px solid #bbb}
.bk-notes{font:600 9pt Helvetica,Arial,sans-serif;color:#888;margin:0;height:.34in;border-bottom:1px solid #bbb;box-sizing:border-box;padding-top:.1in}
.bk-spines{display:flex;gap:.3in;align-items:flex-start}
.bk-spine{height:7.6in;border:1px dashed #999;display:flex;flex-direction:column;align-items:center;justify-content:center;writing-mode:vertical-rl;gap:.15in;box-sizing:border-box}
.bk-spine b{font-size:18pt;font-weight:normal}.bk-spine small{font-size:11pt}.bk-spine i{font:8pt Helvetica,Arial,sans-serif;color:#999}
@page{size:letter;margin:0}
@media print{
  html.bk-open-doc body>*:not(#bcBook){display:none!important}
  html.bk-open-doc,html.bk-open-doc body{overflow:visible!important;background:#fff!important;height:auto!important}
  #bcBook{position:static!important;overflow:visible!important;background:#fff!important}
  #bcBook .bk-bar,#bcBook .bk-hint{display:none!important}
  .bk-pages{zoom:1!important;padding:0!important}
  .bk-page{margin:0!important;box-shadow:none!important;-webkit-print-color-adjust:exact;print-color-adjust:exact}
  .bk-page:last-child{break-after:auto;page-break-after:auto}
}`;
  return {open, close, _plan: plan, _choose: choose, _refs: refsOf, _yeshua: yeshua, _short: shortName, _library: libraryPrayers};
})();
if(typeof module !== "undefined") module.exports = BCBook;
