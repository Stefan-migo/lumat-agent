import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { SearchInput } from "./SearchInput";

describe("SearchInput (T8.1)", () => {
  it("labels its search control and debounces the submitted query", async () => {
    vi.useFakeTimers();
    const onSearch = vi.fn();
    render(<SearchInput onSearch={onSearch} />);
    expect(screen.getByRole("searchbox").parentElement?.querySelector("svg")).toHaveClass(
      "icon",
      "icon--sm",
    );
    expect(screen.queryByText("⌕")).not.toBeInTheDocument();
    const input = screen.getByRole("searchbox", { name: "Buscar" });
    fireEvent.change(input, { target: { value: "fuga" } });
    expect(onSearch).not.toHaveBeenCalled();
    await vi.advanceTimersByTimeAsync(300);
    expect(onSearch).toHaveBeenCalledWith("fuga");
    vi.useRealTimers();
  });

  it("uses the approved surface and boundary roles while retaining a visible focus-within indicator", () => {
    const css = readFileSync(join(process.cwd(), "src/components/primitives/primitives.css"), "utf8");
    expect(css).toMatch(/\.search-input\s*\{[^}]*border:\s*1px solid var\(--border-strong\)[^}]*background:\s*var\(--surface\)/s);
    expect(css).toMatch(/\.search-input:focus-within\s*\{[^}]*border-color:\s*var\(--focus-ring\)[^}]*outline:\s*var\(--focus-ring-width\) solid var\(--focus-ring\)/s);
  });
});
