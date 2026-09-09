"""Small, replaceable web-search adapter with strict response bounds."""

from __future__ import annotations

from html.parser import HTMLParser
from urllib.parse import quote_plus

import httpx

MAX_RESULTS = 5
MAX_QUERY_LENGTH = 500
MAX_TEXT_LENGTH = 1000


class SearchFailure(RuntimeError):
    """The provider failed; an empty result is reserved for a valid no-hit response."""


class _ResultParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.results: list[dict[str, str]] = []
        self._current: dict[str, str] | None = None
        self._capture = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        classes = (attributes.get("class") or "").split()
        if tag == "a" and "result__a" in classes and len(self.results) < MAX_RESULTS:
            self._current = {"title": "", "url": attributes.get("href") or ""}
            self._capture = True

    def handle_data(self, data: str) -> None:
        if self._capture and self._current is not None:
            self._current["title"] += data

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._capture and self._current is not None:
            title = " ".join(self._current["title"].split())[:MAX_TEXT_LENGTH]
            url = self._current["url"][:MAX_TEXT_LENGTH]
            if title and url.startswith(("http://", "https://")):
                self.results.append({"title": title, "url": url})
            self._current = None
            self._capture = False


class DuckDuckGoSearch:
    """DuckDuckGo HTML search, isolated behind a provider-shaped interface."""

    def __init__(self, client: httpx.Client | None = None) -> None:
        self.client = client

    def search(self, query: str, *, limit: int = MAX_RESULTS) -> list[dict[str, str]]:
        query = query.strip()[:MAX_QUERY_LENGTH]
        if not query:
            return []
        request = self.client or httpx.Client(timeout=5.0, follow_redirects=True)
        owned = self.client is None
        try:
            response = request.get(f"https://html.duckduckgo.com/html/?q={quote_plus(query)}")
            response.raise_for_status()
            parser = _ResultParser()
            parser.feed(response.text[:100_000])
            return parser.results[: min(max(limit, 0), MAX_RESULTS)]
        except httpx.HTTPError as exc:
            raise SearchFailure("network request failed") from exc
        except (ValueError, UnicodeError) as exc:
            raise SearchFailure("malformed search response") from exc
        finally:
            if owned:
                request.close()


def search(query: str, *, limit: int = MAX_RESULTS) -> list[dict[str, str]]:
    return DuckDuckGoSearch().search(query, limit=limit)
