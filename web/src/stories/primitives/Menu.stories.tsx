import type { Meta, StoryObj } from "@storybook/react";
import { Archive, ArchiveRestore, ArrowRightLeft } from "lucide-react";
import { Menu } from "../../components/primitives/Menu";

const items = [
  { value: "edit", label: "Editar" },
  { value: "duplicate", label: "Duplicar" },
  { value: "archive", label: "Archivar", disabled: true },
];

const meta = {
  title: "primitives/Menu",
  component: Menu,
  args: { label: "Acciones", items, onSelect: () => {} },
  parameters: {
    docs: {
      description: {
        component:
          "Radix-backed menu for actions with menu semantics (CST-PRIM-7).\n\n" +
          "**When to use** — a set of actions that belongs to one object, including a table row, when the actions do not each deserve their own control.\n" +
          "**When not to use** — confirming a destructive outcome (that is a `Dialog`, DESIGN_SYSTEM.md:493-498) or a single standalone action (that is a `Button`).\n\n" +
          "**Trigger** — `label` renders the label as visible trigger text; `icon` renders a compact icon-only trigger whose accessible name is `label`, so a dense row can carry one action control without repeating the row's own name (DESIGN_SYSTEM.md:475).\n" +
          "**Items** — an item may carry a decorative `icon` and a `tone`. `tone=\"danger\"` marks a destructive action; the glyph and the label still carry the meaning, so colour is never the only channel (DESIGN_SYSTEM.md:509-510).",
      },
    },
  },
} satisfies Meta<typeof Menu>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const Disabled: Story = { args: { disabled: true } };

/** A table row: one icon trigger per row, whose accessible name identifies the row,
 *  and a destructive item that is distinguishable without colour alone. */
export const RowActions: Story = {
  args: {
    label: "Acciones para Marcela Fuentes",
    trigger: "icon",
    items: [
      { value: "state", label: "Cambiar estado", icon: ArrowRightLeft },
      { value: "archive", label: "Archivar", icon: Archive, tone: "danger" },
    ],
  },
};

/** The same row affordance for an archived customer: the destructive item is replaced
 *  by its reversible counterpart. */
export const RowActionsArchived: Story = {
  args: {
    label: "Acciones para Marcela Fuentes",
    trigger: "icon",
    items: [
      { value: "state", label: "Cambiar estado", icon: ArrowRightLeft },
      { value: "restore", label: "Restaurar", icon: ArchiveRestore },
    ],
  },
};
