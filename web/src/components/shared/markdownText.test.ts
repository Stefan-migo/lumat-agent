import { describe, expect, it } from "vitest";
import { plainSummary } from "./markdownText";

describe("plainSummary", () => {
  it("removes bold markers", () => expect(plainSummary("**Urgent** visit")).toBe("Urgent visit"));
  it("removes heading markers", () => expect(plainSummary("## Summary")).toBe("Summary"));
  it("removes unordered and ordered list markers", () => expect(plainSummary("- Client\n1. Visit")).toBe("Client Visit"));
  it("keeps link labels", () => expect(plainSummary("[Schedule](https://example.com) now")).toBe("Schedule now"));
  it("keeps image alt text", () => expect(plainSummary("![Boiler](https://example.com/boiler.png)")).toBe("Boiler"));
  it("collapses multi-line whitespace", () => expect(plainSummary("First\n\nsecond\tline")).toBe("First second line"));
});
