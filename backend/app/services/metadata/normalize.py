"""Pure normalisation helpers: ISBNs, titles, people, languages, dates, text.

Nothing in here does I/O. Everything the matcher and merger rely on lives here so it can be tested
in isolation. Guiding rule: when in doubt return None / "unknown" rather than guess; the matcher
treats unknown as "no evidence" and never as agreement.
"""
from __future__ import annotations

import re
import string
import unicodedata
from datetime import date
from difflib import SequenceMatcher
from html import unescape
from typing import Iterable, Optional

# --------------------------------------------------------------------------------------------
# ISBN / ASIN
# --------------------------------------------------------------------------------------------
_ISBN_STRIP = re.compile(r"[\s\-\u2010-\u2015]")
_ISBN_PREFIX = re.compile(r"^ISBN(?:-?1[03])?:?", re.I)


def clean_isbn(raw) -> Optional[str]:
    """Strip separators / 'ISBN' prefix. Returns 10 or 13 chars (checksum NOT verified) or None."""
    if raw is None:
        return None
    s = _ISBN_PREFIX.sub("", _ISBN_STRIP.sub("", str(raw)).upper())
    return s if re.fullmatch(r"\d{9}[\dX]|\d{13}", s) else None


def is_valid_isbn10(s: str) -> bool:
    if not re.fullmatch(r"\d{9}[\dX]", s or ""):
        return False
    total = sum((10 - i) * (10 if c == "X" else int(c)) for i, c in enumerate(s))
    return total % 11 == 0


def is_valid_isbn13(s: str) -> bool:
    if not re.fullmatch(r"\d{13}", s or ""):
        return False
    total = sum(int(c) * (1 if i % 2 == 0 else 3) for i, c in enumerate(s))
    return total % 10 == 0


def isbn10_to_isbn13(isbn10: str) -> str:
    core = "978" + isbn10[:9]
    check = (10 - sum(int(c) * (1 if i % 2 == 0 else 3) for i, c in enumerate(core)) % 10) % 10
    return core + str(check)


def isbn13_to_isbn10(isbn13: str) -> Optional[str]:
    """Only 978-prefixed ISBN-13s have an ISBN-10 equivalent."""
    if not is_valid_isbn13(isbn13) or not isbn13.startswith("978"):
        return None
    core = isbn13[3:12]
    check = (11 - sum((10 - i) * int(c) for i, c in enumerate(core)) % 11) % 11
    return core + ("X" if check == 10 else str(check))


def canonical_isbn13(raw) -> Optional[str]:
    """Any valid ISBN-10/13 (hyphens, prefix, lowercase x all fine) -> its ISBN-13. Invalid -> None."""
    s = clean_isbn(raw)
    if s is None:
        return None
    if len(s) == 10:
        return isbn10_to_isbn13(s) if is_valid_isbn10(s) else None
    return s if is_valid_isbn13(s) else None


def valid_isbn10(raw) -> Optional[str]:
    s = clean_isbn(raw)
    return s if s and len(s) == 10 and is_valid_isbn10(s) else None


def split_isbns(raws: Iterable) -> tuple[Optional[str], Optional[str], list[str]]:
    """Sort a bag of ISBN strings into (isbn_10, isbn_13, other_isbn_13s).

    The primary ISBN-13 is the first valid one listed (or the conversion of the first ISBN-10 when no
    ISBN-13 is present). Any further distinct ISBN-13s are returned as `other`.
    """
    isbn10: Optional[str] = None
    thirteens: list[str] = []
    for raw in raws or []:
        s = clean_isbn(raw)
        if not s:
            continue
        if len(s) == 10 and is_valid_isbn10(s):
            isbn10 = isbn10 or s
            c13 = isbn10_to_isbn13(s)
            if c13 not in thirteens:
                thirteens.append(c13)
        elif len(s) == 13 and is_valid_isbn13(s) and s not in thirteens:
            thirteens.append(s)
    primary = thirteens[0] if thirteens else None
    if primary and not isbn10:
        isbn10 = isbn13_to_isbn10(primary)
    return isbn10, primary, thirteens[1:]


def looks_like_isbn(query: str) -> Optional[str]:
    """If the whole query is an ISBN, return its canonical ISBN-13."""
    q = (query or "").strip()
    if not q or not re.fullmatch(r"(?i)(isbn[\s:\-]*(1[03])?[\s:\-]*)?[\dX][\dX\s\-]{8,16}[\dX]", q):
        return None
    return canonical_isbn13(q)


# Audible/Amazon digital ASINs are "B0" + 8 alphanumerics. A looser pattern would also match ordinary 10-letter
# words that start with B ("Bridgerton", "Blackwater", "Bloodlines") and hijack the search.
_ASIN_RE = re.compile(r"^B0[0-9A-Z]{8}$")


