/* BibleChat 📰 In the news: one or two of today's headlines next to the prophecy passages they touch, and a box to
   paste any headline or link. Shown on Home under today's prayer.

   The rules:
   - The themes, their passages, the readings and the news sources live in web/prophecy.json (tests/test_news.py
     checks every verse and every quoted word). The day's picks are news.json, written twice a day by
     packaging/build_news.py when the site is published; the matching here uses the same word rules.
   - Every headline says where it came from and what kind of source it is (Mainstream, Israeli press, Christian,
     Alternative / independent).
   - BibleChat gives no verdict and sets no dates: every match shows the four ways Christians read prophecy and
     "of that day and hour knoweth no man".
   - Nothing is sent anywhere. "Ask AI" only opens the AI the person picks, as everywhere else in BibleChat. */
"use strict";
const BCNews = (() => {
  let H = null, data = null, news = null, loading = null, box = null;
  const esc = s => String(s == null ? "" : s).replace(/[&<>"']/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]));
  const T = x => (typeof tr === "function" ? tr(x) : x);
  const label = r => String(r).replace(/-/g, "–");
  const norm = s => " " + String(s).toLowerCase().replace(/&amp;/g, "&").replace(/[^a-z0-9]+/g, " ").trim() + " ";

  function load(){
    if(data) return Promise.resolve();
    return loading || (loading = Promise.all([
      fetch("prophecy.json").then(r => { if(!r.ok) throw new Error(r.status); return r.json(); }),
      fetch("news.json").then(r => r.ok ? r.json() : null).catch(() => null)
    ]).then(([d, n]) => { data = d; news = n; }).catch(e => { loading = null; throw e; }));
  }

  /* the same rule as packaging/build_news.py: a word or phrase counts when it stands whole in the text */
  function match(text){
    const t = norm(text);
    return data.themes.map(th => ({th, found: th.words.filter(w => t.includes(norm(w)))}))
      .filter(x => x.found.length).sort((a, b) => b.found.length - a.found.length);
  }
  /* a pasted link: the words in its address usually say what the story is (…/israel-iran-strike-…) */
  function words(input){
    const s = String(input).trim();
    if(!/^https?:\/\//i.test(s)) return s;
    try{
      const u = new URL(s);
      return decodeURIComponent(u.pathname + " " + u.search).replace(/[-_/+.=?&]+/g, " ").replace(/\b\d+\b/g, " ");
    }catch(e){ return s; }
  }
  const theme = id => data.themes.find(t => t.id === id);
  const site = link => { try{ return new URL(link).hostname.replace(/^www\./, ""); }catch(e){ return ""; } };

  function refs(th){
    return `<div class="nw-refs">${th.refs.map(r => `<button class="btn nw-ref" data-r="${esc(r)}">📖 ${esc(label(r))}</button>`).join("")}</div>`;
  }
  function readings(th){
    return `<details class="nw-read"><summary>${esc(T("How Christians read it"))}</summary>
      <p>${esc(th.note)}</p>
      <ul>${data.readings.map(x => `<li><b>${esc(T(x.name))}:</b> ${esc(x.text)}</li>`).join("")}</ul>
      <p class="nw-caution">${esc(data.caution_text)}</p></details>`;
  }
  function item(n, th, i){
    const when = n.date ? new Date(n.date).toLocaleDateString(undefined, {month: "short", day: "numeric"}) : "";
    return `<div class="nw-item">
      <div class="nw-src"><span class="nw-lab">${esc(T(n.label))}</span> ${esc(n.source)}${when ? " · " + esc(when) : ""}</div>
      <a class="nw-tt" href="${esc(n.link)}" target="_blank" rel="noopener">${esc(n.title)}</a>
      <div class="nw-th">${esc(T("Touches"))}: <b>${esc(th.title)}</b></div>
      ${refs(th)}${readings(th)}
      <div class="alt"><button class="btn" data-ai="${i}">${esc(T("✨ Ask AI"))}</button></div></div>`;
  }

  let shown = [];
  function render(){
    const picks = (news && news.picks || []).map(n => ({n, th: theme(n.theme)})).filter(x => x.th);
    shown = picks.slice();
    box.innerHTML = `<div class="lab">📰 ${esc(T("In the news"))}</div>
      <p class="nw-about">${esc(T("Today's headlines next to what the prophets wrote. BibleChat gives no verdict and sets no dates."))}</p>
      ${picks.map((x, i) => item(x.n, x.th, i)).join("") || `<p class="nw-none">${esc(T("No headline today touched a prophecy theme."))}</p>`}
      <form class="nw-paste"><input type="text" placeholder="${esc(T("Paste a headline or a link"))}" aria-label="${esc(T("Paste a headline or a link"))}">
        <button class="btn" type="submit">${esc(T("Find the passages"))}</button></form>
      <div class="nw-out"></div>
      <details class="nw-srcs"><summary>${esc(T("Where the news comes from"))}</summary>
        <ul>${data.sources.map(s => `<li>${esc(s.name)}: ${esc(T(s.label))}</li>`).join("")}</ul>
        ${news && news.updated ? `<p>${esc(T("Updated"))} ${esc(new Date(news.updated).toLocaleString())}</p>` : ""}</details>`;
    box.hidden = false;
  }

  function prompt(n, th){
    return `A news headline${n.source ? ` (${n.source}, ${n.label})` : ""}: "${n.title}"\n\n` +
      `BibleChat matched it to the theme "${th.title}" and these passages: ${th.refs.join("; ")}.\n\n` +
      `Please: (1) say what these passages say in their own context; (2) explain fairly how a futurist, a historicist, ` +
      `a preterist and an idealist reader would each see this headline, without taking sides; (3) say plainly where a ` +
      `link between the news and the text is speculation; (4) remember Matthew 24:36 and set no dates; ` +
      `(5) end with how a Christian can respond today: watch, pray, and love our neighbour.`;
  }

  function wire(){
    box.addEventListener("click", e => {
      const r = e.target.closest(".nw-ref");
      if(r){ const p = BCPaths.parseRef(r.dataset.r); if(p) H.openVerse(p.book, p.c1, p.v1 || 1); return; }
      const a = e.target.closest("[data-ai]");
      if(a){ const x = shown[+a.dataset.ai]; if(x) H.askAI(prompt(x.n, x.th)); }
    });
    box.addEventListener("submit", e => {
      e.preventDefault();
      const input = box.querySelector(".nw-paste input").value.trim(), out = box.querySelector(".nw-out");
      if(!input){ out.innerHTML = ""; return; }
      const m = match(words(input));
      shown = shown.filter(x => !x.pasted);
      if(!m.length){
        out.innerHTML = `<p class="nw-none">${esc(T("No prophecy theme found in these words. Try the main words of the headline, or search the Bible for them."))}</p>`;
        return;
      }
      const isLink = /^https?:\/\//i.test(input);
      const n = {title: input, link: isLink ? input : "", source: isLink ? site(input) : "", label: isLink ? "Pasted link" : "Pasted headline", date: null};
      out.innerHTML = m.slice(0, 2).map(({th}) => { shown.push({n, th, pasted: true}); return `<div class="nw-item">
        <div class="nw-th">${esc(T("Touches"))}: <b>${esc(th.title)}</b></div>${refs(th)}${readings(th)}
        <div class="alt"><button class="btn" data-ai="${shown.length - 1}">${esc(T("✨ Ask AI"))}</button></div></div>`; }).join("");
    });
  }

  /* Home: the card under today's prayer. hooks: {openVerse(book, ch, v), askAI(text)} */
  function card(el, hooks){
    H = hooks; const first = box !== el; box = el;
    load().then(() => { render(); if(first) wire(); }).catch(() => { el.hidden = true; });
  }
  return {card, match: t => match(t), _words: words};
})();
