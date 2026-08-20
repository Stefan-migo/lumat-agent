import type { Meta, StoryObj } from "@storybook/react";
import { Matrix as MatrixGrid } from "../helpers/matrix";
import { Badge } from "../../components/primitives/Badge";

const meta = {
  title: "primitives/Badge",
  component: Badge,
  parameters: {
    docs: {
      description: {
        component:
          "Píldora compacta de estado/etiqueta con tonos por token (DS-STORY-2).\n\n" +
          "**Cuándo usarla** — etiquetas cortas de estado: En espera, Éxito, Riesgo, etiquetas neutras.\n" +
          "**Cuándo no usarla** — controles interactivos (para eso usa `Button`) o identidad de usuario (para eso usa `Avatar`); nunca como único canal para un estado crítico: debe acompañarse de una etiqueta de texto (ver `StatusBadge`).\n\n" +
          "**Accesibilidad** — el texto de la insignia es contenido real (nunca `aria-hidden`); los colores de tono vienen de los tokens `--success*`/`--warning*`/`--danger*` y la insignia siempre renderiza su etiqueta de texto, por lo que el color nunca es la única señal. Contraste: fondos de tono (`--*-bg`) con `--text` cumplen WCAG AA para texto normal (DS-STORY-5).",
      },
    },
  },
  argTypes: {
    tone: {
      control: "select",
      options: ["neutral", "success", "warning", "danger"],
      description: "Tono semántico que mapea a colores de token.",
    },
    children: { control: "text", description: "Contenido de la etiqueta." },
  },
} satisfies Meta<typeof Badge>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Warning: Story = {
  args: { tone: "warning", children: "En espera" },
};

export const Matrix: StoryObj = {
  render: () => (
    <MatrixGrid
      cells={[
        ["neutral", <Badge key="n" tone="neutral">Neutro</Badge>],
        ["success", <Badge key="s" tone="success">Éxito</Badge>],
        ["warning", <Badge key="w" tone="warning">En espera</Badge>],
        ["danger", <Badge key="d" tone="danger">Riesgo</Badge>],
      ]}
    />
  ),
};
