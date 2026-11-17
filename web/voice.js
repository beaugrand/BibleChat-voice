/* BibleChat 🎙 Tap and talk: voice as the front door of the phone version (Phase 1 of the voice handover).

   How it works:
   - Home shows a big "Tap and talk" button. The first tap speaks a short greeting, then the microphone opens.
     (Browsers do not let a page speak or listen before the first tap, so the greeting comes on that tap.)
   - What the person says goes into Search. BibleChat reads the first verses it finds aloud, in the Bible's voice,
     then opens the microphone again for the next question: a hands-free loop.
   - "■ Stop listening" is on screen the whole time. Saying "stop" also ends it.
   - If nothing is heard for 8 seconds, the microphone closes quietly, with no error message.
   - The setting "Start in voice mode" (on at first) puts the big button at the top of Home. Off, Home looks as it did
     before, with a small "Tap and talk" button lower down.

   Privacy: listening uses the browser's own speech recognition. The browser sends the spoken words to Google, Apple
   or Microsoft to turn them into text; the Home screen says so under the button. BibleChat keeps no recording.
   Everything spoken back is Bible text that Search found, never invented words.

   index.html hands this file a small adapter (BCVoice.mount): how to search, which language and voice to use, and
   how to stop the chapter reader. tests/test_voice.py drives this file in Node with a pretend microphone. */
