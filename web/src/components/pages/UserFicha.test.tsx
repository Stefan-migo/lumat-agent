import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, getAdminUser, resetUserPassword, toggleUserActive, unlockUser, updateAdminUser } from "../../api";
import { UserFicha } from "./UserFicha";

vi.mock("../../api", async (importActual) => ({
  ...(await importActual<typeof import("../../api")>()),
  getAdminUser: vi.fn(), resetUserPassword: vi.fn(), toggleUserActive: vi.fn(), unlockUser: vi.fn(), updateAdminUser: vi.fn(),
}));

const lockedUser = { id: 8, username: "carlos", role: "tecnico" as const, active: true, name: "Carlos", phone: "+56912345678", email: "carlos@example.cl", position: "Técnico", locked_until: "2026-10-01T14:00:00Z", failed_logins: 5 };

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(getAdminUser).mockResolvedValue({ user: lockedUser });
  vi.mocked(updateAdminUser).mockResolvedValue({ user: { ...lockedUser, locked_until: null, failed_logins: 0 } });
  vi.mocked(unlockUser).mockResolvedValue({ user: { ...lockedUser, locked_until: null, failed_logins: 0 } });
  vi.mocked(toggleUserActive).mockResolvedValue({ user: { ...lockedUser, active: false } });
  vi.mocked(resetUserPassword).mockResolvedValue({ user: lockedUser });
});

describe("UserFicha", () => {
  it("loads profile data and renders the details and locked security state", async () => {
    render(<UserFicha userId={8} />);
    expect(await screen.findByRole("heading", { name: "Detalle del usuario" })).toBeInTheDocument();
    expect(screen.getByText("Consulta y actualiza los datos de esta cuenta.")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Carlos" })).toBeInTheDocument();
    expect(screen.getByText("Usuario de acceso")).toBeInTheDocument();
    expect(screen.getByText("carlos")).toBeInTheDocument();
    expect(screen.getAllByText("Técnico").length).toBeGreaterThan(0);
    for (const field of ["Nombre", "Teléfono", "Correo electrónico", "Cargo"]) expect(screen.getByLabelText(field)).toBeInTheDocument();
    expect(screen.getByText(/5 intentos fallidos/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Desbloquear cuenta" })).toBeInTheDocument();
    expect(screen.getByText("Activa")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Acciones de la cuenta" })).toBeInTheDocument();
  });

  it("shows the profile name and keeps the login username visible", async () => {
    vi.mocked(getAdminUser).mockResolvedValue({ user: { ...lockedUser, username: "carlos", name: "Stefan" } });
    render(<UserFicha userId={8} />);
    expect(await screen.findByRole("heading", { name: "Stefan" })).toBeInTheDocument();
    expect(screen.getByText("carlos")).toBeInTheDocument();
  });

  it("falls back to the username when the profile name is null", async () => {
    vi.mocked(getAdminUser).mockResolvedValue({ user: { ...lockedUser, name: null } });
    render(<UserFicha userId={8} />);
    expect(await screen.findByRole("heading", { name: "carlos" })).toBeInTheDocument();
  });

  it("saves only the four profile fields and maps empty fields to null", async () => {
    const user = userEvent.setup();
    render(<UserFicha userId={8} />);
    await screen.findByLabelText("Nombre");
    await waitFor(() => expect(screen.getByLabelText("Nombre")).toHaveValue("Carlos"));
    await user.clear(screen.getByLabelText("Nombre"));
    await user.click(screen.getByRole("button", { name: "Guardar cambios" }));
    await waitFor(() => expect(updateAdminUser).toHaveBeenCalledWith(8, { name: null, phone: "+56912345678", email: "carlos@example.cl", position: "Técnico" }));
  });

  it("explains duplicate email conflicts", async () => {
    vi.mocked(updateAdminUser).mockRejectedValue(new ApiError(409, "Email already exists"));
    const user = userEvent.setup();
    render(<UserFicha userId={8} />);
    await screen.findByLabelText("Correo electrónico");
    await waitFor(() => expect(screen.getByLabelText("Correo electrónico")).toHaveValue("carlos@example.cl"));
    await user.clear(screen.getByLabelText("Correo electrónico"));
    await user.type(screen.getByLabelText("Correo electrónico"), "other@example.cl");
    await user.click(screen.getByRole("button", { name: "Guardar cambios" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/correo.*registrado|correo.*otro usuario/i);
  });

  it("unlocks and updates lockout state", async () => {
    const user = userEvent.setup();
    render(<UserFicha userId={8} />);
    await user.click(await screen.findByRole("button", { name: "Desbloquear cuenta" }));
    expect(unlockUser).toHaveBeenCalledWith(8);
    expect(await screen.findByText("No hay un bloqueo de seguridad activo.")).toBeInTheDocument();
    expect(screen.getByText("Desbloqueada")).toBeInTheDocument();
    expect(screen.queryByText(/5 intentos fallidos/)).not.toBeInTheDocument();
  });

  it("toggles the real account state and shows feedback", async () => {
    const user = userEvent.setup();
    render(<UserFicha userId={8} />);
    await user.click(await screen.findByRole("button", { name: "Desactivar cuenta" }));
    expect(toggleUserActive).toHaveBeenCalledWith(8);
    expect(await screen.findByText("Inactiva")).toBeInTheDocument();
    expect(await screen.findByRole("status")).toHaveTextContent("La cuenta está desactivada");
  });

  it("opens the shared password reset flow for the current account", async () => {
    const user = userEvent.setup();
    render(<UserFicha userId={8} />);
    await user.click(await screen.findByRole("button", { name: "Restablecer contraseña" }));
    const dialog = await screen.findByRole("dialog", { name: "Restablecer contraseña" });
    expect(within(dialog).getByText("carlos")).toBeInTheDocument();
    await user.type(within(dialog).getByLabelText("Nueva contraseña"), "long-enough");
    await user.click(within(dialog).getByRole("button", { name: "Restablecer contraseña" }));
    await waitFor(() => expect(resetUserPassword).toHaveBeenCalledWith(8, "long-enough"));
    expect(await within(dialog).findByRole("status")).toHaveTextContent("Contraseña restablecida");
  });

  it("discards unsaved changes back to loaded values", async () => {
    const user = userEvent.setup();
    render(<UserFicha userId={8} />);
    await screen.findByDisplayValue("Carlos");
    await user.clear(screen.getByLabelText("Nombre"));
    await user.type(screen.getByLabelText("Nombre"), "Changed");
    await user.click(screen.getByRole("button", { name: "Descartar cambios" }));
    expect(screen.getByLabelText("Nombre")).toHaveValue("Carlos");
  });

  it("shows the permission-denied state", async () => {
    vi.mocked(getAdminUser).mockRejectedValue(new ApiError(403, "Forbidden"));
    render(<UserFicha userId={8} />);
    expect(await screen.findByRole("alert")).toHaveTextContent("No tienes permiso para ver esta ficha");
  });
});
