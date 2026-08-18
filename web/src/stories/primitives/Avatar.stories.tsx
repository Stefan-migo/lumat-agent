import type { Meta, StoryObj } from "@storybook/react";
import { Avatar } from "../../components/primitives/Avatar";
const meta = { title: "primitives/Avatar", component: Avatar } satisfies Meta<
  typeof Avatar
>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Initials: Story = { args: { name: "Camila Soto" } };
