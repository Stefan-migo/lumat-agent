"""The assistant's single-URL reader: an explicit SSRF policy and a bounded fetch.

The policy is deliberately boring and total: a URL is only read when its scheme, its credentials,
its port and *every* address its host resolves to are all acceptable. Anything else is refused with
a reason, never silently skipped.
"""

from __future__ import annotations

import ipaddress
import socket
from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit, urlunsplit

import httpx

#: Only the public web. `file`, `data`, `gopher`, `ftp` and friends are refused before any I/O.
ALLOWED_SCHEMES = frozenset({"http", "https"})
#: Non-default ports are refused: they are the cheapest way to probe internal services.
DEFAULT_PORTS = {"http": 80, "https": 443}
#: An IPv6 address in this prefix carries an IPv4 destination in its low 32 bits (RFC 6052).
NAT64_PREFIX = ipaddress.ip_network("64:ff9b::/96")
#: Redirects are followed by hand so every hop goes back through the policy.
MAX_REDIRECTS = 3
#: Hard stop on the bytes read from a page, enforced while reading, not from a header.
MAX_BYTES = 512_000
#: A page is read as text or not at all.
ALLOWED_CONTENT_TYPES = frozenset({"text/html", "application/xhtml+xml", "text/plain"})
WEB_FETCH_TIMEOUT = httpx.Timeout(5.0, connect=3.0)
USER_AGENT = "Mozilla/5.0 (compatible; LumatReader/1.0)"
#: The reader owns its bound, so a full result always fits `_TOOL_EVIDENCE_LIMIT` (4,000) with room.
MAX_TEXT = 3_000
TITLE_LIMIT = 200
URL_LIMIT = 500
#: Tags whose text is not page content: a sanitizer that only keeps `handle_data` would leak them.
_SKIPPED_TAGS = frozenset({"script", "style", "noscript", "template", "svg"})
#: Block-level tags separate text. Without this, two adjacent paragraphs glue their last and first
#: words together once whitespace is collapsed. Inline tags must NOT separate: `foo<b>bar</b>` is one
#: word in the page and has to stay one word here.
_BLOCK_TAGS = frozenset(
    {
        "address", "article", "aside", "blockquote", "br", "dd", "div", "dl", "dt", "fieldset",
        "figcaption", "figure", "footer", "form", "h1", "h2", "h3", "h4", "h5", "h6", "header",
        "hr", "li", "main", "nav", "ol", "p", "pre", "section", "table", "tbody", "td", "tfoot",
        "th", "thead", "tr", "ul",
    }
)

#: An HTML page is parsed; anything else is treated as already-plain text.
_PARSEABLE_TYPES = frozenset({"text/html", "application/xhtml+xml"})
_REDIRECT_STATUSES = frozenset({301, 302, 303, 307, 308})


class FetchFailure(RuntimeError):
    """The URL was refused, or the page could not be fetched safely."""


@dataclass(frozen=True)
class FetchTarget:
    """A URL that passed the policy, with every address it resolved to, all validated."""

    url: str
    host: str
    port: int
    addresses: tuple[str, ...]


@dataclass(frozen=True)
class FetchedPage:
    """What the network returned: the final URL, its type, and its bounded body."""

    url: str
    content_type: str
    body: str
    truncated: bool


def _unsafe_reason(raw: str) -> str | None:
    """Why `raw` must not be connected to, or `None` when it is safe.

    `not is_global` covers loopback, private, link-local, reserved, unspecified and carrier-grade
    NAT ranges for both families. Multicast is checked separately because `is_global` reports it as
    global. NAT64 addresses are unwrapped first: the prefix itself looks global, but what it carries
    is the real destination.
    """
    try:
        address = ipaddress.ip_address(raw)
    except ValueError:
        return f"unusable address {raw}"
    if isinstance(address, ipaddress.IPv6Address) and address in NAT64_PREFIX:
        return _unsafe_reason(str(ipaddress.IPv4Address(int(address) & 0xFFFFFFFF)))
    if not address.is_global or address.is_multicast:
        return f"non-public address {raw}"
    return None


def resolve_target(url: str) -> FetchTarget:
    """Validate `url` and its resolved addresses, or raise `FetchFailure`."""
    try:
        parts = urlsplit(url.strip())
    except ValueError as exc:
        # The stdlib parser rejects malformed bracketed hosts with its own ValueError. Refusal has to
        # be total: a caller catching only FetchFailure must not have a raw parser error leak past it.
        raise FetchFailure("fetch could not read the URL") from exc
    scheme = parts.scheme.lower()
    if scheme not in ALLOWED_SCHEMES:
        raise FetchFailure(f"fetch requires an http or https URL, not {scheme or 'a schemeless URL'!r}")
    if parts.username or parts.password:
        raise FetchFailure("fetch refuses URLs carrying credentials")
    host = parts.hostname or ""
    if not host:
        raise FetchFailure("fetch requires a URL with a host")
    try:
        port = parts.port or DEFAULT_PORTS[scheme]
    except ValueError as exc:
        raise FetchFailure(f"fetch refused an invalid port in {url!r}") from exc
    if port != DEFAULT_PORTS[scheme]:
        raise FetchFailure(f"fetch only reads {scheme} on port {DEFAULT_PORTS[scheme]}, not {port}")
    try:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise FetchFailure(f"fetch could not resolve {host}") from exc
    addresses: list[str] = []
    for info in infos:
        address = info[4][0]
        reason = _unsafe_reason(address)
        if reason is not None:
            raise FetchFailure(f"fetch refuses {host}: it resolves to a {reason}")
        if address not in addresses:
            addresses.append(address)
    if not addresses:
        raise FetchFailure(f"fetch could not resolve {host}")
    # Fragments never reach the server, so they are not part of what is read.
    normalized = urlunsplit((scheme, parts.netloc, parts.path or "/", parts.query, ""))
    return FetchTarget(url=normalized, host=host, port=port, addresses=tuple(addresses))


