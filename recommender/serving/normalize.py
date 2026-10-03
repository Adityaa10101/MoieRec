"""
recommender/serving/normalize.py
==================================
Title display and search normalization utilities.
Uses ONLY Python stdlib (no pandas/pyarrow) so the backend tests can
import it without the recommender venv.
"""

import re
import unicodedata

_TRAILING_ARTICLE_RE = re.compile(
    r"^(.+),\s+(The|A|An|Les|Le|La|Los|Las|Der|Die|Das|De|El|Il|L\')\s*(\(\d{4}\))?\s*$",
    re.IGNORECASE,
)
_AKA_RE = re.compile(r"\s*\(a\.k\.a\..+?\)", re.IGNORECASE)
_YEAR_SUFFIX_RE = re.compile(r"\s*\(\d{4}\)\s*$")


def make_title_display(raw_title: str) -> str:
    """
    Convert MovieLens raw title to display form:
      'Matrix, The (1999)'   -> 'The Matrix'
      'Grumpier Old Men (1995)' -> 'Grumpier Old Men'
      'Cry Freedom (a.k.a. A Dry White Season) (1987)' -> 'Cry Freedom'
    """
    title = str(raw_title).strip()
    # Remove (a.k.a. ...) parts first
    title = _AKA_RE.sub("", title).strip()
    # Move trailing article back to front
    m = _TRAILING_ARTICLE_RE.match(title)
    if m:
        base, article = m.group(1).strip(), m.group(2)
        title = f"{article} {base}"
    # Strip trailing year "(YYYY)"
    title = _YEAR_SUFFIX_RE.sub("", title).strip()
    return title


def normalize_for_search(title: str) -> str:
    """Lowercase + ASCII-fold (remove diacritics) for search index."""
    nfkd = unicodedata.normalize("NFKD", title.lower())
    return "".join(c for c in nfkd if not unicodedata.combining(c))
