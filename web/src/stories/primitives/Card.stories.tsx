import type { Meta, StoryObj } from "@storybook/react";
import { Matrix as MatrixGrid } from "../helpers/matrix";
import { Card } from "../../components/primitives/Card";

const meta = {
  title: "primitives/Card",
  component: Card,
  parameters: {
    docs: {
      description: {
        component:
          "Contenedor de superficie con título opcional, para agrupar contenido relacionado (DS-STORY-2).\n\n" +
          "**Cuándo usarla** — paneles, ítems de lista, secciones de formulario que necesitan un límite visual sobre `--bg`.\n" +
          "**Cuándo no usarla** — filas interactivas (para eso usa `Button`/semántica de lista) o layouts de página completa (para eso usa `AppShell`).\n\n" +
          "**Accesibilidad** — el título opcional se renderiza como `<h2>`, por lo que el orden de encabezados debe seguir la estructura de la página; las tarjetas son elementos `section`, así que el título (o un `aria-label`) DEBERÍA estar presente para nombrar la región. Contraste: la superficie es `--surface` sobre `--bg`, y el texto interior DEBE usar los tokens `--text`/`--text-muted` (DS-STORY-5).",
      },
    },
  },
  argTypes: {
    title: { control: "text", description: "Título opcional de la sección (renderiza un <h2>)." },
    children: { control: "text", description: "Contenido del cuerpo de la tarjeta." },
  },
} satisfies Meta<typeof Card>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  args: { title: "Cliente", children: "Camila Soto" },
};

export const Matrix: StoryObj = {
  render: () => (
    <MatrixGrid
      cells={[
        ["Con título", <Card key="t" title="Cliente">Camila Soto</Card>],
        ["Sin título", <Card key="n">Camila Soto</Card>],
      ]}
    />
  ),
};
