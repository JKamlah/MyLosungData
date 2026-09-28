#!/usr/bin/env python3
"""
bibleserver_passages.py

Finds and links the corresponding Bible passages for all 60 translations available
on ERF Bibleserver (https://www.bibleserver.com/webmasters), using LUT (Lutherbibel 2017)
as the base edition from the Losungen dataset.

Supports generating:
1. `2026/bibleserver_passages.json` with complete mappings & links for all 60 translations.
2. `<year>/<Übersetzung>/text/Losungen_<year>.<übersetzung>.xml` directly in each translation's folder
   (e.g., `2026/ESV/text/Losungen_2026.esv.xml`, `2026/KJV/text/Losungen_2026.kjv.xml`, etc.).

Usage:
    # Generate links JSON & Markdown overview:
    python bibleserver_passages.py 2026

    # Generate XML files in the respective translation folders:
    python bibleserver_passages.py 2026 --xml ESV,KJV
    python bibleserver_passages.py 2026 --xml all

    # Single passage query:
    python bibleserver_passages.py --query "Jesaja 25,8"
"""

import argparse
import base64
import glob
import json
import os
import re
import sys
import time
import urllib.parse
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests

# 60 official Bibleserver translations as defined on https://www.bibleserver.com/webmasters
BIBLES = [
    {"abbr": "ESV", "name": "English Standard Version", "lang": "English", "locale": "en", "ot": True, "nt": True},
    {"abbr": "NIV", "name": "New International Version", "lang": "English", "locale": "en", "ot": True, "nt": True},
    {"abbr": "NIRV", "name": "New International Reader’s Version", "lang": "English", "locale": "en", "ot": True, "nt": True},
    {"abbr": "KJV", "name": "King James Version", "lang": "English", "locale": "en", "ot": True, "nt": True},
    {"abbr": "LUT", "name": "Lutherbibel 2017", "lang": "German", "locale": "de", "ot": True, "nt": True},
    {"abbr": "ELB", "name": "Elberfelder Bibel", "lang": "German", "locale": "de", "ot": True, "nt": True},
    {"abbr": "HFA", "name": "Hoffnung für alle", "lang": "German", "locale": "de", "ot": True, "nt": True},
    {"abbr": "SLT", "name": "Schlachter 2000", "lang": "German", "locale": "de", "ot": True, "nt": True},
    {"abbr": "GNB", "name": "Gute Nachricht Bibel 2018", "lang": "German", "locale": "de", "ot": True, "nt": True},
    {"abbr": "ZB", "name": "Zürcher Bibel", "lang": "German", "locale": "de", "ot": True, "nt": True},
    {"abbr": "NGÜ", "name": "Neue Genfer Übersetzung", "lang": "German", "locale": "de", "ot": True, "nt": True},
    {"abbr": "EU", "name": "Einheitsübersetzung 2016", "lang": "German", "locale": "de", "ot": True, "nt": True},
    {"abbr": "NLB", "name": "Neues Leben. Die Bibel", "lang": "German", "locale": "de", "ot": True, "nt": True},
    {"abbr": "NeÜ", "name": "Neue evangelistische Übersetzung", "lang": "German", "locale": "de", "ot": True, "nt": True},
    {"abbr": "MENG", "name": "Menge Bibel", "lang": "German", "locale": "de", "ot": True, "nt": True},
    {"abbr": "DBU", "name": "Das Buch", "lang": "German", "locale": "de", "ot": True, "nt": True},
    {"abbr": "VXB", "name": "VOLXBIBEL", "lang": "German", "locale": "de", "ot": True, "nt": True},
    {"abbr": "BDS", "name": "La Bible du Semeur", "lang": "French", "locale": "fr", "ot": True, "nt": True},
    {"abbr": "PEV", "name": "La Parola è Vita", "lang": "Italian", "locale": "it", "ot": True, "nt": True},
    {"abbr": "S21", "name": "Segond 21", "lang": "French", "locale": "fr", "ot": True, "nt": True},
    {"abbr": "LSG", "name": "Louis Segond 1910", "lang": "French", "locale": "fr", "ot": True, "nt": True},
    {"abbr": "NRS", "name": "Nuova Riveduta 2006", "lang": "Italian", "locale": "it", "ot": True, "nt": True},
    {"abbr": "HET", "name": "Het Boek", "lang": "Dutch", "locale": "nl", "ot": True, "nt": True},
    {"abbr": "NVIC", "name": "Nueva Versión Internacional (Castellano)", "lang": "Spanish", "locale": "es", "ot": True, "nt": True},
    {"abbr": "OL", "name": "O Livro", "lang": "Portuguese", "locale": "pt", "ot": True, "nt": True},
    {"abbr": "NVIP", "name": "Nova Versão Internacional", "lang": "Portuguese", "locale": "pt", "ot": True, "nt": True},
    {"abbr": "NVI", "name": "Nueva Versión Internacional", "lang": "Spanish", "locale": "es", "ot": True, "nt": True},
    {"abbr": "NBV", "name": "Nueva Biblia Viva", "lang": "Spanish", "locale": "es", "ot": True, "nt": True},
    {"abbr": "BTX", "name": "La Biblia Textual", "lang": "Spanish", "locale": "es", "ot": True, "nt": True},
    {"abbr": "NOR", "name": "En Levende Bok", "lang": "Norwegian", "locale": "no", "ot": True, "nt": True},
    {"abbr": "BSV", "name": "Nya Levande Bibeln", "lang": "Swedish", "locale": "sv", "ot": True, "nt": True},
    {"abbr": "NUB", "name": "nuBibeln", "lang": "Swedish", "locale": "sv", "ot": True, "nt": True},
    {"abbr": "BPH", "name": "Bibelen på hverdagsdansk", "lang": "Danish", "locale": "da", "ot": True, "nt": True},
    {"abbr": "PSZ", "name": "Słowo Życia", "lang": "Polish", "locale": "pl", "ot": True, "nt": True},
    {"abbr": "SNPD4", "name": "Pismo Święte Starego i Nowego Przymierza (dosłowny)", "lang": "Polish", "locale": "pl", "ot": True, "nt": True},
    {"abbr": "SNP", "name": "Pismo Święte Starego i Nowego Przymierza (literacki)", "lang": "Polish", "locale": "pl", "ot": True, "nt": True},
    {"abbr": "CEP", "name": "Český ekumenický překlad", "lang": "Czech", "locale": "cs", "ot": True, "nt": True},
    {"abbr": "SNC", "name": "Slovo na cestu", "lang": "Czech", "locale": "cs", "ot": True, "nt": True},
    {"abbr": "B21", "name": "Bible, překlad 21. století", "lang": "Czech", "locale": "cs", "ot": True, "nt": True},
    {"abbr": "BKR", "name": "Bible Kralická", "lang": "Czech", "locale": "cs", "ot": True, "nt": True},
    {"abbr": "NPK", "name": "Nádej pre kazdého", "lang": "Slovak", "locale": "sk", "ot": True, "nt": True},
    {"abbr": "KAR", "name": "IBS-fordítás (Új Károli)", "lang": "Hungarian", "locale": "hu", "ot": True, "nt": False},  # OT only
    {"abbr": "EIV", "name": "Újszövetség: élet, igazság és világosság", "lang": "Hungarian", "locale": "hu", "ot": False, "nt": True},  # NT only
    {"abbr": "NTR", "name": "Noua Traducere Românească", "lang": "Romanian", "locale": "ro", "ot": True, "nt": True},
    {"abbr": "BGV", "name": "Верен", "lang": "Bulgarian", "locale": "bg", "ot": True, "nt": True},
    {"abbr": "CBT", "name": "Съвременен български превод", "lang": "Bulgarian", "locale": "bg", "ot": True, "nt": True},
    {"abbr": "BPB", "name": "Библия, ревизирано издание", "lang": "Bulgarian", "locale": "bg", "ot": True, "nt": True},
    {"abbr": "BOB", "name": "Библия, синодално издание", "lang": "Bulgarian", "locale": "bg", "ot": True, "nt": True},
    {"abbr": "CKK", "name": "Knjiga O Kristu", "lang": "Croatian", "locale": "hr", "ot": True, "nt": True},
    {"abbr": "NRT", "name": "Новый Русский Перевод", "lang": "Russian", "locale": "ru", "ot": True, "nt": True},
    {"abbr": "CARS", "name": "Священное Писание, Восточный перевод", "lang": "Russian", "locale": "ru", "ot": True, "nt": True},
    {"abbr": "RST", "name": "Синодальный перевод", "lang": "Russian", "locale": "ru", "ot": True, "nt": True},
    {"abbr": "TR", "name": "Kutsal Kitap Yeni Çeviri", "lang": "Turkish", "locale": "tr", "ot": True, "nt": True},
    {"abbr": "NAV", "name": "الكتاب المقدس", "lang": "Arabic", "locale": "ar", "ot": True, "nt": True},
    {"abbr": "PCB", "name": "کتاب مقدس، ترجمۀ معاصر", "lang": "Persian", "locale": "fa", "ot": True, "nt": True},
    {"abbr": "CUVS", "name": "中文和合本（简体）", "lang": "Chinese (Simplified)", "locale": "zh_CN", "ot": True, "nt": True},
    {"abbr": "CCBT", "name": "聖經當代譯本修訂版", "lang": "Chinese (Simplified)", "locale": "zh_CN", "ot": True, "nt": True},
    {"abbr": "CCB", "name": "圣经当代译本修订版", "lang": "Chinese (Simplified)", "locale": "zh_CN", "ot": True, "nt": True},
    {"abbr": "NPU", "name": "Новий Переклад Українською", "lang": "Ukrainian", "locale": "uk", "ot": True, "nt": True},
    {"abbr": "UTT", "name": "Українська Біблія LXX УБТ", "lang": "Ukrainian", "locale": "uk", "ot": True, "nt": True},
]

