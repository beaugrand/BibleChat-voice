"""🎙 Tap and talk on the phone (web/voice.js): the big button, the spoken greeting, the hands-free loop that stops
after 8 seconds of silence, and the "Start in voice mode" setting.

The behaviour tests run web/voice.js in Node with a pretend microphone and a pretend voice. The silence time is
shortened from 8 seconds to a fraction of a second so the tests stay fast; the real value is checked separately."""
import json
import os
import re
import shutil
import subprocess
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB = os.path.join(ROOT, "web")


def read(*p):
    with open(os.path.join(ROOT, *p), encoding="utf-8") as f:
        return f.read()


class VoicePageTest(unittest.TestCase):
    def test_home_has_the_big_button_type_instead_privacy_and_setting(self):
        s = read("web", "index.html")
        home = s[s.index('<section id="v-home"'):s.index("<!-- READ -->")]
        for part in ('id="talkBtn"', ">Tap and talk<", 'id="talkType"', ">Type instead<", 'id="talkStart"',
                     "Start in voice mode", 'id="talkPriv"', "Google, Apple or Microsoft"):
            self.assertIn(part, home, part)
        self.assertLess(home.index('id="talkBox"'), home.index('id="votd"'))   # at the top of Home, above the verse of the day
        self.assertIn('id="homePathsRow"', home)                               # where it goes when voice mode is off

    def test_stop_listening_is_always_on_screen_while_voice_is_on(self):
        s = read("web", "index.html")
        self.assertIn('id="talkBar"', s)
        self.assertIn('id="talkStop">■ Stop listening<', s)
        self.assertIn("#talkBar{position:fixed", s)

    def test_page_loads_and_mounts_voice(self):
        s = read("web", "index.html")
        self.assertIn('<script src="voice.js"></script>', s)
        self.assertIn("BCVoice.mount({", s)
        self.assertIn("async function runSearch(q, onFirst){", s)
        self.assertIn("if(onFirst) onFirst();", s)
        # only the verses Search found are spoken: the text comes from the open Bible, never from anywhere else
        ask = s[s.index("function talkAsk(q){"):s.index("BCVoice.mount({")]
        self.assertIn("bible.byName[b]", ask)
        self.assertNotIn("fetch(", ask)
        # a topic ("what is love") shows 📌 key passages on top: those are read first, as the eye reads the screen
        self.assertLess(ask.index(".bc-keys .bc-kv > a[data-b]"), ask.index(".res > a[data-b]"))

    def test_kept_offline_and_published(self):
        self.assertIn('"voice.js"', read("web", "sw.js"))
        self.assertIn('"voice.js"', read("web", "build_study.py"))

    def test_eight_seconds_and_the_greeting(self):
        v = read("web", "voice.js")
        self.assertIn("const SILENCE_MS = 8000;", v)
        self.assertIn("Shalom. What's on your heart today? You can ask about any verse, topic, or start a study path.", v)

    def test_new_words_are_translated(self):
        src = read("web", "i18n.js")
        for phrase in ("Tap and talk", "Type instead", "Start in voice mode", "■ Stop listening", "🎙 Listening…",
                       "🔍 Searching…", "🔊 Reading the verses…",
                       "Shalom. What's on your heart today? You can ask about any verse, topic, or start a study path.",
                       "When you talk, your browser sends your spoken words to Google, Apple or Microsoft to turn them into text. BibleChat keeps no recording.",
                       "This browser can't listen. Try Chrome or Safari, or type instead."):
            m = re.search(r'^' + re.escape(json.dumps(phrase, ensure_ascii=False)) + r': \[(.*)\],$', src, re.M)
            self.assertTrue(m, phrase)
            self.assertEqual(len(json.loads("[" + m.group(1) + "]")), 7, phrase)

    def test_privacy_policy_mentions_voice(self):
        self.assertIn("Tap and talk", read("PRIVACY.md"))


