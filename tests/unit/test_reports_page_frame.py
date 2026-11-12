from pypdf import PdfReader

from app.chat.assistant.tools.registry import ArtifactPdfArgs
from app.services import reports
from app.services.reports import render_report_pdf


def _spec(title="Quarterly report"):
    return ArtifactPdfArgs.model_validate({
        "filename": "report.pdf",
        "title": title,
        "sections": [{"heading": "Summary", "body": "Report body"}],
    })


def test_backslash_title_keeps_page_frame_and_title_in_pdf_text():
    pdf = render_report_pdf(_spec("Back\\"))

    assert pdf.startswith(b"%PDF-")
    page_text = PdfReader(__import__("io").BytesIO(pdf)).pages[0].extract_text()
    assert "Page 1 of 1" in page_text
    assert "Back\\" in page_text


def test_all_report_resource_paths_are_recorded_and_degrade_to_pdf(monkeypatch):
    class RecordingRejector:
        _fail_on_errors = False

        def __init__(self):
            self.urls = []

        def __call__(self, url, *args, **kwargs):
            self.urls.append(url)
            raise ValueError(f"blocked: {url}")

    fetcher = RecordingRejector()
    monkeypatch.setattr(reports, "_reject_url", fetcher)
    html = """<!doctype html><html><head>
      <style>
        @import url('https://resources.example/import.css');
        .background { background-image: url('https://resources.example/background.png'); }
      </style>
    </head><body>
      <div class="background">resource test</div>
      <img src="https://resources.example/image.png">
      <img src="data:image/png;base64,AAAA">
    </body></html>"""
    monkeypatch.setattr(reports, "_render_report_html", lambda _spec: html)

    pdf = render_report_pdf(_spec())

    assert pdf.startswith(b"%PDF-")
    assert set(fetcher.urls) == {
        "https://resources.example/import.css",
        "https://resources.example/background.png",
        "https://resources.example/image.png",
        "data:image/png;base64,AAAA",
    }
