"""🔊 Reading voice (⚙ Settings on the phone's Love page): pick which of the device's own voices reads aloud.

The page test checks the setting is there and that all four readers (🔊 Listen, 🙏 Prayers, 📜 Study Paths and
🎙 Tap and talk) go through pickVoice(). The behaviour test runs the real voice-choosing code from web/index.html
in Node with pretend voices, including an iPhone "Lee (Premium)" voice."""
import json
import os
import re
import shutil
import subprocess
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(*p):
    with open(os.path.join(ROOT, *p), encoding="utf-8") as f:
        return f.read()


class ReadingVoicePageTest(unittest.TestCase):
    def test_setting_is_on_the_love_page_with_default_and_sample(self):
        s = read("web", "index.html")
        love = s[s.index('<section id="v-love"'):s.index("</main>")]
        for part in ('data-sec="lvSettings"', 'id="lvSettings"', "🔊 Reading voice", 'id="rvSel"', 'id="rvHear">▶ Hear a sample<'):
            self.assertIn(part, love, part)
        self.assertIn('<option value="">${esc(tr("Default (automatic)"))}</option>', s)   # Default comes first
        self.assertIn('if(t === "love") rvFill();', s)                                     # refreshed for the open Bible
        # Love Donations, the About credit and the license stay
        for part in ("♥ Love Donations", "Hans W. Beaugrand", "Apache License 2.0", "NOTICE"):
            self.assertIn(part, love, part)

    def test_all_four_readers_use_pickVoice(self):
        s = read("web", "index.html")
        self.assertIn("voice = pickVoice(lang);", s)                                          # 🔊 Listen
        self.assertIn("voice: lang => { loadVoices(); return pickVoice(lang); },", s)         # 🎙 Tap and talk
        self.assertIn('return {lang, voice: pickVoice(lang)}; },', s)                         # 📜 Study Paths (🙏 Prayers borrows it)
        self.assertIn("A.voice ? A.voice(lang) : null", read("web", "voice.js"))
        self.assertIn("A.voice ? A.voice(kind, text) : null", read("web", "paths.js"))
        self.assertIn("A.voice ? A.voice(kind, text) : null", read("web", "prayers.js"))
        self.assertIn("BCPaths.adapter()", read("web", "prayers.js"))

    def test_new_words_are_translated(self):
        i18n = read("web", "i18n.js")
        for w in ("⚙ Settings", "🔊 Reading voice", "Choose a voice", "▶ Hear a sample", "Default (automatic)"):
            m = re.search(r'^"' + re.escape(w) + r'": \[(.*)\],$', i18n, re.M)
            self.assertTrue(m, w)
            self.assertEqual(len(json.loads("[" + m.group(1) + "]")), 7, w)


HARNESS = r"""
const fs = require("fs"), s = fs.readFileSync(process.argv[1], "utf8");
const part = (a, b) => s.slice(s.indexOf(a), s.indexOf(b));
const V = [["Samantha", "en-US", "com.apple.voice.compact.en-US.Samantha", true], ["Lee", "en-AU", "com.apple.voice.premium.en-AU.Lee", false],
           ["Anna", "de-DE", "com.apple.voice.compact.de-DE.Anna", false], ["Markus", "de-DE", "com.apple.voice.enhanced.de-DE.Markus", false]]
  .map(([name, lang, voiceURI, d]) => ({name, lang, voiceURI, default: d}));
let saved = {}, voices = V;
const store = {get: (k, d) => (k in saved ? JSON.parse(saved[k]) : d), set: (k, v) => { saved[k] = JSON.stringify(v); }};
eval(part("const vNorm", "function intro("));
const out = {};
out.autoEn = pickVoice("en-US").name;
out.englishList = voicesFor("en-US").map(v => v.name);
store.set("voicePick", {en: {uri: "com.apple.voice.premium.en-AU.Lee", name: "Lee"}});
out.chosenEn = pickVoice("en-US").name;
out.chosenGb = pickVoice("en-GB").name;               // the same English choice for every English Bible
out.autoIgnoresChoice = pickVoice("en-US", true).name;
out.germanUntouched = pickVoice("de-DE").name;
store.set("voicePick", {en: {uri: "com.apple.voice.premium.en-AU.Lee", name: "Lee"}, de: {uri: "com.apple.voice.enhanced.de-DE.Markus", name: "Markus"}});
out.germanChosen = pickVoice("de-DE").name;
voices = V.filter(v => v.name !== "Lee");              // the voice was removed from the device
out.removedFallsBack = pickVoice("en-US").name;
console.log(JSON.stringify(out));
"""


@unittest.skipUnless(shutil.which("node"), "Node.js is not installed")
class ReadingVoiceChoiceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        got = subprocess.run(["node", "-e", HARNESS, os.path.join(ROOT, "web", "index.html")], capture_output=True, text=True, timeout=60)
        assert got.returncode == 0, got.stderr
        cls.r = json.loads(got.stdout.strip().splitlines()[-1])

    def test_without_a_choice_it_picks_as_before(self):
        self.assertEqual(self.r["autoEn"], "Samantha")
        self.assertEqual(self.r["englishList"], ["Samantha", "Lee"])   # every English voice, any region

    def test_a_chosen_voice_wins_for_its_language(self):
        self.assertEqual(self.r["chosenEn"], "Lee")
        self.assertEqual(self.r["chosenGb"], "Lee")
        self.assertEqual(self.r["autoIgnoresChoice"], "Samantha")
        self.assertEqual(self.r["germanUntouched"], "Anna")
        self.assertEqual(self.r["germanChosen"], "Markus")

    def test_a_removed_voice_falls_back(self):
        self.assertEqual(self.r["removedFallsBack"], "Samantha")


if __name__ == "__main__":
    unittest.main()
