import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { EmptyState } from "./EmptyState";
import { FlashMessage } from "./FlashMessage";
import { PageHeader } from "./PageHeader";
import { StatCard } from "./StatCard";

describe("PageHeader", () => {
  it("renders the title and subtitle/meta", () => {
    render(<PageHeader title="Panel" meta="últimos 30 días" />);
    expect(screen.getByRole("heading", { name: "Panel" })).toBeInTheDocument();
    expect(screen.getByText("últimos 30 días")).toBeInTheDocument();
  });

  it("renders actions when provided", () => {
    render(
      <PageHeader
        title="Casos"
        actions={<button type="button">Exportar CSV</button>}
      />,
    );
    expect(screen.getByRole("button", { name: "Exportar CSV" })).toBeInTheDocument();
  });
});

describe("StatCard", () => {
  it("emits the .kpi primitive class", () => {
    const { container } = render(<StatCard label="Contactos" value={42} />);
    expect(container.querySelector(".kpi")).not.toBeNull();
  });

  it("renders the label and value", () => {
    render(<StatCard label="Contactos" value={42} />);
    expect(screen.getByText("Contactos")).toBeInTheDocument();
    expect(screen.getByText("42")).toBeInTheDocument();
  });
});

describe("EmptyState", () => {
  it("renders title through the .empty-state wrapper", () => {
    render(<EmptyState title="No se encontraron clientes" />);
    expect(screen.getByText("No se encontraron clientes")).toBeInTheDocument();
  });

  it("emits the .empty-state primitive class", () => {
    const { container } = render(<EmptyState title="Vacío" />);
    expect(container.querySelector(".empty-state")).not.toBeNull();
  });
});

describe("FlashMessage", () => {
  it("renders the message text", () => {
    render(<FlashMessage tone="success">Guardado</FlashMessage>);
    expect(screen.getByText("Guardado")).toBeInTheDocument();
  });

  it("emits the .flash-message--{tone} class for each tone", () => {
    const { container } = render(<FlashMessage tone="danger">Bloqueado</FlashMessage>);
    expect(container.querySelector(".flash-message--danger")).not.toBeNull();
  });
});
