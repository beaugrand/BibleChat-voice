# Rules for anyone changing BibleChat (people and AI assistants)

Read [README.md](README.md) first. Its top half is the project handover: where everything lives, how it works, the code map, every feature, the comparison with other apps and the open items.

## Keep the handover current: every change, same commit

When you add, change or remove anything in the app, update README.md in the same commit:

1. **Status**: what changed since the last release; the version if you bumped it; the test count.
2. **Features** (section 4) and the **User guide** if people will see the change.
3. **Code map** (section 3) if you added, renamed or removed a file.
4. **Sources and licenses** (section 6) and THIRD_PARTY_NOTICES.md if you added data, a font or a library.
5. **Open items** (section 7): remove what you finished, add what you found.

Then tell the owner that the Google Doc "BibleChat – Handover" needs the same update (it mirrors this README for non-developers), or update it yourself if you have access to it.

## Writing style

- Plain language for a non-programmer. Short sentences.
- Say "the local computer/device", never a person's machine name or home-folder path.
- Never claim a feature of another app without a source; write "Not listed" when the source is silent.

## Other rules

- Run `python -m unittest discover -s tests` before committing; all tests must pass.
- Release: set `__version__` in `bibleask/__init__.py`, then run the **Build BibleChat** workflow with the same `vX.Y.Z`.
- Keep the Love Donations button, the About/credit to Hans W. Beaugrand and all license notices.
