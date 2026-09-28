#!/usr/bin/env python3
"""
generate_losungen.py

Processes Losungen data for a given year:
1. Reads the German XML from <year>/de/text/
2. Looks up all passages in the King James Version (KJV) via die-bibel.de (e.g. https://www.die-bibel.de/bibel/KJV/GEN.1)
3. Produces the English XML in <year>/en/text/
4. Optionally generates audio files for both German and English versions using the Gemini API (TTS).

Usage:
    python generate_losungen.py 2026
    python generate_losungen.py 2026 --api-key YOUR_GEMINI_KEY --generate-audio --days 5
    python generate_losungen.py 2026 --generate-audio --audio-lang en
"""

import argparse
import base64
import glob
import json
import os
import re
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed

# Mapping of German book names in Losungen to USFM codes and English names
BOOK_MAP = {
    '1. Chronik': ('1CH', '1 Chronicles'),
    '2. Chronik': ('2CH', '2 Chronicles'),
    '1. Johannes': ('1JN', '1 John'),
    '2. Johannes': ('2JN', '2 John'),
    '3. Johannes': ('3JN', '3 John'),
    '1. Korinther': ('1CO', '1 Corinthians'),
    '2. Korinther': ('2CO', '2 Corinthians'),
    '1. Könige': ('1KI', '1 Kings'),
    '2. Könige': ('2KI', '2 Kings'),
    '1. Mose': ('GEN', 'Genesis'),
    '2. Mose': ('EXO', 'Exodus'),
    '3. Mose': ('LEV', 'Leviticus'),
    '4. Mose': ('NUM', 'Numbers'),
    '5. Mose': ('DEU', 'Deuteronomy'),
    '1. Petrus': ('1PE', '1 Peter'),
    '2. Petrus': ('2PE', '2 Peter'),
    '1. Samuel': ('1SA', '1 Samuel'),
    '2. Samuel': ('2SA', '2 Samuel'),
    '1. Thessalonicher': ('1TH', '1 Thessalonians'),
    '2. Thessalonicher': ('2TH', '2 Thessalonians'),
    '1. Timotheus': ('1TI', '1 Timothy'),
    '2. Timotheus': ('2TI', '2 Timothy'),
    'Amos': ('AMO', 'Amos'),
    'Apostelgeschichte': ('ACT', 'Acts'),
    'Daniel': ('DAN', 'Daniel'),
    'Epheser': ('EPH', 'Ephesians'),
    'Esra': ('EZR', 'Ezra'),
    'Ester': ('EST', 'Esther'),
    'Galater': ('GAL', 'Galatians'),
    'Habakuk': ('HAB', 'Habakkuk'),
    'Haggai': ('HAG', 'Haggai'),
    'Hebräer': ('HEB', 'Hebrews'),
    'Hesekiel': ('EZK', 'Ezekiel'),
    'Ezechiel': ('EZK', 'Ezekiel'),
    'Hiob': ('JOB', 'Job'),
    'Hosea': ('HOS', 'Hosea'),
    'Hoheslied': ('SNG', 'Song of Solomon'),
    'Hohelied': ('SNG', 'Song of Solomon'),
    'Jakobus': ('JAS', 'James'),
    'Jeremia': ('JER', 'Jeremiah'),
    'Jesaja': ('ISA', 'Isaiah'),
    'Joel': ('JOL', 'Joel'),
    'Johannes': ('JHN', 'John'),
    'Jona': ('JON', 'Jonah'),
    'Josua': ('JOS', 'Joshua'),
    'Judas': ('JUD', 'Jude'),
    'Klagelieder': ('LAM', 'Lamentations'),
    'Kolosser': ('COL', 'Colossians'),
    'Lukas': ('LUK', 'Luke'),
    'Maleachi': ('MAL', 'Malachi'),
    'Markus': ('MRK', 'Mark'),
    'Matthäus': ('MAT', 'Matthew'),
    'Micha': ('MIC', 'Micah'),
    'Nahum': ('NAM', 'Nahum'),
    'Nehemia': ('NEH', 'Nehemiah'),
    'Obadja': ('OBA', 'Obadiah'),
    'Offenbarung': ('REV', 'Revelation'),
    'Philipper': ('PHP', 'Philippians'),
    'Philemon': ('PHM', 'Philemon'),
    'Prediger': ('ECC', 'Ecclesiastes'),
    'Psalm': ('PSA', 'Psalm'),
    'Psalmen': ('PSA', 'Psalm'),
    'Richter': ('JDG', 'Judges'),
    'Rut': ('RUT', 'Ruth'),
    'Römer': ('ROM', 'Romans'),
    'Sacharja': ('ZEC', 'Zechariah'),
    'Sprüche': ('PRO', 'Proverbs'),
    'Titus': ('TIT', 'Titus'),
    'Zefanja': ('ZEP', 'Zephaniah')
}

