import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, createUser, fetchUsers, resetUserPassword, toggleUserActive } from "../../api";
import { UserManagement } from "./UserManagement";

vi.mock("../../api", async (importActual) => ({
  ...(await importActual<typeof import("../../api")>()),
  createUser: vi.fn(), fetchUsers: vi.fn(), resetUserPassword: vi.fn(), toggleUserActive: vi.fn(),
}));

const admin = { id: 1, username: "ana", role: "admin" as const };
const users = [
  { id: 1, username: "ana", role: "admin" as const, active: true, email: null, name: null, phone: null, position: null, locked_until: null, failed_logins: 0 },
  { id: 2, username: "op", role: "operador" as const, active: false, email: null, name: null, phone: null, position: null, locked_until: null, failed_logins: 0 },
  { id: 3, username: "tec", role: "tecnico" as const, active: true, email: null, name: null, phone: null, position: null, locked_until: null, failed_logins: 0 },
];

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(fetchUsers).mockResolvedValue({ users });
  vi.mocked(createUser).mockResolvedValue({ user: { id: 4, username: "new", role: "operador", active: true, email: null, name: null, phone: null, position: null, locked_until: null, failed_logins: 0 } });
  vi.mocked(toggleUserActive).mockResolvedValue({ user: { ...users[1], active: true } });
  vi.mocked(resetUserPassword).mockResolvedValue({ user: users[1] });
});

