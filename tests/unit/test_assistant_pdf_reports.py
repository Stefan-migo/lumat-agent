from datetime import date

import pytest
from pydantic import ValidationError

from app.chat.assistant.tools.registry import ArtifactPdfArgs, PdfSection, PdfTable
from app.services import reports
from app.services.reports import _render_report_html, _reject_url, render_report_pdf


def _minimal_args(**overrides):
    values = {
        "filename": "report.pdf",
        "title": "Quarterly report",
        "sections": [{"heading": "Summary", "body": "All good"}],
    }
    values.update(overrides)
    return values


def test_pdf_argument_models_reject_extra_fields_and_html_only_input():
    with pytest.raises(ValidationError):
        ArtifactPdfArgs.model_validate({**_minimal_args(), "unexpected": True})
    with pytest.raises(ValidationError):
        PdfSection.model_validate({"heading": "Heading", "html": "<b>not a field</b>"})


@pytest.mark.parametrize("value", ["", "x" * 201])
def test_pdf_title_enforces_both_bounds(value):
    with pytest.raises(ValidationError):
        ArtifactPdfArgs.model_validate(_minimal_args(title=value))


def test_pdf_subtitle_accepts_empty_and_300_but_rejects_301():
    ArtifactPdfArgs.model_validate(_minimal_args(subtitle=""))
    ArtifactPdfArgs.model_validate(_minimal_args(subtitle="x" * 300))
    with pytest.raises(ValidationError):
        ArtifactPdfArgs.model_validate(_minimal_args(subtitle="x" * 301))


@pytest.mark.parametrize("value", ["", "x" * 201])
def test_pdf_heading_enforces_both_bounds(value):
    with pytest.raises(ValidationError):
        PdfSection.model_validate({"heading": value})


@pytest.mark.parametrize("value", ["x" * 4001])
def test_pdf_body_rejects_above_maximum(value):
    with pytest.raises(ValidationError):
        PdfSection.model_validate({"heading": "Heading", "body": value})


def test_pdf_body_accepts_empty_and_maximum():
    PdfSection.model_validate({"heading": "x", "body": ""})
    PdfSection.model_validate({"heading": "x", "body": "x" * 4000})


@pytest.mark.parametrize("columns", [[], ["x"] * 9])
def test_pdf_table_enforces_column_bounds(columns):
    with pytest.raises(ValidationError):
        PdfTable.model_validate({"columns": columns})


@pytest.mark.parametrize("rows", [[[]] * 201])
def test_pdf_table_rejects_more_than_200_rows(rows):
    with pytest.raises(ValidationError):
        PdfTable.model_validate({"columns": ["x"], "rows": rows})


@pytest.mark.parametrize("cell", ["x" * 201])
def test_pdf_table_rejects_long_cells(cell):
    with pytest.raises(ValidationError):
        PdfTable.model_validate({"columns": ["x"], "rows": [[cell]]})


def test_pdf_table_accepts_one_to_eight_columns_and_empty_to_200_rows():
    PdfTable.model_validate({"columns": ["x"]})
    PdfTable.model_validate({"columns": ["x"] * 8, "rows": [["x"] * 8 for _ in range(200)]})


@pytest.mark.parametrize("sections", [[], [{"heading": "x"}] * 41])
def test_pdf_args_enforces_section_count_bounds(sections):
    with pytest.raises(ValidationError):
        ArtifactPdfArgs.model_validate(_minimal_args(sections=sections))


def test_pdf_filename_must_end_in_pdf_and_subtitle_has_limit():
    with pytest.raises(ValidationError):
        ArtifactPdfArgs.model_validate(_minimal_args(filename="report.txt"))
    ArtifactPdfArgs.model_validate(_minimal_args(subtitle="x" * 300))


def test_pdf_args_accept_title_subtitle_and_section_field_boundaries():
    ArtifactPdfArgs.model_validate({
        "filename": "report.pdf", "title": "x" * 200,
        "subtitle": "x" * 300, "sections": [{"heading": "x" * 200, "body": "x" * 4000}],
    })


def test_pdf_aggregate_content_limit_accepts_just_under_and_rejects_over():
    sections = [{"heading": "h" * 200, "body": "b" * 4000} for _ in range(14)]
    sections.append({"heading": "h" * 200, "body": "b" * 998})
    under_limit = {"filename": "report.pdf", "title": "x", "sections": sections}

    ArtifactPdfArgs.model_validate(under_limit)
    sections[-1]["body"] += "bb"
    with pytest.raises(ValidationError):
        ArtifactPdfArgs.model_validate(under_limit)


def test_pdf_template_escapes_body_and_fetcher_refuses_every_scheme():
    spec = ArtifactPdfArgs.model_validate(_minimal_args(sections=[{
        "heading": "Summary", "body": "<script>alert(1)</script>"
    }]))
    html = _render_report_html(spec, generated_on=date(2026, 11, 6))
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    for url in ("http://example.test/a", "https://example.test/a", "file:///etc/passwd", "data:text/plain,x", "relative/path"):
        with pytest.raises(ValueError):
            _reject_url(url)


def test_report_fetcher_disables_weasyprint_error_propagation():
    assert _reject_url._fail_on_errors is False


def test_report_with_blocked_image_still_renders_and_records_url(monkeypatch):
    spec = ArtifactPdfArgs.model_validate(_minimal_args())
    blocked_url = "http://example.com/x.png"

    class RecordingRejector:
        _fail_on_errors = False

        def __init__(self):
            self.urls = []

        def __call__(self, url, *args, **kwargs):
            self.urls.append(url)
            raise ValueError(f"blocked: {url}")

    fetcher = RecordingRejector()
    monkeypatch.setattr(reports, "_reject_url", fetcher)
    monkeypatch.setattr(reports, "_render_report_html", lambda _spec: f'<img src="{blocked_url}">')

    pdf = render_report_pdf(spec)

    assert pdf.startswith(b"%PDF-")
    assert fetcher.urls == [blocked_url]


def test_report_pdf_real_render_returns_pdf_bytes_and_html_has_title():
    spec = ArtifactPdfArgs.model_validate(_minimal_args())
    html = _render_report_html(spec, generated_on=date(2026, 11, 6))
    pdf = render_report_pdf(spec)
    assert pdf.startswith(b"%PDF-")
    assert "Quarterly report" in html
