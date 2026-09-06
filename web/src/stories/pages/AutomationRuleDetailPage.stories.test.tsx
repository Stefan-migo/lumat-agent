import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { act } from "react";
import { disableAutomationRule, getAutomationRule } from "../../api";
import {
  AutomationRuleDetailPageStory,
  Confirmation,
  Create,
  Edit,
  NotFound,
  OperatorData,
} from "./AutomationRuleDetailPage.stories";

vi.mock("../../api", () => ({
  disableAutomationRule: vi.fn(),
  getAutomationRule: vi.fn(),
}));

beforeEach(() => vi.clearAllMocks());

describe("AutomationRuleDetailPage Storybook state matrix", () => {
  it("renders create and edit stories with their intended controls", () => {
    const { unmount } = render(<AutomationRuleDetailPageStory {...(Create.args ?? {})} />);
    expect(screen.getByRole("heading", { name: "Nueva regla de automatización" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Crear regla" })).toBeInTheDocument();

    unmount();
    render(<AutomationRuleDetailPageStory {...(Edit.args ?? {})} />);
    expect(screen.getByDisplayValue("Avisar caso nuevo")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Editar regla" })).toBeInTheDocument();
  });

  it("opens confirmation and refreshes the persisted status", async () => {
    const user = userEvent.setup();
    vi.mocked(disableAutomationRule).mockResolvedValue({ ok: true, rule: { ...Edit.args!.data!, enabled: false } });
    vi.mocked(getAutomationRule).mockResolvedValue({ rule: { ...Edit.args!.data!, enabled: false } });
    render(<AutomationRuleDetailPageStory {...(Confirmation.args ?? {})} />);

    await user.click(screen.getByRole("button", { name: "Deshabilitar regla" }));
    expect(screen.getByRole("dialog", { name: "Deshabilitar regla" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Confirmar deshabilitación" }));

    expect(disableAutomationRule).toHaveBeenCalledWith(7);
    expect(await screen.findByText("Deshabilitada")).toBeInTheDocument();
  });

  it("renders the operator story read-only without mutation controls", () => {
    render(<AutomationRuleDetailPageStory {...(OperatorData.args ?? {})} />);

    expect(screen.queryByRole("button", { name: /editar|crear|habilitar|deshabilitar|guardar/i })).not.toBeInTheDocument();
    expect(screen.getByLabelText("Nombre")).toHaveAttribute("readonly");
    expect(screen.getByLabelText("Evento")).toHaveAttribute("readonly");
    expect(screen.getByLabelText("Canal")).toHaveAttribute("readonly");
  });

  it("names the missing detail state as not found, not empty", () => {
    render(<AutomationRuleDetailPageStory {...(NotFound.args ?? {})} />);
    expect(screen.getByText("Regla no encontrada")).toBeInTheDocument();
    expect(screen.queryByText("No hay reglas de automatización")).not.toBeInTheDocument();
  });

  it("defines Confirmation as an interactive story that opens its Dialog", async () => {
    render(<AutomationRuleDetailPageStory {...(Confirmation.args ?? {})} />);

    expect(Confirmation.play).toBeTypeOf("function");
    await act(async () => {
      await Confirmation.play?.({ canvasElement: document.body } as Parameters<NonNullable<typeof Confirmation.play>>[0]);
    });
    expect(screen.getByRole("dialog", { name: "Deshabilitar regla" })).toBeInTheDocument();
  });
});
