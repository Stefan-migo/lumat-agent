import { describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import { fireEvent, waitFor } from "@testing-library/react";
import { clients as customers } from "./_shared/mockData/clients";
import { customerStateLabel, customerStateTone } from "./_shared/toneMaps";
import { ClientesListView, ClientesListEmpty, ClientesListFilteredEmpty } from "./ClientesList.stories";
import { ClientesList } from "../../components/pages/ClientesList";

describe("ClientesList page story (R-PRD-PG-6)", () => {
  it("renders the page title", () => {
    render(<ClientesListView />);
    expect(screen.getByRole("heading", { name: "Clientes" })).toBeInTheDocument();
  });

  it("renders the SearchInput-pattern search control", () => {
    render(<ClientesListView />);
    expect(screen.getByRole("searchbox", { name: "Buscar clientes" })).toBeInTheDocument();
  });

  it("renders authenticated client and case export links", () => {
    render(<ClientesListView />);
    expect(screen.getByRole("link", { name: "Exportar clientes CSV" }).getAttribute("href")).toBe(
      "/panel/export/clients.csv",
    );
    expect(screen.getByRole("link", { name: "Exportar casos CSV" }).getAttribute("href")).toBe(
      "/panel/export/cases.csv",
    );
  });

  it("uses same-origin navigation when an export is activated", () => {
    render(<ClientesListView />);
    const exportLink = screen.getByRole("link", { name: "Exportar clientes CSV" });

    fireEvent.click(exportLink);

    expect(exportLink.getAttribute("href")).toBe("/panel/export/clients.csv");
    expect(exportLink.getAttribute("href")).not.toMatch(/^data:text\/csv;base64,/);
  });

  it("keeps denied exports server-controlled without a fabricated fallback", () => {
    render(<ClientesListView />);

    for (const link of screen.getAllByRole("link", { name: /Exportar (clientes|casos) CSV/ })) {
      expect(link.getAttribute("href")).toMatch(/^\/panel\/export\/(clients|cases)\.csv$/);
      expect(link.getAttribute("href")).not.toMatch(/^data:/);
    }
  });

  it("does not fabricate a client-side download when export is server-denied", () => {
    const createObjectURL = vi.fn();
    Object.defineProperty(URL, "createObjectURL", { configurable: true, value: createObjectURL });

    render(<ClientesListView />);
    const exportLink = screen.getByRole("link", { name: "Exportar clientes CSV" });
    const serverEndpoint = "/panel/export/clients.csv";

    fireEvent.click(exportLink);

    expect(createObjectURL).not.toHaveBeenCalled();
    expect(exportLink).toBeInTheDocument();
    expect(exportLink).toHaveAttribute("href", serverEndpoint);
    expect(exportLink.getAttribute("href")).not.toMatch(/^data:|^blob:/);
  });

  it("renders the customer table with R-PRD-PG-6 fields", () => {
    render(<ClientesListView />);
    const table = screen.getByRole("table");
    const first = customers[0];

    // Name → ficha link (scope the row for unambiguous field lookups)
    const nameLink = within(table).getByRole("link", { name: first.name! });
    expect(nameLink.getAttribute("href")).toContain(String(first.id));
    const firstRow = nameLink.closest("tr")!;
    expect(firstRow).not.toBeNull();

    // Phone, state (Spanish label + tone-wired), consent, created
    expect(within(firstRow).getByText(first.phone_e164!)).toBeInTheDocument();
    const stateLabel = customerStateLabel(first.state);
    const stateBadge = within(firstRow).getByText(stateLabel);
    expect(stateBadge.getAttribute("data-tone")).toBe(customerStateTone(first.state));

    const consentCell = within(firstRow).getByText(first.consent_status ? "Sí" : "No");
    expect(consentCell).toBeInTheDocument();
    expect(within(firstRow).getByText(new RegExp("^2026"))).toBeInTheDocument();
  });

  it("renders each customer's approved Spanish state label (triangulation)", () => {
    render(<ClientesListView />);
    const table = screen.getByRole("table");
    // Cover a different state than the first row (e.g. bloqueado → "Bloqueado")
    const blocked = customers.find((c) => c.state === "bloqueado")!;
    const row = within(table).getByRole("link", { name: blocked.name! }).closest("tr")!;
    const badge = within(row).getByText(customerStateLabel(blocked.state));
    expect(badge.getAttribute("data-tone")).toBe(customerStateTone(blocked.state));
  });

  it("renders a stale-data banner pairing status role with a visible label", () => {
    render(<ClientesListView state="stale" />);
    const banner = screen.getByRole("status");
    expect(within(banner).getByText("Datos posiblemente desactualizados")).toBeInTheDocument();
  });

  it("renders a partial-error banner pairing status role with a visible label", () => {
    render(<ClientesListView state="partial-error" />);
    const banner = screen.getByRole("status");
    expect(within(banner).getByText(/no pudimos actualizar parte del listado/i)).toBeInTheDocument();
  });

  it("renders a fatal-error banner pairing alert role with a visible label", () => {
    render(<ClientesListView state="fatal-error" />);
    const banner = screen.getByRole("alert");
    expect(within(banner).getByText(/no pudimos cargar los clientes/i)).toBeInTheDocument();
  });

  it("renders a loading banner pairing status role with a visible label and spinner", () => {
    render(<ClientesListView state="loading" />);
    const banner = screen.getByRole("status");
    expect(within(banner).getByText("Cargando clientes")).toBeInTheDocument();
  });

  it("renders the Consent header", () => {
    render(<ClientesListView />);
    const table = screen.getByRole("table");
    expect(within(table).getByRole("columnheader", { name: "Consentimiento" })).toBeInTheDocument();
  });
});

describe("ClientesList Empty story", () => {
  it("renders the empty state with the approved Spanish message", () => {
    render(<ClientesListEmpty />);
    expect(screen.getByText("No hay registros")).toBeInTheDocument();
  });
});

describe("ClientesList Denied and FilteredEmpty stories", () => {
  it("renders the denied banner pairing alert role with a visible label", () => {
    render(<ClientesListView state="denied" />);
    const banner = screen.getByRole("alert");
    expect(within(banner).getByText("No tienes permiso para ver este panel")).toBeInTheDocument();
  });

  it("renders the filtered-empty state with its recovery action, distinct from the empty state", () => {
    render(<ClientesListFilteredEmpty />);

    expect(screen.getByText("Sin resultados")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Limpiar búsqueda" })).toBeInTheDocument();
    expect(screen.queryByText("No hay registros")).not.toBeInTheDocument();
  });
});

describe("ClientesList appearance axis (amended DS-GRAMMAR-1)", () => {
  it("composes the list into a named region with the shared toolbar and data surface", () => {
    const { container } = render(<ClientesListView />);

    expect(screen.getByRole("region", { name: "Listado de clientes" })).toBeInTheDocument();
    expect(container.querySelector(".toolbar")).not.toBeNull();
    expect(container.querySelector(".data-region")).not.toBeNull();
  });

  it("styles the drill-down link through the shared table link contract", () => {
    render(<ClientesListView />);

    const link = screen.getByRole("link", { name: customers[0].name! });
    expect(link).toHaveClass("table__link");
    expect(link).not.toHaveAttribute("style");
  });

  it("keeps the dense data layer tabular with no conversation component", () => {
    const { container } = render(<ClientesListView />);

    expect(screen.getByRole("table")).toBeInTheDocument();
    expect(
      container.querySelector(".ai-agent-grammar__bubble, .assistant-chat__conversation, .ai-agent-grammar__composer"),
    ).toBeNull();
  });
});

describe("ClientesList API behavior", () => {
  it("adds the search query to the clients API request", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ clients: customers.slice(0, 1), query: "Jorge" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    render(<ClientesList />);
    const search = screen.getByRole("searchbox", { name: "Buscar clientes" });
    fireEvent.change(search, { target: { value: "Jorge" } });

    await waitFor(() => {
      expect(fetchMock.mock.calls.some(([path]) => path === "/panel/api/clients?q=Jorge")).toBe(true);
    });
  });

  it("renders the shared empty message when the API has no matching clients", () => {
    render(<ClientesList data={[]} state="empty" />);

    expect(screen.getByText("No hay registros")).toBeInTheDocument();
  });

  it("encodes spaces in a search query before requesting the API", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ clients: [], query: "Marcela Fuentes" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    render(<ClientesList />);
    fireEvent.change(screen.getByRole("searchbox", { name: "Buscar clientes" }), {
      target: { value: "Marcela Fuentes" },
    });

    await waitFor(() => {
      expect(fetchMock.mock.calls.some(([path]) => path === "/panel/api/clients?q=Marcela%20Fuentes")).toBe(true);
    });
  });
});
