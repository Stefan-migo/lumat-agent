import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { AgendaCalendar } from "../../components/shared/AgendaCalendar";
import { DenseMonth, EmptyMonth, Month, Narrow, SelectedDay, Week } from "./AgendaCalendar.stories";

describe("AgendaCalendar Storybook stories", () => {
  it.each([
    ["month", Month],
    ["week", Week],
    ["selected day", SelectedDay],
    ["empty month", EmptyMonth],
    ["dense month", DenseMonth],
    ["narrow", Narrow],
  ])("renders the %s variant", (_name, story) => {
    render(<AgendaCalendar {...(story.args ?? {})} />);
    expect(screen.getByRole("table")).toBeInTheDocument();
  });
});