# Weekday translations
WEEKDAY_MAP = {
    'Montag': 'Monday',
    'Dienstag': 'Tuesday',
    'Mittwoch': 'Wednesday',
    'Donnerstag': 'Thursday',
    'Freitag': 'Friday',
    'Samstag': 'Saturday',
    'Sonntag': 'Sunday',
}

# Month names for spoken audio
MONTH_NAMES_DE = ['', 'Januar', 'Februar', 'März', 'April', 'Mai', 'Juni', 'Juli', 'August', 'September', 'Oktober', 'November', 'Dezember']
MONTH_NAMES_EN = ['', 'January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']

# Ecclesiastical Sunday & holiday translations
HOLIDAY_MAP = {
    'Neujahr': "New Year's Day",
    'Heiliger Abend': 'Christmas Eve',
    'Weihnachtsfest': 'Christmas Day',
    '2. Weihnachtstag': 'Second Day of Christmas',
    'Altjahresabend': "New Year's Eve",
    'Epiphanias': 'Epiphany',
    'Gründonnerstag': 'Maundy Thursday',
    'Karfreitag': 'Good Friday',
    'Osterfest': 'Easter Sunday',
    'Ostermontag': 'Easter Monday',
    'Christi Himmelfahrt': 'Ascension Day',
    'Pfingstfest': 'Pentecost',
    'Pfingstmontag': 'Whit Monday',
    'Trinitatis (Dreieinigkeit)': 'Trinity Sunday',
    'Erntedankfest': 'Harvest Festival / Thanksgiving',
    'Reformationstag': 'Reformation Day',
    'Buss- und Bettag': 'Day of Repentance and Prayer',
    'Johannistag': "St. John's Day",
    'Michaelistag': 'Michaelmas',
    'Drittletzter Sonntag des Kirchenjahres': 'Third-last Sunday of the Church Year',
    'Vorletzter Sonntag des Kirchenjahres': 'Penultimate Sunday of the Church Year',
    'Letzter Sonntag des Kirchenjahres – Ewigkeitssonntag': 'Last Sunday of the Church Year – Eternity Sunday',
    'Letzter Sonntag nach Epiphanias': 'Last Sunday after Epiphany',
}

# Standard Psalm offset rules (Hebrew/Luther versification vs KJV)
# In KJV, psalm superscriptions are not given verse numbers.
# In chapters with offset 1, KJV verse = Luther verse - 1.
PSALM_OFFSET_1 = {
    3, 4, 5, 6, 7, 8, 9, 12, 13, 18, 19, 20, 21, 22, 30, 31, 34, 36, 38, 39,
    40, 41, 42, 44, 45, 46, 47, 48, 49, 53, 54, 55, 56, 57, 58, 59, 61, 62,
    63, 64, 65, 67, 68, 69, 70, 75, 76, 77, 80, 81, 83, 84, 85, 88, 89, 92,
    102, 108, 140, 142
}
# Chapters with offset 2 (long historical titles spanning 2 verses in MT):
PSALM_OFFSET_2 = {51, 52, 60}

HTTP_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1',
    'Upgrade-Insecure-Requests': '1'
}


