import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Combobox } from "./Combobox";

const options = [
  { value: "ar", label: "Argentina" },
  { value: "cl", label: "Chile" },
  { value: "uy", label: "Uruguay" },
];

describe("Combobox (CST-PRIM-7)", () => {
  it("exposes combobox/listbox semantics and filters while typing", async () => {
    const user = userEvent.setup();
    render(<Combobox label="País" value={null} onChange={() => {}} options={options} id="country" />);
    const input = screen.getByRole("combobox", { name: "País" });
    expect(input).toHaveAttribute("aria-expanded", "false");
    await user.type(input, "chi");
    expect(input).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByRole("listbox")).toHaveAttribute("id", "country-listbox");
    expect(screen.getByRole("option", { name: "Chile" })).toHaveAttribute("aria-selected", "false");
    expect(screen.queryByRole("option", { name: "Argentina" })).not.toBeInTheDocument();
  });

  it("moves the active option and selects it with Enter", () => {
    const onChange = vi.fn();
    render(<Combobox label="País" value={null} onChange={onChange} options={options} id="country" />);
    const input = screen.getByRole("combobox", { name: "País" });
    fireEvent.keyDown(input, { key: "ArrowDown" });
    expect(input).toHaveAttribute("aria-activedescendant", "country-option-0");
    fireEvent.keyDown(input, { key: "ArrowDown" });
    expect(input).toHaveAttribute("aria-activedescendant", "country-option-1");
    fireEvent.keyDown(input, { key: "Enter" });
    expect(onChange).toHaveBeenCalledWith("cl");
    expect(input).toHaveAttribute("aria-expanded", "false");
  });

  it("points aria-activedescendant at the filtered option's original id", async () => {
    const user = userEvent.setup();
    render(<Combobox label="País" value={null} onChange={() => {}} options={options} id="country" />);
    const input = screen.getByRole("combobox", { name: "País" });
    await user.type(input, "chi");
    fireEvent.keyDown(input, { key: "ArrowDown" });
    expect(input).toHaveAttribute("aria-activedescendant", "country-option-1");
    expect(screen.getByRole("option", { name: "Chile" })).toHaveAttribute("id", "country-option-1");
  });

  it("activates the last match on ArrowUp from a fresh state", () => {
    render(<Combobox label="País" value={null} onChange={() => {}} options={options} id="country" />);
    const input = screen.getByRole("combobox", { name: "País" });
    fireEvent.keyDown(input, { key: "ArrowUp" });
    expect(input).toHaveAttribute("aria-activedescendant", "country-option-2");
  });

  it("selects an option by pointer and closes the listbox", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<Combobox label="País" value={null} onChange={onChange} options={options} />);
    const input = screen.getByRole("combobox", { name: "País" });
    await user.click(input);
    expect(screen.getByRole("listbox")).toBeInTheDocument();
    await user.click(screen.getByRole("option", { name: "Chile" }));
    expect(onChange).toHaveBeenCalledWith("cl");
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
  });

  it("preserves typed text when identical options receive a new identity", async () => {
    const user = userEvent.setup();
    const { rerender } = render(
      <Combobox label="País" value={null} onChange={() => {}} options={options} />,
    );
    const input = screen.getByRole("combobox", { name: "País" });
    await user.type(input, "chi");
    rerender(
      <Combobox
        label="País"
        value={null}
        onChange={() => {}}
        options={options.map((option) => ({ ...option }))}
      />,
    );
    expect(input).toHaveValue("chi");
  });

  it("closes the listbox when the input loses focus", () => {
    render(<Combobox label="País" value={null} onChange={() => {}} options={options} />);
    const input = screen.getByRole("combobox", { name: "País" });
    fireEvent.keyDown(input, { key: "ArrowDown" });
    expect(screen.getByRole("listbox")).toBeInTheDocument();
    fireEvent.blur(input);
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
  });

  it("closes on Escape without changing the value and shows no-match copy", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<Combobox label="País" value="ar" onChange={onChange} options={options} />);
    const input = screen.getByRole("combobox", { name: "País" });
    await user.clear(input);
    await user.type(input, "zzz");
    expect(screen.getByText("Sin coincidencias")).toBeInTheDocument();
    await user.keyboard("{Escape}");
    expect(input).toHaveAttribute("aria-expanded", "false");
    expect(onChange).not.toHaveBeenCalled();
  });

  it("disables the input and does not render a listbox", () => {
    render(<Combobox label="País" value={null} onChange={() => {}} options={options} disabled />);
    expect(screen.getByRole("combobox", { name: "País" })).toBeDisabled();
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
  });
});