BIBLES_BY_ABBR = {b["abbr"]: b for b in BIBLES}

GERMAN_BOOK_TO_ID = {
    '1. Mose': 1, '2. Mose': 2, '3. Mose': 3, '4. Mose': 4, '5. Mose': 5,
    'Josua': 6, 'Richter': 7, 'Rut': 8,
    '1. Samuel': 9, '2. Samuel': 10, '1. Könige': 11, '2. Könige': 12,
    '1. Chronik': 13, '2. Chronik': 14, 'Esra': 15, 'Nehemia': 16,
    'Ester': 17, 'Hiob': 18, 'Psalm': 19, 'Psalmen': 19, 'Sprüche': 20,
    'Prediger': 21, 'Hoheslied': 22, 'Hohelied': 22, 'Jesaja': 23,
    'Jeremia': 24, 'Klagelieder': 25, 'Hesekiel': 26, 'Ezechiel': 26,
    'Daniel': 27, 'Hosea': 28, 'Joel': 29, 'Amos': 30, 'Obadja': 31,
    'Jona': 32, 'Micha': 33, 'Nahum': 34, 'Habakuk': 35, 'Zefanja': 36,
    'Haggai': 37, 'Sacharja': 38, 'Maleachi': 39,
    'Matthäus': 40, 'Markus': 41, 'Lukas': 42, 'Johannes': 43,
    'Apostelgeschichte': 44, 'Römer': 45, '1. Korinther': 46, '2. Korinther': 47,
    'Galater': 48, 'Epheser': 49, 'Philipper': 50, 'Kolosser': 51,
    '1. Thessalonicher': 52, '2. Thessalonicher': 53,
    '1. Timotheus': 54, '2. Timotheus': 55, 'Titus': 56, 'Philemon': 57,
    'Hebräer': 58, 'Jakobus': 59, '1. Petrus': 60, '2. Petrus': 61,
    '1. Johannes': 62, '2. Johannes': 63, '3. Johannes': 64,
    'Judas': 65, 'Offenbarung': 66
}