def clean_verse_text(text: str) -> str:
    """Cleans verse text extracted from die-bibel.de."""
    # Remove Hebrew characters if present
    text = re.sub(r'[\u0590-\u05FF]+', '', text)
    # Remove trailing Hebrew acrostic names (e.g. Aleph, Beth...)
    acrostics = r'\b(Aleph|Beth|Gimel|Daleth|He|Vau|Zain|Cheth|Teth|Tet|Jod|Yod|Caph|Lamed|Mem|Nun|Samech|Ain|Pe|Tzaddi|Koph|Resh|Schin|Shin|Tau|Taw)\b'
    text = re.sub(rf'\s+{acrostics}\s*$', '', text)
    # Ensure space after punctuation if followed directly by a letter (poetry line splits)
    text = re.sub(r'([,;:])([A-Za-z])', r'\1 \2', text)
    # Normalize whitespace
    return ' '.join(text.split())


def translate_sunday(de_sunday: str) -> str:
    """Translates German church year Sunday / holiday string into English."""
    if not de_sunday:
        return ''
    s = de_sunday.strip()
    if s in HOLIDAY_MAP:
        return HOLIDAY_MAP[s]

    # Pattern: N. Sonntag im Advent -> Nth Sunday of Advent
    m = re.match(r'^(\d+)\.\s+Sonntag im Advent', s)
    if m:
        n = m.group(1)
        suffix = 'th' if n in ('4', '5') else {'1': 'st', '2': 'nd', '3': 'rd'}.get(n, 'th')
        return f'{n}{suffix} Sunday of Advent'

    # Pattern: N. Sonntag nach Weihnachten -> Nth Sunday after Christmas
    m = re.match(r'^(\d+)\.\s+Sonntag nach Weihnachten', s)
    if m:
        n = m.group(1)
        suffix = {'1': 'st', '2': 'nd', '3': 'rd'}.get(n, 'th')
        return f'{n}{suffix} Sunday after Christmas'

    # Pattern: N. Sonntag nach Epiphanias -> Nth Sunday after Epiphany
    m = re.match(r'^(\d+)\.\s+Sonntag nach Epiphanias', s)
    if m:
        n = m.group(1)
        suffix = {'1': 'st', '2': 'nd', '3': 'rd'}.get(n, 'th')
        return f'{n}{suffix} Sunday after Epiphany'

    # Pattern: N. Sonntag nach Trinitatis -> Nth Sunday after Trinity
    m = re.match(r'^(\d+)\.\s+Sonntag nach Trinitatis(.*)', s)
    if m:
        n = m.group(1)
        extra = m.group(2)
        suffix = 'th' if int(n) >= 4 and int(n) <= 20 else {'1': 'st', '2': 'nd', '3': 'rd'}.get(n[-1], 'th')
        res = f'{n}{suffix} Sunday after Trinity'
        if 'Israelsonntag' in extra:
            res += ' (Israel Sunday)'
        return res

    # Pattern: N. Sonntag der Passionszeit -> Nth Sunday in Lent
    m = re.match(r'^(\d+)\.\s+Sonntag der Passionszeit\s*–?\s*(.*)', s)
    if m:
        n = m.group(1)
        suffix = {'1': 'st', '2': 'nd', '3': 'rd', '4': 'th', '5': 'th', '6': 'th'}.get(n, 'th')
        rest = m.group(2).strip()
        return f'{n}{suffix} Sunday in Lent' + (f' – {rest}' if rest else '')

    # Pattern: N. Sonntag nach Ostern -> Nth Sunday of Easter
    m = re.match(r'^(\d+)\.\s+Sonntag nach Ostern\s*–?\s*(.*)', s)
    if m:
        n = m.group(1)
        suffix = {'1': 'st', '2': 'nd', '3': 'rd', '4': 'th', '5': 'th', '6': 'th'}.get(n, 'th')
        rest = m.group(2).strip()
        return f'{n}{suffix} Sunday of Easter' + (f' – {rest}' if rest else '')

    return s


