import type { Meta, StoryObj } from "@storybook/react";
import { Skeleton } from "../../components/primitives/Skeleton";

const meta = {
  title: "primitives/Skeleton",
  component: Skeleton,
  parameters: {
    docs: {
      description: {
        component:
          "Decorative CSS-only placeholder. The loading region owns its accessible status; the placeholder is always hidden from assistive technology.",
      },
    },
  },
  argTypes: {
    width: { control: "text", description: "Optional CSS width." },
    height: { control: "text", description: "Optional CSS height." },
  },
} satisfies Meta<typeof Skeleton>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  args: { width: "12rem", height: "1rem" },
};
