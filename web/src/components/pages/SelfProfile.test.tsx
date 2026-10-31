import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, changePassword, fetchMe, updateMe } from "../../api";
import { SelfProfile } from "./SelfProfile";
import { ToastProvider } from "../primitives/Toast";

vi.mock("../../api", async (importActual) => ({
  ...(await importActual<typeof import("../../api")>()),
  changePassword: vi.fn(), fetchMe: vi.fn(), updateMe: vi.fn(),
}));

const profile = { id: 9, username: "teo", role: "tecnico" as const, email: null, name: "Teodoro", phone: "+56912345678", position: null };

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(fetchMe).mockResolvedValue(profile);
  vi.mocked(updateMe).mockResolvedValue({ user: { name: "Teodoro", phone: "+56912345678" } });
  vi.mocked(changePassword).mockResolvedValue({ ok: true });
});

describe("SelfProfile", () => {
  it("renders the user's identity and editable name and phone fields", async () => {
    render(<SelfProfile />);
    expect((await screen.findAllByText("teo")).length).toBeGreaterThan(0);
    expect(screen.getByText("Técnico")).toBeInTheDocument();
    expect(screen.getByLabelText("Nombre")).toHaveValue("Teodoro");
    expect(screen.getByLabelText("Teléfono (opcional)")).toHaveValue("+56912345678");
  });

  it("saves only name and phone, mapping a cleared field to null", async () => {
    const user = userEvent.setup();
    render(<ToastProvider><SelfProfile /></ToastProvider>);
    await screen.findByLabelText("Nombre");
    await user.clear(screen.getByLabelText("Nombre"));
    await user.click(screen.getByRole("button", { name: "Guardar cambios" }));
    await waitFor(() => expect(updateMe).toHaveBeenCalledExactlyOnceWith({ name: null, phone: "+56912345678" }));
    expect(await screen.findByText("Datos personales guardados.", { selector: ".toast__message" })).toBeInTheDocument();
  });

  it("restores the stored values when discarding unsaved edits", async () => {
    const user = userEvent.setup();
    render(<SelfProfile />);
    await screen.findByLabelText("Nombre");
    await user.clear(screen.getByLabelText("Nombre"));
    await user.type(screen.getByLabelText("Nombre"), "Otro nombre");
    await user.click(screen.getByRole("button", { name: "Descartar cambios" }));
    expect(screen.getByLabelText("Nombre")).toHaveValue("Teodoro");
  });

  it("allows saving a phone when no name has ever been stored", async () => {
    vi.mocked(fetchMe).mockResolvedValue({ ...profile, name: null, phone: null });
    const user = userEvent.setup();
    render(<SelfProfile />);
    await screen.findByLabelText("Teléfono (opcional)");
    await user.type(screen.getByLabelText("Teléfono (opcional)"), "+56987654321");
    await user.click(screen.getByRole("button", { name: "Guardar cambios" }));
    await waitFor(() => expect(updateMe).toHaveBeenCalledExactlyOnceWith({ name: null, phone: "+56987654321" }));
  });

  it("blocks the password change when the confirmation does not match", async () => {
    const user = userEvent.setup();
    render(<SelfProfile />);
    await screen.findByLabelText("Nombre");
    await user.type(screen.getByLabelText("Contraseña actual"), "current-pass");
    await user.type(screen.getByLabelText("Nueva contraseña"), "new-password");
    await user.type(screen.getByLabelText("Confirmar nueva contraseña"), "different-pass");
    await user.click(screen.getByRole("button", { name: "Actualizar contraseña" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/no coinciden/i);
    expect(changePassword).not.toHaveBeenCalled();
  });

  it("submits the current and new password and explains 401 and 422 responses", async () => {
    const user = userEvent.setup();
    vi.mocked(changePassword).mockRejectedValueOnce(new ApiError(401, "password change failed"));
    render(<ToastProvider><SelfProfile /></ToastProvider>);
    await screen.findByLabelText("Nombre");
    await user.type(screen.getByLabelText("Contraseña actual"), "wrong-password");
    await user.type(screen.getByLabelText("Nueva contraseña"), "new-password");
    await user.type(screen.getByLabelText("Confirmar nueva contraseña"), "new-password");
    await user.click(screen.getByRole("button", { name: "Actualizar contraseña" }));
    expect(await screen.findByText(/contraseña actual/i, { selector: ".toast__message" })).toBeInTheDocument();
    expect(changePassword).toHaveBeenCalledWith({ current_password: "wrong-password", new_password: "new-password" });

    vi.mocked(changePassword).mockRejectedValueOnce(new ApiError(422, "password must be at least 8 characters"));
    await user.click(screen.getByRole("button", { name: "Actualizar contraseña" }));
    expect(await screen.findByText(/al menos 8 caracteres/i, { selector: ".toast__message" })).toBeInTheDocument();
  });
});
