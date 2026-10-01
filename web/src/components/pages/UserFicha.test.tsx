import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, getAdminUser, unlockUser, updateAdminUser } from "../../api";
import { UserFicha } from "./UserFicha";

vi.mock("../../api", async (importActual) => ({
  ...(await importActual<typeof import("../../api")>()),
  getAdminUser: vi.fn(), unlockUser: vi.fn(), updateAdminUser: vi.fn(),
}));

const lockedUser = { id: 8, username: "carlos", role: "tecnico" as const, active: true, name: "Carlos", phone: "+56912345678", email: "carlos@example.cl", position: "Técnico", locked_until: "2026-10-01T14:00:00Z", failed_logins: 5 };

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(getAdminUser).mockResolvedValue({ user: lockedUser });
  vi.mocked(updateAdminUser).mockResolvedValue({ user: { ...lockedUser, locked_until: null, failed_logins: 0 } });
  vi.mocked(unlockUser).mockResolvedValue({ user: { ...lockedUser, locked_until: null, failed_logins: 0 } });
});

describe("UserFicha", () => {
  it("renders identity, editable profile and lockout state", async () => {
    render(<UserFicha userId={8} />);
    expect(await screen.findByRole("heading", { name: /carlos/i })).toBeInTheDocument();
    expect(screen.getAllByText("Técnico").length).toBeGreaterThan(0);
    for (const field of ["Nombre", "Teléfono", "Correo", "Cargo"]) expect(screen.getByLabelText(field)).toBeInTheDocument();
    expect(screen.getByText(/5 intentos fallidos/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Desbloquear cuenta" })).toBeInTheDocument();
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
    await screen.findByLabelText("Correo");
    await waitFor(() => expect(screen.getByLabelText("Correo")).toHaveValue("carlos@example.cl"));
    await user.clear(screen.getByLabelText("Correo"));
    await user.type(screen.getByLabelText("Correo"), "other@example.cl");
    await user.click(screen.getByRole("button", { name: "Guardar cambios" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/correo.*registrado|correo.*otro usuario/i);
  });

  it("unlocks and updates lockout state", async () => {
    const user = userEvent.setup();
    render(<UserFicha userId={8} />);
    await user.click(await screen.findByRole("button", { name: "Desbloquear cuenta" }));
    expect(unlockUser).toHaveBeenCalledWith(8);
    expect((await screen.findAllByText("La cuenta está desbloqueada")).length).toBeGreaterThan(0);
    expect(screen.queryByText(/5 intentos fallidos/)).not.toBeInTheDocument();
  });
});
