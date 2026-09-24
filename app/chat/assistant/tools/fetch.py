"""The assistant's single-URL reader: an explicit SSRF policy and a bounded fetch.

The policy is deliberately boring and total: a URL is only read when its scheme, its credentials,
its port and *every* address its host resolves to are all acceptable. Anything else is refused with
a reason, never silently skipped.
"""

from __future__ import annotations

import ipaddress
import socket
from dataclasses import dataclass
from urllib.parse import urlsplit, urlunsplit

#: Only the public web. `file`, `data`, `gopher`, `ftp` and friends are refused before any I/O.
ALLOWED_SCHEMES = frozenset({"http", "https"})
#: Non-default ports are refused: they are the cheapest way to probe internal services.
DEFAULT_PORTS = {"http": 80, "https": 443}
#: An IPv6 address in this prefix carries an IPv4 destination in its low 32 bits (RFC 6052).
NAT64_PREFIX = ipaddress.ip_network("64:ff9b::/96")


class FetchFailure(RuntimeError):
    """The URL was refused, or the page could not be fetched safely."""


@dataclass(frozen=True)
class FetchTarget:
    """A URL that passed the policy, with every address it resolved to, all validated."""

    url: str
    host: str
    port: int
    addresses: tuple[str, ...]


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
    parts = urlsplit(url.strip())
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
