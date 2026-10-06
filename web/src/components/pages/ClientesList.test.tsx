import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ApiError, fetchClients, createCustomer, getClientFicha, archiveCustomer, unarchiveCustomer, changeClientState } from "../../api";
import { ClientesList } from "./ClientesList";
import type { Customer } from "../../types";

vi.mock("../../api", async () => {
  const actual = await vi.importActual<typeof import("../../api")>("../../api");
  return { ...actual, fetchClients: vi.fn(), createCustomer: vi.fn(), getClientFicha: vi.fn(), archiveCustomer: vi.fn(), unarchiveCustomer: vi.fn(), changeClientState: vi.fn() };
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
    allowed_transitions: ["pendiente", "agendado", "en_evaluacion", "finalizado", "cancelado"],
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

type User = ReturnType<typeof userEvent.setup>;

/** Opens a row's action menu and returns it scoped to that row's accessible name. */
async function openRowActions(user: User, row: HTMLElement, name: string) {
  await user.click(within(row).getByRole("button", { name: `Acciones para ${name}` }));
  return within(await screen.findByRole("menu", { name: `Acciones para ${name}` }));
}

function desktopRow(container: HTMLElement, text: string) {
  return Array.from(container.querySelectorAll(".table-card__desktop tr")).find((row) => row.textContent?.includes(text)) as HTMLElement;
}

describe("ClientesList", () => {
  beforeEach(() => vi.clearAllMocks());
  afterEach(() => vi.restoreAllMocks());

  it("renders the operational table with the client columns and values", () => {
    render(<ClientesList data={customers} state="ready" />);

    expect(screen.getByRole("main")).toHaveTextContent("Clientes");
    const table = screen.getByRole("table");
    expect(within(table).getByRole("columnheader", { name: "Cliente" })).toBeInTheDocument();
    expect(within(table).getByRole("columnheader", { name: "Registro" })).toBeInTheDocument();
    expect(within(table).getByRole("columnheader", { name: "Teléfono" })).toBeInTheDocument();
    expect(within(table).getByRole("columnheader", { name: "Estado" })).toBeInTheDocument();
    expect(within(table).getByRole("columnheader", { name: "Consentimiento" })).toBeInTheDocument();
    expect(within(table).getByRole("columnheader", { name: "Creado ↓" })).toBeInTheDocument();

    // The client name and phone remain distinct reference columns.
    const cell = within(table).getByRole("link", { name: "Marcela Fuentes" }).closest(".table__resource");
    expect(cell).not.toBeNull();
    expect(cell!.querySelector(".table__resource-avatar")).toHaveTextContent("MF");
    expect(within(cell as HTMLElement).queryByText("+56912345678")).not.toBeInTheDocument();
    expect(within(table).getByText("Marcela Fuentes")).toBeInTheDocument();
    expect(within(table).getByRole("cell", { name: "+56912345678" })).toBeInTheDocument();
    expect(screen.getAllByText("Contactado").length).toBeGreaterThan(1);
    expect(screen.getAllByText("En evaluación").length).toBeGreaterThan(1);
    expect(within(table).getByText("15 jul 2026")).toBeInTheDocument();
    expect(screen.getAllByText("—").length).toBeGreaterThan(0);
  });

  it("omits the muted phone line when the customer has no phone", () => {
    const { container } = render(<ClientesList data={[{ ...customers[0], phone_e164: null }]} state="ready" />);

    const cell = container.querySelector(".table-card__desktop .table__resource");
    expect(cell).not.toBeNull();
    expect(cell!.querySelector(".table__resource-avatar")).toHaveTextContent("MF");
    expect(cell!.querySelector(".table__resource-meta")).toBeNull();
  });

  // The plural form only. The singular ("1 clientes") is a known defect fixed in T3 and is
  // deliberately NOT blessed here.
  it("reports the pluralised count for several records", () => {
    render(<ClientesList data={customers} state="ready" />);

    const titleRow = screen.getByRole("heading", { name: "Clientes" }).closest(".page-header__title-row");
    expect(titleRow).not.toBeNull();
    expect(within(titleRow as HTMLElement).getByText("3")).toBeInTheDocument();
  });

  // T3 — the singular form. Today the meta renders "1 clientes".
  it("reports the count in the singular for one record", () => {
    render(<ClientesList data={[customers[0]]} state="ready" />);

    expect(screen.getByText("Mostrando 1 de 1 clientes")).toBeInTheDocument();
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
    expect(await within(await screen.findByRole("table")).findByText("Marcela Fuentes")).toBeInTheDocument();

    await user.type(screen.getByLabelText("Buscar clientes"), "zzz");
    expect(await screen.findByText("Sin resultados")).toBeInTheDocument();
    expect(screen.queryByText("No hay registros")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Limpiar búsqueda" }));

    await waitFor(() => expect(within(screen.getByRole("table")).getByText("Marcela Fuentes")).toBeInTheDocument());
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

  it("shows all customer-state tabs in canonical order with counts and filters by state", async () => {
    const user = userEvent.setup();
    const allStates: Customer[] = ["nuevo", "contactado", "pendiente", "agendado", "en_evaluacion", "finalizado", "cancelado", "postventa"].map((state, index) => ({
      ...customers[0], id: index + 1, name: `Customer ${state}`, state: state as Customer["state"],
    }));
    render(<ClientesList data={allStates} state="ready" />);

    const tabs = screen.getAllByRole("tab");
    expect(tabs.map((tab) => tab.textContent?.replace(/\s+/g, " ").trim())).toEqual([
      "Todos 8", "Nuevo 1", "Contactado 1", "Pendiente 1", "Agendado 1", "En evaluación 1", "Finalizado 1", "Cancelado 1", "Postventa 1",
    ]);
    await user.click(screen.getByRole("tab", { name: "Cancelado 1" }));
    expect(within(screen.getByRole("table")).getByRole("link", { name: "Customer cancelado" })).toBeInTheDocument();
    expect(within(screen.getByRole("table")).queryByRole("link", { name: "Customer nuevo" })).not.toBeInTheDocument();
    expect(screen.getByText("Mostrando 1 de 1 clientes")).toBeInTheDocument();
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

  it("binds the search and filters to the list card and keeps exports in the page header", () => {
    const { container } = render(<ClientesList data={customers} state="ready" />);

    const toolbar = container.querySelector(".clientes-list__toolbar");
    expect(toolbar).not.toBeNull();
    expect(toolbar).toContainElement(screen.getByLabelText("Buscar clientes"));
    expect(toolbar).not.toContainElement(screen.getByRole("button", { name: "Exportar" }));
    expect(screen.getByRole("button", { name: "Nuevo cliente" }).closest(".page-header__actions")).not.toBeNull();
  });

  it("exposes the search and export dropdown", () => {
    render(<ClientesList data={customers} state="ready" />);

    expect(screen.getByLabelText("Buscar clientes")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Exportar" })).toBeInTheDocument();
  });

  it("opens the client through the drill-down link instead of navigating", async () => {
    const user = userEvent.setup();
    const onOpenClient = vi.fn();
    render(<ClientesList data={customers} state="ready" onOpenClient={onOpenClient} />);

    const link = screen.getAllByRole("link", { name: "Marcela Fuentes" }).find((item) => item.closest(".table-card__desktop"))!;
    expect(link).toHaveAttribute("href");

    await user.click(link);
    expect(onOpenClient).toHaveBeenCalledWith(1);
  });

  // T4 — the accessible link colour is a shared contract, not an inline call-site style.
  it("styles the drill-down link without browser-default underlining", () => {
    render(<ClientesList data={customers} state="ready" />);

    const link = screen.getAllByRole("link", { name: "Marcela Fuentes" }).find((item) => item.closest(".table-card__desktop"))!;
    expect(link).toHaveClass("clientes-list__name");
    expect(link).not.toHaveAttribute("style");
  });

  it("fetches the list on mount through the panel API", async () => {
    vi.mocked(fetchClients).mockResolvedValue({ clients: customers });

    render(<ClientesList />);

    expect(await within(await screen.findByRole("table")).findByText("Marcela Fuentes")).toBeInTheDocument();
    expect(fetchClients).toHaveBeenCalledWith({ onlyArchived: false, query: "", consent: undefined, sort: "created_desc" });
  });

  it("changes a client's state from the row and refreshes the list", async () => {
    const user = userEvent.setup();
    vi.mocked(fetchClients).mockResolvedValue({ clients: customers });
    vi.mocked(changeClientState).mockResolvedValue({ customer: { ...customers[0], state: "en_evaluacion" } } as never);

    render(<ClientesList />);
    const row = Array.from((await screen.findByRole("table")).querySelectorAll("tr")).find((item) => item.textContent?.includes("Marcela Fuentes")) as HTMLElement;
    expect(row).not.toBeNull();
    const menu = await openRowActions(user, row!, "Marcela Fuentes");
    await user.click(menu.getByRole("menuitem", { name: "Cambiar estado" }));
    expect(screen.getAllByRole("radio").map((radio) => radio.getAttribute("aria-label") ?? radio.textContent)).toHaveLength(5);
    expect(screen.queryByRole("radio", { name: "Nuevo" })).not.toBeInTheDocument();
    await user.click(screen.getByRole("radio", { name: /En evaluación/ }));
    await user.click(screen.getByRole("button", { name: "Guardar estado" }));

    expect(changeClientState).toHaveBeenCalledWith(1, "en_evaluacion");
    await waitFor(() => expect(fetchClients).toHaveBeenCalledTimes(2));
  });

  it("shows no state options or save action for a terminal customer", async () => {
    const user = userEvent.setup();
    const terminal = { ...customers[1], state: "cancelado" as const, allowed_transitions: [] };
    render(<ClientesList data={[terminal]} state="ready" />);
    const row = desktopRow(document.body, "Pedro Soto");
    await user.click((await openRowActions(user, row, "Pedro Soto")).getByRole("menuitem", { name: "Cambiar estado" }));
    expect(screen.getByRole("status")).toHaveTextContent("no tiene transiciones");
    expect(screen.queryByRole("radio")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Guardar estado" })).not.toBeInTheDocument();
  });

  it("opens the create dialog and offers ficha navigation for a duplicate phone", async () => {
    const user = userEvent.setup();
    const onOpenClient = vi.fn();
    vi.mocked(createCustomer).mockRejectedValue(Object.assign(new ApiError(409, "Duplicate", { code: "phone_exists", message: "Duplicate", customer_id: 9 })));
    render(<ClientesList data={customers} state="ready" onOpenClient={onOpenClient} />);
    await user.click(screen.getByRole("button", { name: "Nuevo cliente" }));
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByText("Registra sus datos de contacto y ubicación.")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Datos de contacto" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Ubicación" })).toBeInTheDocument();
    expect(screen.getByLabelText("Teléfono")).toBeRequired();
    await user.click(screen.getByLabelText("Teléfono")); await user.paste("+56912345678");
    await user.click(screen.getByLabelText("Nombre (opcional)")); await user.paste("Carla Núñez");
    await user.click(screen.getByLabelText("Correo (opcional)")); await user.paste("carla@example.com");
    await user.click(screen.getByLabelText("Comuna (opcional)")); await user.paste("Providencia");
    await user.click(screen.getByLabelText("Dirección (opcional)")); await user.paste("Av. Providencia 123");
    await user.click(screen.getByRole("button", { name: "Crear cliente" }));
    expect(createCustomer).toHaveBeenCalledWith({ phone: "+56912345678", name: "Carla Núñez", email: "carla@example.com", comuna: "Providencia", address: "Av. Providencia 123" });
    await user.click(await screen.findByRole("button", { name: "Abrir la ficha existente" }));
    expect(onOpenClient).toHaveBeenCalledWith(9);
    expect(screen.queryByText("phone_exists")).not.toBeInTheDocument();
  });

  it("loads D7 counts once before confirming archive and supports unarchive", async () => {
    const user = userEvent.setup();
    vi.mocked(getClientFicha).mockResolvedValue({ customer: customers[0], history: { cases: [{ is_open: true }, { is_open: false }], appointments: [{ starts_at: "2099-01-01", status: "booked" }] } } as never);
    vi.mocked(archiveCustomer).mockResolvedValue({ customer: customers[0] });
    const { unmount } = render(<ClientesList data={[{ ...customers[0], archived_at: null }]} state="ready" />);
    const activeRow = desktopRow(document.body, "Marcela Fuentes");
    await user.click((await openRowActions(user, activeRow, "Marcela Fuentes")).getByRole("menuitem", { name: "Archivar" }));
    expect(getClientFicha).toHaveBeenCalledTimes(1);
    await waitFor(() => expect(screen.getAllByText("1", { selector: ".clientes-list__archive-stats strong" })).toHaveLength(2));
    await user.click(screen.getByRole("button", { name: "Archivar cliente" }));
    expect(archiveCustomer).toHaveBeenCalledWith(1);
    unmount();

    render(<ClientesList data={[{ ...customers[0], archived_at: "2026-01-01" }]} state="ready" />);
    const archivedRow = desktopRow(document.body, "Marcela Fuentes");
    await user.click((await openRowActions(user, archivedRow, "Marcela Fuentes")).getByRole("menuitem", { name: "Restaurar" }));
    expect(unarchiveCustomer).toHaveBeenCalledWith(1);
  });

  it("surfaces a failed restore to the operator instead of failing silently", async () => {
    const user = userEvent.setup();
    vi.mocked(unarchiveCustomer).mockRejectedValue(new Error("offline"));
    render(<ClientesList data={[{ ...customers[0], archived_at: "2026-01-01" }]} state="ready" />);
    const row = desktopRow(document.body, "Marcela Fuentes");
    await user.click((await openRowActions(user, row, "Marcela Fuentes")).getByRole("menuitem", { name: "Restaurar" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("No pudimos restaurar");
  });

  it("shows the archived filter and marks archived customers", () => {
    render(<ClientesList data={[{ ...customers[0], archived_at: "2026-01-01" }]} state="ready" />);
    expect(screen.getByRole("switch", { name: "Mostrar archivados" })).toBeInTheDocument();
    expect(within(screen.getByRole("table")).getByText("Archivado")).toBeInTheDocument();
  });

  it("requests archived clients only after enabling the toggle", async () => {
    const user = userEvent.setup();
    vi.mocked(fetchClients).mockResolvedValue({ clients: customers });
    render(<ClientesList />);
    await within(await screen.findByRole("table")).findByText("Marcela Fuentes");
    await user.click(screen.getByRole("switch", { name: "Mostrar archivados" }));
    await waitFor(() => expect(fetchClients).toHaveBeenLastCalledWith({ onlyArchived: true, query: "", consent: undefined, sort: "created_desc" }));
  });

  it("resets pagination and selection when the archived filter changes", async () => {
    const user = userEvent.setup();
    const manyCustomers = Array.from({ length: 12 }, (_, index) => ({ ...customers[0], id: index + 1, name: `Customer ${index + 1}` }));
    render(<ClientesList data={manyCustomers} state="ready" />);

    await user.click(screen.getByRole("checkbox", { name: "Seleccionar todos" }));
    await user.click(screen.getByRole("button", { name: "Página siguiente" }));
    expect(screen.getByText("2", { selector: ".table-footer__page" })).toBeInTheDocument();
    expect(screen.getByText("10 seleccionados")).toBeInTheDocument();

    await user.click(screen.getByRole("switch", { name: "Mostrar archivados" }));

    expect(screen.getByText("1", { selector: ".table-footer__page" })).toBeInTheDocument();
    expect(screen.queryByText("10 seleccionados")).not.toBeInTheDocument();
  });

  it("renders the paginated client cards with identity, details, and row actions", () => {
    const { container } = render(<ClientesList data={[{ ...customers[0], archived_at: "2026-01-01" }]} state="ready" />);
    const list = screen.getByRole("list", { name: "Lista de clientes" });
    const card = within(list).getByRole("listitem");

    expect(within(card).getByRole("link", { name: "Marcela Fuentes" })).toHaveAttribute("href");
    expect(within(card).getByRole("checkbox", { name: "Seleccionar Marcela Fuentes" })).toBeInTheDocument();
    expect(card).toHaveTextContent("RegistroArchivado");
    expect(card).toHaveTextContent("Teléfono+56912345678");
    expect(card).toHaveTextContent("EstadoContactado");
    expect(card).toHaveTextContent("ConsentimientoSí");
    expect(card).toHaveTextContent("Creado15 jul 2026");
    expect(within(card).getByRole("button", { name: "Acciones para Marcela Fuentes" })).toBeInTheDocument();
    expect(container.querySelector(".clientes-list__mobile-card")?.textContent).not.toContain(">");
  });

  // T2 — clearing the search must return to the unfiltered list. Today the refetch only
  // fires for a non-empty query, so a cleared search leaves the filtered result on screen.
  it("resets the list when the search is cleared", async () => {
    const user = userEvent.setup();
    vi.mocked(fetchClients).mockImplementation(async ({ query = "" } = {}) =>
      ({ clients: query.toLowerCase() === "marcela" ? [customers[0]] : customers }),
    );

    render(<ClientesList />);
    expect(await within(await screen.findByRole("table")).findByText("Pedro Soto")).toBeInTheDocument();

    const search = screen.getByLabelText("Buscar clientes");
    await user.type(search, "marcela");
    await waitFor(() => expect(within(screen.getByRole("table")).queryByText("Pedro Soto")).not.toBeInTheDocument());

    await user.clear(search);
    await waitFor(() => expect(within(screen.getByRole("table")).getByText("Pedro Soto")).toBeInTheDocument());
    expect(fetchClients).toHaveBeenLastCalledWith({ onlyArchived: false, query: "", consent: undefined, sort: "created_desc" });
  });
});

// panel-action-affordances — the row action is one icon trigger named for the row,
// not two pills whose visible labels repeat the customer name and dominate the cell
// (DESIGN_SYSTEM.md:475).
describe("ClientesList — row actions", () => {
  beforeEach(() => vi.clearAllMocks());

  it("gives each row only its action menu", () => {
    render(<ClientesList data={customers} state="ready" />);

    const row = desktopRow(document.body, "Marcela Fuentes");
    expect(row).not.toBeNull();
    expect(within(row!).getAllByRole("button")).toHaveLength(1);
    expect(
      within(row!).getByRole("button", { name: "Acciones para Marcela Fuentes" }),
    ).toBeInTheDocument();
  });

  it("keeps the customer name out of the visible action text", () => {
    render(<ClientesList data={customers} state="ready" />);

    const row = desktopRow(document.body, "Marcela Fuentes");
    for (const control of within(row).getAllByRole("button")) {
      expect(control.textContent).not.toContain("Marcela Fuentes");
    }
  });

  it("falls back to the phone when the customer has no name", () => {
    render(<ClientesList data={customers} state="ready" />);

    const row = desktopRow(document.body, "+56955555555");
    expect(
      within(row).getByRole("button", { name: "Acciones para +56955555555" }),
    ).toBeInTheDocument();
  });

  it("wraps the row actions in the shared action-cell contract", () => {
    const { container } = render(<ClientesList data={customers} state="ready" />);

    const cell = container.querySelector(".table__actions");
    expect(cell).not.toBeNull();
    expect(cell!.querySelector(".menu__trigger")).not.toBeNull();
  });

  it("offers page-composable selection and pagination controls", async () => {
    const user = userEvent.setup();
    render(<ClientesList data={customers} state="ready" />);
    await user.click(screen.getByRole("checkbox", { name: "Seleccionar todos" }));
    expect(screen.getByText("3 seleccionados")).toBeInTheDocument();
    expect(screen.getByText("Mostrando 3 de 3 clientes")).toBeInTheDocument();
  });

  it("routes Cambiar estado from the row menu to the state dialog", async () => {
    const user = userEvent.setup();
    render(<ClientesList data={customers} state="ready" />);

    const row = desktopRow(document.body, "Marcela Fuentes");
    const menu = await openRowActions(user, row, "Marcela Fuentes");
    await user.click(menu.getByRole("menuitem", { name: "Cambiar estado" }));

    expect(await screen.findByRole("dialog")).toHaveTextContent("Cambiar estado del cliente");
  });

  it("marks Archivar as a destructive item with an icon and its label", async () => {
    const user = userEvent.setup();
    render(<ClientesList data={[{ ...customers[0], archived_at: null }]} state="ready" />);

    const row = desktopRow(document.body, "Marcela Fuentes");
    const menu = await openRowActions(user, row, "Marcela Fuentes");
    const archive = menu.getByRole("menuitem", { name: "Archivar" });

    expect(archive).toHaveClass("menu__item--danger");
    expect(archive.querySelector("svg")).not.toBeNull();
    expect(archive).toHaveTextContent("Archivar");
  });

  it("offers Restaurar instead of Archivar for an archived customer", async () => {
    const user = userEvent.setup();
    render(<ClientesList data={[{ ...customers[0], archived_at: "2026-01-01" }]} state="ready" />);

    const row = desktopRow(document.body, "Marcela Fuentes");
    const menu = await openRowActions(user, row, "Marcela Fuentes");

    expect(menu.getByRole("menuitem", { name: "Restaurar" })).toBeInTheDocument();
    expect(menu.queryByRole("menuitem", { name: "Archivar" })).not.toBeInTheDocument();
  });
});
