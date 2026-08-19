import type { Meta, StoryObj } from "@storybook/react";
import { SearchInput } from "../../components/primitives/SearchInput";
const meta = {
  title: "primitives/SearchInput",
  component: SearchInput,
} satisfies Meta<typeof SearchInput>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Default: Story = {
  args: { onSearch: () => {}, placeholder: "Search clients" },
};
