import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { fetchPushConfig, savePushSubscription } from "../../api";
import { PushSettings } from "./PushSettings";

vi.mock("../../api", () => ({
  fetchPushConfig: vi.fn(),
  savePushSubscription: vi.fn(),
}));

describe("PushSettings", () => {
  it("explains fallback when push is unsupported", () => {
    render(<PushSettings supported={false} />);
    expect(screen.getByText(/notificaciones por correo o whatsapp/i)).toBeInTheDocument();
  });

  it("requests permission only after the user clicks and explains denial", async () => {
    const requestPermission = vi.fn().mockResolvedValue("denied");
    vi.mocked(fetchPushConfig).mockResolvedValue({ public_key: "AQID" });
    vi.stubGlobal("Notification", { requestPermission });
    vi.stubGlobal("PushManager", vi.fn());
    Object.defineProperty(navigator, "serviceWorker", { configurable: true, value: { ready: Promise.resolve({ pushManager: { subscribe: vi.fn() } }) } });
    render(<PushSettings supported />);

    expect(requestPermission).not.toHaveBeenCalled();
    expect(screen.getByText("El navegador te pedirá permiso.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /activar notificaciones/i }));
    await waitFor(() => expect(screen.getByText(/denegaste|denegada/i)).toBeInTheDocument());
    expect(screen.getByText(/correo o whatsapp/i)).toBeInTheDocument();
    vi.unstubAllGlobals();
  });

  it("subscribes and saves the browser subscription when permission is granted", async () => {
    vi.mocked(fetchPushConfig).mockResolvedValue({ public_key: "AQID" });
    vi.mocked(savePushSubscription).mockResolvedValue(undefined);
    vi.stubGlobal("Notification", { requestPermission: vi.fn().mockResolvedValue("granted") });
    vi.stubGlobal("PushManager", vi.fn());
    const subscribe = vi.fn().mockResolvedValue({ toJSON: () => ({ endpoint: "https://push.test/one", keys: { p256dh: "public", auth: "secret" } }) });
    Object.defineProperty(navigator, "serviceWorker", { configurable: true, value: { ready: Promise.resolve({ pushManager: { subscribe } }) } });
    render(<PushSettings supported />);

    fireEvent.click(screen.getByRole("button", { name: /activar notificaciones/i }));
    await waitFor(() => expect(savePushSubscription).toHaveBeenCalledWith({
      endpoint: "https://push.test/one", p256dh: "public", auth: "secret", user_agent: navigator.userAgent,
    }));
    expect(subscribe).toHaveBeenCalledWith({ userVisibleOnly: true, applicationServerKey: new Uint8Array([1, 2, 3]) });
    expect(screen.getByText("Push activado.")).toBeInTheDocument();
    vi.unstubAllGlobals();
  });

  it("shows fallback when push is unconfigured", async () => {
    vi.mocked(fetchPushConfig).mockResolvedValue({ public_key: null });
    const subscribe = vi.fn();
    Object.defineProperty(navigator, "serviceWorker", { configurable: true, value: { ready: Promise.resolve({ pushManager: { subscribe } }) } });
    vi.stubGlobal("PushManager", vi.fn());
    render(<PushSettings supported />);

    fireEvent.click(screen.getByRole("button", { name: /activar notificaciones/i }));
    await waitFor(() => expect(screen.getByText(/no admite push/i)).toBeInTheDocument());
    expect(subscribe).not.toHaveBeenCalled();
    vi.unstubAllGlobals();
  });
});
