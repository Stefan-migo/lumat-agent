import type { Meta, StoryObj } from "@storybook/react";
import { AgendaCalendar } from "../../components/shared/AgendaCalendar";

const meta = {
  title: "pages/AgendaCalendar",
  component: AgendaCalendar,
  parameters: { layout: "padded" },
} satisfies Meta<typeof AgendaCalendar>;

export default meta;
type Story = StoryObj<typeof meta>;

const visitCounts = {
  "2026-09-05": 4,
  "2026-09-12": 2,
  "2026-09-18": 1,
  "2026-09-24": 3,
};

const callbacks = {
  onSelectDay: () => undefined,
  onViewChange: () => undefined,
  onNavigate: () => undefined,
};

export const Month: Story = {
  args: {
    view: "month",
    anchor: "2026-09-05",
    timezone: "America/Santiago",
    today: "2026-09-05",
    visitCounts,
    ...callbacks,
  },
};

export const Week: Story = {
  args: { ...Month.args, view: "week" },
};

export const SelectedDay: Story = {
  args: { ...Month.args, selectedDay: "2026-09-05" },
};

export const EmptyMonth: Story = {
  args: { ...Month.args, visitCounts: {}, today: "2026-09-24" },
};

export const DenseMonth: Story = {
  args: {
    ...Month.args,
    visitCounts: Object.fromEntries(Array.from({ length: 30 }, (_, index) => [`2026-09-${String(index + 1).padStart(2, "0")}`, index + 1])),
  },
};

export const Narrow: Story = {
  args: { ...Week.args },
  parameters: { viewport: { defaultViewport: "bp-sm" } },
};