"use strict";
const BCVoice = (() => {
  const SILENCE_MS = 8000;   // the microphone closes after 8 seconds without a word
  const MAX_VERSES = 3, MAX_REF_VERSES = 6;   // a word search reads the best 3; "Psalm 23:1-6" reads up to 6
  const GREETING = "Shalom. What's on your heart today? You can ask about any verse, topic, or start a study path.";
  const STOP_WORDS = /^(stop|stop listening|stop talking|be quiet|quiet|that's all|that is all|goodbye|good bye|bye|amen|halt|stopp|para|parar|basta|arrête|arrete)$/i;
  let A = null, el = {}, state = "off", rec = null, tok = 0, silenceT = null, greeted = false, opts = {silenceMs: SILENCE_MS};
  const W = typeof window !== "undefined" ? window : globalThis;
  const T = x => (typeof tr === "function" ? tr(x) : x);
  const RecClass = () => W.SpeechRecognition || W.webkitSpeechRecognition || null;
  const canListen = () => !!RecClass();
  const canSpeak = () => "speechSynthesis" in W;
  const store = {get: (k, d) => (A && A.store ? A.store.get(k, d) : d), set: (k, v) => { if(A && A.store) A.store.set(k, v); }};

  /* ---------- the setting ---------- */
  function startInVoice(){ return store.get("voiceStart", true) !== false; }   // on until someone turns it off
  function setStartInVoice(on){ store.set("voiceStart", !!on); layout(); }

  /* "stop", "Stop listening.", "Amen!" end the loop */
  function isStop(text){ return STOP_WORDS.test(String(text || "").trim().replace(/[.!?,]+$/g, "").trim()); }

  /* which verses to read aloud: a reference ("John 3:16-18") reads its verses, up to 6; a word search the best 3 */
  function pick(items){
    if(!items || !items.length) return [];
    const sameChapter = items.every(x => x.book === items[0].book && x.ch === items[0].ch);
    return items.slice(0, sameChapter && items.length <= MAX_REF_VERSES ? MAX_REF_VERSES : MAX_VERSES);
  }

  /* ---------- speaking ---------- */
  function speak(text, lang, t){
    return new Promise(res => {
      if(!canSpeak() || t !== tok) return res();
      const u = new W.SpeechSynthesisUtterance(text), v = A && A.voice ? A.voice(lang) : null;
      u.lang = v ? v.lang : lang; try{ if(v) u.voice = v; }catch(e){} u.rate = .95;
      u.onend = () => res(); u.onerror = () => res();   // a voice that fails is skipped, never an error box
      W.speechSynthesis.speak(u);
    });
  }
  async function speakAll(lines, lang, t){
    for(const line of lines){ if(t !== tok) return false; await speak(line, lang, t); }   // one verse at a time: long text cuts off in some browsers
    return t === tok;
  }

  /* ---------- listening ---------- */
  function clearSilence(){ if(silenceT){ clearTimeout(silenceT); silenceT = null; } }
  function armSilence(t){ clearSilence(); silenceT = setTimeout(() => { if(t === tok && state === "listening") stop(true); }, opts.silenceMs); }
  function listen(t){
    if(t !== tok) return;
    const R = RecClass(); if(!R){ stop(true); return; }
    setState("listening", "");
    let heardBy = Date.now() + opts.silenceMs, done = false;   // heardBy: 8 seconds after the last word heard
    const deadline = () => Date.now() >= heardBy;
    const start = () => {
      rec = new R(); rec.lang = A && A.listenLang ? A.listenLang() : "en-US";
      rec.interimResults = true; rec.continuous = false; rec.maxAlternatives = 1;
      rec.onspeechstart = () => { if(t === tok){ heardBy = Date.now() + opts.silenceMs; armSilence(t); } };
      rec.onresult = e => {
        if(t !== tok) return;
        let text = "", fin = false;
        for(let i = 0; i < e.results.length; i++){ text += e.results[i][0].transcript; if(e.results[i].isFinal) fin = true; }
        heardBy = Date.now() + opts.silenceMs; armSilence(t); showHeard(text);
        if(fin && text.trim()){ done = true; try{ rec.abort(); }catch(x){} answer(text.trim(), t); }
      };
      rec.onerror = e => {
        if(t !== tok) return;
        const err = e && e.error;
        if(err === "not-allowed" || err === "service-not-allowed" || err === "audio-capture"){
          done = true; stop(true); note(T("The microphone is blocked. Allow it for this site in the browser's settings, or type instead.")); }
        else if(err === "network" || err === "language-not-supported"){
          done = true; stop(true); note(T("Listening needs the internet. Type instead, or try again later.")); }
        // "no-speech" and "aborted": nothing to say; onend decides whether to keep waiting
      };
      rec.onend = () => {
        if(t !== tok || done || state !== "listening") return;
        if(deadline()) stop(true);                // 8 seconds of silence: close quietly
        else try{ start(); }catch(x){ stop(true); }   // the browser gave up early: keep waiting until the 8 seconds are up
      };
      rec.start();
    };
    try{ start(); armSilence(t); }catch(e){ stop(true); note(T("Tap the microphone to talk.")); }
  }

  /* ---------- one question, one answer ---------- */
  async function answer(text, t){
    if(isStop(text)){ stop(true); return; }
    setState("thinking", text);
    let res = {items: [], paths: []};
    try{ res = (await A.ask(text)) || res; }catch(e){}
    if(t !== tok) return;
    const lang = A.speakLang ? A.speakLang() : "en-US", en = /^en/i.test(lang);
    const items = pick(res.items || []), lines = [];
    if(!items.length && en) lines.push("I found nothing for that in this Bible. Try other words, or a verse like John 3:16.");
    for(const x of items) lines.push(x.ref + ". " + x.text);
    if(en && res.paths && res.paths.length) lines.push("There is a study path about this: " + res.paths[0] + ". It is on the screen.");
    setState("speaking", text);
    if(await speakAll(lines, lang, t)) listen(t);   // the loop: the microphone opens again
  }

  /* ---------- start and stop ---------- */
  function begin(){
    if(!A) return;
    if(!canListen()){ note(T("This browser can't listen. Try Chrome or Safari, or type instead.")); if(A.typeInstead) A.typeInstead(); return; }
    if(A.stopOthers) A.stopOthers();   // the chapter reader stops first
    const t = ++tok;
    if(!greeted && canSpeak()){
      greeted = true; setState("greeting", "");
      const lang = A.uiLang ? A.uiLang() : "en-US";
      speak(T(GREETING), lang, t).then(() => listen(t));   // the first speak() runs inside the tap, as browsers require
    } else listen(t);
  }
  function stop(quiet){
    tok++; clearSilence();
    if(rec){ const r = rec; rec = null; r.onend = r.onresult = r.onerror = r.onspeechstart = null; try{ r.abort(); }catch(e){} }
    if(canSpeak() && state !== "off") try{ W.speechSynthesis.cancel(); }catch(e){}
    setState("off", "");
  }

  /* ---------- the screen ---------- */
  const LABEL = {greeting: "🔊 Shalom…", listening: "🎙 Listening…", thinking: "🔍 Searching…", speaking: "🔊 Reading the verses…"};
  function setState(s, heard){
    state = s;
    if(el.bar){
      el.bar.hidden = s === "off";
      if(typeof document !== "undefined") document.body.classList.toggle("talking", s !== "off");
      if(el.state) el.state.textContent = LABEL[s] ? T(LABEL[s]) : "";
      if(heard !== undefined) showHeard(heard);
    }
    if(el.btn) el.btn.classList.toggle("on", s !== "off");
    if(A && A.onState) A.onState(s);
  }
  function showHeard(text){ if(el.heard) el.heard.textContent = text ? "“" + text + "”" : ""; }
  function note(msg){ if(A && A.toast) A.toast(msg); }
  function layout(){
    if(!el.box) return;
    const on = startInVoice();
    el.box.classList.toggle("compact", !on);
    if(el.setting) el.setting.checked = on;
    if(on && el.top && el.box.previousElementSibling !== el.top) el.top.after(el.box);        // at the top of Home
    if(!on && el.low && el.box.previousElementSibling !== el.low) el.low.after(el.box);      // lower down, as before
  }
  function mount(adapter, elements, o){
    A = adapter; el = elements || {}; if(o) Object.assign(opts, o);
    if(el.btn) el.btn.onclick = () => (state === "off" ? begin() : stop(true));
    if(el.stopBtn) el.stopBtn.onclick = () => stop(true);
    if(el.type) el.type.onclick = e => { if(e && e.preventDefault) e.preventDefault(); stop(true); if(A.typeInstead) A.typeInstead(); };
    if(el.setting) el.setting.onchange = () => setStartInVoice(el.setting.checked);
    if(el.privacy) el.privacy.hidden = !canListen();
    layout();
    if(typeof document !== "undefined" && document.addEventListener)
      document.addEventListener("visibilitychange", () => { if(document.hidden && state !== "off") stop(true); });   // the phone locked or another app opened
  }

  return {mount, begin, stop, startInVoice, setStartInVoice, isStop, pick, canListen, state: () => state, SILENCE_MS, GREETING};
})();
if(typeof module !== "undefined") module.exports = BCVoice;