PSALM_OFFSET_1 = {
    3, 4, 5, 6, 7, 8, 9, 12, 13, 18, 19, 20, 21, 22, 30, 31, 34, 36, 38, 39,
    40, 41, 42, 44, 45, 46, 47, 48, 49, 53, 54, 55, 56, 57, 58, 59, 61, 62,
    63, 64, 65, 67, 68, 69, 70, 75, 76, 77, 80, 81, 83, 84, 85, 88, 89, 92,
    102, 108, 140, 142
}
PSALM_OFFSET_2 = {51, 52, 60}

WEEKDAY_EN = {
    'Montag': 'Monday', 'Dienstag': 'Tuesday', 'Mittwoch': 'Wednesday',
    'Donnerstag': 'Thursday', 'Freitag': 'Friday', 'Samstag': 'Saturday', 'Sonntag': 'Sunday'
}

HOLIDAY_EN = {
    'Neujahr': "New Year's Day", 'Heiliger Abend': 'Christmas Eve', 'Weihnachtsfest': 'Christmas Day',
    '2. Weihnachtstag': 'Second Day of Christmas', 'Altjahresabend': "New Year's Eve",
    'Epiphanias': 'Epiphany', 'Gründonnerstag': 'Maundy Thursday', 'Karfreitag': 'Good Friday',
    'Osterfest': 'Easter Sunday', 'Ostermontag': 'Easter Monday', 'Christi Himmelfahrt': 'Ascension Day',
    'Pfingstfest': 'Pentecost', 'Pfingstmontag': 'Whit Monday', 'Trinitatis (Dreieinigkeit)': 'Trinity Sunday',
    'Erntedankfest': 'Harvest Festival / Thanksgiving', 'Reformationstag': 'Reformation Day',
    'Buss- und Bettag': 'Day of Repentance and Prayer', 'Johannistag': "St. John's Day", 'Michaelistag': 'Michaelmas'
}

