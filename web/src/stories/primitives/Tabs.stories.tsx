import { useState } from "react";
import type { Meta, StoryObj } from "@storybook/react";
import { Tabs } from "../../components/primitives/Tabs";

const meta = {
  title: "primitives/Tabs",
  component: Tabs,
  parameters: {
    docs: {
      description: {
        component:
          "Pestañas corporativas (catálogo `tabs`) con semántica WAI-ARIA: `tablist`, `tab` y `tabpanel`.\n\n" +
          "**Cuándo usarla** — alternar entre secciones relacionadas de un mismo contexto (ficha de cliente, detalle de caso, configuración).\n" +
          "**Cuándo no usarla** — navegación entre páginas (para eso está la navegación del `PanelShell`) o acordeones para contenido jerárquico.\n\n" +
          "**Accesibilidad** — la pestaña activa expone `aria-selected`, cada `tab` apunta a su panel con `aria-controls` y el `tabpanel` visible es el único renderizado. Activación por clic; navegación por teclado (flechas) queda documentada como follow-up.",
      },
    },
  },
  argTypes: {
    ariaLabel: { control: "text", description: "Etiqueta accesible del tablist." },
  },
} satisfies Meta<typeof Tabs>;

export default meta;

const fichaTabs = [
  { id: "datos", label: "Datos" },
  { id: "motivos", label: "Motivos" },
  { id: "notas", label: "Notas" },
];

export const Default: StoryObj = {
  render: () => (
    <Tabs tabs={fichaTabs} ariaLabel="Ficha">
      {(activeId) => <p>Panel activo: {activeId}</p>}
    </Tabs>
  ),
};

export const Controlled: StoryObj = {
  render: () => {
    const [active, setActive] = useState("motivos");
    return (
      <Tabs tabs={fichaTabs} activeTab={active} onTabChange={setActive} ariaLabel="Ficha">
        {(activeId) => <p>Panel activo (controlado): {activeId}</p>}
      </Tabs>
    );
  },
};