def _read_bounded(response: httpx.Response) -> tuple[str, bool]:
    """Read the body, stopping at `MAX_BYTES` rather than trusting `Content-Length`."""
    chunks: list[bytes] = []
    total = 0
    truncated = False
    for chunk in response.iter_bytes():
        chunks.append(chunk)
        total += len(chunk)
        if total >= MAX_BYTES:
            truncated = True
            break
    raw = b"".join(chunks)[:MAX_BYTES]
    return raw.decode("utf-8", errors="replace"), truncated


def fetch_page(url: str, *, client: httpx.Client | None = None) -> FetchedPage:
    """Fetch one public text page, following at most `MAX_REDIRECTS` revalidated hops.

    Redirects are resolved by hand: `follow_redirects` is forced off per request, so every hop's
    target goes back through `resolve_target` before it is requested. Any refusal, timeout, error
    status or unusable body raises `FetchFailure` -- this reader never reports a silent empty page.
    """
    target = resolve_target(url)
    http = client or httpx.Client(timeout=WEB_FETCH_TIMEOUT)
    try:
        for hop in range(MAX_REDIRECTS + 1):
            with http.stream(
                "GET", target.url, headers={"user-agent": USER_AGENT}, follow_redirects=False
            ) as response:
                if response.status_code in _REDIRECT_STATUSES:
                    location = response.headers.get("location")
                    if not location:
                        raise FetchFailure(f"fetch got a redirect without a target from {target.host}")
                    if hop == MAX_REDIRECTS:
                        raise FetchFailure(f"fetch stopped after {MAX_REDIRECTS} redirects")
                    target = resolve_target(urljoin(target.url, location))
                    continue
                if response.status_code >= 400:
                    raise FetchFailure(f"fetch got HTTP {response.status_code} from {target.host}")
                content_type = response.headers.get("content-type", "").split(";")[0].strip().lower()
                if content_type not in ALLOWED_CONTENT_TYPES:
                    raise FetchFailure(
                        f"fetch only reads text pages, not {content_type or 'a response without a content type'}"
                    )
                body, truncated = _read_bounded(response)
                return FetchedPage(
                    url=target.url, content_type=content_type, body=body, truncated=truncated
                )
    except httpx.HTTPError as exc:
        raise FetchFailure(f"fetch request failed: {type(exc).__name__}") from exc
    finally:
        if client is None:
            http.close()
    raise FetchFailure("fetch ended without a response")


class _PageText(HTMLParser):
    """Collect a page's title and its visible text, skipping non-content elements."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._skipped = 0
        self._in_title = False
        self.parts: list[str] = []
        self.title_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _SKIPPED_TAGS:
            self._skipped += 1
        elif tag == "title":
            self._in_title = True
        elif tag in _BLOCK_TAGS and not self._in_title:
            self.parts.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if tag in _SKIPPED_TAGS:
            self._skipped = max(0, self._skipped - 1)
        elif tag == "title":
            self._in_title = False
        elif tag in _BLOCK_TAGS and not self._in_title:
            self.parts.append(" ")

    def handle_data(self, data: str) -> None:
        if self._skipped:
            return
        target = self.title_parts if self._in_title else self.parts
        target.append(data)


def _collapse(text: str) -> str:
    return " ".join(text.split())


def extract_text(html: str) -> tuple[str, str]:
    """Return `(title, visible_text)`, both whitespace-collapsed."""
    parser = _PageText()
    parser.feed(html)
    parser.close()
    return _collapse("".join(parser.title_parts)), _collapse("".join(parser.parts))


def read_page(url: str, *, client: httpx.Client | None = None) -> dict[str, str]:
    """Fetch `url` and return the bounded, citable evidence the assistant answers from.

    The result is `{"url", "title", "text"}`: the final URL after redirects so the answer can cite
    its source, and text sized to fit the tool-evidence budget without downstream truncation.
    """
    page = fetch_page(url, client=client)
    if page.content_type in _PARSEABLE_TYPES:
        title, text = extract_text(page.body)
    else:
        title, text = "", _collapse(page.body)
    return {
        "url": page.url[:URL_LIMIT],
        "title": title[:TITLE_LIMIT],
        "text": text[:MAX_TEXT],
    }
