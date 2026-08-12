module.exports = {
  dest: "propuesta-tecnica-economica-lumat.pdf",
  stylesheet: "style.css",
  pdf_options: {
    format: "A4",
    margin: {
      top: "24mm",
      bottom: "20mm",
      left: "18mm",
      right: "18mm"
    },
    printBackground: true,
    displayHeaderFooter: true,
    headerTemplate: `<div style="font-family: Helvetica, Arial, sans-serif; font-size: 8px; color: #888; text-align: right; width: 100%; padding-right: 18mm; padding-top: 5mm;">Propuesta Técnica y Económica — Lumat · Julio 2026 · HandCodeStudio</div>`,
    footerTemplate: `<div style="font-family: Helvetica, Arial, sans-serif; font-size: 8px; color: #888; text-align: center; width: 100%; padding-bottom: 5mm;"><span class="pageNumber"></span> / <span class="totalPages"></span></div>`
  }
};
