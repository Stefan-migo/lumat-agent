import { useState } from "react";
import type { Meta, StoryObj } from "@storybook/react";
import { Dialog } from "../../components/primitives/Dialog";

const meta = {
  title: "primitives/Dialog",
  component: Dialog,
  parameters: {
    docs: {
      description: {
        component:
          "Diálogo corporativo (catálogo `dialog`) para confirmaciones destructivas o tareas que deben bloquear la interacción de fondo.\n\n" +
          "**Cuándo usarla** — confirmar una acción destructiva (eliminar registro, cerrar caso) o capturar un dato sin perder contexto.\n" +
          "**Cuándo no usarla** — mensajes informativos pasajeros (para eso están `FlashMessage`/`StateMessage`); el overlay NO cierra con clic afuera a propósito.\n\n" +
          "**Accesibilidad (DESIGN_SYSTEM §Dialog)** — usa el elemento nativo `<dialog>` y `showModal()`: el navegador gestiona foco, trampa de foco, Escape, restauración y backdrop. El overlay NO cierra con clic afuera a propósito.",
      },
    },
  },
  argTypes: {
    title: { control: "text", description: "Título del diálogo." },
    closeLabel: { control: "text", description: "Etiqueta accesible del botón de cierre." },
  },
} satisfies Meta<typeof Dialog>;

export default meta;

export const Confirmacion: StoryObj = {
  render: () => {
    const [open, setOpen] = useState(true);
    return (
      <>
        <button type="button" onClick={() => setOpen(true)}>
          Eliminar registro
        </button>
        <Dialog open={open} onClose={() => setOpen(false)} title="Eliminar registro">
          <p style={{ margin: "0 0 var(--space-3)" }}>
            Esta acción no se puede deshacer. ¿Desea continuar?
          </p>
          <div style={{ display: "flex", gap: "var(--space-2)", justifyContent: "flex-end" }}>
            <button type="button" onClick={() => setOpen(false)}>
              Cancelar
            </button>
            <button type="button" onClick={() => setOpen(false)}>
              Eliminar
            </button>
          </div>
        </Dialog>
      </>
    );
  },
};
