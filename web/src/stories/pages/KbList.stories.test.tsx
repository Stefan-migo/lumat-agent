import { describe, expect, it } from "vitest";
import { render, screen, within } from "@testing-library/react";
import { docs } from "./_shared/mockData/kb";
import { KbListView, KbListEmpty } from "./KbList.stories";

describe("KbList page story (T5.2, R-PRD-PG-6)", () => {
  it("renders the 'Knowledge Base' page title", () => {
    render(<KbListView />);
    expect(screen.getByRole("heading", { name: "Knowledge Base" })).toBeInTheDocument();
  });

  it("renders the add-document Card with Title input + File input + Add button", () => {
    render(<KbListView />);
    const addCard = screen.getByRole("heading", { name: "Add document" }).closest(".card") as HTMLElement;
    const withinCard = within(addCard);
    expect(withinCard.getByLabelText(/title/i)).toBeInTheDocument();
    expect(withinCard.getByLabelText(/file/i)).toBeInTheDocument();
    expect(withinCard.getByRole("button", { name: "Add" })).toBeInTheDocument();
  });

  it("renders the docs DataTable with #, Format, Version, Active, Provider/Model, Cost fields", () => {
    render(<KbListView />);
    const table = screen.getByRole("table");
    const first = docs[0];

    // # column
    const idCell = within(table).getByText(`#${first.id}`);
    expect(idCell).toBeInTheDocument();
    const row = idCell.closest("tr") as HTMLElement;
    expect(row).not.toBeNull();

    // Title
    expect(within(table).getByText(first.title)).toBeInTheDocument();
    // Format
    expect(within(row).getByText(first.format)).toBeInTheDocument();
    // Version (version + active_version)
    expect(within(row).getByText(`${first.version} (active: ${first.active_version})`)).toBeInTheDocument();
    // Active state (yes/no)
    const activeCell = within(row).getByText(first.active ? "yes" : "no");
    expect(activeCell).toBeInTheDocument();
    // Provider / Model
    expect(within(row).getByText(`${first.provider} / ${first.model}`)).toBeInTheDocument();
    // Cost 6-decimal USD (formatted like '%.6f')
    expect(within(row).getByText("$0.000412")).toBeInTheDocument();
  });

  it("renders per-doc Edit accordion as a native <details>", () => {
    render(<KbListView />);
    const table = screen.getByRole("table");
    const row = within(table).getByText(`#${docs[0].id}`).closest("tr") as HTMLElement;
    const details = within(row).getByRole("group");
    expect(details.tagName).toBe("DETAILS");
    expect(within(details).getByText("Edit")).toBeInTheDocument();
  });

  it("renders Disable button for active docs and Restore select for versioned rows", () => {
    render(<KbListView />);
    const table = screen.getByRole("table");
    const activeDoc = docs.find((d) => d.active)!;
    const activeRow = within(table).getByText(`#${activeDoc.id}`).closest("tr") as HTMLElement;
    expect(within(activeRow).getByRole("button", { name: "Disable" })).toBeInTheDocument();

    const versionedDoc = docs.find((d) => d.version > 1)!;
    const versionedRow = within(table).getByText(`#${versionedDoc.id}`).closest("tr") as HTMLElement;
    // Restore select is labelled "Restore" (aria-label per doc id).
    const restoreSelect = within(versionedRow).getByLabelText(`Restore doc ${versionedDoc.id}`);
    expect(restoreSelect.tagName).toBe("SELECT");
    expect(within(restoreSelect).getByRole("option", { name: "v1" })).toBeInTheDocument();
    expect(within(versionedRow).getByRole("button", { name: "Restore" })).toBeInTheDocument();
  });

  it("renders its provider/model own pair and 6-decimal cost per non-null doc", () => {
    render(<KbListView />);
    const table = screen.getByRole("table");
    for (const doc of docs) {
      const row = within(table).getByText(`#${doc.id}`).closest("tr") as HTMLElement;
      if (doc.provider && doc.model) {
        expect(within(row).getByText(`${doc.provider} / ${doc.model}`)).toBeInTheDocument();
      }
      if (doc.cost_meta !== null) {
        expect(within(row).getByText(`$${doc.cost_meta.toFixed(6)}`)).toBeInTheDocument();
      }
    }
  });
});

describe("KbList Empty story", () => {
  it("renders the empty state with the expected message", () => {
    render(<KbListEmpty />);
    expect(screen.getByText("No documents yet")).toBeInTheDocument();
  });
});
