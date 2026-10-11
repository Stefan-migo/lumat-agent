import { describe, expect, it } from "vitest";
import { assistantToolLabel } from "./assistantToolLabels";

describe("assistantToolLabel", () => {
  it("returns the declared label, description, and group", () => {
    expect(assistantToolLabel("web.search")).toEqual({
      label: "Buscar en la web",
      description: "Consulta información actualizada",
      group: "Consultar información",
    });
  });

  it("does not invent a description for unknown tools", () => {
    expect(assistantToolLabel("custom.tool")).toEqual({ label: "custom.tool", group: "Otras" });
  });
});
