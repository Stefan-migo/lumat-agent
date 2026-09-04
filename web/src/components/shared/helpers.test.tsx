import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { DataTable } from "./DataTable";
import { EmptyState } from "./EmptyState";
import { PageHeader } from "./PageHeader";
import { StatCard } from "./StatCard";
import { DataTable as StoryDataTable } from "../../stories/pages/_shared/DataTable";
import { EmptyState as StoryEmptyState } from "../../stories/pages/_shared/EmptyState";
import { PageHeader as StoryPageHeader } from "../../stories/pages/_shared/PageHeader";
import { StatCard as StoryStatCard } from "../../stories/pages/_shared/StatCard";

describe("production shared helper boundary", () => {
  it("resolves all four core helpers from components/shared", () => {
    render(
      <>
        <EmptyState title="No clients" />
        <DataTable columns={[{ key: "name", header: "Name", render: (row: { name: string }) => row.name }]} rows={[{ name: "Ada" }]} />
        <PageHeader title="Clients" />
        <StatCard label="Total" value={1} />
      </>,
    );

    expect(screen.getByText("No clients")).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Name" })).toBeInTheDocument();
    expect(screen.getByText("Ada")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Clients" })).toBeInTheDocument();
    expect(screen.getByText("Total")).toBeInTheDocument();
  });

  it("keeps existing story helper imports rendering the same contracts", () => {
    render(
      <>
        <StoryEmptyState title="Story empty" />
        <StoryDataTable columns={[{ key: "name", header: "Story name", render: (row: { name: string }) => row.name }]} rows={[{ name: "Grace" }]} />
        <StoryPageHeader title="Story clients" />
        <StoryStatCard label="Story total" value={2} />
      </>,
    );

    expect(screen.getByText("Story empty")).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Story name" })).toBeInTheDocument();
    expect(screen.getByText("Grace")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Story clients" })).toBeInTheDocument();
    expect(screen.getByText("Story total")).toBeInTheDocument();
  });
});
