import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { SearchInput } from "./SearchInput";

describe("SearchInput (T8.1)", () => {
  it("labels its search control and debounces the submitted query", async () => {
    vi.useFakeTimers();
    const onSearch = vi.fn();
    render(<SearchInput onSearch={onSearch} />);
    const input = screen.getByRole("searchbox", { name: "Buscar" });
    fireEvent.change(input, { target: { value: "fuga" } });
    expect(onSearch).not.toHaveBeenCalled();
    await vi.advanceTimersByTimeAsync(300);
    expect(onSearch).toHaveBeenCalledWith("fuga");
    vi.useRealTimers();
  });
});
