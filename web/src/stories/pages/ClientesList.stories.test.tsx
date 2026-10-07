import { describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import { fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { clients as customers } from "./_shared/mockData/clients";
import { customerStateLabel, customerStateTone } from "./_shared/toneMaps";
import { ClientesListView, ClientesListEmpty, ClientesListFilteredEmpty } from "./ClientesList.stories";
import { ClientesList } from "../../components/pages/ClientesList";
import type { CustomerState } from "../../types";

describe("ClientesList page story (R-PRD-PG-6)", () => {
  it("renders the page title", () => {
    render(<ClientesListView />);
    expect(screen.getByRole("heading", { name: "Clientes" })).toBeInTheDocument();
  });

  it("renders the SearchInput-pattern search control", () => {
    render(<ClientesListView />);
    expect(screen.getByRole("searchbox", { name: "Buscar clientes" })).toBeInTheDocument();
  });

  it("renders the export menu", () => {
    render(<ClientesListView />);
    expect(screen.getByRole("button", { name: "Exportar" })).toBeInTheDocument();
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
    expect(within(firstRow).getByRole("cell", { name: first.phone_e164! })).toBeInTheDocument();
    const stateLabel = customerStateLabel(first.state);
    const stateBadge = within(firstRow).getByText(stateLabel);
    expect(stateBadge.getAttribute("data-tone")).toBe(customerStateTone(first.state));

    const consentCell = within(firstRow).getByText(first.consent_status ? "Sí" : "No");
    expect(consentCell).toBeInTheDocument();
    expect(within(firstRow).getByText(/\d{1,2} \w{3} 2026/)).toBeInTheDocument();
  });

  it("renders each customer's approved Spanish state label (triangulation)", () => {
    render(<ClientesListView />);
    const table = screen.getByRole("table");
    // Cover a different state than the first row (e.g. en_evaluacion → "En evaluación")
    const evaluating = customers.find((c) => c.state === "en_evaluacion")!;
    const row = within(table).getByRole("link", { name: evaluating.name! }).closest("tr")!;
    const badge = within(row).getByText(customerStateLabel(evaluating.state));
    expect(badge.getAttribute("data-tone")).toBe(customerStateTone(evaluating.state));
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
    expect(container.querySelector(".clientes-list__toolbar")).not.toBeNull();
    expect(container.querySelector(".clientes-list__card")).not.toBeNull();
    expect(container.querySelector(".data-region")).not.toBeNull();
  });

  it("styles the drill-down link without browser-default underlining", () => {
    render(<ClientesListView />);

    const link = within(screen.getByRole("table")).getByRole("link", { name: customers[0].name! });
    expect(link).toHaveClass("clientes-list__name");
    expect(link).not.toHaveAttribute("style");
  });

  it("shows the row actions as one icon menu per row in the shared action cell", () => {
    const { container } = render(<ClientesListView />);

    const cell = container.querySelector(".table__actions");
    expect(cell).not.toBeNull();
    expect(
      within(cell as HTMLElement).getByRole("button", {
        name: `Acciones para ${customers[0].name}`,
      }),
    ).toBeInTheDocument();
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
  it("offers only the allowed lifecycle transitions in the dialog", async () => {
    const customer = { ...customers[0], allowed_transitions: ["contactado", "pendiente"] as CustomerState[] };
    render(<ClientesList data={[customer]} state="ready" />);
    const user = userEvent.setup();
    const row = within(screen.getByRole("table")).getByRole("link", { name: customer.name! }).closest("tr")!;
    await user.click(within(row).getByRole("button", { name: `Acciones para ${customer.name}` }));
    await user.click(await screen.findByRole("menuitem", { name: "Cambiar estado" }));
    expect(screen.getAllByRole("radio")).toHaveLength(2);
    expect(screen.getByRole("radio", { name: "Contactado" })).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: "Pendiente" })).toBeInTheDocument();
    expect(screen.queryByRole("radio", { name: "Nuevo" })).not.toBeInTheDocument();
  });

  it("adds the search query to the clients API request", async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(
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
      expect(fetchMock.mock.calls.some(([path]) => path === "/panel/api/clients?q=Jorge&sort=created_desc")).toBe(true);
    });
  });

  it("renders the shared empty message when the API has no matching clients", () => {
    render(<ClientesList data={[]} state="empty" />);

    expect(screen.getByText("No hay registros")).toBeInTheDocument();
  });

  it("encodes spaces in a search query before requesting the API", async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(
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
      expect(fetchMock.mock.calls.some(([path]) => path === "/panel/api/clients?q=Marcela+Fuentes&sort=created_desc")).toBe(true);
    });
  });

  it("sends include_archived, not only_archived, when the archived toggle is enabled", async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(new Response(JSON.stringify({ clients: customers }), { status: 200, headers: { "Content-Type": "application/json" } }));
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    render(<ClientesList />);
    await screen.findByRole("table");
    await user.click(screen.getByRole("switch", { name: "Mostrar archivados" }));
    await waitFor(() => expect(fetchMock.mock.calls.some(([url]) => String(url).includes("include_archived=true"))).toBe(true));
    expect(fetchMock.mock.calls.some(([url]) => String(url).includes("only_archived=true"))).toBe(false);
  });

});
