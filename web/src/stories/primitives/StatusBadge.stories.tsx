import type { Meta, StoryObj } from "@storybook/react";
import { Matrix as MatrixGrid } from "../helpers/matrix";
import { StatusBadge } from "../../components/primitives/StatusBadge";

const meta = {
  title: "primitives/StatusBadge",
  component: StatusBadge,
  parameters: {
    docs: {
      description: {
        component:
          "Insignia de estado de dominio para estados de conversación/caso, que mapea el estado a un tono de `Badge` (DS-STORY-2).\n\n" +
          "**Cuándo usarlo** — los cinco estados del panel: bot, human, closed, pending, escalated.\n" +
          "**Cuándo no usarlo** — etiquetas ad-hoc (para eso usa `Badge` directamente).\n\n" +
          "**Accesibilidad** — la etiqueta de texto siempre se renderiza (Agente atendiendo / Atención humana / Cerrada / En espera / Escalado) desde el mapa de etiquetas en español, de modo que el color NUNCA es el único canal de información (DS-STORY-5, DS-UI-LABELS). Contraste: los fondos de tono (`--success-bg`, `--warning-bg`, `--danger-bg`) con `--text` cumplen WCAG AA para texto normal; `escalated` mapea a danger y `human`/`pending` a warning según el mapa de tonos del componente.",
      },
    },
  },
  argTypes: {
    status: {
      control: "select",
      options: ["bot", "human", "closed", "pending", "escalated"],
      description: "Estado de dominio — mapeado a un tono de insignia y una etiqueta de texto.",
    },
    label: {
      control: "text",
      description: "Etiqueta aprobada (en español) que se muestra en lugar del estado crudo.",
    },
  },
} satisfies Meta<typeof StatusBadge>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Escalated: Story = { args: { status: "escalated" } };

export const Matrix: StoryObj = {
  render: () => (
    <MatrixGrid
      cells={[
        ["bot", <StatusBadge key="b" status="bot" />],
        ["human", <StatusBadge key="h" status="human" />],
        ["closed", <StatusBadge key="c" status="closed" />],
        ["pending", <StatusBadge key="p" status="pending" />],
        ["escalated", <StatusBadge key="e" status="escalated" />],
      ]}
    />
  ),
};