HTTP_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
}


def load_locale_booknames(cache_dir: str):
    """Loads localized booknames from cache directory."""
    os.makedirs(cache_dir, exist_ok=True)
    loc_books = {}
    for filename in glob.glob(os.path.join(cache_dir, "*.json")):
        loc = os.path.splitext(os.path.basename(filename))[0]
        with open(filename, 'r', encoding='utf-8') as f:
            loc_books[loc] = json.load(f)
    return loc_books


def parse_lut_reference(ref_str: str):
    """Parses a German LUT reference like 'Jesaja 25,8' or 'Johannes 5,7-8'."""
    ref_str = ref_str.strip()
    m = re.match(r'^(?P<book>.+?)\s+(?P<chap>\d+),(?P<verses>[\d\.\-]+)$', ref_str)
    if not m:
        raise ValueError(f"Could not parse LUT reference: {ref_str}")

    book_de = m.group('book').strip()
    chap = int(m.group('chap'))
    verses_str = m.group('verses')

    if book_de not in GERMAN_BOOK_TO_ID:
        raise KeyError(f"Unknown German book name: '{book_de}'")

    book_id = GERMAN_BOOK_TO_ID[book_de]
    is_ot = book_id <= 39

    return book_id, book_de, chap, verses_str, is_ot


def format_passage_for_translation(bible_info: dict, book_id: int, chap: int, verses_str: str,
                                   loc_books: dict, book_de: str):
    """Builds the localized Bible passage string and Bibleserver links for a given translation."""
    abbr = bible_info['abbr']
    locale = bible_info['locale']
    is_ot = book_id <= 39

    if is_ot and not bible_info['ot']:
        return None
    if not is_ot and not bible_info['nt']:
        return None

    book_name = None
    if locale in loc_books and str(book_id) in loc_books[locale]:
        book_name = loc_books[locale][str(book_id)]
    if not book_name:
        book_name = book_de
    book_name = book_name.strip(" \u200c\u200b\r\n\t")

    target_verses_str = verses_str
    if bible_info['lang'] == 'English':
        offset = 0
        if book_id == 19:
            if chap in PSALM_OFFSET_2:
                offset = 2
            elif chap in PSALM_OFFSET_1:
                offset = 1
        elif book_id == 28 and chap == 2:
            offset = 2

        if offset > 0:
            if '-' in verses_str:
                start_v, end_v = map(int, verses_str.split('-'))
                target_verses_str = f"{max(1, start_v - offset)}-{max(1, end_v - offset)}"
            elif '.' in verses_str:
                target_verses_str = '.'.join(str(max(1, int(v) - offset)) for v in verses_str.split('.') if v)
            else:
                target_verses_str = str(max(1, int(verses_str) - offset))

    if locale == 'de':
        verse_formatted = target_verses_str
        sep = ','
        display_passage = f"{book_name} {chap}{sep}{verse_formatted}"
        url_passage = f"{book_name} {chap}{sep}{verse_formatted}".strip()
    else:
        verse_formatted = target_verses_str.replace('.', ',')
        display_passage = f"{book_name} {chap}:{verse_formatted}"
        url_passage = f"{book_name} {chap}:{target_verses_str}".strip()

    url_passage_encoded = urllib.parse.quote(url_passage, safe='/:,')

    direct_link = f"https://www.bibleserver.com/{abbr}/{url_passage_encoded}"
    lut_base_passage = f"{book_de}{chap},{verses_str}".replace(" ", "")
    lut_base_encoded = urllib.parse.quote(lut_base_passage, safe='/:,')
    compare_lut_link = f"https://www.bibleserver.com/LUT.{abbr}/{lut_base_encoded}"

    return {
        "translation": abbr,
        "name": bible_info['name'],
        "language": bible_info['lang'],
        "locale": locale,
        "passage": display_passage,
        "url_passage": url_passage,
        "link": direct_link,
        "compare_lut_link": compare_lut_link
    }


