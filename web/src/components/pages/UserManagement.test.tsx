import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, createUser, deleteUser, fetchUsers, resetUserPassword, toggleUserActive } from "../../api";
import { UserManagement } from "./UserManagement";

vi.mock("../../api", async (importActual) => ({
  ...(await importActual<typeof import("../../api")>()),
  createUser: vi.fn(), deleteUser: vi.fn(), fetchUsers: vi.fn(), resetUserPassword: vi.fn(), toggleUserActive: vi.fn(),
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
  vi.mocked(deleteUser).mockResolvedValue({ ok: true });
  vi.mocked(toggleUserActive).mockResolvedValue({ user: { ...users[1], active: true } });
  vi.mocked(resetUserPassword).mockResolvedValue({ user: users[1] });
});

describe("UserManagement", () => {
  it("renders every supported role, status, and safe list shape", async () => {
    render(<UserManagement currentUser={admin} />);
    const table = await screen.findByRole("table");
    expect(within(table).getByText("ana")).toBeInTheDocument();
    expect(screen.getAllByText("Administrador").length).toBeGreaterThan(1);
    expect(screen.getAllByText("Operador").length).toBeGreaterThan(1);
    expect(screen.getAllByText("Técnico").length).toBeGreaterThan(1);
    expect(screen.getAllByText("Activo").length).toBeGreaterThan(1);
    expect(within(table).getByText("Inactivo")).toBeInTheDocument();
    expect(screen.queryByText("tecnico")).not.toBeInTheDocument();
    expect(screen.queryByText(/password|failed_logins|locked_until/i)).not.toBeInTheDocument();
  });

  it("requires confirmation before deleting a user and refreshes the list", async () => {
    const user = userEvent.setup();
    vi.mocked(fetchUsers).mockResolvedValueOnce({ users }).mockResolvedValueOnce({ users: users.filter((entry) => entry.id !== 2) });
    render(<UserManagement currentUser={admin} />);
    await screen.findByRole("table");
    const row = screen.getByRole("row", { name: /op Operador/i });
    await user.click(within(row).getByRole("button", { name: /acciones para op/i }));
    await user.click(await screen.findByRole("menuitem", { name: "Eliminar usuario" }));
    expect(screen.getByRole("dialog", { name: "Eliminar usuario" })).toHaveTextContent("Elimina a op de forma permanente. No se puede deshacer.");
    expect(deleteUser).not.toHaveBeenCalled();
    await user.click(within(screen.getByRole("dialog", { name: "Eliminar usuario" })).getByRole("button", { name: "Eliminar usuario" }));
    await waitFor(() => expect(deleteUser).toHaveBeenCalledWith(2));
    await waitFor(() => expect(fetchUsers).toHaveBeenCalledTimes(2));
    expect(screen.queryByRole("row", { name: /op Operador/i })).not.toBeInTheDocument();
  });

  it("surfaces a delete conflict without dismissing the confirmation", async () => {
    const user = userEvent.setup();
    vi.mocked(deleteUser).mockRejectedValue(new ApiError(409, "user is referenced by other records; deactivate instead"));
    render(<UserManagement currentUser={admin} />);
    await screen.findByRole("table");
    const row = screen.getByRole("row", { name: /op Operador/i });
    await user.click(within(row).getByRole("button", { name: /acciones para op/i }));
    await user.click(await screen.findByRole("menuitem", { name: "Eliminar usuario" }));
    const dialog = screen.getByRole("dialog", { name: "Eliminar usuario" });
    await user.click(within(dialog).getByRole("button", { name: "Eliminar usuario" }));
    expect(await within(dialog).findByRole("alert")).toHaveTextContent("user is referenced by other records; deactivate instead");
    expect(screen.getByRole("dialog", { name: "Eliminar usuario" })).toBeInTheDocument();
  });

  it("opens a user's ficha from the list", async () => {
    const user = userEvent.setup();
    const onOpenUser = vi.fn();
    render(<UserManagement currentUser={admin} onOpenUser={onOpenUser} />);
    await user.click(within(await screen.findByRole("table")).getByRole("link", { name: "op" }));
    expect(onOpenUser).toHaveBeenCalledWith(2);
  });

  it("shows the profile name instead of the login username when present", async () => {
    vi.mocked(fetchUsers).mockResolvedValue({ users: [{ id: 9, username: "admin", role: "admin" as const, active: true, email: null, name: "Stefan", phone: null, position: null, locked_until: null, failed_logins: 0 }] });
    render(<UserManagement currentUser={admin} />);
    expect(within(await screen.findByRole("table")).getByRole("link", { name: "Stefan" })).toBeInTheDocument();
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
    await screen.findByRole("table");
    await user.click(screen.getByRole("button", { name: "Nuevo usuario" }));
    await user.click(screen.getByRole("button", { name: "Crear usuario" }));
    expect(within(screen.getByRole("dialog")).getByRole("alert")).toHaveTextContent("usuario");
    expect(createUser).not.toHaveBeenCalled();
    await user.type(screen.getByLabelText("Nombre de usuario"), "nuevo");
    await user.type(screen.getByLabelText("Contraseña"), "short");
    await user.type(screen.getByLabelText("Confirmar contraseña"), "short");
    await user.click(screen.getByRole("button", { name: "Crear usuario" }));
    expect(screen.getByRole("alert")).toHaveTextContent("8 caracteres");
  });

  it("creates a user and refreshes the safe list", async () => {
    const user = userEvent.setup();
    vi.mocked(fetchUsers).mockResolvedValueOnce({ users }).mockResolvedValueOnce({ users: [...users, { id: 4, username: "new", role: "operador", active: true, email: null, name: null, phone: null, position: null, locked_until: null, failed_logins: 0 }] });
    render(<UserManagement currentUser={admin} />);
    await screen.findByRole("table");
    await user.click(screen.getByRole("button", { name: "Nuevo usuario" }));
    expect(screen.getByText("Datos de acceso")).toBeInTheDocument();
    expect(screen.getByText("Permisos")).toBeInTheDocument();
    expect(screen.getByText("Crea una cuenta y asigna su rol de acceso.")).toBeInTheDocument();
    await user.type(screen.getByLabelText("Nombre de usuario"), "new");
    await user.type(screen.getByLabelText("Contraseña"), "long enough");
    await user.type(screen.getByLabelText("Confirmar contraseña"), "long enough");
    await user.click(screen.getByRole("button", { name: "Crear usuario" }));
    await waitFor(() => expect(createUser).toHaveBeenCalledWith({ username: "new", password: "long enough", role: "operador" }));
    expect(await screen.findByRole("status")).toHaveTextContent("Usuario creado");
    expect(await screen.findAllByText("new")).not.toHaveLength(0);
  });

  it("shows conflict errors while preserving username and role", async () => {
    const user = userEvent.setup();
    vi.mocked(createUser).mockRejectedValue(new ApiError(409, "El usuario ya existe"));
    render(<UserManagement currentUser={admin} />);
    await screen.findByRole("table");
    await user.click(screen.getByRole("button", { name: "Nuevo usuario" }));
    await user.type(screen.getByLabelText("Nombre de usuario"), "duplicate");
    await user.selectOptions(screen.getByLabelText("Rol de acceso"), "tecnico");
    await user.type(screen.getByLabelText("Contraseña"), "long enough");
    await user.type(screen.getByLabelText("Confirmar contraseña"), "long enough");
    await user.click(screen.getByRole("button", { name: "Crear usuario" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("El usuario ya existe");
    expect(screen.getByLabelText("Nombre de usuario")).toHaveValue("duplicate");
    expect(screen.getByLabelText("Rol de acceso")).toHaveValue("tecnico");
  });

  it("disables self-protection controls and manages another user", async () => {
    const user = userEvent.setup();
    render(<UserManagement currentUser={admin} />);
    await screen.findByRole("table");
    const ownRow = screen.getByRole("row", { name: /ana.*Administrador/i });
    expect(within(ownRow).queryByRole("button", { name: /acciones para/i })).not.toBeInTheDocument();
    expect(within(ownRow).getByText(/Acciones no disponibles/)).toBeInTheDocument();
    expect(within(ownRow).getByText("Tú")).toBeInTheDocument();
    const otherRow = screen.getByRole("row", { name: /op Operador/i });
    await user.click(within(otherRow).getByRole("button", { name: /acciones para op/i }));
    await user.click(await screen.findByRole("menuitem", { name: "Activar usuario" }));
    expect(toggleUserActive).toHaveBeenCalledWith(2);
    expect(await screen.findAllByText("Estado actualizado")).not.toHaveLength(0);
    await user.click(within(otherRow).getByRole("button", { name: /acciones para op/i }));
    await user.click(await screen.findByRole("menuitem", { name: "Restablecer contraseña" }));
    expect(await screen.findByRole("dialog", { name: "Restablecer contraseña" })).toBeInTheDocument();
    expect(resetUserPassword).not.toHaveBeenCalled();
  });

  it("renders mobile user cards and opens the user's action sheet", async () => {
    const user = userEvent.setup();
    render(<UserManagement currentUser={admin} />);
    const cards = await screen.findByRole("list", { name: "Lista de usuarios" });
    const operatorCard = within(cards).getAllByRole("listitem")[1];
    expect(within(operatorCard).getByRole("link", { name: "op" })).toBeInTheDocument();
    expect(within(operatorCard).getByText("Inactivo")).toBeInTheDocument();
    expect(within(cards).getByText("Tú")).toBeInTheDocument();
    expect(screen.getByText("3 de 3 usuarios")).toBeInTheDocument();
    await user.click(within(operatorCard).getByRole("button", { name: "Acciones para op" }));
    const sheet = await screen.findByRole("dialog", { name: "Acciones de usuario" });
    expect(within(sheet).getByText("op")).toBeInTheDocument();
    expect(within(sheet).getByText("Operador · Inactivo")).toBeInTheDocument();
    expect(within(sheet).getByRole("button", { name: /Restablecer contraseña/ })).toBeInTheDocument();
    await user.click(within(sheet).getByRole("button", { name: /Activar usuario/ }));
    expect(toggleUserActive).toHaveBeenCalledWith(2);
  });

  it("enables password reset only at the eight-character minimum", async () => {
    const user = userEvent.setup();
    render(<UserManagement currentUser={admin} />);
    await screen.findByRole("table");
    await user.click(within(screen.getByRole("row", { name: /op Operador/i })).getByRole("button", { name: /acciones para op/i }));
    await user.click(await screen.findByRole("menuitem", { name: "Restablecer contraseña" }));
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
    await screen.findByRole("table");
    await user.click(within(screen.getByRole("row", { name: /op Operador/i })).getByRole("button", { name: /acciones para op/i }));
    await user.click(await screen.findByRole("menuitem", { name: "Restablecer contraseña" }));
    await user.click(screen.getByRole("button", { name: "Generar contraseña" }));
    const field = screen.getByLabelText("Nueva contraseña");
    await user.click(screen.getByRole("button", { name: "Mostrar contraseña" }));
    const generated = (field as HTMLInputElement).value;
    expect(generated).toHaveLength(16);
    expect(field).toHaveAttribute("type", "text");
    await user.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Restablecer contraseña" }));
    await waitFor(() => expect(resetUserPassword).toHaveBeenCalledExactlyOnceWith(2, generated));
  });

  it("keeps the successful password visible until the admin closes the dialog", async () => {
    const user = userEvent.setup();
    render(<UserManagement currentUser={admin} />);
    await screen.findByRole("table");
    await user.click(within(screen.getByRole("row", { name: /op Operador/i })).getByRole("button", { name: /acciones para op/i }));
    await user.click(await screen.findByRole("menuitem", { name: "Restablecer contraseña" }));
    await user.type(screen.getByLabelText("Nueva contraseña"), "typed-secret");
    await user.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Restablecer contraseña" }));
    expect(await within(screen.getByRole("dialog")).findByRole("status")).toHaveTextContent("Contraseña restablecida");
    await waitFor(() => expect(fetchUsers).toHaveBeenCalledTimes(2));
    expect(screen.getByLabelText("Nueva contraseña")).toHaveValue("typed-secret");
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Listo" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("keeps the dialog open and explains a rejected short password", async () => {
    const user = userEvent.setup();
    vi.mocked(resetUserPassword).mockRejectedValue(new ApiError(422, "Unprocessable Entity"));
    render(<UserManagement currentUser={admin} />);
    await screen.findByRole("table");
    await user.click(within(screen.getByRole("row", { name: /op Operador/i })).getByRole("button", { name: /acciones para op/i }));
    await user.click(await screen.findByRole("menuitem", { name: "Restablecer contraseña" }));
    await user.type(screen.getByLabelText("Nueva contraseña"), "long enough");
    await user.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Restablecer contraseña" }));
    expect(await within(screen.getByRole("dialog")).findByRole("alert")).toHaveTextContent("al menos 8 caracteres");
    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });

  it("filters by role and status and reports the current result count", async () => {
    const user = userEvent.setup();
    render(<UserManagement currentUser={admin} />);
    await screen.findByRole("table");
    expect(screen.getByText("Mostrando 3 de 3 usuarios")).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Todos 3" })).toBeInTheDocument();
    await user.selectOptions(screen.getByLabelText("Filtrar por rol"), "tecnico");
    expect(screen.getByText("Mostrando 1 de 1 usuarios")).toBeInTheDocument();
    await user.selectOptions(screen.getByLabelText("Filtrar por rol"), "all");
    await user.click(screen.getByRole("tab", { name: "Inactivos 1" }));
    expect(screen.getByRole("row", { name: /op Operador/i })).toBeInTheDocument();
    expect(screen.getByText("Mostrando 1 de 1 usuarios")).toBeInTheDocument();
  });

  it("paginates the filtered user list", async () => {
    const user = userEvent.setup();
    const manyUsers = Array.from({ length: 12 }, (_, index) => ({ ...users[index % users.length], id: index + 10, username: `user${index}` }));
    vi.mocked(fetchUsers).mockResolvedValue({ users: manyUsers });
    render(<UserManagement currentUser={admin} />);
    await within(await screen.findByRole("table")).findByRole("link", { name: "user0" });
    expect(screen.getByText("Mostrando 10 de 12 usuarios")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Página siguiente" }));
    expect(screen.getByText("Mostrando 2 de 12 usuarios")).toBeInTheDocument();
    expect(screen.getByText("2", { selector: "span" })).toBeInTheDocument();
  });

  it("shows search and opens user creation in a dialog", async () => {
    const user = userEvent.setup();
    render(<UserManagement currentUser={admin} />);
    await screen.findByRole("table");
    const search = screen.getByRole("searchbox", { name: "Buscar usuarios" });
    expect(search).toBeInTheDocument();
    await user.type(search, "op");
    await waitFor(() => expect(within(screen.getByRole("table")).queryByRole("link", { name: "ana" })).not.toBeInTheDocument());
    expect(within(screen.getByRole("table")).getByRole("link", { name: "op" })).toBeInTheDocument();
    expect(screen.getByText("Mostrando 1 de 1 usuarios")).toBeInTheDocument();
    await user.clear(search);
    await waitFor(() => expect(within(screen.getByRole("table")).getByRole("link", { name: "ana" })).toBeInTheDocument());
    await user.click(screen.getByRole("button", { name: "Nuevo usuario" }));
    expect(screen.getByRole("dialog", { name: "Nuevo usuario" })).toBeInTheDocument();
    expect(screen.getByLabelText("Nombre de usuario")).toBeInTheDocument();
    expect(screen.getByLabelText("Confirmar contraseña")).toBeInTheDocument();
  });

  it("rejects a create password confirmation that does not match", async () => {
    const user = userEvent.setup();
    render(<UserManagement currentUser={admin} />);
    await screen.findByRole("table");
    await user.click(screen.getByRole("button", { name: "Nuevo usuario" }));
    await user.type(screen.getByLabelText("Nombre de usuario"), "new");
    await user.type(screen.getByLabelText("Contraseña"), "long enough");
    await user.type(screen.getByLabelText("Confirmar contraseña"), "different");
    await user.click(screen.getByRole("button", { name: "Crear usuario" }));
    expect(await within(screen.getByRole("dialog")).findByRole("alert")).toHaveTextContent("no coinciden");
    expect(createUser).not.toHaveBeenCalled();
  });

  it("shows the target account on password reset and lets the admin cancel", async () => {
    const user = userEvent.setup();
    render(<UserManagement currentUser={admin} />);
    await screen.findByRole("table");
    await user.click(within(screen.getByRole("row", { name: /op Operador/i })).getByRole("button", { name: /acciones para op/i }));
    await user.click(await screen.findByRole("menuitem", { name: "Restablecer contraseña" }));
    const dialog = screen.getByRole("dialog", { name: "Restablecer contraseña" });
    expect(within(dialog).getByRole("region", { name: "Usuario de acceso" })).toBeInTheDocument();
    expect(within(dialog).getAllByText("op")).toHaveLength(2);
    expect(within(dialog).getByText("Define una nueva contraseña para esta cuenta.")).toBeInTheDocument();
    await user.click(within(dialog).getByRole("button", { name: "Cancelar" }));
    expect(screen.queryByRole("dialog", { name: "Restablecer contraseña" })).not.toBeInTheDocument();
  });
});
