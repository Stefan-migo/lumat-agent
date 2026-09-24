"""SSRF policy and bounds for the panel assistant's single-URL reader (`web.fetch`)."""

import json
import socket

import httpx
import pytest
import respx

from app.chat.assistant.nodes import _TOOL_EVIDENCE_LIMIT
from app.chat.assistant.tools import fetch as fetch_module
from app.chat.assistant.tools.fetch import (
    MAX_BYTES,
    MAX_REDIRECTS,
    MAX_TEXT,
    FetchFailure,
    extract_text,
    fetch_page,
    read_page,
    resolve_target,
)

# Every host here is a literal public address, so the policy's resolution step never touches DNS.
PUBLIC = "http://93.184.216.34"
OTHER_PUBLIC = "http://93.184.216.35"


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
    "url",
    [
        "http://[::1/",
        "http://[::1]x/",
        "http://]foo/",
        "http://[not]/",
        "http://[v6.]/",
    ],
)
def test_reader_refuses_a_url_the_parser_cannot_even_read(url):
    # Refusal is total: a URL the stdlib parser rejects is a FetchFailure, never a raw ValueError
    # escaping the policy (R3-malformed-url).
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


@respx.mock
def test_fetch_reads_a_public_page():
    respx.get(f"{PUBLIC}/page").respond(200, headers={"content-type": "text/html"}, content=b"<p>hello</p>")

    page = fetch_page(f"{PUBLIC}/page")

    assert page.url == f"{PUBLIC}/page"
    assert page.content_type == "text/html"
    assert "hello" in page.body
    assert page.truncated is False


@respx.mock
def test_fetch_follows_a_public_redirect_and_reports_the_final_url():
    respx.get(f"{PUBLIC}/start").respond(302, headers={"location": f"{OTHER_PUBLIC}/final"})
    respx.get(f"{OTHER_PUBLIC}/final").respond(200, headers={"content-type": "text/html"}, content=b"landed")

    page = fetch_page(f"{PUBLIC}/start")

    assert page.url == f"{OTHER_PUBLIC}/final"
    assert "landed" in page.body


@respx.mock
def test_fetch_refuses_a_redirect_to_a_private_address_without_requesting_it():
    respx.get(f"{PUBLIC}/start").respond(302, headers={"location": "http://10.0.0.1/admin"})
    private_route = respx.get("http://10.0.0.1/admin").respond(200, content=b"secret")

    with pytest.raises(FetchFailure, match="non-public"):
        fetch_page(f"{PUBLIC}/start")

    assert not private_route.called


@respx.mock
def test_fetch_refuses_a_redirect_to_a_non_http_scheme():
    respx.get(f"{PUBLIC}/start").respond(302, headers={"location": "file:///etc/passwd"})

    with pytest.raises(FetchFailure, match="http or https"):
        fetch_page(f"{PUBLIC}/start")


@respx.mock
def test_fetch_refuses_a_redirect_chain_beyond_the_cap():
    for hop in range(MAX_REDIRECTS + 2):
        respx.get(f"{PUBLIC}/hop{hop}").respond(302, headers={"location": f"{PUBLIC}/hop{hop + 1}"})

    with pytest.raises(FetchFailure, match="redirect"):
        fetch_page(f"{PUBLIC}/hop0")


@respx.mock
def test_fetch_refuses_a_redirect_without_a_target():
    respx.get(f"{PUBLIC}/start").respond(302)

    with pytest.raises(FetchFailure, match="redirect"):
        fetch_page(f"{PUBLIC}/start")


@respx.mock
def test_fetch_stops_reading_at_the_byte_cap():
    respx.get(f"{PUBLIC}/big").respond(
        200, headers={"content-type": "text/html"}, content=b"x" * (MAX_BYTES + 10_000)
    )

    page = fetch_page(f"{PUBLIC}/big")

    assert page.truncated is True
    assert len(page.body) == MAX_BYTES


@pytest.mark.parametrize("content_type", ["application/pdf", "image/png", "application/json", ""])
@respx.mock
def test_fetch_refuses_anything_that_is_not_text(content_type):
    headers = {"content-type": content_type} if content_type else {}
    respx.get(f"{PUBLIC}/file").respond(200, headers=headers, content=b"binary")

    with pytest.raises(FetchFailure, match="text"):
        fetch_page(f"{PUBLIC}/file")


