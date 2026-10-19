/* BibleChat search for the phone: the same three ways of finding verses as the computer app, in plain JavaScript.
     matched word        word ranking (BM25), as bibleask/search.py
     Hebrew/Greek word   the question's words are what a Hebrew or Greek word means (bibleask/strongs.py, blend.py)
     matched by meaning  the BGE-small-en v1.5 sentence model (MIT license) with 8-bit weights, as bibleask/meaning.py
   Nothing leaves the phone: the model and the verse fingerprints are files of this site, loaded the first time a
   meaning search runs and kept for offline use. tests/test_smart_js.py checks that this file gives the same
   answers as the Python code. */
"use strict";

/* ---------- words (bibleask/search.py: _STOP, _stem, tokenize) ---------- */
const STOP = new Set(("a about above after again all also am an and any are as at be because been before being below between both but by " +
"can could did do does doing down during each few for from further had has have having he her here hers herself him himself " +
"his how i if in into is it its itself just me more most my myself no nor not now of off on once only or other our ours " +
"ourselves out over own same she should so some such than that the their theirs them themselves then there these they this " +
"those through to too under until up very was we were what when where which while who whom why will with would you your " +
"yours yourself yourselves say says said saying tell tells told mention mentions mentioned written write bible verse verses passage passages " +
"scripture scriptures where whats what's find show give please want know person people someone anyone anything thing things " +
"about regarding concerning talk talks talking discuss discusses refer refers").split(/\s+/));
const IRREGULAR = {fallen: "fall", fell: "fall"};
function stem(w){
  w = IRREGULAR[w] || w;
  if(w.length <= 3) return w;
  if(w.endsWith("ies") && w.length > 4) w = w.slice(0, -3) + "y";
  else if(w.endsWith("ing") && w.length > 5) w = w.slice(0, -3);
  else if(w.endsWith("eth") && w.length > 5) w = w.slice(0, -3);   // King James: "loveth", "falleth"
  else if(w.endsWith("ed") && w.length > 4) w = w.slice(0, -2);
  else if(w.endsWith("es") && w.length > 4) w = w.slice(0, -1);
  else if(w.endsWith("s") && !w.endsWith("ss") && w.length > 3) w = w.slice(0, -1);
  if(w.endsWith("e") && w.length > 3) w = w.slice(0, -1);
  if(w.length > 3 && w[w.length - 1] === w[w.length - 2] && !"lsz".includes(w[w.length - 1])) w = w.slice(0, -1);
  return w;
}
const WORD = /[\p{L}\p{N}]+(?:['’]\p{L}+)?/gu;
function tokenize(text, keepStop){
  const out = [];
  for(let w of (text.toLowerCase().replace(/’/g, "'").match(WORD) || [])){
    w = (w.endsWith("'s") || w.endsWith("s'")) ? w.split("'")[0] : w.replace(/'/g, "");
    if(!keepStop && STOP.has(w)) continue;
    out.push(/^[a-z0-9]+$/.test(w) ? stem(w) : w);
  }
  return out;
}

const Smart = (() => {
  /* ---------- word search (bibleask/search.py: Index.search) ---------- */
  function makeIndex(flat){   // flat: [{b: book, c: chapter, v: verse, t: text}, ...] in Bible order
    const post = new Map(), dlen = [], toks = [], byRef = new Map(), vocab = new Set();
    flat.forEach((x, i) => {
      const ts = tokenize(x.t); toks.push(ts); dlen.push(Math.max(ts.length, 1));
      const tf = new Map(); for(const w of ts) tf.set(w, (tf.get(w) || 0) + 1);
      for(const [w, n] of tf){ let p = post.get(w); if(!p) post.set(w, p = []); p.push([i, n]); }
      const k = x.b + "|" + x.c + "|" + x.v; if(!byRef.has(k)) byRef.set(k, i);
      for(const w of (x.t.toLowerCase().match(/\p{L}+/gu) || [])) vocab.add(w);
    });
    return {post, dlen, toks, byRef, vocab, avg: dlen.reduce((a, b) => a + b, 0) / Math.max(flat.length, 1), n: flat.length};
  }
  function wordSearch(ix, flat, q, k){
    const idf = w => { const df = (ix.post.get(w) || []).length; return Math.log(1 + (ix.n - df + .5) / (df + .5)); };
    let qs = tokenize(q); if(!qs.length) qs = tokenize(q, true); if(!qs.length) return [];
    if(qs.includes("lord") && !qs.includes("yahweh")) qs.push("yahweh");   // modern Bibles print "Yahweh" for "the LORD"
    const k1 = 1.4, b = .75, scores = new Map();
    for(const w of new Set(qs)){
      const p = ix.post.get(w); if(!p) continue; const f = idf(w);
      for(const [i, tf] of p){ const d = tf + k1 * (1 - b + b * ix.dlen[i] / ix.avg); scores.set(i, (scores.get(i) || 0) + f * tf * (k1 + 1) / d); }
    }
    const top = [...scores].sort((a, b) => b[1] - a[1]).slice(0, 400);
    const bigr = new Set(); for(let j = 0; j < qs.length - 1; j++) bigr.add(qs[j] + " " + qs[j + 1]);
    const qset = new Set(qs), out = [];
    for(const [i, sc] of top){
      const ts = ix.toks[i]; let bonus = 0;
      if(bigr.size){ const have = new Set(); for(let j = 0; j < ts.length - 1; j++) have.add(ts[j] + " " + ts[j + 1]); for(const g of bigr) if(have.has(g)) bonus += 1.5; }
      const own = new Set(ts.filter(w => qset.has(w))), cov = own.size / qset.size;
      const near = new Set(), v = flat[i];   // a story spans several verses: credit the asked-for words around this one
      for(let j = Math.max(0, i - 3); j < Math.min(flat.length, i + 4); j++){
        if(j !== i && flat[j].b === v.b && flat[j].c === v.c) for(const w of ix.toks[j]) if(qset.has(w)) near.add(w);
      }
      for(const w of near) if(!own.has(w)) bonus += .6 * idf(w);
      out.push([i, sc * (.6 + .8 * cov) + bonus]);
    }
    out.sort((a, b) => b[1] - a[1]);
    const seen = new Set(), res = [];
    for(const [i] of out){ const key = flat[i].t.toLowerCase().replace(/[^\p{L}\p{N}]/gu, "").slice(0, 160); if(seen.has(key)) continue; seen.add(key); res.push(i); if(res.length >= k) break; }
    return res;
  }

  /* ---------- loading files of this site (the phone keeps them; tests hand in their own loader) ---------- */
  let load = async (path, kind) => {
    let err;
    for(let t = 0; t < 3; t++){   // a weak connection: try three times
      try{ const r = await fetch("data/" + path); if(!r.ok) throw new Error(r.status); return kind === "bin" ? r.arrayBuffer() : kind === "text" ? r.text() : r.json(); }
      catch(e){ err = e; await new Promise(ok => setTimeout(ok, 800 * (t + 1))); }
    }
    throw err;
  };

  /* ---------- Hebrew/Greek words (bibleask/strongs.py: gloss_terms, meaning_matches, gloss_label) ---------- */
  let gloss = null, books = null; const whereFiles = {};
  async function loadGloss(){
    if(!gloss){ [gloss, books] = await Promise.all([load("study/gloss.json"), load("study/books.json")]); gloss.common = new Set(gloss.common); }
    return gloss;
  }
  function content(text){   // runs of neighbouring content words; a little word such as "of" breaks a run
    const runs = []; let cur = [];
    for(const w of (text.toLowerCase().match(/[a-z]+/g) || [])){
      if(STOP.has(w) || w.length < 3){ if(cur.length){ runs.push(cur); cur = []; } continue; }
      cur.push(stem(w));
    }
    if(cur.length) runs.push(cur);
    return runs;
  }
  function glossTerms(q){
    const runs = content(q), found = [], used = new Set();
    runs.forEach((r, ri) => { for(let i = 0; i + 1 < r.length; i++) if(gloss.terms[r[i] + " " + r[i + 1]]){ found.push(r[i] + " " + r[i + 1]); used.add(ri + ":" + i); used.add(ri + ":" + (i + 1)); } });
    runs.forEach((r, ri) => r.forEach((w, i) => { if(!used.has(ri + ":" + i) && gloss.terms[w] && !gloss.common.has(w)) found.push(w); }));
    return found;
  }
  function label(n, name, words, term){
    const hit = words.filter(w => content(w).flat().join(" ") === term).slice(0, 1);
    const shown = hit.concat(words.filter(w => !hit.includes(w)));
    return (n[0] === "H" ? "Hebrew" : "Greek") + " word " + name + " (" + n + "): " + shown.slice(0, 4).join(", ");
  }
  async function where(n){
    const f = n[0] + Math.floor(+n.slice(1) / 100);
    if(!whereFiles[f]) whereFiles[f] = load("study/where/" + f + ".json").catch(e => { delete whereFiles[f]; throw e; });
    return ((await whereFiles[f])[n] || []).map(([b, c, v]) => [books[b], c, v]);
  }
  async function meaningMatches(q){
    await loadGloss();
    const out = [];
    for(const term of glossTerms(q)) for(const [n, quality] of gloss.terms[term]){
      const [df, name, words] = gloss.info[n];
      out.push({number: n, term, quality, idf: Math.log(1 + gloss.verses / df), label: label(n, name, words, term), verses: await where(n)});
    }
    return out.sort((a, b) => b.quality * b.idf - a.quality * a.idf);
  }

  /* ---------- the meaning model (bibleask/meaning.py) ---------- */
  let M = null, mPromise = null;
  const isPunct = (ch, cp) => (cp >= 33 && cp <= 47) || (cp >= 58 && cp <= 64) || (cp >= 91 && cp <= 96) || (cp >= 123 && cp <= 126) || /\p{P}/u.test(ch);
  const isCjk = cp => (cp >= 0x4E00 && cp <= 0x9FFF) || (cp >= 0x3400 && cp <= 0x4DBF) || (cp >= 0x20000 && cp <= 0x2A6DF) || (cp >= 0x2A700 && cp <= 0x2B81F) || (cp >= 0xF900 && cp <= 0xFAFF) || (cp >= 0x2F800 && cp <= 0x2FA1F);
  function basicWords(text){
    const out = []; let cur = "";
    for(const ch of text.toLowerCase().normalize("NFD")){
      const cp = ch.codePointAt(0);
      if(cp === 0 || cp === 0xFFFD || /\p{Mn}/u.test(ch)) continue;
      if(/[\p{Cc}\p{Cf}]/u.test(ch) && !"\t\n\r".includes(ch)) continue;
      if(/\s/.test(ch)){ if(cur){ out.push(cur); cur = ""; } }
      else if(isPunct(ch, cp) || isCjk(cp)){ if(cur){ out.push(cur); cur = ""; } out.push(ch); }
      else cur += ch;
    }
    if(cur) out.push(cur);
    return out;
  }
  function encode(text, maxLen){
    const ids = M.ids, out = [ids.get("[CLS]")], unk = ids.get("[UNK]");
    for(const w of basicWords(text)){
      const cps = [...w];
      if(cps.length > 100){ out.push(unk); continue; }
      let pieces = [], start = 0;
      while(start < cps.length){
        let end = cps.length, hit = null;
        while(start < end){ const sub = (start ? "##" : "") + cps.slice(start, end).join(""); if(ids.has(sub)){ hit = ids.get(sub); break; } end--; }
        if(hit === null){ pieces = [unk]; break; }
        pieces.push(hit); start = end;
      }
      out.push(...pieces);
    }
    return out.slice(0, maxLen - 1).concat([ids.get("[SEP]")]);
  }
  async function loadMeaning(progress){
    const [head, vj, vocab] = await Promise.all([load("meaning/model.json"), load("meaning/verses.json"), load("meaning/vocab.txt", "text")]);
    const files = head.parts.map((size, i) => ["meaning/model." + i + ".bin", size]).concat(vj.parts.map((cnt, i) => ["meaning/verses." + i + ".bin", cnt * (vj.dim + 4)]));
    const total = files.reduce((a, f) => a + f[1], 0) + vocab.length; let done = vocab.length;
    if(progress) progress(done, total);
    const bufs = [];
    for(const [path, size] of files){ bufs.push(await load(path, "bin")); done += size; if(progress) progress(done, total); }   // one by one: easy on a phone
    const blob = new Uint8Array(head.parts.reduce((a, b) => a + b, 0)); let off = 0;
    head.parts.forEach((_, i) => { blob.set(new Uint8Array(bufs[i]), off); off += bufs[i].byteLength; });
    const w = {};
    for(const [name, [kind, shape, o, so]] of Object.entries(head.tensors)){
      const n = shape.reduce((a, b) => a * b, 1);
      w[name] = kind === "i8" ? {q: new Int8Array(blob.buffer, o, n), s: new Float32Array(blob.buffer, so, shape[0]), rows: shape[0], cols: shape[1]} : new Float32Array(blob.buffer, o, n);
    }
    const parts = vj.parts.map((cnt, i) => { const b = bufs[head.parts.length + i]; return {cnt, m: new Int8Array(b, 0, cnt * vj.dim), s: new Float32Array(b, cnt * vj.dim, cnt)}; });
    const ids = new Map(); vocab.split("\n").forEach((t, i) => { if(!ids.has(t)) ids.set(t, i); });
    M = {ids, w, cfg: head.config, prefix: head.query_prefix, refs: vj.refs, books: vj.books, dim: vj.dim, parts, bytes: total};
    return M;
  }
  function meaningSize(){ return Promise.all([load("meaning/model.json"), load("meaning/verses.json")]).then(([h, v]) => h.parts.reduce((a, b) => a + b, 0) + v.parts.reduce((a, c) => a + c * (v.dim + 4), 0) + 240000); }
  function lin(x, n, name){
    const W = M.w[name + ".weight"], bias = M.w[name + ".bias"], O = W.rows, I = W.cols, y = new Float32Array(n * O);
    for(let o = 0; o < O; o++){
      const row = o * I, sc = W.s[o], bo = bias[o];
      for(let t = 0; t < n; t++){ let s = 0; const xt = t * I; for(let i = 0; i < I; i++) s += x[xt + i] * W.q[row + i]; y[t * O + o] = s * sc + bo; }
    }
    return y;
  }
  function norm(x, n, d, name){
    const g = M.w[name + ".weight"], b = M.w[name + ".bias"];
    for(let t = 0; t < n; t++){
      let m = 0; for(let i = 0; i < d; i++) m += x[t * d + i]; m /= d;
      let v = 0; for(let i = 0; i < d; i++){ const z = x[t * d + i] - m; v += z * z; } v /= d;
      const r = 1 / Math.sqrt(v + 1e-12);
      for(let i = 0; i < d; i++) x[t * d + i] = (x[t * d + i] - m) * r * g[i] + b[i];
    }
    return x;
  }
  function erf(x){   // Abramowitz & Stegun 7.1.26, the same formula as the computer
    const s = Math.sign(x), a = Math.abs(x), t = 1 / (1 + 0.3275911 * a);
    return s * (1 - (((((1.061405429 * t - 1.453152027) * t) + 1.421413741) * t - 0.284496736) * t + 0.254829592) * t * Math.exp(-a * a));
  }
  function embed(text){
    const ids = encode(M.prefix + text, 512), n = ids.length, d = M.cfg.hidden_size, H = M.cfg.num_attention_heads, hd = d / H;
    const we = M.w["embeddings.word_embeddings.weight"], pe = M.w["embeddings.position_embeddings.weight"], te = M.w["embeddings.token_type_embeddings.weight"];
    let x = new Float32Array(n * d);
    for(let t = 0; t < n; t++) for(let i = 0; i < d; i++)
      x[t * d + i] = we.q[ids[t] * d + i] * we.s[ids[t]] + pe.q[t * d + i] * pe.s[t] + te.q[i] * te.s[0];
    x = norm(x, n, d, "embeddings.LayerNorm");
    const sq = Math.sqrt(hd), a = new Float64Array(n);
    for(let L = 0; L < M.cfg.num_hidden_layers; L++){
      const p = "encoder.layer." + L + ".";
      const q = lin(x, n, p + "attention.self.query"), k = lin(x, n, p + "attention.self.key"), v = lin(x, n, p + "attention.self.value");
      const ctx = new Float32Array(n * d);
      for(let h = 0; h < H; h++) for(let t = 0; t < n; t++){
        let mx = -Infinity;
        for(let u = 0; u < n; u++){ let s = 0; for(let j = 0; j < hd; j++) s += q[t * d + h * hd + j] * k[u * d + h * hd + j]; a[u] = s / sq; if(a[u] > mx) mx = a[u]; }
        let sum = 0; for(let u = 0; u < n; u++){ a[u] = Math.exp(a[u] - mx); sum += a[u]; }
        for(let j = 0; j < hd; j++){ let s = 0; for(let u = 0; u < n; u++) s += a[u] * v[u * d + h * hd + j]; ctx[t * d + h * hd + j] = s / sum; }
      }
      const ao = lin(ctx, n, p + "attention.output.dense"); for(let i = 0; i < n * d; i++) ao[i] += x[i];
      x = norm(ao, n, d, p + "attention.output.LayerNorm");
      const hh = lin(x, n, p + "intermediate.dense"); for(let i = 0; i < hh.length; i++) hh[i] = 0.5 * hh[i] * (1 + erf(hh[i] / Math.SQRT2));
      const o = lin(hh, n, p + "output.dense"); for(let i = 0; i < n * d; i++) o[i] += x[i];
      x = norm(o, n, d, p + "output.LayerNorm");
    }
    const e = x.slice(0, d); let len = 0; for(const z of e) len += z * z; len = Math.max(Math.sqrt(len), 1e-9);
    return e.map(z => z / len);   // the [CLS] position carries the sentence's meaning in this model
  }
  function similarities(text){   // {"book#|ch|v": similarity} for every verse
    const q = embed(text), sims = new Map(); let r = 0;
    for(const P of M.parts) for(let j = 0; j < P.cnt; j++, r++){
      let s = 0; const o = j * M.dim; for(let i = 0; i < M.dim; i++) s += q[i] * P.m[o + i];
      const [b, c, v] = M.refs[r]; sims.set(M.books[b] + "|" + c + "|" + v, s * P.s[j] / 127);
    }
    return sims;
  }

  /* ---------- one ranked list (bibleask/blend.py) ---------- */
  const K = 2, DEPTH = 60, MEANING_FLOOR = 0.55, W_STRONGS = 1, W_PHRASE = 2, W_MEANING = 1, PHRASE = 0.9;
  const WHY_WORD = "matched word", WHY_NEAR = "matched words in the verses around it", WHY_MEANING = "matched by meaning";
  function indexOf(ctx, book, c, v){
    let i = ctx.ix.byRef.get(book + "|" + c + "|" + v);
    if(i === undefined && ctx.resolve){ const t = ctx.resolve(book); if(t) i = ctx.ix.byRef.get(t + "|" + c + "|" + v); }
    return i === undefined ? null : i;
  }
  function meaningRanked(sims, ctx){
    if(!sims) return [];
    const out = [];
    for(const [key, sim] of [...sims].sort((a, b) => b[1] - a[1])){
      if(sim < MEANING_FLOOR || out.length >= DEPTH) break;
      const [b, c, v] = key.split("|"), i = indexOf(ctx, b, +c, +v);
      if(i !== null) out.push([i, sim]);
    }
    return out;
  }
  async function strongsRanked(q, ctx, sims){
    const matches = await meaningMatches(q);
    if(!matches.length) return [];
    const words = content(q).flat().filter(w => !gloss.common.has(w));
    const agree = new Set(meaningRanked(sims, ctx).map(x => x[0]));
    const best = new Map();   // "book|ch|v" -> Map(term -> [weight, label, quality])
    for(const m of matches){
      const weight = m.quality * m.idf;
      for(const [b, c, v] of m.verses){
        const key = b + "|" + c + "|" + v; let t = best.get(key); if(!t) best.set(key, t = new Map());
        if(weight > (t.get(m.term) || [0])[0]) t.set(m.term, [weight, m.label, m.quality]);
      }
    }
    const near = new Map();   // a story spans several verses: credit what the verses around it have
    for(const [key, terms] of best){
      const [b, c, v] = key.split("|");
      for(const d of [-3, -2, -1, 1, 2, 3]){ const k2 = b + "|" + c + "|" + (+v + d); let s = near.get(k2); if(!s) near.set(k2, s = new Set()); for(const t of terms.keys()) s.add(t); }
    }
    const out = [];
    for(const [key, terms] of best){
      const len = t => t.split(" ").length, nb = near.get(key) || new Set();
      let covered = 0, wsum = 0; for(const [t, [w]] of terms){ covered += len(t); wsum += w; }
      for(const t of nb) if(!terms.has(t)) covered += 0.5 * len(t);
      let score = wsum * (0.4 + 0.6 * Math.min(covered / Math.max(words.length, 1), 1));
      const [b, c, v] = key.split("|"), i = indexOf(ctx, b, +c, +v);
      if(i === null) continue;
      // new: the Bible says it in other words (KJV "great whales" for "sea monsters"); such a clear phrase counts double
      const own = new Set(ctx.ix.toks[i]), fresh = [...terms.keys()].filter(t => !t.split(" ").every(w => own.has(w)));
      const clear = [...terms.keys()].filter(t => t.includes(" ") && terms.get(t)[2] >= PHRASE);   // "sea monster" = tannin
      const phrase = clear.some(t => fresh.includes(t));   // ... where the Bible says it in other words: counts double
      if(!clear.length && terms.size < 2 && words.length > 1) score = 0;   // one word alone: only with a second word, or a one-word question
      if(sims && sims.size){   // the meaning search must agree, even for a phrase (tannin is also the ASV's "jackals")
        score *= Math.max((sims.get(key) || 0) - 0.4, 0.02);
        if(!agree.has(i)) score = 0;
      }
      let top = null; for(const x of terms.values()) if(!top || x[0] > top[0] || (x[0] === top[0] && x[1] > top[1])) top = x;
      out.push([i, fresh.length || clear.length ? score : 0, top[1], phrase]);   // a word the Bible already uses adds nothing
    }
    return out.sort((a, b) => b[1] - a[1]);
  }
  function realWords(q, ix){   // a real content word, one the Bible or the model knows ("asdf": no guessing)
    for(const w of (q.toLowerCase().match(/[a-z]+/g) || [])) if(w.length >= 3 && !STOP.has(w) && (ix.vocab.has(w) || (M && M.ids.has(w)))) return true;
    return false;
  }
  /* ctx: {flat, ix: makeIndex(flat), english: true/false, resolve: book name -> this Bible's name, meaning: use the model if loaded}
     -> [{i, score, why: [...]}], best first */
  async function blend(q, ctx, k){
    const found = new Map();
    const add = (i, rank, why, weight = 1) => { let f = found.get(i); if(!f) found.set(i, f = {i, score: 0, why: []}); if(rank !== null) f.score += weight / (K + rank + 1); if(!f.why.includes(why)) f.why.push(why); };
    const qwords = new Set(tokenize(q).length ? tokenize(q) : tokenize(q, true));
    wordSearch(ctx.ix, ctx.flat, q, DEPTH).forEach((i, r) => add(i, r, ctx.ix.toks[i].some(w => qwords.has(w)) ? WHY_WORD : WHY_NEAR));
    if(ctx.english){
      let sims = null;
      try{ if(M && ctx.meaning !== false && realWords(q, ctx.ix)){ sims = similarities(q); meaningRanked(sims, ctx).forEach(([i], r) => add(i, r, WHY_MEANING, W_MEANING)); } }catch(e){ sims = null; }
      try{
        let r = 0;
        for(const [i, sc, lab, phrase] of await strongsRanked(q, ctx, sims)){
          if(sc > 0 && r < DEPTH){ add(i, r, lab, phrase ? W_PHRASE : W_STRONGS); r++; }
          else if(found.has(i)) add(i, null, lab);   // found another way: say which Hebrew/Greek word it is
        }
      }catch(e){}
    }
    const ranked = [...found.values()].sort((a, b) => b.score - a.score || a.i - b.i), seen = new Set(), out = [];
    for(const f of ranked){ const key = ctx.flat[f.i].t.toLowerCase().slice(0, 160); if(seen.has(key)) continue; seen.add(key); out.push(f); if(out.length >= k) break; }
    return out;
  }

  return {makeIndex, wordSearch, blend, loadMeaning, meaningSize, meaningReady: () => !!M, embed: t => embed(t), encode: t => encode(t, 512),
          meaningMatches, setLoader: f => { load = f; }};
})();
if(typeof module !== "undefined") module.exports = {Smart, tokenize, stem, STOP};