def clean_meta_text(meta_str: str) -> str:
    """Extracts and cleans verse text from Bibleserver's meta description tag."""
    # Remove trailing citation e.g. (Isa 25:8; ESV) or (Joh 3,16; LUT)
    text = re.sub(r'\s*\([^;()]+;\s*[^)]+\)\s*$', '', meta_str.strip())
    # Remove footnote markers
    text = re.sub(r'[*†]', '', text)
    # Remove surrounding quote marks
    text = text.strip('\"“”„«»')
    clean = ' '.join(text.split())
    if clean.lower() == 'undefined':
        return ''
    return clean


def split_url_passage_into_single_verses(url_passage: str) -> list[str]:
    """
    Splits multi-verse url_passages into individual single-verse queries.
    E.g.
    'James2:15-16' -> ['James2:15', 'James2:16']
    '1Corinthians15:55.57' -> ['1Corinthians15:55', '1Corinthians15:57']
    'Acts2:5.7.11' -> ['Acts2:5', 'Acts2:7', 'Acts2:11']
    'Jakobus2,15-16' -> ['Jakobus2,15', 'Jakobus2,16']
    'Isaiah25:8' -> ['Isaiah25:8']
    """
    if ':' in url_passage:
        prefix, verse_spec = url_passage.split(':', 1)
        sep = ':'
    elif ',' in url_passage:
        prefix, verse_spec = url_passage.split(',', 1)
        sep = ','
    else:
        return [url_passage]

    if '-' not in verse_spec and '.' not in verse_spec:
        return [url_passage]

    parts = verse_spec.split('.')
    verses = []
    for p in parts:
        if '-' in p:
            s_str, e_str = p.split('-', 1)
            if s_str.isdigit() and e_str.isdigit():
                verses.extend(range(int(s_str), int(e_str) + 1))
            else:
                return [url_passage]
        elif p.isdigit():
            verses.append(int(p))
        else:
            return [url_passage]

    if len(verses) <= 1:
        return [url_passage]

    return [f"{prefix}{sep}{v}" for v in verses]