class KJVChapterCache:
    """Fetches and caches KJV Bible chapters from die-bibel.de."""

    def __init__(self, cache_dir: str):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        self._memory_cache = {}

    def get_chapter(self, book_code: str, chapter_num: int) -> dict:
        key = (book_code, chapter_num)
        if key in self._memory_cache:
            return self._memory_cache[key]

        disk_path = os.path.join(self.cache_dir, f'{book_code}_{chapter_num}.json')
        if os.path.exists(disk_path):
            with open(disk_path, 'r', encoding='utf-8') as f:
                verses = {int(k): v for k, v in json.load(f).items()}
                self._memory_cache[key] = verses
                return verses

        verses = self._fetch_remote(book_code, chapter_num)
        if verses:
            with open(disk_path, 'w', encoding='utf-8') as f:
                json.dump(verses, f, ensure_ascii=False)
        self._memory_cache[key] = verses
        return verses

    def _fetch_remote(self, book_code: str, chapter_num: int) -> dict:
        url = f'https://www.die-bibel.de/bibel/KJV/{book_code}.{chapter_num}'
        for attempt in range(3):
            try:
                req = urllib.request.Request(url, headers=HTTP_HEADERS)
                with urllib.request.urlopen(req, timeout=15) as resp:
                    html = resp.read().decode('utf-8')

                match = re.search(r'<script id="IBEP-main-state" type="application/json">(.*?)</script>', html)
                if not match:
                    return {}

                data = json.loads(match.group(1))
                verses = {}
                for k, v in data.items():
                    if f'chapters/{book_code}.{chapter_num}/with-study-content' in k:
                        chapter_obj = v['data']['chapter']

                        def extract_content(items):
                            for it in items:
                                if it.get('type') == 'verse-text':
                                    vid = it.get('verseId')
                                    if vid:
                                        v_num = int(vid.split('.')[-1])
                                        verses[v_num] = verses.get(v_num, '') + it.get('content', '')
                                if 'content' in it and isinstance(it['content'], list):
                                    extract_content(it['content'])

                        extract_content(chapter_obj.get('content', []))

                for v_num in verses:
                    verses[v_num] = clean_verse_text(verses[v_num])

                return verses
            except Exception as e:
                time.sleep(1 + attempt)

        print(f"[Warning] Failed to fetch {url}", file=sys.stderr)
        return {}


def parse_german_reference(ref_str: str):
    """
    Parses German reference like:
      'Jesaja 25,8'
      'Johannes 5,7-8'
      'Psalm 107,3.8'
      'Apostelgeschichte 2,5.7.11'
    Returns (book_de, chapter_int, list_of_verse_ints, raw_verses_part)
    """
    ref_str = ref_str.strip()
    m = re.match(r'^(?P<book>.+?)\s+(?P<chap>\d+),(?P<verses>[\d\.\-]+)$', ref_str)
    if not m:
        raise ValueError(f"Unrecognized reference format: {ref_str}")

    book_de = m.group('book').strip()
    chap = int(m.group('chap'))
    verses_str = m.group('verses')

    verse_list = []
    # Check for range: '7-8'
    if '-' in verses_str:
        start_v, end_v = map(int, verses_str.split('-'))
        verse_list = list(range(start_v, end_v + 1))
    elif '.' in verses_str:
        # Dot list: '3.8' or '5.7.11'
        verse_list = [int(v) for v in verses_str.split('.') if v]
    else:
        verse_list = [int(verses_str)]

    return book_de, chap, verse_list, verses_str


def resolve_kjv_passage(cache: KJVChapterCache, ref_de: str, de_text: str = ''):
    """
    Resolves the English KJV text and English reference string.
    Takes care of versification offsets between German Luther and KJV.
    """
    book_de, chap, verse_list, raw_verses = parse_german_reference(ref_de)
    if book_de not in BOOK_MAP:
        raise KeyError(f"Unknown book: {book_de}")

    book_code, book_en = BOOK_MAP[book_de]

    # Calculate versification offset
    offset = 0
    target_chap = chap

    if book_code == 'PSA':
        if chap in PSALM_OFFSET_2:
            offset = 2
        elif chap in PSALM_OFFSET_1:
            offset = 1
    elif book_code == 'HOS' and chap == 2 and verse_list[0] >= 3:
        offset = 2

    # Map target verses in KJV
    kjv_verses_needed = [v - offset for v in verse_list]

    chapter_data = cache.get_chapter(book_code, target_chap)

    # Collect verse texts
    texts = []
    for kv in kjv_verses_needed:
        if kv in chapter_data:
            texts.append(chapter_data[kv])
        else:
            # Fallback if unshifted verse exists
            if kv + offset in chapter_data and offset != 0:
                texts.append(chapter_data[kv + offset])

    joined_text = ' '.join(texts)

    # Format English reference
    # If range: 7-8 -> 7-8
    # If dot list: 3.8 -> 3,8
    if '-' in raw_verses:
        v_str = f"{kjv_verses_needed[0]}-{kjv_verses_needed[-1]}"
    elif '.' in raw_verses:
        v_str = ','.join(str(v) for v in kjv_verses_needed)
    else:
        v_str = str(kjv_verses_needed[0])

    ref_en = f"{book_en} {target_chap}:{v_str}"
    return joined_text, ref_en


