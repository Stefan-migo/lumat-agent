import type { Meta, StoryObj } from "@storybook/react";
import { ApiError } from "../../api";
import { KbList } from "../../components/pages/KbList";
import { docs } from "./_shared/mockData/kb";

type StoryState = "ready" | "empty" | "loading" | "error" | "denied";

export function KbListView({ state = "ready" }: { state?: StoryState }) {
  if (state === "ready") return <KbList data={{ docs }} />;
  if (state === "empty") return <KbList data={{ docs: [] }} />;
  if (state === "loading") return <KbList fetchDocuments={() => new Promise(() => undefined)} />;
  return <KbList fetchDocuments={() => Promise.reject(new ApiError(state === "denied" ? 403 : 500, "story failure"))} />;
}

export function KbListEmpty() {
  return <KbList data={{ docs: [] }} />;
}

const meta = {
  title: "pages/KbList",
  parameters: {
    layout: "fullscreen",
    docs: {
      description: {
        component: "Panel de la base de conocimientos: listado administrable con estados de carga, error, procesamiento, confirmación y vacío.",
      },
    },
  },
  excludeStories: ["KbListView", "KbListEmpty"],
} satisfies Meta;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = { render: () => <KbListView /> };
export const Processing: Story = { render: () => <KbList data={{ docs }} /> };
export const Error: Story = { render: () => <KbListView state="error" /> };
export const DisableConfirmation: Story = {
  render: () => <KbListView />,
  play: async ({ canvasElement }) => {
    const button = Array.from(canvasElement.querySelectorAll("button")).find((item) => item.textContent === "Deshabilitar");
    button?.click();
  },
};
export const Empty: Story = { render: () => <KbListEmpty /> };
