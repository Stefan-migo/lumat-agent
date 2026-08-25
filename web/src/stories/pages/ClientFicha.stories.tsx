import type { Meta, StoryObj } from "@storybook/react";
import type { ClientFichaResponse } from "../../types";
import { ClientFicha } from "../../components/pages/ClientFicha";
import { clients } from "./_shared/mockData/clients";
import { memories } from "./_shared/mockData/memories";

const customer = clients[0];
const ficha: ClientFichaResponse = {
  customer,
  history: {
    conversations: [],
    cases: [],
    messages: [],
  },
  notes: [],
  memo: memories.find((memory) => memory.topic_key === "customer_memo")?.contenido ?? "",
  states: ["nuevo", "activo", "inactivo", "bloqueado"],
};

export function ClientFichaView({ memo = ficha.memo }: { memo?: string }) {
  return <ClientFicha data={{ ...ficha, memo }} memories={memories} />;
}

export function NoMemo() {
  return <ClientFichaView memo="" />;
}

const meta = {
  title: "pages/ClientFicha",
  parameters: {
    layout: "fullscreen",
    docs: {
      description: {
        component: "Ficha de cliente con memo, memorias, notas e historial.",
      },
    },
  },
  excludeStories: ["ClientFichaView", "NoMemo"],
} satisfies Meta;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = { render: () => <ClientFichaView /> };
export const NoMemoState: Story = { render: () => <NoMemo /> };
