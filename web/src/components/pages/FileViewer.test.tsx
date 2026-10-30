import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { FileViewer, parseDelimited, viewerKind } from "./FileViewer";

const source = (filename: string, contentType: string | null = null) => ({ url: `/content/${filename}`, filename, contentType });

const mockText = (body: string) => vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(body, { status: 200 }));

describe("viewerKind", () => {
  it("decides by extension first and content type only as a fallback", () => {
    expect(viewerKind("notas.md", "application/octet-stream")).toBe("markdown");
    expect(viewerKind("datos.csv")).toBe("table");
    expect(viewerKind("informe.pdf")).toBe("pdf");
    expect(viewerKind("captura.PNG")).toBe("image");
    expect(viewerKind("pagina.html")).toBe("html");
    expect(viewerKind("script.py")).toBe("text");
    expect(viewerKind("archivo", "application/pdf")).toBe("pdf");
    expect(viewerKind("planilla.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")).toBe("unsupported");
  });
});

describe("parseDelimited", () => {
  it("keeps quoted commas, doubled quotes and embedded newlines in one cell", () => {
    const rows = parseDelimited('nombre,nota\n"Perez, Ana","dijo ""hola"""\n"dos\nlineas",ok\n', ",");
    expect(rows).toStrictEqual([["nombre", "nota"], ["Perez, Ana", 'dijo "hola"'], ["dos\nlineas", "ok"]]);
  });

  it("drops rows that are entirely empty", () => {
    expect(parseDelimited("a,b\n\n1,2\n", ",")).toStrictEqual([["a", "b"], ["1", "2"]]);
  });
});

describe("FileViewer", () => {
  it("renders markdown instead of the source text", async () => {
    mockText("# Informe\n\n**cerrado**\n");
    render(<FileViewer source={source("informe.md")} onClose={vi.fn()} />);

    expect(await screen.findByRole("heading", { level: 1, name: "Informe" })).toBeInTheDocument();
    expect(screen.getByText("cerrado").tagName).toBe("STRONG");
    expect(screen.queryByText("# Informe")).not.toBeInTheDocument();
  });

  it("renders a delimited file as a table with a header row", async () => {
    mockText("cliente,estado\nPerez,activo\nSoto,cerrado\n");
    render(<FileViewer source={source("clientes.csv")} onClose={vi.fn()} />);

    const table = await screen.findByRole("table");
    expect(table).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "cliente" })).toBeInTheDocument();
    expect(screen.getByRole("cell", { name: "Soto" })).toBeInTheDocument();
  });

  it("sandboxes html so no script can run and never injects it as markup", async () => {
    mockText("<script>window.parent.__pwned = true</script><p>hola</p>");
    render(<FileViewer source={source("pagina.html")} onClose={vi.fn()} />);

    const frame = await screen.findByTitle("pagina.html");
    expect(frame.tagName).toBe("IFRAME");
    expect(frame).toHaveAttribute("sandbox", "");
    expect((window as unknown as { __pwned?: boolean }).__pwned).toBeUndefined();
    expect(document.querySelector(".dialog script")).toBeNull();
  });

  it("shows a pdf through the browser viewer without reading it as text", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch");
    render(<FileViewer source={source("informe.pdf", "application/pdf")} onClose={vi.fn()} />);

    const frame = screen.getByTitle("informe.pdf");
    expect(frame).toHaveAttribute("src", "/content/informe.pdf");
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("offers an honest fallback and a download for a format it cannot preview", async () => {
    render(<FileViewer source={source("planilla.xlsx")} onClose={vi.fn()} />);

    expect(await screen.findByText(/No hay vista previa para este formato/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Descargar/ })).toBeInTheDocument();
  });

  it("reports a failed read instead of showing an empty document", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response("nope", { status: 500 }));
    render(<FileViewer source={source("notas.md")} onClose={vi.fn()} />);

    expect(await screen.findByRole("alert")).toHaveTextContent("No pudimos abrir este archivo");
  });

  it("closes from the dialog control", async () => {
    mockText("hola");
    const onClose = vi.fn();
    render(<FileViewer source={source("notas.txt")} onClose={onClose} />);
    await waitFor(() => expect(screen.getByText("hola")).toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: "Cerrar" }));
    expect(onClose).toHaveBeenCalled();
  });
});