def clean_asin(raw) -> Optional[str]:
    s = (str(raw).strip().upper() if raw is not None else "")
    return s if _ASIN_RE.fullmatch(s) else None


# --------------------------------------------------------------------------------------------
# Text, titles
# --------------------------------------------------------------------------------------------
def fold(text: str) -> str:
    """Case/accents/punctuation-insensitive form used for comparisons."""
    s = unicodedata.normalize("NFKD", text or "")
    s = "".join(ch for ch in s if not unicodedata.combining(ch)).casefold()
    s = s.replace("&", " and ").replace("’", "").replace("'", "")
    s = re.sub(r"[^0-9a-z\u00c0-\uffff]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


# Marketing / format noise that appears in titles but isn't part of the work's identity.
_NOISE_PAREN = re.compile(
    r"[\(\[]\s*(?:un)?abridged(?:\s+edition)?\s*[\)\]]|[\(\[]\s*(?:the\s+)?audiobook\s*[\)\]]|"
    r"[\(\[]\s*a\s+novel\s*[\)\]]|[\(\[]\s*audio\s+edition\s*[\)\]]|[\(\[]\s*dramati[sz]ed(?:\s+edition)?\s*[\)\]]",
    re.I,
)
_LEADING_ARTICLE = re.compile(r"^(?:the|a|an)\s+")
_SUBTITLE_SPLIT = re.compile(r"\s*(?::|\s[-\u2013\u2014]\s|\s\()\s*")


def strip_title_noise(title: str) -> str:
    return re.sub(r"\s+", " ", _NOISE_PAREN.sub(" ", title or "")).strip(" -:")


def split_title(title: str, subtitle: Optional[str] = None) -> tuple[str, str]:
    """-> (folded main title, folded subtitle). A subtitle embedded in `title` after ':' / ' - ' / '(' is
    extracted, so "Dune: Deluxe Edition" and title="Dune" / subtitle="Deluxe Edition" compare equal."""
    t = strip_title_noise(title)
    parts = _SUBTITLE_SPLIT.split(t, maxsplit=1)
    # library-style inverted article: "Hobbit, The" -> "The Hobbit"
    inverted = re.match(r"^(.*?),\s*(the|a|an)$", parts[0].strip(), re.I)
    main = fold(f"{inverted.group(2)} {inverted.group(1)}" if inverted else parts[0])
    embedded = fold(parts[1]) if len(parts) > 1 else ""
    sub = fold(subtitle or "") or embedded
    main = _LEADING_ARTICLE.sub("", main)
    return main, sub


def normalize_title(title: str, subtitle: Optional[str] = None) -> str:
    main, sub = split_title(title, subtitle)
    return f"{main} {sub}".strip()


def similarity(a: str, b: str) -> float:
    a, b = fold(a), fold(b)
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def titles_compatible(t1: str, s1: Optional[str], t2: str, s2: Optional[str]) -> bool:
    """Same work title? Main titles must be IDENTICAL after folding ("Dune" != "Dune Messiah"); when both
    sides carry a subtitle they must also be similar ("Dune" with subtitle X vs subtitle Y -> no)."""
    m1, sub1 = split_title(t1, s1)
    m2, sub2 = split_title(t2, s2)
    if not m1 or not m2 or m1 != m2:
        return False
    if sub1 and sub2 and sub1 != sub2:
        return similarity(sub1, sub2) >= 0.6
    return True


# --------------------------------------------------------------------------------------------
# People
# --------------------------------------------------------------------------------------------
_ROLE_PAREN = re.compile(r"\((?:[^)]*)\)")
_HONORIFIC = re.compile(r"^(?:dr|prof|mr|mrs|ms|sir|dame)\.?\s+", re.I)
_SUFFIXES = {"jr", "sr", "ii", "iii", "iv"}


def person_tokens(name: str) -> list[str]:
    """"Tolkien, J. R. R." / "J.R.R. Tolkien" / "john ronald reuel tolkien (author)" -> comparable tokens."""
    s = _ROLE_PAREN.sub(" ", name or "").strip()
    s = _HONORIFIC.sub("", s)
    if s.count(",") == 1:
        last, first = (p.strip() for p in s.split(","))
        if first and first.lower().strip(". ") not in _SUFFIXES:
            s = f"{first} {last}"
    s = s.replace(".", " ")
    tokens = fold(s).split()
    return [t for t in tokens if t not in _SUFFIXES] or tokens


def normalize_person(name: str) -> str:
    return " ".join(person_tokens(name))


def persons_match(a: str, b: str) -> bool:
    ta, tb = person_tokens(a), person_tokens(b)
    if not ta or not tb or ta[-1] != tb[-1]:
        return False
    ga, gb = ta[:-1], tb[:-1]
    if not ga or not gb:  # one side is surname-only: weak but acceptable
        return True
    ia, ib = [g[0] for g in ga], [g[0] for g in gb]
    if ia[0] != ib[0]:  # first given name must agree by initial (J. == John, Frank != Brian)
        return False
    short, long_ = (ia, ib) if len(ia) <= len(ib) else (ib, ia)
    it = iter(long_)  # a missing middle name/initial on one side is fine: initials must be a subsequence
    return all(c in it for c in short)


def people_overlap(a: Iterable[str], b: Iterable[str]) -> float:
    """Fraction of the SMALLER list that has a match in the other (0..1). 0 if either is empty."""
    la, lb = [x for x in a or [] if x], [x for x in b or [] if x]
    if not la or not lb:
        return 0.0
    small, big = (la, lb) if len(la) <= len(lb) else (lb, la)
    hits = sum(1 for p in small if any(persons_match(p, q) for q in big))
    return hits / len(small)


def dedupe_people(names: Iterable[str]) -> list[str]:
    out: list[str] = []
    for n in names or []:
        n = re.sub(r"\s+", " ", (n or "")).strip()
        if n and not any(persons_match(n, o) and len(person_tokens(n)) == len(person_tokens(o)) for o in out):
            out.append(n)
    return out


# --------------------------------------------------------------------------------------------
# Language
# --------------------------------------------------------------------------------------------
_LANG_3_TO_2 = {
    "eng": "en", "fre": "fr", "fra": "fr", "ger": "de", "deu": "de", "spa": "es", "ita": "it", "por": "pt",
    "rus": "ru", "jpn": "ja", "chi": "zh", "zho": "zh", "dut": "nl", "nld": "nl", "swe": "sv", "nor": "no",
    "dan": "da", "fin": "fi", "pol": "pl", "tur": "tr", "ara": "ar", "heb": "he", "hin": "hi", "kor": "ko",
    "lat": "la", "gre": "el", "ell": "el", "cze": "cs", "ces": "cs", "hun": "hu", "ukr": "uk", "cat": "ca",
    "rum": "ro", "ron": "ro", "bul": "bg", "hrv": "hr", "srp": "sr", "slo": "sk", "slk": "sk", "ind": "id",
    "vie": "vi", "tha": "th", "per": "fa", "fas": "fa", "ice": "is", "isl": "is", "gle": "ga", "wel": "cy",
    "cym": "cy", "baq": "eu", "eus": "eu", "glg": "gl", "est": "et", "lav": "lv", "lit": "lt", "slv": "sl",
}
_LANG_NAMES = {
    "english": "en", "french": "fr", "german": "de", "spanish": "es", "italian": "it", "portuguese": "pt",
    "russian": "ru", "japanese": "ja", "chinese": "zh", "dutch": "nl", "swedish": "sv", "norwegian": "no",
    "danish": "da", "finnish": "fi", "polish": "pl", "turkish": "tr", "arabic": "ar", "hebrew": "he",
    "hindi": "hi", "korean": "ko", "latin": "la", "greek": "el", "czech": "cs", "hungarian": "hu",
    "ukrainian": "uk", "catalan": "ca", "romanian": "ro",
}


def normalize_language(raw) -> Optional[str]:
    """'eng' / 'en-US' / 'English' / '/languages/eng' -> 'en'. Unknown -> None."""
    if raw is None:
        return None
    s = str(raw).strip().lower().rsplit("/", 1)[-1]
    if not s or s in {"und", "mul", "zxx", "unknown"}:
        return None
    s = s.replace("_", "-").split("-")[0]
    if s in _LANG_NAMES:
        return _LANG_NAMES[s]
    if len(s) == 2 and s.isalpha():
        return s
    if len(s) == 3 and s.isalpha():
        return _LANG_3_TO_2.get(s, s)
    return None


# --------------------------------------------------------------------------------------------
# Dates
# --------------------------------------------------------------------------------------------
_MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], start=1)}


