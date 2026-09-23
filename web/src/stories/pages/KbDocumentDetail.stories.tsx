import type { Meta, StoryObj } from "@storybook/react";
import { KbDocumentDetail, type KbDocumentDetailProps } from "../../components/pages/KbDocumentDetail";
import type { KbDocument } from "../../types";
import { docs } from "./_shared/mockData/kb";

const document: KbDocument = { ...docs[0], content: "Contenido almacenado de la guía de atención al cliente." };

export function KbDocumentDetailStory({ width, ...props }: KbDocumentDetailProps & { width?: number }) {
  return <div style={{ maxWidth: width ? `${width}px` : undefined, width: "100%" }}><KbDocumentDetail {...props} /></div>;
}

const meta = {
  title: "pages/KbDocumentDetail",
  component: KbDocumentDetailStory,
  parameters: { layout: "fullscreen", docs: { description: { component: "Detalle documental con identidad, versiones, audiencia y operaciones administrables." } } },
  excludeStories: ["KbDocumentDetailStory"],
} satisfies Meta<typeof KbDocumentDetailStory>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Ready: Story = { args: { documentId: document.id, data: document, state: "ready", width: 1000 } };
export const Loading: Story = { args: { documentId: document.id, data: null, state: "loading", width: 1000 } };
export const Error: Story = { args: { documentId: document.id, data: null, state: "error", width: 1000 } };
export const Denied: Story = { args: { documentId: document.id, data: null, state: "denied", width: 1000 } };
export const Confirmation: Story = {
  args: { documentId: document.id, data: document, state: "ready", width: 1000 },
  play: async ({ canvasElement }) => {
    const button = Array.from(canvasElement.querySelectorAll("button")).find((item) => item.textContent === "Deshabilitar");
    button?.click();
  },
};
