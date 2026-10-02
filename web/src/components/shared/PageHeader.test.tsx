import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { PageHeader } from "./PageHeader";

const source = readFileSync(join(process.cwd(), "src/components/shared/PageHeader.tsx"), "utf8");
const primitives = readFileSync(join(process.cwd(), "src/components/primitives/primitives.css"), "utf8");

describe("PageHeader (DS-SHELL-6)", () => {
  it("renders title, metadata, and every supplied action", () => {
    render(
      <PageHeader
        title="Conversaciones"
        meta="Actividad reciente"
        actions={
          <>
            <button type="button">Exportar</button>
            <button type="button">Actualizar</button>
          </>
        }
      />,
    );

    expect(screen.getByRole("heading", { name: "Conversaciones" })).toBeInTheDocument();
    expect(screen.getByText("Actividad reciente")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Exportar" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Actualizar" })).toBeInTheDocument();
  });

  it("uses tokenized shared classes and wraps actions at responsive widths", () => {
    const { container } = render(<PageHeader title="Clientes" actions={<button type="button">Nuevo cliente</button>} />);

    expect(container.querySelector(".page-header")).toBeInTheDocument();
    expect(container.querySelector(".page-header__actions")).toBeInTheDocument();
    expect(source).not.toContain("style=");
    expect(primitives).toMatch(/\.page-header[\s\S]*?var\(--/);
    expect(primitives).toMatch(/\.page-header__actions[\s\S]*?flex-wrap:\s*wrap/);
  });

  it("keeps the shared rail and plain subtitle CSS contract", () => {
    const header = primitives.match(/\.page-header\s*\{([^}]*)\}/)?.[1] ?? "";
    const subtitle = primitives.match(/\.page-header p\s*\{([^}]*)\}/)?.[1] ?? "";
    expect(header).toMatch(/position:\s*relative/);
    expect(primitives).toMatch(/\.page-header__copy\s*\{[^}]*padding-left:/s);
    expect(primitives).toMatch(/\.page-header__copy::before\s*\{[^}]*background:\s*var\(--lime-700\)/s);
    expect(subtitle).not.toMatch(/border-radius:\s*999px|background:/);
    expect(primitives).not.toMatch(/\.dashboard-(?:meta|header)/);
  });
});
