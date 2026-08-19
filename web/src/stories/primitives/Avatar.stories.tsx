import type { Meta, StoryObj } from "@storybook/react";
import { Matrix as MatrixGrid } from "../helpers/matrix";
import { Avatar } from "../../components/primitives/Avatar";

const avatarImage =
  "data:image/svg+xml;utf8," +
  "<svg xmlns='http://www.w3.org/2000/svg' width='48' height='48'>" +
  "<rect width='48' height='48' fill='%23c2ebda'/>" +
  "<circle cx='24' cy='18' r='9' fill='%23256f51'/>" +
  "<path d='M10 42c2-9 8-13 14-13s12 4 14 13z' fill='%23256f51'/></svg>";

const meta = {
  title: "primitives/Avatar",
  component: Avatar,
  parameters: {
    docs: {
      description: {
        component:
          "Circular user avatar: initials fallback when no image is provided (DS-STORY-2).\n\n" +
          "**When to use** — user/client identity in lists, headers, and chat threads.\n" +
          "**When not to use** — product logos or non-person icons.\n\n" +
          "**Accessibility** — when `src` is present the image carries `alt={name}`; the initials fallback is text so it is always readable. Contrast expectations: initials render in the panel text color on `--surface`; if a future image variant needs a border it MUST use `--border`/`--border-strong`, not a hard-coded color (DS-STORY-5).",
      },
    },
  },
  argTypes: {
    name: { control: "text", description: "Full name — drives initials and alt text." },
    src: { control: "text", description: "Optional image URL; initials render when absent." },
  },
} satisfies Meta<typeof Avatar>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Initials: Story = { args: { name: "Camila Soto" } };

export const Matrix: StoryObj = {
  render: () => (
    <MatrixGrid
      cells={[
        ["Initials", <Avatar key="i" name="Camila Soto" />],
        ["Image (src)", <Avatar key="s" name="Camila Soto" src={avatarImage} />],
      ]}
    />
  ),
};
