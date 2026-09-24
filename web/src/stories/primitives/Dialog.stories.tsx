import { useState } from "react";
import type { Meta, StoryObj } from "@storybook/react";
import { Button } from "../../components/primitives/Button";
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
  excludeStories: ["DialogConfirmView"],
} satisfies Meta<typeof Dialog>;

export default meta;

export function DialogConfirmView() {
  const [open, setOpen] = useState(true);
  return (
    <>
      <Button variant="secondary" onClick={() => setOpen(true)}>
        Eliminar registro
      </Button>
      <Dialog open={open} onClose={() => setOpen(false)} title="Eliminar registro">
        <p className="dialog__message">
          Esta acción no se puede deshacer. ¿Desea continuar?
        </p>
        <div className="dialog__actions">
          <Button variant="secondary" onClick={() => setOpen(false)}>
            Cancelar
          </Button>
          <Button variant="primary" onClick={() => setOpen(false)}>
            Eliminar
          </Button>
        </div>
      </Dialog>
    </>
  );
}

export const Confirmacion: StoryObj = {
  render: () => <DialogConfirmView />,
};
