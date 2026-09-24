import { describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ClientMemories } from "../../components/domain/ClientMemories";
import { ClientMemoriesView } from "./ClientMemories.stories";
import { memories } from "./_shared/mockData/memories";

describe("ClientMemories domain component (MEM-6)", () => {
  it("renders one region heading without a nested page heading", () => {
    render(<ClientMemoriesView />);
    expect(screen.getAllByRole("heading", { name: "Memorias del cliente" })).toHaveLength(1);
    expect(screen.queryByRole("heading", { name: "Memorias" })).not.toBeInTheDocument();
    expect(screen.queryAllByRole("heading", { level: 1 })).toHaveLength(0);
  });

  it("renders every memory as a table row with stable identity", () => {
    render(<ClientMemoriesView />);
    const table = screen.getByRole("table");
    for (const m of memories) {
      expect(within(table).getByText(m.contenido)).toBeInTheDocument();
    }
  });

  it("renders empty state when there are no memories", () => {
    render(<ClientMemories memories={[]} />);
    expect(screen.getByText("Sin memorias todavía")).toBeInTheDocument();
  });

  it("adds a memory via the textarea and fires onUpsert, emptying the draft", async () => {
    const onUpsert = vi.fn();
    render(<ClientMemories memories={[]} onUpsert={onUpsert} />);
    const textbox = screen.getByRole("textbox", { name: /Nueva memoria/i });
    await userEvent.type(textbox, "cliente pidio seguimiento semanal");
    const add = screen.getByRole("button", { name: /Agregar memoria/ });
    expect(add).toBeEnabled();
    await userEvent.click(add);
    expect(onUpsert).toHaveBeenCalledWith("cliente pidio seguimiento semanal");
    expect(textbox).toHaveValue("");
  });

  it("disables the add button while the draft is empty", () => {
    render(<ClientMemories memories={[]} onUpsert={() => {}} />);
    expect(screen.getByRole("button", { name: /Agregar memoria/ })).toBeDisabled();
  });

  it("fires onDelete and onPin row actions", async () => {
    const onDelete = vi.fn();
    const onPin = vi.fn();
    render(
      <ClientMemories
        memories={[memories[0]]}
        onDelete={onDelete}
        onPin={onPin}
      />,
    );
    const firstRowButtons = within(screen.getByRole("table")).getAllByRole("button");
    // pined row (memories[0].pin=false) -> "Fijar"; then "Eliminar"
    expect(firstRowButtons[0].textContent).toBe("Fijar");
    await userEvent.click(firstRowButtons[0]);
    expect(onPin).toHaveBeenCalledWith(memories[0].id, true);
    await userEvent.click(firstRowButtons[1]);
    expect(onDelete).toHaveBeenCalledWith(memories[0].id);
  });

  it("renders 'Quitar pin' when the row is pinned", () => {
    const pinned = { ...memories[0], pin: true };
    render(<ClientMemories memories={[pinned]} onPin={() => {}} onDelete={() => {}} />);
    expect(screen.getByRole("button", { name: "Quitar pin" })).toBeInTheDocument();
  });
});