def fetch_raw_single_verse(translation: str, single_url_passage: str, cache_dir: str) -> str:
    """Fetches a single verse from ERF Bibleserver and caches it."""
    slug = re.sub(r'[^A-Za-z0-9_\-\.]+', '_', single_url_passage)
    t_cache_dir = os.path.join(cache_dir, "verses", translation)
    os.makedirs(t_cache_dir, exist_ok=True)
    cache_file = os.path.join(t_cache_dir, f"{slug}.txt")

    if os.path.exists(cache_file):
        with open(cache_file, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if content:
                return content

    url = f"https://www.bibleserver.com/{translation}/" + urllib.parse.quote(single_url_passage, safe='/:,')
    for attempt in range(3):
        try:
            r = requests.get(url, headers=HTTP_HEADERS, timeout=12)
            if r.status_code == 200:
                m = re.search(r'<meta name="description" content="(.*?)">', r.text)
                if m:
                    verse_text = clean_meta_text(m.group(1))
                    with open(cache_file, "w", encoding="utf-8") as f:
                        f.write(verse_text)
                    return verse_text
        except Exception:
            time.sleep(1 + attempt)

    return ""


def fetch_verse_text_from_bibleserver(translation: str, url_passage: str, cache_dir: str) -> str:
    """
    Fetches verse text from ERF Bibleserver.
    For passages with multiple parts (e.g. James2:15-16), calls each verse individually,
    removes trailing [...] from all parts except the last one, and concatenates them together.
    """
    single_verses = split_url_passage_into_single_verses(url_passage)
    if len(single_verses) == 1:
        return fetch_raw_single_verse(translation, single_verses[0], cache_dir)

    slug = re.sub(r'[^A-Za-z0-9_\-\.]+', '_', url_passage)
    t_cache_dir = os.path.join(cache_dir, "verses", translation)
    os.makedirs(t_cache_dir, exist_ok=True)
    cache_file = os.path.join(t_cache_dir, f"{slug}.txt")

    # If already cached and valid (does NOT end with [...]), return cached
    if os.path.exists(cache_file):
        with open(cache_file, "r", encoding="utf-8") as f:
            cached = f.read().strip()
            if cached and not re.search(r'(\[\.{3,}\]|\[…\]|\.{3,}|…)\s*$', cached):
                return cached

    # Fetch each part individually
    part_texts = []
    for i, s_url in enumerate(single_verses):
        part_text = fetch_raw_single_verse(translation, s_url, cache_dir)
        is_last = (i == len(single_verses) - 1)
        if not is_last:
            # remove trailing [...] from intermediate parts
            part_text = re.sub(r'\s*(\[\.{3,}\]|\[…\]|\.{3,}|…)\s*$', '', part_text).strip()
        if part_text:
            part_texts.append(part_text)

    combined = ' '.join(part_texts)
    if combined:
        with open(cache_file, "w", encoding="utf-8") as f:
            f.write(combined)

    return combined


def generate_translation_xml(year_dir: str, year: str, trl_code: str, days_data: list, cache_dir: str, max_workers: int = 8):
    """
    Generates <year>/<Übersetzung>/text/Losungen_<year>.<übersetzung>.xml for the specified translation.
    """
    if trl_code.upper() == "LUT":
        print(f"Skipping LUT: Ground truth file in '{year_dir}/LUT/text/' is protected and must not be overwritten.")
        return

    b_info = BIBLES_BY_ABBR.get(trl_code)
    if not b_info:
        print(f"Error: Translation '{trl_code}' is not in the list of 60 translations.", file=sys.stderr)
        return

    out_text_dir = os.path.join(year_dir, trl_code, "text")
    os.makedirs(out_text_dir, exist_ok=True)
    out_xml_path = os.path.join(out_text_dir, f"Losungen_{year}.{trl_code.lower()}.xml")

    print(f"\n[XML] Generating: {out_xml_path} ({b_info['name']} / {b_info['lang']})...")

    # Collect passages that need to be fetched
    fetch_tasks = []
    for day in days_data:
        l_info = day["losung"]["translations"].get(trl_code)
        if l_info and l_info.get("url_passage"):
            fetch_tasks.append((day["date"], "losung", l_info["url_passage"]))

        lt_info = day["lehrtext"]["translations"].get(trl_code)
        if lt_info and lt_info.get("url_passage"):
            fetch_tasks.append((day["date"], "lehrtext", lt_info["url_passage"]))

    print(f"  Fetching verse texts for {len(fetch_tasks)} passages...")
    text_results = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_map = {
            executor.submit(fetch_verse_text_from_bibleserver, trl_code, item[2], cache_dir): item
            for item in fetch_tasks
        }
        done_count = 0
        for f in as_completed(future_map):
            dt, p_type, _ = future_map[f]
            txt = f.result()
            text_results[(dt, p_type)] = txt
            done_count += 1
            if done_count % 100 == 0 or done_count == len(fetch_tasks):
                print(f"    Progress: {done_count}/{len(fetch_tasks)} passages ready")

    # Build XML tree
    root = ET.Element("FreeXml", {"xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance"})

    for day in days_data:
        dt = day["date"]
        elem = ET.SubElement(root, "Losungen")

        # Datum
        ET.SubElement(elem, "Datum").text = f"{dt}T00:00:00.000"

        # Wtag (localized if English)
        wtag = day["weekday"]
        if b_info["lang"] == "English":
            wtag = WEEKDAY_EN.get(wtag, wtag)
        ET.SubElement(elem, "Wtag").text = wtag

        # Sonntag
        sonntag = day["sunday"]
        if sonntag:
            if b_info["lang"] == "English" and sonntag in HOLIDAY_EN:
                sonntag = HOLIDAY_EN[sonntag]
            ET.SubElement(elem, "Sonntag").text = sonntag

        # Losung
        l_info = day["losung"]["translations"].get(trl_code)
        l_text = text_results.get((dt, "losung"), "") or day["losung"]["text"]
        l_ref = l_info["passage"] if l_info else day["losung"]["base_ref"]

        ET.SubElement(elem, "Losungstext").text = l_text
        ET.SubElement(elem, "Losungsvers").text = l_ref

        # Lehrtext
        lt_info = day["lehrtext"]["translations"].get(trl_code)
        lt_text = text_results.get((dt, "lehrtext"), "") or day["lehrtext"]["text"]
        lt_ref = lt_info["passage"] if lt_info else day["lehrtext"]["base_ref"]

        ET.SubElement(elem, "Lehrtext").text = lt_text
        ET.SubElement(elem, "Lehrtextvers").text = lt_ref

    tree = ET.ElementTree(root)
    ET.indent(tree, space="\t", level=0)
    tree.write(out_xml_path, encoding='utf-8', xml_declaration=True)
    print(f"  -> Successfully generated: {out_xml_path}")


def process_losungen_bibleserver(year: str, base_dir: str = None):
    """Processes Losungen XML for a given year and generates BibleServer links for all 60 translations."""
    base_dir = base_dir or os.getcwd()
    year_dir = os.path.join(base_dir, str(year))

    xml_candidates = (
        glob.glob(os.path.join(year_dir, "LUT", "text", "*.xml")) +
        glob.glob(os.path.join(year_dir, "de", "text", "*.xml")) +
        glob.glob(os.path.join(year_dir, "text", "*.xml"))
    )

    if not xml_candidates:
        print(f"Error: No XML file found in {year_dir}/LUT/text/ or {year_dir}/de/text/", file=sys.stderr)
        sys.exit(1)

    source_xml = sorted(xml_candidates)[0]
    print(f"Reading base Losungen XML (LUT): {source_xml}")

    tree = ET.parse(source_xml)
    root = tree.getroot()
    losungen_elements = root.findall('.//Losungen')
    print(f"Loaded {len(losungen_elements)} daily entries.")

    cache_dir = os.path.join(base_dir, ".cache_bibleserver", "locales")
    loc_books = load_locale_booknames(cache_dir)
    print(f"Loaded localized book dictionaries for {len(loc_books)} locales.")

    days_data = []

    for item in losungen_elements:
        datum = item.findtext('Datum', '')[:10]
        wtag = item.findtext('Wtag', '')
        sonntag = item.findtext('Sonntag', '')

        lv_raw = item.findtext('Losungsvers', '').strip()
        lt_text = item.findtext('Losungstext', '').strip()

        ltv_raw = item.findtext('Lehrtextvers', '').strip()
        lehr_text = item.findtext('Lehrtext', '').strip()

        day_record = {
            "date": datum,
            "weekday": wtag,
            "sunday": sonntag,
            "losung": {
                "base_ref": lv_raw,
                "text": lt_text,
                "translations": {}
            },
            "lehrtext": {
                "base_ref": ltv_raw,
                "text": lehr_text,
                "translations": {}
            }
        }

        # Resolve OT Losung
        if lv_raw:
            try:
                b_id, b_de, chap, v_str, is_ot = parse_lut_reference(lv_raw)
                for b_info in BIBLES:
                    res = format_passage_for_translation(b_info, b_id, chap, v_str, loc_books, b_de)
                    if res:
                        day_record["losung"]["translations"][b_info["abbr"]] = res
            except Exception as e:
                print(f"Warning: Failed to parse Losungsvers '{lv_raw}' on {datum}: {e}", file=sys.stderr)

        # Resolve NT Lehrtext
        if ltv_raw:
            try:
                b_id, b_de, chap, v_str, is_ot = parse_lut_reference(ltv_raw)
                for b_info in BIBLES:
                    res = format_passage_for_translation(b_info, b_id, chap, v_str, loc_books, b_de)
                    if res:
                        day_record["lehrtext"]["translations"][b_info["abbr"]] = res
            except Exception as e:
                print(f"Warning: Failed to parse Lehrtextvers '{ltv_raw}' on {datum}: {e}", file=sys.stderr)

        days_data.append(day_record)

    out_json = os.path.join(year_dir, "bibleserver_passages.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(days_data, f, ensure_ascii=False, indent=2)
    print(f"Successfully generated Bibleserver passages JSON: {out_json}")

    out_md = os.path.join(year_dir, "bibleserver_overview.md")
    with open(out_md, "w", encoding="utf-8") as f:
        f.write(f"# Bibleserver Passages & Links {year}\n\n")
        f.write(f"Based on **LUT** (Lutherbibel 2017) with links to all 60 Bibleserver translations.\n\n")
        f.write("## Sample Entries\n\n")
        for day in days_data[:5]:
            f.write(f"### {day['date']} ({day['weekday']}" + (f", {day['sunday']}" if day['sunday'] else "") + ")\n")
            f.write(f"- **Losung (LUT):** {day['losung']['base_ref']} – *\"{day['losung']['text']}\"*\n")
            esv_l = day['losung']['translations'].get('ESV', {})
            kjv_l = day['losung']['translations'].get('KJV', {})
            f.write(f"  - **ESV:** [{esv_l.get('passage')}]({esv_l.get('link')}) | [LUT-Vergleich]({esv_l.get('compare_lut_link')})\n")
            f.write(f"  - **KJV:** [{kjv_l.get('passage')}]({kjv_l.get('link')}) | [LUT-Vergleich]({kjv_l.get('compare_lut_link')})\n")
            f.write(f"- **Lehrtext (LUT):** {day['lehrtext']['base_ref']} – *\"{day['lehrtext']['text']}\"*\n")
            esv_lt = day['lehrtext']['translations'].get('ESV', {})
            kjv_lt = day['lehrtext']['translations'].get('KJV', {})
            f.write(f"  - **ESV:** [{esv_lt.get('passage')}]({esv_lt.get('link')}) | [LUT-Vergleich]({esv_lt.get('compare_lut_link')})\n")
            f.write(f"  - **KJV:** [{kjv_lt.get('passage')}]({kjv_lt.get('link')}) | [LUT-Vergleich]({kjv_lt.get('compare_lut_link')})\n\n")
    print(f"Wrote Markdown sample overview: {out_md}")

    return days_data


def query_passage(query_ref: str, cache_dir: str):
    """Interactive / CLI query of a single LUT reference across all 60 translations."""
    loc_books = load_locale_booknames(cache_dir)
    b_id, b_de, chap, v_str, is_ot = parse_lut_reference(query_ref)
    print(f"\nPassage Query: '{query_ref}' (LUT base -> Book #{b_id})\n" + "=" * 70)
    for b_info in BIBLES:
        res = format_passage_for_translation(b_info, b_id, chap, v_str, loc_books, b_de)
        if res:
            print(f"[{res['translation']:6}] ({res['language']:18}): {res['passage']:25} -> {res['link']}")
        else:
            print(f"[{b_info['abbr']:6}] ({b_info['lang']:18}): (Not available in this testament)")


def main():
    parser = argparse.ArgumentParser(description="Find and link Bible passages across all 60 Bibleserver translations using LUT as base.")
    parser.add_argument("year", nargs="?", default="2026", help="Year of the Losungen dataset (e.g. 2026)")
    parser.add_argument("--xml", help="Generate XML files for translations: comma-separated list (e.g. 'ESV,KJV,ELB') or 'all'")
    parser.add_argument("--query", "-q", help="Query a single German LUT passage (e.g. 'Jesaja 25,8')")
    parser.add_argument("--date", "-d", help="Inspect Bible passages for a specific date (e.g. 2026-01-01)")
    parser.add_argument("--translation", "-t", help="Show all passages for a specific translation (e.g. ESV, KJV, LSG)")

    args = parser.parse_args()
    base_dir = os.getcwd()
    cache_dir = os.path.join(base_dir, ".cache_bibleserver")
    locales_cache = os.path.join(cache_dir, "locales")

    if args.query:
        query_passage(args.query, locales_cache)
        return

    data = process_losungen_bibleserver(args.year, base_dir)

    # XML generation if requested
    if args.xml:
        year_dir = os.path.join(base_dir, str(args.year))
        target_trls = []
        if args.xml.strip().lower() in ("all", "*"):
            target_trls = [b["abbr"] for b in BIBLES if b["abbr"] != "LUT"]
        else:
            target_trls = [t.strip().upper() for t in args.xml.split(",") if t.strip() and t.strip().upper() != "LUT"]

        for trl in target_trls:
            generate_translation_xml(year_dir, str(args.year), trl, data, cache_dir)

    if args.date:
        for day in data:
            if day['date'] == args.date:
                print(f"\nDate: {day['date']} ({day['weekday']})")
                print(f"Losung: {day['losung']['base_ref']} – {day['losung']['text']}")
                print(f"Lehrtext: {day['lehrtext']['base_ref']} – {day['lehrtext']['text']}\n")
                trl_code = args.translation or "ESV"
                l_res = day['losung']['translations'].get(trl_code)
                lt_res = day['lehrtext']['translations'].get(trl_code)
                if l_res:
                    print(f"  [{trl_code}] Losung:   {l_res['passage']} -> {l_res['link']}")
                if lt_res:
                    print(f"  [{trl_code}] Lehrtext: {lt_res['passage']} -> {lt_res['link']}")
                return


if __name__ == '__main__':
    main()
