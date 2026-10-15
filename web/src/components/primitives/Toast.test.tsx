import { afterEach, describe, expect, it, vi } from "vitest";
import { act, fireEvent, render, screen } from "@testing-library/react";
import { ToastProvider, useToast } from "./Toast";

function Trigger() {
  const toast = useToast();
  return (
    <>
      <button type="button" onClick={() => toast.show("Guardado", "success")}>Lanzar</button>
      <button type="button" onClick={() => toast.show("Falló", "danger")}>Lanzar error</button>
    </>
  );
}

describe("ToastProvider", () => {
  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it("shows a notification and auto-dismisses it after the duration", () => {
    vi.useFakeTimers();
    render(<ToastProvider duration={1000}><Trigger /></ToastProvider>);

    fireEvent.click(screen.getByRole("button", { name: "Lanzar" }));
    expect(screen.getByText("Guardado")).toBeInTheDocument();

    act(() => { vi.advanceTimersByTime(1000); });
    expect(screen.queryByText("Guardado")).not.toBeInTheDocument();
  });

  it("dismisses a notification through its close control", () => {
    render(<ToastProvider><Trigger /></ToastProvider>);

    fireEvent.click(screen.getByRole("button", { name: "Lanzar error" }));
    expect(screen.getByText("Falló")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Cerrar notificación" }));
    expect(screen.queryByText("Falló")).not.toBeInTheDocument();
  });

  it("stacks multiple notifications", () => {
    render(<ToastProvider><Trigger /></ToastProvider>);
    fireEvent.click(screen.getByRole("button", { name: "Lanzar" }));
    fireEvent.click(screen.getByRole("button", { name: "Lanzar error" }));
    expect(screen.getByText("Guardado")).toBeInTheDocument();
    expect(screen.getByText("Falló")).toBeInTheDocument();
  });
});
