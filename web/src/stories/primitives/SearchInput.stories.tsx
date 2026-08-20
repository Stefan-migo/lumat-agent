import type { Meta, StoryObj } from "@storybook/react";
import { Matrix as MatrixGrid } from "../helpers/matrix";
import { SearchInput } from "../../components/primitives/SearchInput";

const meta = {
  title: "primitives/SearchInput",
  component: SearchInput,
  parameters: {
    docs: {
      description: {
        component:
          "Campo de búsqueda con debounce y glifo de lupa integrado (DS-STORY-2).\n\n" +
          "**Cuándo usarlo** — búsqueda de clientes/facturas donde conviene retrasar las pulsaciones y llamar a `onSearch` tras una pausa.\n" +
          "**Cuándo no usarlo** — un campo cuyo valor se lee al enviar (para eso usa `Input`).\n\n" +
          "**Accesibilidad** — el control expone un `aria-label` (por defecto `Buscar`) porque no tiene etiqueta visible; pasá uno más específico, p. ej. `Buscar clientes`. El foco DEBE usar los tokens de diseño: `--focus-ring`, `--focus-ring-width`, `--focus-ring-offset` (2px sólido, 2px de offset) para cumplir WCAG 2.4.11 sobre `--bg` y `--surface`.",
      },
    },
  },
  argTypes: {
    placeholder: { control: "text", description: "Texto de sugerencia." },
    "aria-label": { control: "text", description: "Nombre accesible del campo de búsqueda." },
    delay: { control: "number", description: "Retraso de debounce en ms antes de disparar onSearch." },
  },
} satisfies Meta<typeof SearchInput>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  args: { onSearch: () => {}, placeholder: "Buscar clientes" },
};

export const Matrix: StoryObj = {
  render: () => (
    <MatrixGrid
      cells={[
        [
          "Predeterminado (con debounce)",
          <SearchInput key="d" onSearch={() => {}} placeholder="Buscar clientes" />,
        ],
      ]}
    />
  ),
};
