import { describe, expect, it, vi } from "vitest";
import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {
  AppointmentDetailStory,
  ConversationSummary,
  CloseActions,
  Completed,
  ConversationWithoutSummary,
  ManualCase,
  RescheduleDialog,
  Error,
} from "./AppointmentDetail.stories";
import { fetchUsers } from "../../api";

vi.mock("../../api", () => ({ getAppointment: vi.fn(), closeAppointment: vi.fn(), fetchUsers: vi.fn(), rescheduleAppointment: vi.fn() }));

describe("AppointmentDetail stories", () => {
  it("shows the conversation summary when available", () => {
    render(<AppointmentDetailStory {...(ConversationSummary.args ?? {})} />);
    expect(screen.getByRole("heading", { name: "Resumen de la conversación" })).toBeInTheDocument();
    expect(screen.getByText("La clienta solicita revisar el calefón antes del invierno.")).toBeInTheDocument();
  });

  it.each([
    ["conversation without a generated summary", ConversationWithoutSummary],
    ["a manually created case", ManualCase],
  ])("keeps the appointment intact for %s without a summary", (_name, story) => {
    render(<AppointmentDetailStory {...(story.args ?? {})} />);
    expect(screen.queryByRole("heading", { name: "Resumen de la conversación" })).toBeNull();
    expect(screen.queryByText("La clienta solicita revisar el calefón antes del invierno.")).toBeNull();
    const customer = screen.getByRole("link", { name: "Marcela Fuentes" });
    expect(customer).toHaveAttribute("href", "/panel/app/clients/12");
    expect(screen.getByText("Mantención de calefón")).toBeInTheDocument();
    expect(screen.getByText("Reservada")).toBeInTheDocument();
  });

  it("renders the audit trail from appointment history", () => {
    render(<AppointmentDetailStory {...(ConversationSummary.args ?? {})} />);
    expect(screen.getByRole("heading", { name: "Historial de la visita" })).toBeInTheDocument();
    expect(screen.getByText(/ana · booked · — → booked/)).toBeInTheDocument();
  });

  it("keeps appointment facts alongside close controls and hides controls for completed visits", () => {
    const { rerender } = render(<AppointmentDetailStory {...(CloseActions.args ?? {})} />);
    expect(screen.getByRole("button", { name: "Cerrar visita" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Marcela Fuentes" })).toHaveAttribute("href", "/panel/app/clients/12");
    expect(screen.getByText("Mantención de calefón")).toBeInTheDocument();
    rerender(<AppointmentDetailStory {...(Completed.args ?? {})} />);
    expect(screen.getByText("Mantención de calefón")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Cerrar visita" })).not.toBeInTheDocument();
  });

  it("covers the reschedule story dialog while keeping the appointment facts", async () => {
    vi.mocked(fetchUsers).mockResolvedValue({ users: [{ id: 4, username: "Tech", role: "tecnico", active: true }] as never });
    const { container } = render(<AppointmentDetailStory {...(RescheduleDialog.args ?? {})} />);
    expect(screen.getByText("Mantención de calefón")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Marcela Fuentes" })).toHaveAttribute("href", "/panel/app/clients/12");
    await act(async () => {
      await RescheduleDialog.play?.({ canvasElement: container } as Parameters<NonNullable<typeof RescheduleDialog.play>>[0]);
    });
    const dialog = await screen.findByRole("dialog", { name: "Reprogramar visita" });
    expect(within(dialog).getByLabelText("Fecha local")).toHaveValue("2026-09-28");
    await waitFor(() => expect(screen.getByText("Mantención de calefón")).toBeInTheDocument());
  });

  it("wires the error story retry action", async () => {
    const onRetry = vi.fn();
    const user = userEvent.setup();
    render(<AppointmentDetailStory {...(Error.args ?? {})} onRetry={onRetry} />);
    await user.click(screen.getByRole("button", { name: "Reintentar" }));
    expect(onRetry).toHaveBeenCalledOnce();
  });
});
