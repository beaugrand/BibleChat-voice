"""Free Bibles BibleChat can download in one click.

All files come from the open-bibles collection (https://github.com/seven1m/open-bibles), which only holds
public-domain and freely licensed translations. The address is pinned to one exact version of that collection
so a file can never change underneath us. Two files there (Bible in Basic English, Hebrew Leningrad Codex)
are damaged and left out. Each entry was test-loaded and its verses counted when it was added here.
"""
from __future__ import annotations

SOURCE = "https://github.com/seven1m/open-bibles"
COMMIT = "f257a3559025c3f873b48a75019f53a9354ed7de"
BASE = f"https://raw.githubusercontent.com/seven1m/open-bibles/{COMMIT}/"

# (file, language, abbreviation, title, license, bytes, verses, note)
CATALOG: list[tuple[str, str, str, str, str, int, int, str]] = [
    ('eng-asv.zefania.xml', 'English', 'ASV', 'American Standard Version (1901)', 'Public Domain', 5239191, 31102, ''),
    ('eng-bsb.usfx.xml', 'English', 'BSB', 'Berean Standard Bible', 'Public Domain', 17599832, 31086, ''),
    ('eng-darby.zefania.xml', 'English', 'DARBY', 'Darby Bible', 'Public Domain', 5183149, 31102, ''),
    ('eng-dra.zefania.xml', 'English', 'DRA', 'Douay-Rheims 1899 American Edition', 'Public Domain', 5886456, 35953, '75 books, includes the Apocrypha/Deuterocanon'),
    ('eng-kjv.osis.xml', 'English', 'KJV', 'King James Version', 'Public Domain', 10096487, 36820, '81 books, includes the Apocrypha/Deuterocanon'),
    ('eng-web.usfx.xml', 'English', 'WEB', 'World English Bible', 'Public Domain', 6210746, 37644, '84 books, includes the Apocrypha/Deuterocanon'),
    ('eng-ylt.zefania.xml', 'English', 'YLT', "Young's Literal Translation", 'Public Domain', 1416994, 7957, 'New Testament only'),
    ('sqi-albanian.osis.xml', 'Albanian', '', 'Albanian Bible', 'Public Domain', 5844222, 31102, ''),
    ('bul-bulgarian.osis.xml', 'Bulgarian', '', 'Bulgarian Bible', 'Public Domain', 7724725, 31101, ''),
    ('chr-cherokee.usfx.xml', 'Cherokee', '', 'Cherokee New Testament', 'Public Domain', 1771830, 7957, 'New Testament only'),
    ('chi-cuv-simp.usfx.xml', 'Chinese (Simplified)', 'CUV', 'Chinese Union Version (Simplified)', 'Public Domain', 3951372, 31100, ''),
    ('chi-cuv.usfx.xml', 'Chinese (Traditional)', 'CUV', 'Chinese Union Version (Traditional)', 'Public Domain', 3951359, 31100, ''),
    ('hrv-croatian.osis.xml', 'Croatian', '', 'Croatian Bible', 'Public Domain', 5222422, 35448, '73 books, includes the Apocrypha/Deuterocanon'),
    ('cze-bkr.zefania.xml', 'Czech', '', 'Bible kralická', 'Public Domain', 4932880, 31172, ''),
    ('dan-danish.osis.xml', 'Danish', '', 'Danish Bible', 'Public Domain', 4894641, 30139, '61 books (incomplete)'),
    ('dut-statenvertaling.zefania.xml', 'Dutch', '', 'Statenvertaling (1637)', 'Public Domain', 5400321, 31079, ''),
    ('eng-gb-oeb.osis.xml', 'English (UK)', 'OEB-CW', 'Open English Bible, Commonwealth Edition', 'Public Domain', 2750474, 11703, '42 books (incomplete)'),
    ('eng-gb-webbe.usfx.xml', 'English (UK)', 'WEBBE', 'World English Bible, British Edition', 'Public Domain', 18723593, 38041, '81 books, includes the Apocrypha/Deuterocanon'),
    ('eng-us-oeb.osis.xml', 'English (US)', 'OEB-US', 'Open English Bible, US Edition', 'Public Domain', 2750152, 11703, '42 books (incomplete)'),
    ('fin-biblia.osis.xml', 'Finnish', '', 'Finnish Bible', 'Public Domain', 5613070, 31107, ''),
    ('fra-ostervald.osis.xml', 'French', '', 'French Ostervald 1996', 'Public Domain', 5663717, 31172, ''),
    ('deu-luther1912.osis.xml', 'German', '', 'Luther Bible 1912', 'Public Domain', 5461565, 31171, ''),
    ('hun-karoli.osis.xml', 'Hungarian', '', 'Hungarian Károli Bible', 'Public Domain', 5593430, 31170, ''),
    ('ita-riveduta.osis.xml', 'Italian', '', 'Italian Riveduta Bible 1927', 'Public Domain', 5500177, 31102, ''),
    ('jpn-kougo.osis.xml', 'Japanese', '', 'Japanese Kougo (Colloquial)', 'Public Domain', 13192436, 31086, ''),
    ('kor-korean.osis.xml', 'Korean', '', 'Korean Bible', 'Public Domain', 5742069, 30625, ''),
    ('lat-clementine.usfx.xml', 'Latin', '', 'Clementine Latin Vulgate', 'Public Domain', 4652377, 35811, '73 books, includes the Apocrypha/Deuterocanon'),
    ('lav-latvian.osis.xml', 'Latvian', '', 'Latvian Bible', 'Public Domain', 1228807, 7899, 'New Testament only'),
    ('mri-maori.osis.xml', 'Maori', '', 'Maori Bible', 'Public Domain', 5816872, 31102, ''),
    ('nor-norwegian.osis.xml', 'Norwegian', '', 'Norwegian Bible', 'Public Domain', 5097903, 30292, '64 books (incomplete)'),
    ('pol-gdanska.osis.xml', 'Polish', '', 'Polish Gdańska Bible', 'Public Domain', 5482751, 31700, ''),
    ('por-almeida.usfx.xml', 'Portuguese', '', 'João Ferreira de Almeida', 'Public Domain', 4745976, 31098, ''),
    ('ron-rccv.usfx.xml', 'Romanian', '', 'Protestant Romanian Corrected Cornilescu Version', 'Public Domain', 4697599, 31102, ''),
    ('rus-synodal.zefania.xml', 'Russian', '', 'Russian Synodal Translation', 'Public Domain', 7154535, 31369, ''),
    ('spa-bes.usfx.xml', 'Spanish', 'SPNBES', 'La Biblia en Español Sencillo', 'CC BY 4.0', 12925919, 31101, ''),
    ('spa-pddpt.usfx.xml', 'Spanish', 'SPAPDT', "Palabra de Dios para ti / God's Word for You", 'CC BY-SA 4.0', 12248612, 31079, ''),
    ('spa-rv1909.usfx.xml', 'Spanish', 'RV1909', 'Reina Valera 1909', 'Public Domain', 11293936, 31084, ''),
    ('spa-vbl.usfx.xml', 'Spanish', 'SPNVBL', 'Versión Biblia Libre / Spanish Free Bible Version', 'CC BY-SA 4.0', 12504316, 31086, ''),
    ('swa-swahili.osis.xml', 'Swahili', '', 'Swahili Bible', 'Public Domain', 1279743, 7815, 'New Testament only'),
    ('swe-swedish.osis.xml', 'Swedish', '', 'Swedish Bible', 'Public Domain', 5642249, 31131, ''),
    ('tgl-tagalog.osis.xml', 'Tagalog', '', 'Tagalog Bible (Ang Dating Biblia)', 'Public Domain', 6258591, 31102, ''),
    ('tha-thai.osis.xml', 'Thai', '', 'Thai Bible', 'Public Domain', 12345244, 31102, ''),
    ('tur-turkish.osis.xml', 'Turkish', '', 'Turkish Bible', 'Public Domain', 5201296, 30182, '65 books (incomplete)'),
    ('vie-cadman.osis.xml', 'Vietnamese', '', 'Vietnamese Cadman Bible 1934', 'Public Domain', 6500011, 31102, ''),
]


