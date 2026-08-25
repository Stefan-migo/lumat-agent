import type { Meta, StoryObj } from "@storybook/react";
import { ConversationsList } from "../../components/pages/ConversationsList";
import { conversations } from "./_shared/mockData/conversations";
import { clients } from "./_shared/mockData/clients";

const customerName = (id: number) => clients.find((client) => client.id === id)?.name ?? "—";
export function ConversationsListView({ state }: { state?: "ready" | "loading" | "empty" | "fatal-error" } = {}) {
  return <ConversationsList data={{ conversations: state === "empty" ? [] : conversations }} state={state === "loading" ? "loading" : state === "fatal-error" ? "fatal-error" : "ready"} customerName={customerName} />;
}
export function ConversationsListEmpty() { return <ConversationsList data={{ conversations: [] }} />; }

const meta = { title: "pages/ConversationsList", parameters: { layout: "fullscreen" }, excludeStories: ["ConversationsListView", "ConversationsListEmpty"] } satisfies Meta;
export default meta;
type Story = StoryObj<typeof meta>;
export const Default: Story = { render: () => <ConversationsListView /> };
export const Loading: Story = { render: () => <ConversationsListView state="loading" /> };
export const Empty: Story = { render: () => <ConversationsListEmpty /> };
