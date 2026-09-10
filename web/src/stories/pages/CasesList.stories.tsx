import type { Meta, StoryObj } from "@storybook/react";
import { CasesList, type CasesListState } from "../../components/pages/CasesList";
import { casesData, users } from "./_shared/mockData/cases";

/** Cases list body (shared frame + emergency banner via StateMessage + table
 *  with inline update/ack). Exported for tests; hidden from the addons panel.
 *  Statuses render approved Spanish labels (DS-UI-LABELS); the emergency note
 *  and loading banner route through StateMessage (DS-UI-FRAME/STATES). */
export function CasesListView({ state = "ready" }: { state?: CasesListState }) {
  return <CasesList data={state === "empty" ? { cases: [], users } : casesData} state={state} />;
}

/** Cases list empty state. Exported for tests. */
export function CasesListEmpty() {
  return <CasesList data={{ cases: [], users }} state="empty" />;
}

const meta = {
  title: "pages/CasesList",
  parameters: {
    layout: "fullscreen",
    docs: {
      description: {
        component:
          'Listado de casos: título en español, banner de emergencias por StateMessage y tabla con estados en etiquetas aprobadas (DS-UI-LABELS/FRAME/STATES).\n\n' +
          "**Uso** — los casos pendientes y escalados.\n" +
          "**Estados** — listo (con banner de emergencias), carga, vacío, datos obsoletos, error parcial y error fatal.\n" +
          "**Fuente** — mock page-first con la forma del serializer productivo; el wiring de producción no cambia.",
      },
    },
  },
  excludeStories: ["CasesListView", "CasesListEmpty"],
} satisfies Meta;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  render: () => <CasesListView />,
};

export const Stale: Story = { render: () => <CasesListView state="stale" /> };
export const PartialError: Story = { render: () => <CasesListView state="partial-error" /> };
export const FatalError: Story = { render: () => <CasesListView state="fatal-error" /> };

export const Loading: Story = {
  render: () => <CasesListView state="loading" />,
};

export const Empty: Story = {
  render: () => <CasesListEmpty />,
};
