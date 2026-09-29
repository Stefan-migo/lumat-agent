import { describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ClientMemories } from "../../components/domain/ClientMemories";
import { ClientMemoriesView } from "./ClientMemories.stories";
import { memories } from "./_shared/mockData/memories";
import type { MemoryRelation } from "../../types";

describe("ClientMemories domain component (MEM-6)", () => {
  it("renders one region heading without a nested page heading", () => {
    render(<ClientMemoriesView />);
    expect(screen.getAllByRole("heading", { name: "Memorias del cliente" })).toHaveLength(1);
    expect(screen.queryByRole("heading", { name: "Memorias" })).not.toBeInTheDocument();
    expect(screen.queryAllByRole("heading", { level: 1 })).toHaveLength(0);
  });

  it("features the memo once and keeps the other memories as table rows", () => {
    render(<ClientMemoriesView />);
    const table = screen.getByRole("table");
    const memo = memories.find((memory) => memory.topic_key === "customer_memo")!;
    const featured = document.querySelector(".client-memories__memo");
    expect(within(table).queryByText(memo.contenido)).not.toBeInTheDocument();
    expect(screen.getAllByText(memo.contenido)).toHaveLength(1);
    expect(featured).not.toBeNull();
    expect(within(featured as HTMLElement).getByText("Activo")).toBeInTheDocument();
    for (const memory of memories.filter((entry) => entry.id !== memo.id)) {
      expect(within(table).getByText(memory.contenido)).toBeInTheDocument();
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
    expect(screen.getByRole("button", { name: "Fijar" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Fijar" }));
    expect(onPin).toHaveBeenCalledWith(memories[0].id, true);
    await userEvent.click(screen.getByRole("button", { name: "Eliminar" }));
    expect(onDelete).toHaveBeenCalledWith(memories[0].id);
  });

  it("renders 'Quitar pin' when the featured memo is pinned", () => {
    const pinned = { ...memories[0], pin: true };
    render(<ClientMemories memories={[pinned]} onPin={() => {}} onDelete={() => {}} />);
    expect(screen.getByRole("button", { name: "Quitar pin" })).toBeInTheDocument();
  });

  it("leaves duplicate customer memo topic rows in the table", () => {
    const duplicate = { ...memories[0], id: memories[0].id + 100, contenido: "Second memo row" };
    render(<ClientMemories memories={[memories[0], duplicate]} />);
    const table = screen.getByRole("table");
    expect(screen.getAllByText(memories[0].contenido)).toHaveLength(1);
    expect(within(table).getByText(duplicate.contenido)).toBeInTheDocument();
  });

  it("uses stylesheet classes for memory layout sites", () => {
    const relation: MemoryRelation = {
      id: 1,
      memory_a: memories[0],
      memory_b: memories[1],
      relation: "related",
      confidence: 0.9,
      reason: "same topic",
      source: "test",
      human_resolved_at: null,
      created_at: null,
    };
    const { container } = render(
      <ClientMemories
        memories={[memories[0]]}
        onPin={() => {}}
        onDelete={() => {}}
        onUpsert={() => {}}
        pendingRelations={[relation]}
        onResolveRelation={() => {}}
      />,
    );
    expect(container.querySelector(".table__actions")).not.toBeNull();
    expect(container.querySelectorAll(".client-memories__section")).toHaveLength(2);
    expect(container.querySelector(".client-memories__relation")).not.toBeNull();
    expect(container.querySelector(".client-memories__relation-actions")).not.toBeNull();
    for (const element of container.querySelectorAll(
      ".table__actions, .client-memories__section, .client-memories__relation, .client-memories__relation-actions",
    )) {
      expect(element).not.toHaveAttribute("style");
    }
  });
});
