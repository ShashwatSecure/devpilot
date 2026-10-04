"""Best-effort enrichment for unfamiliar technology terms, used to build the report's
glossary. Uses only Wikipedia's public REST summary API — no API key, no scraping of
search-engine result pages, and no arbitrary URL fetching. A strict timeout and a hard cap
on the number of lookups (enforced by the caller) mean a slow or unreachable network never
blocks the rest of the analysis; it just produces a shorter glossary.
"""
from __future__ import annotations

from urllib.parse import quote

import httpx

_SUMMARY_URL = "https://en.wikipedia.org/api/rest_v1/page/summary/{title}"
_HEADERS = {"User-Agent": "devpilot-repo-onboarding/0.1 (best-effort tech glossary lookup)"}


def lookup_term(term: str, *, timeout_seconds: int) -> str | None:
    """Returns a short summary for `term`, or None if not found / unreachable / disabled."""
    term = (term or "").strip()
    if not term:
        return None
    try:
        response = httpx.get(
            _SUMMARY_URL.format(title=quote(term, safe="")),
            headers=_HEADERS,
            timeout=timeout_seconds,
            follow_redirects=True,
        )
        if response.status_code != 200:
            return None
        data = response.json()
        extract = data.get("extract")
        return extract.strip() if extract else None
    except (httpx.HTTPError, ValueError):
        return None
