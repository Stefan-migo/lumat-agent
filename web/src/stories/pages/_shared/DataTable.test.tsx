import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { DataTable, tabularNum } from "./DataTable";

interface Row {
  id: number;
  name: string;
}

const COLUMNS = [
  { key: "name", header: "Nombre", render: (r: Row) => r.name },
];

describe("DataTable", () => {
  it("renders column headers", () => {
    render(
      <DataTable<Row>
        columns={COLUMNS}
        rows={[{ id: 1, name: "Ada" }]}
      />,
    );
    expect(screen.getByRole("columnheader", { name: "Nombre" })).toBeInTheDocument();
  });

  it("renders a cell for each row", () => {
    render(
      <DataTable<Row>
        columns={COLUMNS}
        rows={[
          { id: 1, name: "Ada" },
          { id: 2, name: "Grace" },
        ]}
      />,
    );
    expect(screen.getAllByRole("row")).toHaveLength(3); // header + 2 data rows
    expect(screen.getByRole("cell", { name: "Ada" })).toBeInTheDocument();
    expect(screen.getByRole("cell", { name: "Grace" })).toBeInTheDocument();
  });

  it("defaults the empty message to 'No hay registros' (DS-UI-TABLES)", () => {
    render(<DataTable<Row> columns={COLUMNS} rows={[]} />);
    expect(screen.getByText("No hay registros")).toBeInTheDocument();
  });

  it("renders the empty message via .empty-state when rows are empty", () => {
    render(
      <DataTable<Row>
        columns={COLUMNS}
        rows={[]}
        emptyMessage="No se encontraron clientes"
      />,
    );
    expect(screen.getByText("No se encontraron clientes")).toBeInTheDocument();
  });

  it("emits the table primitive class", () => {
    const { container } = render(
      <DataTable<Row>
        columns={COLUMNS}
        rows={[{ id: 1, name: "Ada" }]}
      />,
    );
    expect(container.querySelector("table")!.className).toContain("table");
  });

  it("defaults the actions header to 'Acciones' and renders each action cell", () => {
    render(
      <DataTable<Row>
        columns={COLUMNS}
        rows={[{ id: 1, name: "Ada" }]}
        actions={(r) => <button type="button">Editar {r.name}</button>}
      />,
    );
    expect(screen.getByRole("columnheader", { name: "Acciones" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Editar Ada" })).toBeInTheDocument();
  });

  it("honors a custom actionsHeader", () => {
    render(
      <DataTable<Row>
        columns={COLUMNS}
        rows={[{ id: 1, name: "Ada" }]}
        actionsHeader="Opciones"
        actions={() => <button type="button">Ver</button>}
      />,
    );
    expect(screen.getByRole("columnheader", { name: "Opciones" })).toBeInTheDocument();
  });

  it("renders a loading state instead of rows when loading", () => {
    render(
      <DataTable<Row>
        columns={COLUMNS}
        rows={[{ id: 1, name: "Ada" }]}
        loading
      />,
    );
    expect(screen.getByText(/Cargando/i)).toBeInTheDocument();
    expect(screen.queryByRole("table")).toBeNull();
  });

  it("renders a stale note above the table when stale", () => {
    const { container } = render(
      <DataTable<Row>
        columns={COLUMNS}
        rows={[{ id: 1, name: "Ada" }]}
        stale
      />,
    );
    expect(screen.getByText(/desactualizad/i)).toBeInTheDocument();
    expect(container.querySelector("table")).not.toBeNull();
  });

  it("renders the name as a header regardless of row data", () => {
    render(
      <DataTable<Row>
        columns={COLUMNS}
        rows={[{ id: 7, name: "Linus" }]}
      />,
    );
    expect(screen.getByRole("columnheader", { name: "Nombre" })).toBeInTheDocument();
    expect(screen.getByRole("cell", { name: "Linus" })).toBeInTheDocument();
  });
});

describe("tabularNum (DS-UI-TABLES)", () => {
  it("wraps a numeric cell with tabular-nums alignment via --corp-value for comparable numbers", () => {
    const { container } = render(<>{tabularNum(42)}{tabularNum(7)}</>);
    const spans = container.querySelectorAll("span");
    expect(spans).toHaveLength(2);
    for (const span of spans) {
      // D3 / CST-ALIAS-5: the numeric alignment resolves through --corp-value.
      expect(span.style.fontVariantNumeric).toBe("var(--corp-value)");
    }
  });
});