HARNESS = r"""
const fs = require("fs"); const dir = process.argv[1];
const SIL = 250, wait = ms => new Promise(r => setTimeout(r, ms));
let recs = [], spoken = [], cancels = 0, toasts = [], asked = [], typed = 0, saved = {}, failStart = null;
class FakeRec {
  constructor(){ recs.push(this); this.started = false; this.aborted = false; }
  start(){ if(failStart) throw new Error(failStart); this.started = true; }
  abort(){ this.aborted = true; }
  say(text, final){ this.onresult && this.onresult({results: [Object.assign([{transcript: text}], {isFinal: final !== false})]}); }
  end(){ this.onend && this.onend(); }
  fail(err){ this.onerror && this.onerror({error: err}); this.onend && this.onend(); }
}
global.window = global;
global.SpeechSynthesisUtterance = class { constructor(t){ this.text = t; } };
global.speechSynthesis = {speak(u){ spoken.push(u.text); setTimeout(() => u.onend && u.onend(), 5); }, cancel(){ cancels++; }};
global.webkitSpeechRecognition = FakeRec;
eval(fs.readFileSync(dir + "/voice.js", "utf8") + "; global.BCVoice = BCVoice;");
const verse = (b, c, v, t) => ({book: b, ch: c, v, ref: b + " " + c + ":" + v, text: t});
const adapter = {
  ask: async q => { asked.push(q); return q === "nothing" ? {items: [], paths: []} :
    {items: [verse("1 Corinthians", 13, 4, "Charity suffereth long"), verse("John", 3, 16, "For God so loved"),
             verse("1 John", 4, 8, "God is love"), verse("Romans", 5, 8, "But God commendeth"), verse("John", 15, 13, "Greater love")],
     paths: ["Faith"]}; },
  listenLang: () => "en-US", speakLang: () => "en-US", uiLang: () => "en-US", voice: () => null,
  stopOthers: () => {}, typeInstead: () => { typed++; }, toast: m => toasts.push(m),
  store: {get: (k, d) => (k in saved ? saved[k] : d), set: (k, v) => { saved[k] = v; }}
};
BCVoice.mount(adapter, {}, {silenceMs: SIL});
const out = {};
const last = () => recs[recs.length - 1];
(async () => {
  // 1. first tap: the greeting is spoken, then the microphone opens by itself
  BCVoice.begin();
  out.greetFirst = spoken[0]; out.stateWhileGreeting = BCVoice.state();
  await wait(30); out.listensAfterGreeting = BCVoice.state() === "listening" && recs.length === 1 && recs[0].started;
  // 2. a question: Search is asked, the 3 best verses (and the study path) are read, then the microphone opens again
  last().say("what is love");
  await wait(80);
  out.asked = asked.slice(); out.readAloud = spoken.slice(1);
  out.loopReopened = BCVoice.state() === "listening" && recs.length === 2 && recs[1].started;
  // 3. the browser gives up early (no-speech): BibleChat keeps waiting until the 8 seconds (here SIL) are up
  last().fail("no-speech");
  await wait(20); out.restartedEarly = recs.length === 3 && BCVoice.state() === "listening";
  // 4. silence: the microphone closes quietly, with no message
  await wait(SIL + 60);
  out.offAfterSilence = BCVoice.state(); out.toastsAfterSilence = toasts.length;
  // 5. second tap: no second greeting
  const before = spoken.length; BCVoice.begin(); await wait(10);
  out.noSecondGreeting = spoken.length === before && BCVoice.state() === "listening";
  // 6. saying "Stop." ends it, without searching
  last().say("Stop."); await wait(20);
  out.stopWord = BCVoice.state(); out.stopWordAsked = asked.length;
  // 7. the Stop listening button while reading: the voice is cut off and the microphone stays closed
  BCVoice.begin(); await wait(10); last().say("what is love"); await wait(8);
  const n = recs.length, c = cancels; BCVoice.stop(true); await wait(80);
  out.stopButton = BCVoice.state() === "off" && recs.length === n && cancels > c;
  // 8. a blocked microphone: one plain message, then off
  BCVoice.begin(); await wait(10); last().fail("not-allowed"); await wait(10);
  out.blocked = [BCVoice.state(), toasts.length];
  // 9. nothing found: says so and listens again
  BCVoice.begin(); await wait(10); spoken = []; last().say("nothing"); await wait(60);
  out.nothing = [spoken[0], BCVoice.state()]; BCVoice.stop(true);
  // 10. the setting: on at first, remembered when turned off
  out.settingDefault = BCVoice.startInVoice(); BCVoice.setStartInVoice(false);
  out.settingOff = [BCVoice.startInVoice(), saved.voiceStart];
  out.isStop = ["stop", "Stop listening.", "Amen!", "stop the war in heaven", "Stopp"].map(BCVoice.isStop);
  // 11. a browser that can't listen: says so and opens Search for typing
  delete global.webkitSpeechRecognition; const t0 = toasts.length; BCVoice.begin();
  out.noMic = [toasts.length - t0, typed];
  console.log(JSON.stringify(out));
})();
"""


@unittest.skipUnless(shutil.which("node"), "Node.js is not installed")
class VoiceLoopTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        got = subprocess.run(["node", "-e", HARNESS, WEB], capture_output=True, text=True, timeout=60)
        assert got.returncode == 0, got.stderr
        cls.r = json.loads(got.stdout.strip().splitlines()[-1])

    def test_greeting_then_listening(self):
        self.assertEqual(self.r["greetFirst"], "Shalom. What's on your heart today? You can ask about any verse, topic, or start a study path.")
        self.assertEqual(self.r["stateWhileGreeting"], "greeting")
        self.assertTrue(self.r["listensAfterGreeting"])

    def test_question_is_searched_and_three_verses_read(self):
        self.assertEqual(self.r["asked"], ["what is love"])
        self.assertEqual(self.r["readAloud"], ["1 Corinthians 13:4. Charity suffereth long", "John 3:16. For God so loved",
                                               "1 John 4:8. God is love",
                                               "There is a study path about this: Faith. It is on the screen."])

    def test_hands_free_loop_reopens_the_microphone(self):
        self.assertTrue(self.r["loopReopened"])
        self.assertTrue(self.r["restartedEarly"])

    def test_silence_closes_quietly(self):
        self.assertEqual(self.r["offAfterSilence"], "off")
        self.assertEqual(self.r["toastsAfterSilence"], 0)

    def test_greeting_only_once_and_stop_word(self):
        self.assertTrue(self.r["noSecondGreeting"])
        self.assertEqual(self.r["stopWord"], "off")
        self.assertEqual(self.r["stopWordAsked"], 1)
        self.assertEqual(self.r["isStop"], [True, True, True, False, True])

    def test_stop_button_and_blocked_microphone(self):
        self.assertTrue(self.r["stopButton"])
        self.assertEqual(self.r["blocked"], ["off", 1])

    def test_nothing_found(self):
        self.assertTrue(self.r["nothing"][0].startswith("I found nothing for that in this Bible."))
        self.assertEqual(self.r["nothing"][1], "listening")

    def test_start_in_voice_mode_setting(self):
        self.assertTrue(self.r["settingDefault"])
        self.assertEqual(self.r["settingOff"], [False, False])

    def test_browser_without_listening(self):
        self.assertEqual(self.r["noMic"], [1, 1])


if __name__ == "__main__":
    unittest.main()
