import type { Meta, StoryObj } from "@storybook/react";
import { ClientMemories } from "../../components/domain/ClientMemories";
import { memories } from "./_shared/mockData/memories";

/** Memories panel for a client ficha (MEM-6): list + edit + delete + mark(pin).
 *  Uses the same mock memories as backend to_memory_dict(). Handlers are
 *  story-local no-ops; production wiring happens through the panel API. */
export function ClientMemoriesView() {
  return (
    <ClientMemories
      memories={memories}
      onUpsert={() => {}}
      onDelete={() => {}}
      onPin={() => {}}
    />
  );
}

const meta = {
  title: "pages/ClientMemories",
  parameters: {
    layout: "fullscreen",
    docs: {
      description: {
        component:
          'Ficha memories panel (MEM-6): view, edit, delete and pin/pin-remove the ' +
          'customer\'s `scope="customer"` memories.\n\n' +
          "**When to use** — on the client ficha to manage persistent memories.\n" +
          "**Source** — designs ClientMemories domain component; mocked in Storybook.",
      },
    },
  },
  excludeStories: ["ClientMemoriesView"],
} satisfies Meta;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  render: () => <ClientMemoriesView />,
};
