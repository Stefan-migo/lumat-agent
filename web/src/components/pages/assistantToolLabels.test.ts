import { describe, expect, it } from "vitest";
import { Archive, FolderPlus, GitMerge, Globe, Link2, Pencil, Wrench, Zap } from "lucide-react";
import { assistantToolLabel } from "./assistantToolLabels";

describe("assistantToolLabel", () => {
  it("returns the declared label, description, group, and icon", () => {
    expect(assistantToolLabel("web.search")).toEqual({
      label: "Buscar en la web",
      description: "Consulta información actualizada",
      group: "Consultar información",
      icon: Globe,
    });
  });

  it("maps each supported tool to its Lucide icon", () => {
    expect(assistantToolLabel("web.fetch").icon).toBe(Link2);
    expect(assistantToolLabel("automation.create_rule").icon).toBe(Zap);
    expect(assistantToolLabel("project.create").icon).toBe(FolderPlus);
    expect(assistantToolLabel("project.rename").icon).toBe(Pencil);
    expect(assistantToolLabel("project.archive").icon).toBe(Archive);
    expect(assistantToolLabel("project.merge").icon).toBe(GitMerge);
  });

  it("uses a neutral icon for unknown tools", () => {
    expect(assistantToolLabel("custom.tool")).toEqual({ label: "custom.tool", group: "Otras", icon: Wrench });
  });
});