# Bibles from other places: (file, language, abbreviation, title, license, bytes, verses, note, address).
# The Ethiopian canon is assembled from public-domain texts by packaging/build_ethiopian.py and kept in
# BibleChat's own repository. The Amharic Bible comes straight from eBible.org, whose terms allow free,
# non-commercial use when the copyright notice is shown in full (it is, as the license text).
OWN = "https://raw.githubusercontent.com/beaugrand/BibleChat-voice/main/bibles/"
AMHARIC_NOTICE = ("Copyright © 1962, 2003 United Bible Societies. Used with the kind permission of the Bible "
                  "Society of Ethiopia; electronic text by the Lapsley/Brooks Foundation (1994) and Dirk Röckmann "
                  "(2003), via eBible.org. Free for non-commercial use with this notice; any commercial use needs "
                  "written permission of the Bible Society of Ethiopia.")
EXTRA: list[tuple[str, str, str, str, str, int, int, str, str]] = [
    ('eng-ethiopian-canon.zefania.xml', 'English', 'ETH', 'Ethiopian Canon (public-domain English)', 'Public Domain',
     6244619, 38590, '84 books of the Ethiopian Orthodox canon, incl. 1 Enoch, Jubilees, 2 Enoch, 1 Clement. '
     'Meqabyan I-III and 4 Baruch have no public-domain English translation yet',
     OWN + 'eng-ethiopian-canon.zefania.xml'),
    ('amh_usfx.zip', 'Amharic', 'AMH', 'Amharic Bible (1962)', AMHARIC_NOTICE, 0, 0,
     'The 1962 Haile Selassie Amharic Bible', 'https://ebible.org/Scriptures/amh_usfx.zip'),
]


def _all():
    return [(*row, BASE + row[0]) for row in CATALOG] + EXTRA


def entries() -> list[dict]:
    return [{"file": f, "language": lang, "abbr": ab, "title": t, "license": lic, "bytes": size, "verses": n,
             "note": note, "name": display_name(f)} for f, lang, ab, t, lic, size, n, note, _u in _all()]


def display_name(file: str) -> str:
    for f, _lang, ab, t, *_ in _all():
        if f == file:
            name = f"{ab} - {t}" if ab else t
            return name.replace("/", "-")  # the name doubles as a file name
    raise KeyError(file)


def url(file: str) -> str:
    for row in _all():   # only files on the list
        if row[0] == file:
            return row[-1]
    raise KeyError(file)


def unpack(file: str, data: bytes) -> tuple[str, bytes]:
    """A download that is a .zip (eBible.org) holds the Bible as USFX XML: return (file name, XML bytes)."""
    if not data[:2] == b"PK":
        return file, data
    import io
    import zipfile
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        xml = [n for n in z.namelist() if n.lower().endswith(".xml") and "metadata" not in n.lower()
               and not n.lower().endswith(("vernacularparms.xml", "bookNames.xml".lower()))]
        if not xml:
            raise ValueError("That download didn't contain a Bible.")
        best = max(xml, key=lambda n: z.getinfo(n).file_size)
        return best, z.read(best)
