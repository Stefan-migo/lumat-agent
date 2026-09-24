"""SSRF policy and bounds for the panel assistant's single-URL reader (`web.fetch`)."""

import socket

import pytest

from app.chat.assistant.tools import fetch as fetch_module
from app.chat.assistant.tools.fetch import FetchFailure, resolve_target


def _addresses(monkeypatch, *resolved):
    def fake_getaddrinfo(host, port, **kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (address, port)) for address in resolved]

    monkeypatch.setattr(fetch_module.socket, "getaddrinfo", fake_getaddrinfo)


@pytest.mark.parametrize(
    "url",
    [
        "ftp://example.com/file",
        "file:///etc/passwd",
        "data:text/html,<h1>hi</h1>",
        "javascript:alert(1)",
        "gopher://example.com/",
        "ws://example.com/",
        "example.com",
        "//example.com/path",
    ],
)
def test_reader_refuses_anything_but_http_and_https(url):
    with pytest.raises(FetchFailure):
        resolve_target(url)


def test_reader_accepts_a_case_insensitive_scheme(monkeypatch):
    _addresses(monkeypatch, "93.184.216.34")

    target = resolve_target("HTTPS://Example.COM/path")

    assert target.host == "example.com"
    assert target.port == 443


@pytest.mark.parametrize(
    "url",
    [
        "http://user:secret@example.com/",
        "http://user@example.com/",
    ],
)
def test_reader_refuses_urls_carrying_credentials(url):
    with pytest.raises(FetchFailure, match="credentials"):
        resolve_target(url)


@pytest.mark.parametrize(
    "url",
    [
        "http://example.com:8080/",
        "https://example.com:80/",
        "http://example.com:22/",
        "http://example.com:6379/",
    ],
)
def test_reader_refuses_non_default_ports(url):
    with pytest.raises(FetchFailure, match="port"):
        resolve_target(url)


@pytest.mark.parametrize(
    "url,expected_port",
    [
        ("http://example.com/", 80),
        ("http://example.com:80/", 80),
        ("https://example.com/", 443),
        ("https://example.com:443/", 443),
    ],
)
def test_reader_accepts_the_default_port_for_each_scheme(monkeypatch, url, expected_port):
    _addresses(monkeypatch, "93.184.216.34")

    assert resolve_target(url).port == expected_port


@pytest.mark.parametrize("url", ["http:///path", "https://", "http://:80/"])
def test_reader_refuses_a_url_without_a_host(url):
    with pytest.raises(FetchFailure):
        resolve_target(url)


@pytest.mark.parametrize(
    "host",
    [
        "127.0.0.1",
        "127.1",
        "10.0.0.1",
        "172.16.0.1",
        "192.168.1.1",
        "169.254.169.254",
        "0.0.0.0",
        "100.64.0.1",
        "224.0.0.1",
        "240.0.0.1",
        "192.0.2.1",
        "[::1]",
        "[fe80::1]",
        "[fd00::1]",
        "[::ffff:127.0.0.1]",
        "[64:ff9b::7f00:1]",
    ],
)
def test_reader_refuses_every_non_public_address_class(host):
    with pytest.raises(FetchFailure, match="non-public"):
        resolve_target(f"http://{host}/")


@pytest.mark.parametrize("host", ["2130706433", "0x7f.0.0.1", "0177.0.0.1"])
def test_reader_collapses_alternate_numeric_forms_before_checking(host):
    with pytest.raises(FetchFailure, match="non-public"):
        resolve_target(f"http://{host}/")


def test_reader_accepts_a_public_address():
    target = resolve_target("http://93.184.216.34/page")

    assert target.addresses == ("93.184.216.34",)
    assert target.port == 80


def test_reader_returns_every_validated_address_for_the_connection(monkeypatch):
    _addresses(monkeypatch, "93.184.216.34", "2001:4860:4860::8888")

    target = resolve_target("https://example.com/")

    assert target.addresses == ("93.184.216.34", "2001:4860:4860::8888")


def test_reader_refuses_a_hostname_resolving_to_a_private_address(monkeypatch):
    _addresses(monkeypatch, "10.1.2.3")

    with pytest.raises(FetchFailure, match="non-public"):
        resolve_target("http://internal.example.com/")


def test_reader_refuses_when_any_resolved_address_is_not_public(monkeypatch):
    _addresses(monkeypatch, "93.184.216.34", "169.254.169.254")

    with pytest.raises(FetchFailure, match="non-public"):
        resolve_target("http://dual.example.com/")


def test_reader_reports_an_unresolvable_host(monkeypatch):
    def fake_getaddrinfo(host, port, **kwargs):
        raise socket.gaierror("name or service not known")

    monkeypatch.setattr(fetch_module.socket, "getaddrinfo", fake_getaddrinfo)

    with pytest.raises(FetchFailure, match="resolve"):
        resolve_target("http://does-not-exist.example/")


def test_reader_strips_the_fragment_and_fills_an_empty_path(monkeypatch):
    _addresses(monkeypatch, "93.184.216.34")

    target = resolve_target("https://example.com#section")

    assert target.url == "https://example.com/"
