import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { PushSettings } from "./PushSettings";

describe("PushSettings", () => {
  it("explains fallback when push is unsupported", () => {
    render(<PushSettings supported={false} />);
    expect(screen.getByText(/notificaciones por correo o whatsapp/i)).toBeInTheDocument();
  });

  it("requests permission only after the user clicks and explains denial", async () => {
    const requestPermission = vi.fn().mockResolvedValue("denied");
    vi.stubGlobal("Notification", { requestPermission });
    render(<PushSettings supported />);

    expect(requestPermission).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: /activar push/i }));
    await waitFor(() => expect(screen.getByText(/denegaste|denegada/i)).toBeInTheDocument());
    expect(screen.getByText(/correo o whatsapp/i)).toBeInTheDocument();
    vi.unstubAllGlobals();
  });
});
