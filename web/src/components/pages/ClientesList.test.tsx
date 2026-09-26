import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ApiError, fetchClients, createCustomer, getClientFicha, archiveCustomer, unarchiveCustomer } from "../../api";
import { ClientesList } from "./ClientesList";
import type { Customer } from "../../types";

vi.mock("../../api", async () => {
  const actual = await vi.importActual<typeof import("../../api")>("../../api");
  return { ...actual, fetchClients: vi.fn(), createCustomer: vi.fn(), getClientFicha: vi.fn(), archiveCustomer: vi.fn(), unarchiveCustomer: vi.fn() };
});

const customers: Customer[] = [
  {
    id: 1,
    name: "Marcela Fuentes",
    phone_e164: "+56912345678",
    email: "marcela@example.com",
    comuna: "Ñuñoa",
    address: "Av. Italia 123",
    state: "contactado",
    consent_status: true,
    consent_at: null,
    created_at: "2026-07-15T12:00:00Z",
  },
  {
    id: 2,
    name: "Pedro Soto",
    phone_e164: "+56987654321",
    email: null,
    comuna: null,
    address: null,
    state: "nuevo",
    consent_status: false,
    consent_at: null,
    created_at: "2026-07-16T12:00:00Z",
  },
  {
    id: 3,
    name: null,
    phone_e164: "+56955555555",
    email: null,
    comuna: null,
    address: null,
    state: "en_evaluacion",
    consent_status: true,
    consent_at: null,
    created_at: null,
  },
];

