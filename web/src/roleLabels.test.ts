import { describe, expect, it } from "vitest";
import { roleLabels } from "./roleLabels";

describe("role labels", () => {
  it("covers every role with its established Spanish label", () => {
    expect(roleLabels).toEqual({ admin: "Administrador", operador: "Operador", tecnico: "Técnico" });
  });
});
