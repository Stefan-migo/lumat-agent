import type { Meta, StoryObj } from "@storybook/react";
import { KbList, type KbListState } from "../../components/pages/KbList";
import { docs } from "./_shared/mockData/kb";

export function KbListView({ state = "ready" }: { state?: KbListState }) {
  return <KbList data={state === "empty" ? { docs: [] } : { docs }} state={state} />;
}

export function KbListEmpty() {
  return <KbList data={{ docs: [] }} state="empty" />;
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
export const Processing: Story = { render: () => <KbListView state="processing" /> };
export const Error: Story = { render: () => <KbListView state="error" /> };
export const DisableConfirmation: Story = { render: () => <KbListView state="disable-confirmation" /> };
export const Empty: Story = { render: () => <KbListEmpty /> };
