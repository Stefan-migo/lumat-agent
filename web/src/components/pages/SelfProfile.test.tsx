import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, changePassword, fetchMe, updateMe } from "../../api";
import { SelfProfile } from "./SelfProfile";

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
    expect(await screen.findByText("teo")).toBeInTheDocument();
    expect(screen.getByText("Técnico")).toBeInTheDocument();
    expect(screen.getByLabelText("Nombre")).toHaveValue("Teodoro");
    expect(screen.getByLabelText("Teléfono")).toHaveValue("+56912345678");
  });

  it("saves only name and phone, mapping intentionally cleared values to null", async () => {
    const user = userEvent.setup();
    render(<SelfProfile />);
    await screen.findByLabelText("Nombre");
    await user.clear(screen.getByLabelText("Nombre"));
    await user.click(screen.getByRole("button", { name: "Borrar nombre" }));
    await user.click(screen.getByRole("button", { name: "Guardar cambios" }));
    await waitFor(() => expect(updateMe).toHaveBeenCalledExactlyOnceWith({ name: null, phone: "+56912345678" }));
  });

  it("allows saving a phone when no name has ever been stored", async () => {
    vi.mocked(fetchMe).mockResolvedValue({ ...profile, name: null, phone: null });
    const user = userEvent.setup();
    render(<SelfProfile />);
    await screen.findByLabelText("Teléfono");
    await user.type(screen.getByLabelText("Teléfono"), "+56987654321");
    await user.click(screen.getByRole("button", { name: "Guardar cambios" }));
    await waitFor(() => expect(updateMe).toHaveBeenCalledExactlyOnceWith({ name: null, phone: "+56987654321" }));
  });

  it("submits the current and new password and explains 401 and 422 responses", async () => {
    const user = userEvent.setup();
    vi.mocked(changePassword).mockRejectedValueOnce(new ApiError(401, "password change failed"));
    render(<SelfProfile />);
    await screen.findByLabelText("Nombre");
    await user.type(screen.getByLabelText("Contraseña actual"), "wrong-password");
    await user.type(screen.getByLabelText("Nueva contraseña"), "new-password");
    await user.click(screen.getByRole("button", { name: "Cambiar contraseña" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/contraseña actual/i);
    expect(changePassword).toHaveBeenCalledWith({ current_password: "wrong-password", new_password: "new-password" });

    vi.mocked(changePassword).mockRejectedValueOnce(new ApiError(422, "password must be at least 8 characters"));
    await user.click(screen.getByRole("button", { name: "Cambiar contraseña" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/al menos 8 caracteres/i);
  });
});