describe("ClientesList", () => {
  beforeEach(() => vi.clearAllMocks());
  afterEach(() => vi.restoreAllMocks());

  it("renders the operational table with the client columns and values", () => {
    render(<ClientesList data={customers} state="ready" />);

    expect(screen.getByRole("main")).toHaveTextContent("Clientes");
    expect(screen.getByRole("columnheader", { name: "Cliente" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Teléfono" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Estado" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Consentimiento" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Creado" })).toBeInTheDocument();

    expect(screen.getByText("Marcela Fuentes")).toBeInTheDocument();
    expect(screen.getByText("+56912345678")).toBeInTheDocument();
    expect(screen.getByText("Contactado")).toBeInTheDocument();
    expect(screen.getByText("En evaluación")).toBeInTheDocument();
    expect(screen.getByText("2026-07-15")).toBeInTheDocument();
    expect(screen.getAllByText("—").length).toBeGreaterThan(0);
  });

  // The plural form only. The singular ("1 clientes") is a known defect fixed in T3 and is
  // deliberately NOT blessed here.
  it("reports the pluralised count for several records", () => {
    render(<ClientesList data={customers} state="ready" />);

    expect(screen.getByText("3 clientes")).toBeInTheDocument();
  });

  // T3 — the singular form. Today the meta renders "1 clientes".
  it("reports the count in the singular for one record", () => {
    render(<ClientesList data={[customers[0]]} state="ready" />);

    expect(screen.getByText("1 cliente")).toBeInTheDocument();
  });

  it("shows the loading status without rendering a table", () => {
    render(<ClientesList data={null} state="loading" />);

    expect(screen.getByRole("heading", { name: "Cargando clientes" })).toBeInTheDocument();
    expect(screen.getByText("Clientes del negocio")).toBeInTheDocument();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });

  // Pre-T7 behaviour: an empty payload and a filtered-to-zero result render the same empty
  // state. T7 splits them and adds a recovery action.
  it("renders the shared empty state for an empty payload and for a zero-row result", () => {
    const { unmount } = render(<ClientesList data={null} state="empty" />);
    expect(screen.getByText("No hay registros")).toBeInTheDocument();

    unmount();
    render(<ClientesList data={[]} state="ready" />);
    expect(screen.getByText("No hay registros")).toBeInTheDocument();
  });

  // T7 — a filtered-to-zero result is distinguishable from an empty list, offers recovery,
  // and the recovery actually clears the search field.
  it("distinguishes a filtered-empty result and offers the search recovery", async () => {
    const user = userEvent.setup();
    vi.mocked(fetchClients).mockImplementation(async ({ query = "" } = {}) =>
      ({ clients: query ? [] : customers }),
    );

    render(<ClientesList />);
    expect(await screen.findByText("Marcela Fuentes")).toBeInTheDocument();

    await user.type(screen.getByLabelText("Buscar clientes"), "zzz");
    expect(await screen.findByText("Sin resultados")).toBeInTheDocument();
    expect(screen.queryByText("No hay registros")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Limpiar búsqueda" }));

    await waitFor(() => expect(screen.getByText("Marcela Fuentes")).toBeInTheDocument());
    expect(screen.getByLabelText("Buscar clientes")).toHaveValue("");
  });

  // T8 — the amended DS-GRAMMAR-1 appearance axis: the surface composes into a named region
  // on the shared panel surface idiom, while the data layer stays control-room.
  it("exposes the list as a named region inside the shared data-surface contract", () => {
    const { container } = render(<ClientesList data={customers} state="ready" />);

    expect(screen.getByRole("region", { name: "Listado de clientes" })).toBeInTheDocument();
    expect(container.querySelector(".data-region")).not.toBeNull();
  });

  it("keeps the dense data layer tabular with no conversation component", () => {
    const { container } = render(<ClientesList data={customers} state="ready" />);

    expect(screen.getByRole("table")).toBeInTheDocument();
    expect(container.querySelector(".ai-agent-grammar__bubble, .assistant-chat__conversation, .ai-agent-grammar__composer")).toBeNull();
  });

  // T9 — the story contract must be able to render the filtered-empty state, which depends on
  // the applied query round-trip and therefore cannot be expressed with data/state alone.
  it("renders the filtered-empty state for a controlled query", () => {
    render(<ClientesList data={[]} state="empty" query="zzz" />);

    expect(screen.getByText("Sin resultados")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Limpiar búsqueda" })).toBeInTheDocument();
  });

  it("renders the stale, partial-error and denied states", () => {
    const { unmount } = render(<ClientesList data={customers} state="stale" />);
    expect(screen.getByRole("heading", { name: "Datos posiblemente desactualizados" })).toBeInTheDocument();
    unmount();

    render(<ClientesList data={customers} state="partial-error" />);
    expect(screen.getByRole("heading", { name: "No pudimos actualizar parte del listado" })).toBeInTheDocument();
    unmount();

    render(<ClientesList data={null} state="denied" />);
    expect(screen.getByRole("heading", { name: "No tienes permiso para ver este panel" })).toBeInTheDocument();
  });

  it("renders the fatal error with a retry control that calls onRetry", async () => {
    const user = userEvent.setup();
    const onRetry = vi.fn();
    render(<ClientesList data={null} state="fatal-error" onRetry={onRetry} />);

    expect(screen.getByRole("alert")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "No pudimos cargar los clientes" })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Reintentar" }));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  // T5 — the recovery control is the panel primitive, not a raw <button>.
  it("uses the Button primitive for the recovery control", () => {
    render(<ClientesList data={null} state="fatal-error" onRetry={vi.fn()} />);

    expect(screen.getByRole("button", { name: "Reintentar" })).toHaveClass("btn");
  });

  // T6 — the filter and export controls belong to the region they control, not to the page header.
  it("binds the search and the exports to a toolbar inside the list content", () => {
    const { container } = render(<ClientesList data={customers} state="ready" />);

    const toolbar = container.querySelector(".toolbar");
    expect(toolbar).not.toBeNull();
    expect(toolbar).toContainElement(screen.getByLabelText("Buscar clientes"));
    expect(toolbar).toContainElement(screen.getByText("Exportar clientes CSV"));
    expect(toolbar).toContainElement(screen.getByText("Exportar casos CSV"));
  });

  it("exposes the search and the two export controls", () => {
    render(<ClientesList data={customers} state="ready" />);

    expect(screen.getByLabelText("Buscar clientes")).toBeInTheDocument();
    expect(screen.getByText("Exportar clientes CSV")).toBeInTheDocument();
    expect(screen.getByText("Exportar casos CSV")).toBeInTheDocument();
  });

  it("opens the client through the drill-down link instead of navigating", async () => {
    const user = userEvent.setup();
    const onOpenClient = vi.fn();
    render(<ClientesList data={customers} state="ready" onOpenClient={onOpenClient} />);

    const link = screen.getByRole("link", { name: "Marcela Fuentes" });
    expect(link).toHaveAttribute("href");

    await user.click(link);
    expect(onOpenClient).toHaveBeenCalledWith(1);
  });

  // T4 — the accessible link colour is a shared contract, not an inline call-site style.
  it("styles the drill-down link through the shared table link contract", () => {
    render(<ClientesList data={customers} state="ready" />);

    const link = screen.getByRole("link", { name: "Marcela Fuentes" });
    expect(link).toHaveClass("table__link");
    expect(link).not.toHaveAttribute("style");
  });

  it("fetches the list on mount through the panel API", async () => {
    vi.mocked(fetchClients).mockResolvedValue({ clients: customers });

    render(<ClientesList />);

    expect(await screen.findByText("Marcela Fuentes")).toBeInTheDocument();
    expect(fetchClients).toHaveBeenCalledWith({ includeArchived: false, query: "" });
  });

  it("opens the create dialog and offers ficha navigation for a duplicate phone", async () => {
    const user = userEvent.setup();
    const onOpenClient = vi.fn();
    vi.mocked(createCustomer).mockRejectedValue(Object.assign(new ApiError(409, "Duplicate", { code: "phone_exists", message: "Duplicate", customer_id: 9 })));
    render(<ClientesList data={customers} state="ready" onOpenClient={onOpenClient} />);
    await user.click(screen.getByRole("button", { name: "Nuevo cliente" }));
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByLabelText("Teléfono")).toBeRequired();
    await user.type(screen.getByLabelText("Teléfono"), "+56912345678");
    await user.click(screen.getByRole("button", { name: "Crear cliente" }));
    await user.click(await screen.findByRole("button", { name: "Abrir la ficha existente" }));
    expect(onOpenClient).toHaveBeenCalledWith(9);
    expect(screen.queryByText("phone_exists")).not.toBeInTheDocument();
  });

  it("loads D7 counts once before confirming archive and supports unarchive", async () => {
    const user = userEvent.setup();
    vi.mocked(getClientFicha).mockResolvedValue({ customer: customers[0], history: { cases: [{ is_open: true }, { is_open: false }], appointments: [{ starts_at: "2099-01-01", status: "booked" }] } } as never);
    vi.mocked(archiveCustomer).mockResolvedValue({ customer: customers[0] });
    render(<ClientesList data={[{ ...customers[0], archived_at: null }]} state="ready" />);
    await user.click(screen.getByRole("button", { name: "Archivar Marcela Fuentes" }));
    expect(getClientFicha).toHaveBeenCalledTimes(1);
    expect(await screen.findByText(/1 caso abierto y 1 visita futura/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Confirmar archivo" }));
    expect(archiveCustomer).toHaveBeenCalledWith(1);

    render(<ClientesList data={[{ ...customers[0], archived_at: "2026-01-01" }]} state="ready" />);
    await user.click(screen.getByRole("button", { name: "Restaurar Marcela Fuentes" }));
    expect(unarchiveCustomer).toHaveBeenCalledWith(1);
  });

  it("surfaces a failed restore to the operator instead of failing silently", async () => {
    const user = userEvent.setup();
    vi.mocked(unarchiveCustomer).mockRejectedValue(new Error("offline"));
    render(<ClientesList data={[{ ...customers[0], archived_at: "2026-01-01" }]} state="ready" />);
    await user.click(screen.getByRole("button", { name: "Restaurar Marcela Fuentes" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("No pudimos restaurar");
  });

  it("shows the archived filter and marks archived customers", () => {
    render(<ClientesList data={[{ ...customers[0], archived_at: "2026-01-01" }]} state="ready" />);
    expect(screen.getByRole("checkbox", { name: "Mostrar archivados" })).toBeInTheDocument();
    expect(screen.getByText("Archivado")).toBeInTheDocument();
  });

  it("requests archived clients only after enabling the toggle", async () => {
    const user = userEvent.setup();
    vi.mocked(fetchClients).mockResolvedValue({ clients: customers });
    render(<ClientesList />);
    await screen.findByText("Marcela Fuentes");
    await user.click(screen.getByRole("checkbox", { name: "Mostrar archivados" }));
    await waitFor(() => expect(fetchClients).toHaveBeenLastCalledWith({ includeArchived: true, query: "" }));
  });

  // T2 — clearing the search must return to the unfiltered list. Today the refetch only
  // fires for a non-empty query, so a cleared search leaves the filtered result on screen.
  it("resets the list when the search is cleared", async () => {
    const user = userEvent.setup();
    vi.mocked(fetchClients).mockImplementation(async ({ query = "" } = {}) =>
      ({ clients: query.toLowerCase() === "marcela" ? [customers[0]] : customers }),
    );

    render(<ClientesList />);
    expect(await screen.findByText("Pedro Soto")).toBeInTheDocument();

    const search = screen.getByLabelText("Buscar clientes");
    await user.type(search, "marcela");
    await waitFor(() => expect(screen.queryByText("Pedro Soto")).not.toBeInTheDocument());

    await user.clear(search);
    await waitFor(() => expect(screen.getByText("Pedro Soto")).toBeInTheDocument());
    expect(fetchClients).toHaveBeenLastCalledWith({ includeArchived: false, query: "" });
  });
});
