import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { Doc } from "../../types";
import { KbList } from "./KbList";

const docs: Doc[] = [
  { id: 1, project_id: null, title: "Manual de atención", format: "pdf", version: 3, active_version: 2, active: true, visibility: "customer", provider: null, model: null, cost_meta: 0.0012, created_at: "2026-07-10T14:02:00-04:00" },
  { id: 2, project_id: null, title: "Procedimiento interno", format: "md", version: 1, active_version: 1, active: false, visibility: "internal", provider: null, model: null, cost_meta: null, created_at: "2026-07-14T09:30:00-04:00" },
];

describe("KbList landing", () => {
  it("renders the page header and the document card composition", () => {
    render(<KbList data={{ docs }} />);

    expect(screen.getByText("Gestiona los documentos y prueba la recuperación de información.")).toBeInTheDocument();
    expect(screen.getByText("2 documentos", { selector: ".page-header__title-row .badge" })).toBeInTheDocument();

    const card = screen.getByRole("heading", { name: "Documentos" }).closest(".card") as HTMLElement;
    expect(within(card).getByRole("searchbox", { name: "Buscar documentos" })).toBeInTheDocument();
    expect(within(card).getByRole("button", { name: "Filtros" })).toBeInTheDocument();
    expect(within(card).getByRole("table")).toBeInTheDocument();
    const firstRow = within(within(card).getByRole("table")).getAllByRole("row")[1];
    expect(within(firstRow).getByText(`v${docs[0].active_version} · Activa`)).toBeInTheDocument();
    expect(within(firstRow).getByText("Cliente · Cliente y Lumat")).toBeInTheDocument();
    expect(within(card).getAllByText("Interno · Solo Lumat").length).toBeGreaterThan(0);
    expect(within(card).getByText("2 documentos", { selector: ".kb-list__count" })).toBeInTheDocument();

    const titleLink = within(firstRow).getByRole("link", { name: /Manual de atención/ });
    expect(titleLink.closest(".kb-list__identity")).toHaveTextContent(`#${docs[0].id} · PDF`);
    expect(screen.getByRole("list", { name: "Documentos" })).toBeInTheDocument();
    const mobileCard = screen.getByRole("listitem", { name: /Manual de atención/ });
    expect(mobileCard).toHaveTextContent("Activo");
    expect(mobileCard).toHaveTextContent("$0.001200");
  });

  it("filters document rows by query and status without another request", () => {
    render(<KbList data={{ docs }} />);
    const table = screen.getByRole("table");
    fireEvent.change(screen.getByRole("searchbox", { name: "Buscar documentos" }), { target: { value: "interno" } });
    expect(within(table).getAllByRole("row")).toHaveLength(2);

    fireEvent.change(screen.getByRole("searchbox", { name: "Buscar documentos" }), { target: { value: "" } });
    fireEvent.click(screen.getByRole("button", { name: "Filtros" }));
    fireEvent.change(screen.getByLabelText("Estado"), { target: { value: "inactive" } });
    expect(within(table).getAllByRole("row")).toHaveLength(2);
    expect(within(table).getByRole("link", { name: /Procedimiento interno/ })).toBeInTheDocument();
    expect(within(table).queryByRole("link", { name: /Manual de atención/ })).toBeNull();
  });
});

describe("KbList retrieval and upload cards", () => {
  it("presents retrieval as a card with an inline search action and advanced options", () => {
    render(<KbList data={{ docs }} />);
    const card = screen.getByRole("heading", { name: "Probar recuperación" }).closest(".card") as HTMLElement;
    expect(card.querySelector(".card__icon .lucide-search")).toBeInTheDocument();
    expect(within(card).getByText("Consulta qué información recupera la base.")).toBeInTheDocument();
    expect(within(card).getByRole("button", { name: "Buscar" }).closest(".kb-search__query")).toBeInTheDocument();
    expect(within(card).getByText("Opciones avanzadas").closest("details")).not.toHaveAttribute("open");
    fireEvent.click(within(card).getByText("Opciones avanzadas"));
    expect(within(card).getByLabelText("Máximo de resultados")).toBeInTheDocument();
    expect(within(card).getByLabelText("Similitud mínima")).toBeInTheDocument();
    expect(within(card).getByText("Los resultados aparecerán aquí después de buscar.")).toBeInTheDocument();
  });

  it("stacks retrieval below documents in the primary column and keeps upload secondary", () => {
    render(<KbList data={{ docs }} />);
    const layout = screen.getByRole("heading", { name: "Documentos" }).closest(".kb-list__layout") as HTMLElement;
    const primary = layout.querySelector(".kb-list__primary") as HTMLElement;
    const secondary = layout.querySelector(".kb-list__secondary") as HTMLElement;
    const documents = within(primary).getByRole("heading", { name: "Documentos" }).closest(".card")!;
    const retrieval = within(primary).getByRole("heading", { name: "Probar recuperación" }).closest(".card")!;
    const upload = within(secondary).getByRole("heading", { name: "Agregar documento" }).closest(".card")!;

    expect(documents.compareDocumentPosition(retrieval) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(secondary.querySelector(".kb-search")).toBeNull();
    expect(upload).toBeInTheDocument();
  });

  it("provides a keyboard-operable upload dropzone and file picker button", () => {
    render(<KbList data={{ docs }} />);
    const card = screen.getByRole("heading", { name: "Agregar documento" }).closest(".card") as HTMLElement;
    expect(card.querySelector(".card__icon .lucide-upload")).toBeInTheDocument();
    expect(within(card).getByText("Sube un documento para que esté disponible en la base de conocimientos.")).toBeInTheDocument();
    expect(within(card).getByText("Arrastra un archivo aquí o selecciónalo desde tu equipo")).toBeInTheDocument();
    expect(within(card).getByRole("button", { name: "Seleccionar archivo" })).toBeInTheDocument();
    expect(within(card).getByLabelText("Archivo (PDF / MD / TXT / CSV)")).toHaveAttribute("type", "file");
  });

  it("opens the upload form in a mobile entry dialog while retaining it in the desktop card", () => {
    render(<KbList data={{ docs }} />);
    const open = screen.getByRole("button", { name: "Agregar documento" });
    expect(open).toHaveClass("kb-list__mobile-add");
    fireEvent.click(open);
    const dialog = screen.getByRole("dialog", { name: "Agregar documento" });
    expect(dialog).toHaveClass("dialog");
    expect(within(dialog).getByLabelText("Título")).toBeInTheDocument();
    expect(dialog.querySelector(".kb-upload-form")).toBeInTheDocument();
  });
});
