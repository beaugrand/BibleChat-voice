"""🎧 Guided study by voice on the phone (web/paths.js, Phase 2 of the voice handover).

The rule tested hardest: guided study speaks only the Bible text and the path's own words (its question, its "Facts
about the words" as the reflection, its "For me" line), plus a few fixed sentences of its own. Never commentary,
never anything made up. The test builds every step of Forgiveness with the real King James verses on a pretend page
that also carries a commentary note, and checks each spoken line against that list."""
import json
import os
import re
import shutil
import subprocess
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "packaging"))
import build_paths as bp  # noqa: E402


def read(*p):
    with open(os.path.join(ROOT, *p), encoding="utf-8") as f:
        return f.read()


FIXED = {
    "Reflection.",
    "Guided study. Forgiveness: seventy times seven. I read the verses and ask the question, then I listen for your answer. "
    "When I listen, you can say repeat, skip or pause.",
}
SAY_REF = re.compile(r"^(?:[1-3] )?[A-Z][a-z]+ \d+(?:, verses? \d+(?: to \d+)?)?\.$")   # "Luke 17, verses 3 to 4."


class GuidedPageTest(unittest.TestCase):
    def test_one_path_first_and_phone_only(self):
        js = read("web", "paths.js")
        self.assertIn('const GUIDED = new Set(["forgiveness"]);', js)
        self.assertIn("const canGuide = p => !!(p && !p.mine && GUIDED.has(p.id) && A && A.hear);", js)
        self.assertIn("${canGuide(p) ? `<button class=\"pv-btn pv-listen pv-guide\">", js)
        phone, computer = read("web", "index.html"), read("bibleask", "web", "index.html")
        self.assertIn("hear: o => BCVoice.hear(o)", phone)
        self.assertNotIn("hear: o =>", computer)   # the computer app has no browser listening: no guided button there

    def test_repeat_skip_pause_on_screen_and_progress_saved(self):
        js = read("web", "paths.js")
        for part in ("pv-grep\">↺ Repeat", "pv-gpause", "pv-gskip\">⏭ Skip", "pv-gstop",
                     "saveProgress(S.path.id, {guided: S.step});", "saveProgress(p.id, {guided: null});",
                     "Continue guided study", "if(GD.on && !GD.moving) gdStop();", "function close(){ lsStop(); gdStop();",
                     'const h = GD.hearing = A.hear({lang: "en-US"'):
            self.assertIn(part, js, part)

    def test_spoken_answer_goes_into_the_steps_notes(self):
        js = read("web", "paths.js")
        save = js[js.index("function gdSave(text){"):js.index("async function gdNext(tok){")]
        for part in ('get("notes", {})', 'set("notes", n)', '#pvSee'):
            self.assertIn(part, save)

    def test_new_words_are_translated(self):
        src = read("web", "i18n.js")
        for phrase in ("Start guided study", "Continue guided study", "↺ Repeat", "⏭ Skip", "Your answer…", "Reflection",
                       "Your answer is saved in your notes for this step."):
            m = re.search(r'^' + re.escape(json.dumps(phrase, ensure_ascii=False)) + r': \[(.*)\],$', src, re.M)
            self.assertTrue(m, phrase)
            self.assertEqual(len(json.loads("[" + m.group(1) + "]")), 7, phrase)


