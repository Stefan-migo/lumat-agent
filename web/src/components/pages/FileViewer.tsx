import { useEffect, useState } from "react";
import { Download, FileWarning } from "lucide-react";
import { Dialog } from "../primitives/Dialog";
import { Icon } from "../primitives/Icon";
import { StateMessage } from "../shared/StateMessage";
import { Markdown } from "../shared/Markdown";
import "./FileViewer.css";

export interface ViewerSource {
  url: string;
  filename: string;
  contentType?: string | null;
}

export type ViewerKind = "markdown" | "text" | "table" | "pdf" | "image" | "html" | "unsupported";

const MARKDOWN_EXTENSIONS = ["md", "markdown"];
const TEXT_EXTENSIONS = ["txt", "log", "json", "yaml", "yml", "xml", "py", "ts", "tsx", "js", "css", "sql", "sh"];
const TABLE_EXTENSIONS = ["csv", "tsv"];
const IMAGE_EXTENSIONS = ["png", "jpg", "jpeg", "gif", "webp", "avif", "bmp", "svg"];
const HTML_EXTENSIONS = ["html", "htm"];
/** Rows rendered before the viewer stops and says how much it left out. */
const TABLE_ROW_LIMIT = 200;

function extensionOf(filename: string): string {
  return filename.split(".").pop()?.toLocaleLowerCase("en-US") ?? "";
}

/**
 * The format decides how the file is shown, and the extension wins over the
 * content type: a `.md` served as `application/octet-stream` is still markdown.
 */
export function viewerKind(filename: string, contentType?: string | null): ViewerKind {
  const extension = extensionOf(filename);
  if (MARKDOWN_EXTENSIONS.includes(extension)) return "markdown";
  if (TABLE_EXTENSIONS.includes(extension)) return "table";
  if (IMAGE_EXTENSIONS.includes(extension)) return "image";
  if (HTML_EXTENSIONS.includes(extension)) return "html";
  if (extension === "pdf") return "pdf";
  if (TEXT_EXTENSIONS.includes(extension)) return "text";
  const type = (contentType ?? "").toLocaleLowerCase("en-US");
  if (type.startsWith("image/")) return "image";
  if (type.includes("markdown")) return "markdown";
  if (type.includes("csv") || type.includes("tab-separated")) return "table";
  if (type.includes("html")) return "html";
  if (type.includes("pdf")) return "pdf";
  if (type.startsWith("text/")) return "text";
  return "unsupported";
}

/** Minimal RFC-4180 reader: quotes, doubled quotes and embedded newlines. */
export function parseDelimited(text: string, delimiter: string): string[][] {
  const rows: string[][] = [];
  let row: string[] = [];
  let field = "";
  let quoted = false;
  for (let index = 0; index < text.length; index += 1) {
    const char = text[index];
    if (quoted) {
      if (char === '"') {
        if (text[index + 1] === '"') { field += '"'; index += 1; } else quoted = false;
      } else field += char;
      continue;
    }
    if (char === '"') { quoted = true; continue; }
    if (char === delimiter) { row.push(field); field = ""; continue; }
    if (char === "\n") { row.push(field); rows.push(row); row = []; field = ""; continue; }
    if (char === "\r") continue;
    field += char;
  }
  if (field.length || row.length) { row.push(field); rows.push(row); }
  return rows.filter((entry) => entry.some((cell) => cell.trim().length > 0));
}

const needsText = (kind: ViewerKind) => kind === "markdown" || kind === "text" || kind === "table" || kind === "html";

export interface FileViewerProps {
  source: ViewerSource | null;
  onClose: () => void;
}

/** Opens a sidebar file inside the panel instead of sending the operator to a
 *  download: markdown is rendered, tables become tables, pdf and images use the
 *  browser's own viewers, and html can never run a script. */
export function FileViewer({ source, onClose }: FileViewerProps) {
  const kind = source ? viewerKind(source.filename, source.contentType) : "unsupported";
  const [text, setText] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setText("");
    setError(null);
    if (!source || !needsText(kind)) { setLoading(false); return; }
    let live = true;
    setLoading(true);
    void fetch(source.url, { credentials: "include" })
      .then((response) => {
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return response.text();
      })
      .then((body) => { if (live) setText(body); })
      .catch(() => { if (live) setError("No pudimos abrir este archivo. Puedes descargarlo."); })
      .finally(() => { if (live) setLoading(false); });
    return () => { live = false; };
  }, [source?.url, source?.filename, kind]);

  const download = () => {
    if (!source) return;
    const link = document.createElement("a");
    link.href = source.url;
    link.download = source.filename;
    link.click();
  };

  const body = () => {
    if (!source) return null;
    if (loading) return <StateMessage tone="info" role="status" spinner title="Abriendo el archivo" />;
    if (error) return <StateMessage tone="danger" role="alert" title={error} />;
    if (kind === "markdown") return <Markdown content={text} className="file-viewer__markdown" />;
    if (kind === "text") return <pre className="file-viewer__text">{text}</pre>;
    if (kind === "table") {
      const rows = parseDelimited(text, extensionOf(source.filename) === "tsv" ? "\t" : ",");
      if (!rows.length) return <p className="file-viewer__note">El archivo no tiene filas para mostrar.</p>;
      const [head, ...rest] = rows;
      const visible = rest.slice(0, TABLE_ROW_LIMIT);
      return <div className="file-viewer__table-wrap">
        <table className="file-viewer__table">
          <thead><tr>{head.map((cell, index) => <th key={`h-${index}`} scope="col">{cell}</th>)}</tr></thead>
          <tbody>{visible.map((cells, rowIndex) => <tr key={`r-${rowIndex}`}>{cells.map((cell, cellIndex) => <td key={`c-${rowIndex}-${cellIndex}`}>{cell}</td>)}</tr>)}</tbody>
        </table>
        {rest.length > visible.length ? <p className="file-viewer__note">Mostrando {visible.length} de {rest.length} filas.</p> : null}
      </div>;
    }
    if (kind === "pdf") return <iframe className="file-viewer__frame" src={source.url} title={source.filename} />;
    if (kind === "image") return <img className="file-viewer__image" src={source.url} alt={source.filename} />;
    if (kind === "html") return <iframe className="file-viewer__frame" sandbox="" title={source.filename} srcDoc={text} />;
    return <div className="file-viewer__unsupported">
      <Icon icon={FileWarning} size="lg" />
      <p>No hay vista previa para este formato. Descárgalo para abrirlo con la aplicación correspondiente.</p>
    </div>;
  };

  return <Dialog open={Boolean(source)} onClose={onClose} title={source?.filename ?? "Archivo"} size="wide" icon={Download}>
    {body()}
    {source ? <div className="file-viewer__actions"><button type="button" className="file-viewer__download" onClick={download}><Icon icon={Download} size="sm" />Descargar</button></div> : null}
  </Dialog>;
}