def prefetch_all_chapters(cache: KJVChapterCache, root_xml: ET.Element, max_workers: int = 6):
    """Finds all unique (book_code, chapter) pairs and downloads them in parallel."""
    needed = set()
    for item in root_xml.findall('.//Losungen'):
        for tag in ('Losungsvers', 'Lehrtextvers'):
            v = item.findtext(tag)
            if v:
                book_de, chap, _, _ = parse_german_reference(v)
                if book_de in BOOK_MAP:
                    code, _ = BOOK_MAP[book_de]
                    needed.add((code, chap))

    print(f"Checking / downloading {len(needed)} Bible chapters from die-bibel.de...")
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(cache.get_chapter, code, chap): (code, chap) for code, chap in needed}
        completed = 0
        for f in as_completed(futures):
            f.result()
            completed += 1
            if completed % 50 == 0 or completed == len(needed):
                print(f"  Progress: {completed}/{len(needed)} chapters ready")


def generate_english_xml(source_xml_path: str, target_xml_path: str, cache: KJVChapterCache):
    """Reads German XML and writes English XML with KJV verses."""
    print(f"Parsing German XML: {source_xml_path}")
    tree = ET.parse(source_xml_path)
    root = tree.getroot()

    prefetch_all_chapters(cache, root)

    print("Generating English dataset with KJV passages...")
    losungen_elements = root.findall('.//Losungen')
    total = len(losungen_elements)

    for i, item in enumerate(losungen_elements):
        # 1. Weekday
        wtag_elem = item.find('Wtag')
        if wtag_elem is not None and wtag_elem.text:
            wtag_elem.text = WEEKDAY_MAP.get(wtag_elem.text.strip(), wtag_elem.text)

        # 2. Sonntag / Holiday
        sonntag_elem = item.find('Sonntag')
        if sonntag_elem is not None and sonntag_elem.text:
            sonntag_elem.text = translate_sunday(sonntag_elem.text)

        # 3. Watchword (Losung)
        lv_elem = item.find('Losungsvers')
        lt_text_elem = item.find('Losungstext')
        if lv_elem is not None and lv_elem.text:
            de_ref = lv_elem.text.strip()
            de_t = lt_text_elem.text.strip() if (lt_text_elem is not None and lt_text_elem.text) else ''
            kjv_text, kjv_ref = resolve_kjv_passage(cache, de_ref, de_t)
            if lt_text_elem is not None:
                lt_text_elem.text = kjv_text
            lv_elem.text = kjv_ref

        # 4. Doctrinal text (Lehrtext)
        ltv_elem = item.find('Lehrtextvers')
        lt_body_elem = item.find('Lehrtext')
        if ltv_elem is not None and ltv_elem.text:
            de_ref = ltv_elem.text.strip()
            de_t = lt_body_elem.text.strip() if (lt_body_elem is not None and lt_body_elem.text) else ''
            kjv_text, kjv_ref = resolve_kjv_passage(cache, de_ref, de_t)
            if lt_body_elem is not None:
                lt_body_elem.text = kjv_text
            ltv_elem.text = kjv_ref

    os.makedirs(os.path.dirname(target_xml_path), exist_ok=True)
    ET.indent(tree, space="\t", level=0)
    tree.write(target_xml_path, encoding='utf-8', xml_declaration=True)
    print(f"Successfully wrote English XML with {total} entries: {target_xml_path}")


