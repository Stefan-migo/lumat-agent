import { describe, expect, it } from "vitest";
import { File as FileIcon, FileCode, FileText, Image, Table } from "lucide-react";
import { assistantFileIcon } from "./assistantFileIcon";

describe("assistantFileIcon", () => {
  it.each([
    ["manual.pdf", "", FileText],
    ["budget.xlsx", "", Table],
    ["data.csv", "text/csv", Table],
    ["report.docx", "", FileText],
    ["notes.md", "", FileCode],
    ["photo", "image/png", Image],
    ["archive.zip", "application/zip", FileIcon],
  ])("maps %s (%s) to its file icon", (filename, contentType, icon) => {
    expect(assistantFileIcon(filename, contentType)).toBe(icon);
  });
});