@respx.mock
def test_fetch_reports_an_http_error_status():
    respx.get(f"{PUBLIC}/missing").respond(404, headers={"content-type": "text/html"}, content=b"gone")

    with pytest.raises(FetchFailure, match="404"):
        fetch_page(f"{PUBLIC}/missing")


@respx.mock
def test_fetch_reports_a_timeout():
    respx.get(f"{PUBLIC}/slow").mock(side_effect=httpx.ConnectTimeout("too slow"))

    with pytest.raises(FetchFailure, match="failed"):
        fetch_page(f"{PUBLIC}/slow")


@respx.mock
def test_fetch_never_follows_a_redirect_on_its_own():
    route = respx.get(f"{PUBLIC}/start").respond(302, headers={"location": f"{OTHER_PUBLIC}/final"})
    final = respx.get(f"{OTHER_PUBLIC}/final").respond(200, headers={"content-type": "text/html"}, content=b"x")

    fetch_page(f"{PUBLIC}/start")

    assert route.called
    assert final.called


def test_reader_extracts_the_title_and_collapses_the_body_text():
    html = (
        "<html><head><title>Calefont &amp; Chile</title></head>"
        "<body><p>Precio   desde\n$90.000</p><p>segunda   linea</p></body></html>"
    )

    title, text = extract_text(html)

    assert title == "Calefont & Chile"
    assert text == "Precio desde $90.000 segunda linea"


def test_reader_never_emits_script_style_or_noscript_bodies():
    html = (
        "<html><head><title>T</title>"
        "<script>var SECRET_SCRIPT='leak';</script>"
        "<style>.SECRET_STYLE{color:red}</style></head>"
        "<body><noscript>SECRET_NOSCRIPT</noscript><template>SECRET_TEMPLATE</template>"
        "<p>real text</p></body></html>"
    )

    _, text = extract_text(html)

    assert "real text" in text
    for leak in ("SECRET_SCRIPT", "SECRET_STYLE", "SECRET_NOSCRIPT", "SECRET_TEMPLATE"):
        assert leak not in text


def test_reader_keeps_inline_markup_from_splitting_a_word():
    _, text = extract_text("<p>foo<b>bar</b>baz</p>")

    assert text == "foobarbaz"


def test_reader_handles_a_page_without_a_title():
    title, text = extract_text("<body><p>no title here</p></body>")

    assert title == ""
    assert text == "no title here"


@respx.mock
def test_reader_returns_bounded_citable_evidence():
    body = b"<html><head><title>Fuente</title></head><body><p>" + b"a" * 50_000 + b"</p></body></html>"
    respx.get(f"{PUBLIC}/doc").respond(200, headers={"content-type": "text/html"}, content=body)

    result = read_page(f"{PUBLIC}/doc")

    assert set(result) == {"url", "title", "text"}
    assert result["url"] == f"{PUBLIC}/doc"
    assert result["title"] == "Fuente"
    assert len(result["text"]) == MAX_TEXT


@respx.mock
def test_reader_result_fits_the_tool_evidence_budget_at_its_worst_case():
    page = (
        b"<html><head><title>" + b"t" * 5_000 + b"</title></head>"
        b"<body><p>" + b"a" * 50_000 + b"</p></body></html>"
    )
    respx.get(f"{PUBLIC}/{'u' * 400}").respond(
        200, headers={"content-type": "text/html"}, content=page
    )

    result = read_page(f"{PUBLIC}/{'u' * 400}")

    assert len(json.dumps(result, ensure_ascii=False)) < _TOOL_EVIDENCE_LIMIT


@respx.mock
def test_reader_keeps_plain_text_pages_unparsed():
    respx.get(f"{PUBLIC}/notes").respond(
        200, headers={"content-type": "text/plain"}, content=b"a <b>not</b> html   page"
    )

    result = read_page(f"{PUBLIC}/notes")

    assert result["title"] == ""
    assert result["text"] == "a <b>not</b> html page"


@respx.mock
def test_reader_reports_the_final_redirect_target_as_the_source():
    respx.get(f"{PUBLIC}/go").respond(302, headers={"location": f"{OTHER_PUBLIC}/land"})
    respx.get(f"{OTHER_PUBLIC}/land").respond(
        200, headers={"content-type": "text/html"}, content=b"<p>here</p>"
    )

    result = read_page(f"{PUBLIC}/go")

    assert result["url"] == f"{OTHER_PUBLIC}/land"
    assert result["text"] == "here"