describe("UserManagement", () => {
  it("renders every supported role, status, and safe list shape", async () => {
    render(<UserManagement currentUser={admin} />);
    expect(await screen.findByText("ana")).toBeInTheDocument();
    expect(screen.getAllByText("Administrador").length).toBeGreaterThan(1);
    expect(screen.getAllByText("Operador").length).toBeGreaterThan(1);
    expect(screen.getAllByText("Técnico").length).toBeGreaterThan(1);
    expect(screen.getAllByText("Activo").length).toBeGreaterThan(1);
    expect(screen.getByText("Inactivo")).toBeInTheDocument();
    expect(screen.queryByText("tecnico")).not.toBeInTheDocument();
    expect(screen.queryByText(/password|failed_logins|locked_until/i)).not.toBeInTheDocument();
  });

  it("opens a user's ficha from the list", async () => {
    const user = userEvent.setup();
    const onOpenUser = vi.fn();
    render(<UserManagement currentUser={admin} onOpenUser={onOpenUser} />);
    await user.click(await screen.findByRole("link", { name: "op" }));
    expect(onOpenUser).toHaveBeenCalledWith(2);
  });

  it("shows the profile name instead of the login username when present", async () => {
    vi.mocked(fetchUsers).mockResolvedValue({ users: [{ id: 9, username: "admin", role: "admin" as const, active: true, email: null, name: "Stefan", phone: null, position: null, locked_until: null, failed_logins: 0 }] });
    render(<UserManagement currentUser={admin} />);
    expect(await screen.findByRole("link", { name: "Stefan" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "admin" })).not.toBeInTheDocument();
  });

  it.each([
    ["loading", () => new Promise<never>(() => undefined), "Cargando usuarios"],
    ["empty", () => Promise.resolve({ users: [] }), "No hay usuarios"],
    ["error", () => Promise.reject(new Error("offline")), "No pudimos cargar los usuarios"],
    ["denied", () => Promise.reject(new ApiError(403, "Forbidden")), "No tienes permiso para ver este panel"],
  ])("shows the %s state without fabricated rows", async (_state, response, message) => {
    vi.mocked(fetchUsers).mockReturnValue(response() as ReturnType<typeof fetchUsers>);
    render(<UserManagement currentUser={admin} />);
    expect(await screen.findByText(message)).toBeInTheDocument();
    expect(screen.queryByText("ana")).not.toBeInTheDocument();
  });

  it("validates required fields before creating a user", async () => {
    const user = userEvent.setup();
    render(<UserManagement currentUser={admin} />);
    await screen.findByText("ana");
    await user.click(screen.getByRole("button", { name: "Crear usuario" }));
    expect(screen.getByRole("alert")).toHaveTextContent("usuario");
    expect(createUser).not.toHaveBeenCalled();
    await user.type(screen.getByLabelText("Usuario"), "nuevo");
    await user.type(screen.getByLabelText("Contraseña"), "short");
    await user.click(screen.getByRole("button", { name: "Crear usuario" }));
    expect(screen.getByRole("alert")).toHaveTextContent("8 caracteres");
  });

  it("creates a user and refreshes the safe list", async () => {
    const user = userEvent.setup();
    vi.mocked(fetchUsers).mockResolvedValueOnce({ users }).mockResolvedValueOnce({ users: [...users, { id: 4, username: "new", role: "operador", active: true, email: null, name: null, phone: null, position: null, locked_until: null, failed_logins: 0 }] });
    render(<UserManagement currentUser={admin} />);
    await screen.findByText("ana");
    await user.type(screen.getByLabelText("Usuario"), "new");
    await user.type(screen.getByLabelText("Contraseña"), "long enough");
    await user.click(screen.getByRole("button", { name: "Crear usuario" }));
    await waitFor(() => expect(createUser).toHaveBeenCalledWith({ username: "new", password: "long enough", role: "operador" }));
    expect(await screen.findByText("Usuario creado")).toBeInTheDocument();
    expect(await screen.findAllByText("new")).not.toHaveLength(0);
  });

  it("shows conflict errors while preserving username and role", async () => {
    const user = userEvent.setup();
    vi.mocked(createUser).mockRejectedValue(new ApiError(409, "El usuario ya existe"));
    render(<UserManagement currentUser={admin} />);
    await screen.findByText("ana");
    await user.type(screen.getByLabelText("Usuario"), "duplicate");
    await user.selectOptions(screen.getByLabelText("Rol"), "tecnico");
    await user.type(screen.getByLabelText("Contraseña"), "long enough");
    await user.click(screen.getByRole("button", { name: "Crear usuario" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("El usuario ya existe");
    expect(screen.getByLabelText("Usuario")).toHaveValue("duplicate");
    expect(screen.getByLabelText("Rol")).toHaveValue("tecnico");
  });

  it("disables self-protection controls and manages another user", async () => {
    const user = userEvent.setup();
    render(<UserManagement currentUser={admin} />);
    await screen.findByText("ana");
    const ownRow = screen.getByRole("row", { name: /ana Administrador/i });
    expect(within(ownRow).getByRole("button", { name: /activar|desactivar/i })).toBeDisabled();
    expect(within(ownRow).getByRole("button", { name: /restablecer/i })).toBeDisabled();
    const otherRow = screen.getByRole("row", { name: /op Operador/i });
    await user.click(within(otherRow).getByRole("button", { name: /activar/i }));
    expect(toggleUserActive).toHaveBeenCalledWith(2);
    expect(await screen.findByText("Estado actualizado")).toBeInTheDocument();
    await user.click(within(otherRow).getByRole("button", { name: /restablecer/i }));
    expect(await screen.findByRole("dialog", { name: "Restablecer contraseña" })).toBeInTheDocument();
    expect(resetUserPassword).not.toHaveBeenCalled();
  });

  it("enables password reset only at the eight-character minimum", async () => {
    const user = userEvent.setup();
    render(<UserManagement currentUser={admin} />);
    await screen.findByText("ana");
    await user.click(within(screen.getByRole("row", { name: /op Operador/i })).getByRole("button", { name: /restablecer/i }));
    const field = screen.getByLabelText("Nueva contraseña");
    const dialog = screen.getByRole("dialog");
    const submit = within(dialog).getByRole("button", { name: "Restablecer contraseña" });
    expect(submit).toBeDisabled();
    await user.type(field, "1234567");
    expect(submit).toBeDisabled();
    await user.type(field, "8");
    expect(submit).toBeEnabled();
  });

  it("generates a readable password and submits that exact value", async () => {
    const user = userEvent.setup();
    render(<UserManagement currentUser={admin} />);
    await screen.findByText("ana");
    await user.click(within(screen.getByRole("row", { name: /op Operador/i })).getByRole("button", { name: /restablecer/i }));
    await user.click(screen.getByRole("button", { name: "Generar" }));
    const field = screen.getByLabelText("Nueva contraseña");
    const generated = (field as HTMLInputElement).value;
    expect(generated).toHaveLength(16);
    expect(field).toHaveAttribute("type", "text");
    await user.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Restablecer contraseña" }));
    await waitFor(() => expect(resetUserPassword).toHaveBeenCalledExactlyOnceWith(2, generated));
  });

  it("keeps the successful password visible until the admin closes the dialog", async () => {
    const user = userEvent.setup();
    render(<UserManagement currentUser={admin} />);
    await screen.findByText("ana");
    await user.click(within(screen.getByRole("row", { name: /op Operador/i })).getByRole("button", { name: /restablecer/i }));
    await user.type(screen.getByLabelText("Nueva contraseña"), "typed-secret");
    await user.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Restablecer contraseña" }));
    expect(await within(screen.getByRole("dialog")).findByRole("status")).toHaveTextContent("Contraseña restablecida");
    expect(screen.getByLabelText("Nueva contraseña")).toHaveValue("typed-secret");
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Listo" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("keeps the dialog open and explains a rejected short password", async () => {
    const user = userEvent.setup();
    vi.mocked(resetUserPassword).mockRejectedValue(new ApiError(422, "Unprocessable Entity"));
    render(<UserManagement currentUser={admin} />);
    await screen.findByText("ana");
    await user.click(within(screen.getByRole("row", { name: /op Operador/i })).getByRole("button", { name: /restablecer/i }));
    await user.type(screen.getByLabelText("Nueva contraseña"), "long enough");
    await user.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Restablecer contraseña" }));
    expect(await within(screen.getByRole("dialog")).findByRole("alert")).toHaveTextContent("al menos 8 caracteres");
    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });
});