def synthesize_gemini_audio(client, text: str, voice: str, language_code: str = "en") -> bytes:
    """Calls Gemini API to produce WAV audio from text."""
    # Attempt 1: Gemini 3.8 Flash TTS via interactions API
    try:
        interaction = client.interactions.create(
            model="gemini-3.8-flash-tts",
            input=[{
                "type": "user_input",
                "content": [{
                    "type": "text",
                    "text": text,
                }],
            }],
            response_format={"type": "audio"},
            generation_config={
                "speech_config": [
                    {"voice": voice}
                ]
            }
        )
        if interaction.output_audio and interaction.output_audio.data:
            return base64.b64decode(interaction.output_audio.data)
    except Exception as e:
        pass

    # Attempt 2: gemini-2.5-flash with AUDIO modality via generate_content
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=f"Read aloud clearly and solemnly in {language_code}:\n\n{text}",
            config={
                "response_modalities": ["AUDIO"],
                "speech_config": {
                    "voice_config": {
                        "prebuilt_voice_config": {
                            "voice_name": voice
                        }
                    }
                }
            }
        )
        for part in response.candidates[0].content.parts:
            if hasattr(part, 'inline_data') and part.inline_data:
                return part.inline_data.data
    except Exception as e:
        raise RuntimeError(f"Gemini TTS generation failed: {e}")

    raise RuntimeError("No audio data returned from Gemini API")


def create_audio_prompt_de(item: ET.Element) -> str:
    """Builds spoken narration text for German Losung."""
    datum = item.findtext('Datum', '')[:10]  # YYYY-MM-DD
    wtag = item.findtext('Wtag', '')
    sonntag = item.findtext('Sonntag', '')
    lt = item.findtext('Losungstext', '')
    lv = item.findtext('Losungsvers', '')
    lehrt = item.findtext('Lehrtext', '')
    lehrv = item.findtext('Lehrtextvers', '')

    parts = []
    if datum:
        y, m, d = datum.split('-')
        month_de = MONTH_NAMES_DE[int(m)]
        day_num = int(d)
        date_str = f"Die Losung für {wtag}, den {day_num}. {month_de} {y}"
        if sonntag:
            date_str += f", {sonntag}"
        parts.append(date_str + ".")
    parts.append(f"{lt} {lv}.")
    parts.append(f"Der Lehrtext: {lehrt} {lehrv}.")
    return " ".join(parts)


def create_audio_prompt_en(item: ET.Element) -> str:
    """Builds spoken narration text for English Watchword."""
    datum = item.findtext('Datum', '')[:10]  # YYYY-MM-DD
    wtag = item.findtext('Wtag', '')
    sonntag = item.findtext('Sonntag', '')
    lt = item.findtext('Losungstext', '')
    lv = item.findtext('Losungsvers', '')
    lehrt = item.findtext('Lehrtext', '')
    lehrv = item.findtext('Lehrtextvers', '')

    parts = []
    if datum:
        y, m, d = datum.split('-')
        month_en = MONTH_NAMES_EN[int(m)]
        day_num = int(d)
        date_str = f"Daily Watchword for {wtag}, {month_en} {day_num}, {y}"
        if sonntag:
            date_str += f", {sonntag}"
        parts.append(date_str + ".")
    parts.append(f"{lt} {lv}.")
    parts.append(f"Doctrinal text: {lehrt} {lehrv}.")
    return " ".join(parts)


