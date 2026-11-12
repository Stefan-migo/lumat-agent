"""Safe, structured PDF report rendering for assistant artifacts."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING, Any

from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

if TYPE_CHECKING:
    from app.chat.assistant.tools.registry import ArtifactPdfArgs


_REPORT_TEMPLATE = Environment(
    autoescape=True,
    loader=FileSystemLoader(Path(__file__).parent),
).get_template("report_template.html")


class _RejectResources:
    _fail_on_errors = False

    def __call__(self, url: str, *args: Any, **kwargs: Any) -> Any:
        """Deny every resource URL so reports cannot access network or local files."""
        raise ValueError(f"PDF report resources are disabled: {url}")


_reject_url = _RejectResources()


def _render_report_html(spec: ArtifactPdfArgs, *, generated_on: date | None = None) -> str:
    return _REPORT_TEMPLATE.render(spec=spec, generated_on=(generated_on or date.today()).isoformat())


def render_report_pdf(spec: ArtifactPdfArgs) -> bytes:
    """Render a validated structured report to PDF; report HTML has no resource access."""
    html = _render_report_html(spec)
    # WeasyPrint 70 accepts the fetcher on HTML construction (not on write_pdf).
    # The renderer retains it for all resource requests during PDF generation.
    return HTML(string=html, url_fetcher=_reject_url).write_pdf()
