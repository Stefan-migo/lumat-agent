import type { Meta, StoryObj } from "@storybook/react";
import { Bell, Search } from "lucide-react";
import { Icon } from "../../components/primitives/Icon";

const meta = {
  title: "primitives/Icon",
  component: Icon,
  parameters: {
    docs: {
      description: {
        component:
          "Decorative Lucide icon using the tokenized 16/20/24px size scale and inheriting currentColor.",
      },
    },
  },
  argTypes: {
    icon: { control: false },
    size: { control: "select", options: ["sm", "md", "lg"] },
    className: { control: "text" },
  },
} satisfies Meta<typeof Icon>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Small: Story = { args: { icon: Search, size: "sm" } };

export const Medium: Story = { args: { icon: Bell, size: "md" } };

export const Large: Story = { args: { icon: Search, size: "lg" } };