def generate_audio_files(year_dir: str, lang: str, api_key: str, days_limit: int = None,
                         voice_de: str = "Kore", voice_en: str = "Puck", force: bool = False):
    """Generates audio files for German and/or English Losungen."""
    try:
        from google import genai
    except ImportError:
        print("[Error] 'google-genai' is required for audio generation. Install with: pip install google-genai", file=sys.stderr)
        return

    client = genai.Client(api_key=api_key)

    languages_to_do = []
    if lang in ('de', 'both', 'all'):
        languages_to_do.append(('de', voice_de, create_audio_prompt_de))
    if lang in ('en', 'both', 'all'):
        languages_to_do.append(('en', voice_en, create_audio_prompt_en))

    for lang_code, voice, prompt_fn in languages_to_do:
        xml_pattern = os.path.join(year_dir, lang_code, 'text', '*.xml')
        files = glob.glob(xml_pattern)
        if not files:
            print(f"[Warning] No XML file found at {xml_pattern}. Skipping {lang_code} audio.")
            continue

        xml_file = sorted(files)[0]
        tree = ET.parse(xml_file)
        items = tree.getroot().findall('.//Losungen')
        if days_limit:
            items = items[:days_limit]

        out_audio_dir = os.path.join(year_dir, lang_code, 'audio')
        os.makedirs(out_audio_dir, exist_ok=True)

        print(f"Generating audio for {len(items)} days [{lang_code.upper()}] with voice '{voice}' -> {out_audio_dir}...")
        for idx, item in enumerate(items, 1):
            datum = item.findtext('Datum', f'day_{idx}')[:10]
            out_file = os.path.join(out_audio_dir, f"{datum}.wav")

            if os.path.exists(out_file) and not force:
                continue

            speech_text = prompt_fn(item)
            try:
                audio_bytes = synthesize_gemini_audio(client, speech_text, voice, language_code=lang_code)
                with open(out_file, 'wb') as f:
                    f.write(audio_bytes)
                print(f"  [{idx}/{len(items)}] {datum}.wav ({len(audio_bytes)} bytes)")
            except Exception as e:
                print(f"  [{idx}/{len(items)}] Failed for {datum}: {e}", file=sys.stderr)
            time.sleep(0.5)


def main():
    parser = argparse.ArgumentParser(description="Process Losungen XML and produce English KJV version and Gemini audio.")
    parser.add_argument("year", nargs="?", default="2026", help="Year to process (e.g. 2026)")
    parser.add_argument("--api-key", default=os.environ.get("GEMINI_API_KEY", ""), help="Gemini API Key")
    parser.add_argument("--skip-xml", action="store_true", help="Skip generating the English XML")
    parser.add_argument("--generate-audio", action="store_true", help="Generate audio files with Gemini TTS")
    parser.add_argument("--audio-lang", choices=["all", "both", "de", "en"], default="both", help="Languages for audio generation")
    parser.add_argument("--days", type=int, default=None, help="Limit audio generation to the first N days")
    parser.add_argument("--voice-de", default="Kore", help="Gemini TTS voice for German (e.g. Kore, Fenrir, Puck)")
    parser.add_argument("--voice-en", default="Puck", help="Gemini TTS voice for English (e.g. Puck, Kore, Aoede)")
    parser.add_argument("--force", action="store_true", help="Overwrite existing audio files")

    args = parser.parse_args()
    year = str(args.year)
    year_dir = os.path.join(os.getcwd(), year)
    de_text_dir = os.path.join(year_dir, "de", "text")

    if not os.path.exists(de_text_dir):
        print(f"Error: Directory {de_text_dir} does not exist.", file=sys.stderr)
        sys.exit(1)

    xml_files = glob.glob(os.path.join(de_text_dir, "*.xml"))
    if not xml_files:
        print(f"Error: No XML files found in {de_text_dir}.", file=sys.stderr)
        sys.exit(1)

    source_xml = sorted(xml_files)[0]
    filename = os.path.basename(source_xml)
    en_text_dir = os.path.join(year_dir, "en", "text")
    target_xml = os.path.join(en_text_dir, filename)

    cache_dir = os.path.join(year_dir, ".cache_kjv")
    cache = KJVChapterCache(cache_dir)

    # 1. XML Generation
    if not args.skip_xml:
        generate_english_xml(source_xml, target_xml, cache)

    # 2. Audio Generation
    if args.generate_audio or args.api_key:
        api_key = args.api_key or os.environ.get("GEMINI_API_KEY", "")
        if not api_key:
            print("[Notice] Skipping audio generation because no Gemini API key was provided. Pass with --api-key <KEY> or set GEMINI_API_KEY.", file=sys.stderr)
        else:
            generate_audio_files(
                year_dir=year_dir,
                lang=args.audio_lang,
                api_key=api_key,
                days_limit=args.days,
                voice_de=args.voice_de,
                voice_en=args.voice_en,
                force=args.force
            )


if __name__ == '__main__':
    main()
