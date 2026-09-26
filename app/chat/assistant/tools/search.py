"""Small, replaceable web-search adapter with strict response bounds."""

from __future__ import annotations

import json
import time
from html.parser import HTMLParser
from urllib.parse import quote_plus

import httpx

from app.config import get_settings

MAX_RESULTS = 5
MAX_QUERY_LENGTH = 500
MAX_TEXT_LENGTH = 1000
MAX_TITLE_LENGTH = 100
MAX_SNIPPET_LENGTH = 200
MAX_URL_LENGTH = 300
BRAVE_SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"

# Brave's free tier allows one request per second. Wait out a single burst instead of failing
# the whole turn, but never block longer than the cap: the budget on the catalog and the turn
# deadline matter more than one search.
_RATE_LIMIT_RETRY_DEFAULT_SECONDS = 1.0
_RATE_LIMIT_RETRY_CAP_SECONDS = 2.0


def _rate_limit_delay_seconds(retry_after: str | None) -> float:
    """Seconds to wait before one rate-limit retry: the header, capped, else the default."""
    try:
        requested = float(retry_after)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        requested = _RATE_LIMIT_RETRY_DEFAULT_SECONDS
    return max(0.0, min(requested, _RATE_LIMIT_RETRY_CAP_SECONDS))


class SearchFailure(RuntimeError):
    """The provider failed; an empty result is reserved for a valid no-hit response."""


class _TextSanitizer(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def _sanitize_text(value: str) -> str:
    parser = _TextSanitizer()
    parser.feed(value)
    parser.close()
    return " ".join("".join(parser.parts).split())


class BraveSearch:
    """Brave Search provider behind the provider-neutral search seam."""

    def __init__(
        self,
        api_key: str | None = None,
        client: httpx.Client | None = None,
    ) -> None:
        self.api_key = api_key
        self.client = client

    def search(self, query: str, *, limit: int = MAX_RESULTS) -> list[dict[str, str]]:
        query = query.strip()[:MAX_QUERY_LENGTH]
        if not query:
            raise SearchFailure("search query is required")
        api_key = self.api_key if self.api_key is not None else get_settings().brave_search_api_key
        api_key = api_key.strip() if isinstance(api_key, str) else api_key
        if not api_key:
            raise SearchFailure("BRAVE_SEARCH_API_KEY is required for web search")

        request = self.client or httpx.Client(timeout=5.0)
        owned = self.client is None

        def fetch() -> httpx.Response:
            return request.get(
                BRAVE_SEARCH_URL,
                headers={"X-Subscription-Token": api_key},
                params={"q": query, "count": min(max(limit, 0), MAX_RESULTS), "country": "cl", "search_lang": "es"},
            )

        try:
            response = fetch()
            if response.status_code == 429:
                time.sleep(_rate_limit_delay_seconds(response.headers.get("Retry-After")))
                response = fetch()
                if response.status_code == 429:
                    raise SearchFailure("search provider rate-limited the request")
            response.raise_for_status()
            try:
                payload = response.json()
            except (ValueError, TypeError, UnicodeError) as exc:
                raise SearchFailure("search provider returned a non-JSON response") from exc
            web = payload.get("web") if isinstance(payload, dict) else None
            raw_results = web.get("results") if isinstance(web, dict) else None
            if not isinstance(raw_results, list):
                raise SearchFailure("search provider returned an invalid result structure")
            results = []
            for item in raw_results[:MAX_RESULTS]:
                if not isinstance(item, dict):
                    raise SearchFailure("search provider returned an invalid result entry")
                title = item.get("title")
                url = item.get("url")
                snippet = item.get("description")
                if not all(isinstance(value, str) for value in (title, url, snippet)):
                    raise SearchFailure("search provider returned an invalid result entry")
                if not url.startswith(("http://", "https://")):
                    raise SearchFailure("search provider returned an unsafe result URL")
                results.append(
                    {
                        "title": _sanitize_text(title)[:MAX_TITLE_LENGTH],
                        "url": url[:MAX_URL_LENGTH],
                        "snippet": _sanitize_text(snippet)[:MAX_SNIPPET_LENGTH],
                    }
                )
            if len(json.dumps(results, ensure_ascii=False)) >= 4_000:
                raise SearchFailure("search results exceed the evidence budget")
            return results[: min(max(limit, 0), MAX_RESULTS)]
        except httpx.TimeoutException as exc:
            raise SearchFailure("search provider timed out") from exc
        except httpx.HTTPError as exc:
            raise SearchFailure("search provider request failed") from exc
        finally:
            if owned:
                request.close()


class _ResultParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.results: list[dict[str, str]] = []
        self._current: dict[str, str] | None = None
        self._capture = False
        self.candidate_count = 0
        self.unsafe_count = 0
        self.saw_html = False
        self.saw_body = False
        self.closed_html = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        self.saw_html = self.saw_html or tag == "html"
        self.saw_body = self.saw_body or tag == "body"
        classes = (attributes.get("class") or "").split()
        if tag == "a" and "result__a" in classes:
            self.candidate_count += 1
        if tag == "a" and "result__a" in classes:
            self._current = {"title": "", "url": attributes.get("href") or ""}
            self._capture = True

    def handle_data(self, data: str) -> None:
        if self._capture and self._current is not None:
            self._current["title"] += data

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._capture and self._current is not None:
            title = " ".join(self._current["title"].split())[:MAX_TEXT_LENGTH]
            url = self._current["url"][:MAX_TEXT_LENGTH]
            if title and url.startswith(("http://", "https://")) and len(self.results) < MAX_RESULTS:
                self.results.append({"title": title, "url": url})
            elif not (title and url.startswith(("http://", "https://"))):
                self.unsafe_count += 1
            self._current = None
            self._capture = False
        if tag == "html":
            self.closed_html = True


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
            if not isinstance(response.text, str):
                raise SearchFailure("malformed search response")
            parser = _ResultParser()
            parser.feed(response.text[:100_000])
            parser.close()
            if not (parser.saw_html and parser.saw_body and parser.closed_html):
                raise SearchFailure("malformed search response")
            if parser.unsafe_count or (parser.candidate_count and not parser.results):
                raise SearchFailure("unsafe result entry")
            return parser.results[: min(max(limit, 0), MAX_RESULTS)]
        except httpx.HTTPError as exc:
            raise SearchFailure("network request failed") from exc
        except (AttributeError, TypeError, ValueError, UnicodeError) as exc:
            raise SearchFailure("malformed search response") from exc
        finally:
            if owned:
                request.close()


def search(query: str, *, limit: int = MAX_RESULTS) -> list[dict[str, str]]:
    return BraveSearch().search(query, limit=limit)