HARNESS = r"""
const fs = require("fs"); const [dir, versesJson] = process.argv.slice(1);
eval(fs.readFileSync(dir + "/paths.js", "utf8") + "; global.BCPaths = BCPaths;");
const path = JSON.parse(fs.readFileSync(dir + "/paths/forgiveness.json", "utf8")), verses = JSON.parse(versesJson);
const el = name => ({name, classList: {add(){}, remove(){}}});
function page(step){
  const st = path.steps[step];
  const refs = st.refs.map(r => ({dataset: {ref: r, key: "reader"}, querySelector: () => el("refh"),
    querySelectorAll: () => (verses[r] || []).map(t => ({childNodes: [{nodeName: "SUP", textContent: "4"}, {nodeName: "#text", textContent: t}]}))}));
  const facts = (st.facts || []).map((f, i) => el("fact" + i));
  const commentary = [{textContent: "COMMENTARY: a man's notes, never to be spoken in guided study"}];
  return {querySelector: s => el(s), querySelectorAll: s => s === "#pvVerses .pv-ref" ? refs : s === ".pv-facts p" ? facts
    : s.includes("pnote") ? commentary : []};
}
const A = {bookName: b => b};
const out = path.steps.map((s, i) => BCPaths._guided.parts(A, page(i), path, i, i === 0).map(p => ({name: p.name, listen: !!p.listen, segs: p.segs.map(x => x.text)})));
const cmds = ["repeat", "Say that again.", "Skip", "next", "Pause.", "wait", "Stop", "Amen", "I think seventy times seven means always", "stopp", "repetir"].map(BCPaths._guided.command);
console.log(JSON.stringify({steps: out, cmds, paths: [...BCPaths._guided.paths]}));
"""


@unittest.skipUnless(shutil.which("node"), "Node.js is not installed")
class GuidedSpeaksOnlyThePathTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.path = json.loads(read("web", "paths", "forgiveness.json"))
        B = bp.Bibles(download=False)
        cls.verses = {r: [B.text["KJV"][k] for k in B.verses(r, "KJV")] for s in cls.path["steps"] for r in s["refs"]}
        got = subprocess.run(["node", "-e", HARNESS, os.path.join(ROOT, "web"), json.dumps(cls.verses)],
                             capture_output=True, text=True, timeout=60)
        assert got.returncode == 0, got.stderr
        cls.r = json.loads(got.stdout.strip().splitlines()[-1])

    def test_only_forgiveness_for_now(self):
        self.assertEqual(self.r["paths"], ["forgiveness"])

    def test_every_spoken_line_is_the_bible_or_the_path(self):
        n = len(self.path["steps"])
        self.assertEqual(len(self.r["steps"]), n)
        for i, (st, parts) in enumerate(zip(self.path["steps"], self.r["steps"])):
            allowed = FIXED | {f"Step {i + 1} of {n}.", st["question"], "For me: " + st["apply"]} \
                | {f["text"] for f in st["facts"]} | {t.strip() for r in st["refs"] for t in self.verses[r]}
            for p in parts:
                for line in p["segs"]:
                    with self.subTest(step=i + 1, line=line[:60]):
                        self.assertTrue(line in allowed or SAY_REF.match(line), line)
                        self.assertNotIn("COMMENTARY", line)

    def test_each_step_reads_asks_listens_reflects(self):
        for i, (st, parts) in enumerate(zip(self.path["steps"], self.r["steps"])):
            with self.subTest(step=i + 1):
                self.assertEqual([p["name"] for p in parts], ["verses", "question", "reflection", "apply"])
                self.assertEqual([p["listen"] for p in parts], [False, True, False, False])   # it listens only after the question
                self.assertEqual(parts[1]["segs"], [st["question"]])
                self.assertEqual(parts[2]["segs"], ["Reflection."] + [f["text"] for f in st["facts"]])
                verses_read = [x for x in parts[0]["segs"] if not SAY_REF.match(x) and not x.startswith(("Step ", "Guided study."))]
                self.assertEqual(verses_read, [t.strip() for r in st["refs"] for t in self.verses[r]])   # every verse, in order
        self.assertTrue(self.r["steps"][0][0]["segs"][0].startswith("Guided study."))   # the short welcome, first step only
        self.assertFalse(self.r["steps"][1][0]["segs"][0].startswith("Guided study."))

    def test_spoken_commands(self):
        self.assertEqual(self.r["cmds"], ["repeat", "repeat", "skip", "skip", "pause", "pause", "stop", None, None, "stop", "repeat"])


if __name__ == "__main__":
    unittest.main()
