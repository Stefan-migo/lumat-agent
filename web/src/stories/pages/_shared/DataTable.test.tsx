import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { DataTable } from "./DataTable";

interface Row {
  id: number;
  name: string;
}

const COLUMNS = [
  { key: "name", header: "Name", render: (r: Row) => r.name },
];

describe("DataTable", () => {
  it("renders column headers", () => {
    render(
      <DataTable<Row>
        columns={COLUMNS}
        rows={[{ id: 1, name: "Ada" }]}
      />,
    );
    expect(screen.getByRole("columnheader", { name: "Name" })).toBeInTheDocument();
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

  it("renders the empty message via .empty-state when rows are empty", () => {
    render(
      <DataTable<Row>
        columns={COLUMNS}
        rows={[]}
        emptyMessage="No customers found"
      />,
    );
    expect(screen.getByText("No customers found")).toBeInTheDocument();
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

  it("renders an actions cell when the actions renderer is provided", () => {
    render(
      <DataTable<Row>
        columns={COLUMNS}
        rows={[{ id: 1, name: "Ada" }]}
        actions={(r) => <button type="button">Edit {r.name}</button>}
      />,
    );
    expect(screen.getByRole("button", { name: "Edit Ada" })).toBeInTheDocument();
  });

  it("renders the name as a header regardless of row data", () => {
    render(
      <DataTable<Row>
        columns={COLUMNS}
        rows={[{ id: 7, name: "Linus" }]}
      />,
    );
    expect(screen.getByRole("columnheader", { name: "Name" })).toBeInTheDocument();
    expect(screen.getByRole("cell", { name: "Linus" })).toBeInTheDocument();
  });
});
