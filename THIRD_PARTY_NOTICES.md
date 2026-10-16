# Third-party notices

BibleChat itself is MIT licensed (see `LICENSE`). It is built with, or downloads on request, the
following work by others. Each keeps its own license.

## Code included in BibleChat

| Component | Used for | License |
|---|---|---|
| [Bible](https://github.com/Lugsole/net.lugsole.bible_gui) by Lugsole | Reading view and the SPB, TSV and MyBible readers are modelled on it | MIT (notice below) |

> Copyright (c) 2020 Lugsole. Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions: The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software. THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

## Reference data included in BibleChat

| Data | Used for | License |
|---|---|---|
| **Nave's Topical Bible** (Orville J. Nave, 1896), from the CrossWire SWORD module "Nave" (text from [CCEL](https://ccel.org/ccel/n/nave/bible.xml)) | Topic results in chat, e.g. "fallen angels" | Public domain |

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
- **Bibles people add from their own files** are the person's own business; BibleChat ships none.
