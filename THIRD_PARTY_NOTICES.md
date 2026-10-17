# Third-party notices

BibleChat itself is licensed under the Apache License 2.0 (see `LICENSE` and `NOTICE`). It is built with, or downloads on request, the
following work by others. Each keeps its own license.

## Code included in BibleChat

| Component | Used for | License |
|---|---|---|
| [The SWORD Project](https://crosswire.org/sword/) locale files (libsword-common) | Bible book names in 30 languages (`bibleask/data/booknames.json`); names are facts, files GPL-2 | GPL-2 (source of the name list) |
| [qrcode-generator](https://github.com/kazuhikoarase/qrcode-generator) by Kazuhiko Arase | Makes the church QR codes; built into both `index.html` files | MIT |
| [Bible](https://github.com/Lugsole/net.lugsole.bible_gui) by Lugsole | Reading view and the SPB, TSV and MyBible readers are modelled on it | MIT (notice below) |

> Copyright (c) 2020 Lugsole. Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions: The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software. THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

## Reference data included in BibleChat

| Data | Used for | License |
|---|---|---|
| **Nave's Topical Bible** (Orville J. Nave, 1896), from the CrossWire SWORD module "Nave" (text from [CCEL](https://ccel.org/ccel/n/nave/bible.xml)) | Topic results in chat, e.g. "fallen angels", and the topics of a verse in Read mode | Public domain |
| **Strong's Exhaustive Concordance** Hebrew and Greek dictionaries (James Strong, 1890), from the CrossWire SWORD modules "StrongsHebrew" and "StrongsGreek" | The original Hebrew/Greek word, its meaning and pronunciation | Public domain |
| **Scofield Reference Notes** (C. I. Scofield, 1917 edition), from the CrossWire SWORD module "Scofield" | The highlighted words in Read mode | Public domain |
| **Matthew Henry's Concise Commentary**, from the CrossWire SWORD module "MHCC" (text from CCEL) | "Matthew Henry's Commentary" when you click a verse | Public domain |
| **Easton's Bible Dictionary** (M. G. Easton, 1897), as parsed from CCEL by the [NEUU bible-dictionary-dataset](https://github.com/neuu-org/bible-dictionary-dataset) | The dotted names and places in Read mode | Public domain (dataset: CC BY 4.0, NEUU) |
| **Cross-references** from [OpenBible.info](https://www.openbible.info/labs/cross-references/) (data of 2024-11-04), via the [Scrollmapper](https://github.com/scrollmapper/bible_databases) project | "Cross-references" when you click a verse, and cross-reference questions in chat | CC BY (attribution: OpenBible.info) |
| **King James Version with Strong's numbers**, from the CrossWire SWORD module "KJV" (engKJV2006eb) | Which Hebrew/Greek word stands behind each English word, and every verse that uses it | Public domain |

## Font included in BibleChat

| Font | Used for | License |
|---|---|---|
| [Noto Sans Phoenician](https://github.com/notofonts/phoenician) (The Noto Project Authors) | Showing Hebrew words in Paleo-Hebrew letters | SIL Open Font License 1.1 |

## Libraries packed into the downloadable app

| Library | License |
|---|---|
| Python | PSF License |
| [llama-cpp-python](https://github.com/abetlen/llama-cpp-python) and [llama.cpp](https://github.com/ggml-org/llama.cpp) | MIT |
| [pypdfium2](https://github.com/pypdfium2-team/pypdfium2) / PDFium | Apache-2.0 or BSD-3-Clause / BSD-3-Clause |
| [certifi](https://github.com/certifi/python-certifi) | MPL-2.0 |
| [PyInstaller](https://pyinstaller.org) bootloader | GPL-2.0 with an exception that allows distributing apps built with it |

## Downloaded only when the person asks

Nothing below is shipped inside BibleChat. Each item is fetched from its own home when the person
clicks to get it, and stays under its own license.

- **Bibles** from the [open-bibles](https://github.com/seven1m/open-bibles) collection: public domain or
  Creative Commons (CC BY 4.0 / CC BY-SA 4.0). The license of each one is shown next to it in the app.
- **AI models** from Hugging Face. Bible Assistant 4B and Qwen2.5 1.5B are Apache-2.0; Llama 3.2 uses
  Meta's Llama 3.2 Community License; Qwen2.5 3B is research-only. The model's own page has its terms.
- **Ethiopian Canon (public-domain English)**, assembled by BibleChat (`packaging/build_ethiopian.py`) from
  public-domain texts: the World English Bible; R. H. Charles's *1 Enoch* (1917) and *Jubilees* (1917);
  Morfill and Charles's *2 Enoch* (1896); *1 Clement* from the Ante-Nicene Fathers (1885), as transcribed by
  the [Scrollmapper](https://github.com/scrollmapper/bible_databases_deuterocanonical) project.
- **Amharic New Testament (1962)** from [eBible.org](https://ebible.org/amh/copyright.htm): copyright © 1962, 2003
  United Bible Societies, used with the kind permission of the Bible Society of Ethiopia. Free for
  non-commercial use with this notice; commercial use needs written permission of the Bible Society of Ethiopia.
- **Septuagint in English** from [eBible.org](https://ebible.org): Brenton's *Translation of the Greek
  Septuagint into English* (1851, public domain) and LXX2012, its update to modern English (public domain).
- **Bibles people add from their own files** are the person's own business; BibleChat ships none.
