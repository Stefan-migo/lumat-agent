import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { apiFetch } from "../../api";
import { ClientesList } from "./ClientesList";
import type { Customer } from "../../types";

vi.mock("../../api", async () => {
  const actual = await vi.importActual<typeof import("../../api")>("../../api");
  return { ...actual, apiFetch: vi.fn() };
});

const customers: Customer[] = [
  {
    id: 1,
    name: "Marcela Fuentes",
    phone_e164: "+56912345678",
    email: "marcela@example.com",
    comuna: "Ñuñoa",
    address: "Av. Italia 123",
    state: "activo",
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
    state: "bloqueado",
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
    expect(screen.getByText("Activo")).toBeInTheDocument();
    expect(screen.getByText("Bloqueado")).toBeInTheDocument();
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

  it("fetches the list on mount through the panel API", async () => {
    vi.mocked(apiFetch).mockResolvedValue({ clients: customers });

    render(<ClientesList />);

    expect(await screen.findByText("Marcela Fuentes")).toBeInTheDocument();
    expect(apiFetch).toHaveBeenCalledWith("/panel/api/clients");
  });

  // T2 — clearing the search must return to the unfiltered list. Today the refetch only
  // fires for a non-empty query, so a cleared search leaves the filtered result on screen.
  it("resets the list when the search is cleared", async () => {
    const user = userEvent.setup();
    vi.mocked(apiFetch).mockImplementation(async (path: string) =>
      String(path).includes("q=marcela") ? { clients: [customers[0]] } : { clients: customers },
    );

    render(<ClientesList />);
    expect(await screen.findByText("Pedro Soto")).toBeInTheDocument();

    const search = screen.getByLabelText("Buscar clientes");
    await user.type(search, "marcela");
    await waitFor(() => expect(screen.queryByText("Pedro Soto")).not.toBeInTheDocument());

    await user.clear(search);
    await waitFor(() => expect(screen.getByText("Pedro Soto")).toBeInTheDocument());
    expect(apiFetch).toHaveBeenLastCalledWith("/panel/api/clients");
  });
});