def _plausible_year(y: int) -> bool:
    return 1000 <= y <= date.today().year + 2


def parse_partial_date(raw) -> Optional[str]:
    """Return 'YYYY', 'YYYY-MM' or 'YYYY-MM-DD' (never invents precision). Unparseable -> None."""
    if raw is None:
        return None
    if isinstance(raw, int):
        return str(raw) if _plausible_year(raw) else None
    s = str(raw).strip()
    if not s:
        return None
    m = re.match(r"^(\d{4})(?:-(\d{1,2})(?:-(\d{1,2}))?)?(?:[T\s].*)?$", s)
    if m:
        y = int(m.group(1))
        if not _plausible_year(y):
            return None
        if m.group(2):
            mo = int(m.group(2))
            if not 1 <= mo <= 12:
                return str(y)
            if m.group(3):
                d = int(m.group(3))
                try:
                    date(y, mo, d)
                    return f"{y:04d}-{mo:02d}-{d:02d}"
                except ValueError:
                    return f"{y:04d}-{mo:02d}"
            return f"{y:04d}-{mo:02d}"
        return f"{y:04d}"
    low = s.lower()
    year = re.search(r"(?<!\d)(1\d{3}|20\d{2})(?!\d)", low)
    if not year or not _plausible_year(int(year.group(1))):
        return None
    y = int(year.group(1))
    mon = re.search(r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\b", low)
    if not mon:
        return f"{y:04d}"
    mo = _MONTHS[mon.group(1)]
    day = re.search(r"\b(\d{1,2})(?:st|nd|rd|th)?\b(?!\s*\d{3})", low.replace(str(y), " "))
    if day:
        try:
            date(y, mo, int(day.group(1)))
            return f"{y:04d}-{mo:02d}-{int(day.group(1)):02d}"
        except ValueError:
            pass
    return f"{y:04d}-{mo:02d}"


def year_of(partial: Optional[str]) -> Optional[int]:
    return int(partial[:4]) if partial and re.match(r"^\d{4}", partial) else None


def date_precision(partial: Optional[str]) -> int:
    return len(partial.split("-")) if partial else 0


# --------------------------------------------------------------------------------------------
# Text cleanup
# --------------------------------------------------------------------------------------------
def clean_html(text) -> Optional[str]:
    """Provider descriptions arrive as HTML (<br>, <p>, <b>...). Return readable plain text."""
    if not text or not isinstance(text, str):
        return None
    s = re.sub(r"(?i)<\s*br\s*/?\s*>", "\n", text)
    s = re.sub(r"(?i)</\s*(p|div|li|h\d)\s*>", "\n\n", s)
    s = re.sub(r"<[^>]+>", "", s)
    s = unescape(s).replace("\xa0", " ")
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n[ \t]+", "\n", s)
    s = re.sub(r"\n{3,}", "\n\n", s).strip()
    return s or None


def clean_text(value) -> Optional[str]:
    if value is None:
        return None
    s = re.sub(r"\s+", " ", str(value)).strip()
    return s or None


# --------------------------------------------------------------------------------------------
# Audiobook helpers
# --------------------------------------------------------------------------------------------
RECORDING_TYPES = ("unabridged", "abridged", "dramatized")


def parse_recording_type(*texts) -> Optional[str]:
    """Look for an explicit marker ('(Unabridged)', 'Abridged', 'full-cast dramatisation') in the texts."""
    blob = " ".join(t for t in texts if isinstance(t, str)).lower()
    if not blob:
        return None
    if re.search(r"\bunabridged\b", blob):
        return "unabridged"
    if re.search(r"\babridged\b", blob):
        return "abridged"
    if re.search(r"dramati[sz]ed|dramati[sz]ation|full[\s-]cast|radio (?:play|drama)", blob):
        return "dramatized"
    return None


def seconds_to_minutes(seconds) -> Optional[int]:
    try:
        s = float(seconds)
    except (TypeError, ValueError):
        return None
    return int(round(s / 60)) if s > 0 else None


def positive_int(value) -> Optional[int]:
    try:
        n = int(float(value))
    except (TypeError, ValueError):
        return None
    return n if n > 0 else None


# --------------------------------------------------------------------------------------------
# Genres, series
# --------------------------------------------------------------------------------------------
_GENRE_NOISE = (
    "open library", "staff picks", "accessible book", "protected daisy", "in library", "lending library",
    "overdrive", "large type", "bestseller", "nyt:", "reading level", "internet archive", "long now",
    "general", "miscellaneous",
)


def normalize_genres(items: Iterable[str], limit: int = 8) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items or []:
        for part in re.split(r"\s*/\s*", str(item or "")):
            g = clean_text(part)
            if not g or len(g) > 40 or re.search(r"[\(\)\d:]", g):
                continue
            if any(n in g.lower() for n in _GENRE_NOISE):
                continue
            if g == g.lower():
                g = string.capwords(g)
            k = fold(g)
            if k and k not in seen:
                seen.add(k)
                out.append(g)
            if len(out) >= limit:
                return out
    return out


_SERIES_RE = re.compile(r"^(?P<name>.*?)[\s;,#(\-]*(?:(?:book|vol(?:ume)?|no|part)\.?\s*)?(?P<pos>\d+(?:\.\d+)?)\)?\s*$", re.I)


def parse_series(text: str) -> tuple[Optional[str], Optional[str]]:
    """'Discworld ; 3' / 'Discworld (3)' / 'Discworld, Book 3' / 'Discworld' -> (name, position|None)."""
    t = clean_text(text)
    if not t:
        return None, None
    m = _SERIES_RE.match(t)
    if m and m.group("name").strip(" ;,#()-"):
        return m.group("name").strip(" ;,#()-"), m.group("pos")
    return t, None
