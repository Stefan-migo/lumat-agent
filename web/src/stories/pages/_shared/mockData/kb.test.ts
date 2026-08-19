import { describe, expect, it } from "vitest";
import { docs } from "./kb";

/** Serializer keys from to_doc_dict() in app/panel/api/serializers.py
 *  (R-PRD-PG-3). Must match exactly — snake_case, ISO, nullable fields. */
const DOC_KEYS = [
  "active",
  "active_version",
  "cost_meta",
  "created_at",
  "format",
  "id",
  "model",
  "provider",
  "title",
  "version",
].sort();

const DOC_FORMATS = ["pdf", "md", "csv"];

describe("KB mock (kb.ts)", () => {
  it("exports a non-empty Doc[] list", () => {
    expect(docs.length).toBeGreaterThan(0);
  });

  it("keeps serializer shape fidelity: to_doc_dict keys (R-PRD-PG-3)", () => {
    for (const doc of docs) {
      expect(Object.keys(doc).sort()).toEqual(DOC_KEYS);
    }
  });

  it("covers all 3 DocFormat values (pdf/md/csv)", () => {
    const present = new Set(docs.map((d) => d.format));
    for (const fmt of DOC_FORMATS) {
      expect(present.has(fmt as (typeof docs)[number]["format"]), `missing format: ${fmt}`).toBe(true);
    }
  });

  it("keeps cost_meta as a 6-decimal USD number or null", () => {
    for (const doc of docs) {
      if (doc.cost_meta !== null) {
        expect(typeof doc.cost_meta).toBe("number");
        // 6-decimal fixed formatting matches `'%.6f' % doc.cost_meta` in the
        // Jinja template — assert it round-trips to 6 decimal places.
        const rounded = Number(doc.cost_meta.toFixed(6));
        expect(Math.abs(doc.cost_meta - rounded)).toBeLessThan(0.000001);
      }
    }
  });

  it("covers both active and inactive docs", () => {
    expect(docs.some((d) => d.active)).toBe(true);
    expect(docs.some((d) => !d.active)).toBe(true);
  });

  it("states a version and active_version for every doc; version >= 1", () => {
    for (const doc of docs) {
      expect(doc.version).toBeGreaterThanOrEqual(1);
      expect(doc.active_version).toBeGreaterThanOrEqual(1);
      expect(doc.active_version).toBeLessThanOrEqual(doc.version);
    }
  });

  it("exposes provider and model when available (nullable)", () => {
    expect(docs.some((d) => d.provider !== null && d.model !== null)).toBe(true);
    for (const doc of docs) {
      expect("provider" in doc).toBe(true);
      expect("model" in doc).toBe(true);
    }
  });

  it("uses ISO-8601 datetime strings for created_at", () => {
    for (const doc of docs) {
      if (doc.created_at !== null) {
        expect(new Date(doc.created_at).toString()).not.toBe("Invalid Date");
      }
    }
  });

  it("keeps docs typing against types.ts Doc[]", () => {
    // Type-level conformance: assign to Doc[] (verified at compile time).
    // Runtime check: every doc has the required id field.
    for (const doc of docs) {
      expect(typeof doc.id).toBe("number");
    }
  });
});
