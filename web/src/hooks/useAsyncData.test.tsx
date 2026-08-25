import { renderHook, waitFor, act } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ApiError } from "../api";
import { useAsyncData } from "./useAsyncData";

describe("useAsyncData", () => {
  it("moves from loading to ready and retries with fresh data", async () => {
    const fetcher = vi.fn().mockResolvedValueOnce({ value: 1 }).mockResolvedValueOnce({ value: 2 });
    const { result } = renderHook(() => useAsyncData(fetcher));
    expect(result.current.state).toBe("loading");
    await waitFor(() => expect(result.current.data).toEqual({ value: 1 }));
    expect(result.current.state).toBe("ready");

    act(() => result.current.retry());
    await waitFor(() => expect(result.current.data).toEqual({ value: 2 }));
    expect(fetcher).toHaveBeenCalledTimes(2);
  });

  it("maps empty arrays and 403 errors to their explicit states", async () => {
    const empty = renderHook(() => useAsyncData(() => Promise.resolve([])));
    await waitFor(() => expect(empty.result.current.state).toBe("empty"));

    const denied = renderHook(() => useAsyncData(() => Promise.reject(new ApiError(403, "forbidden"))));
    await waitFor(() => expect(denied.result.current.state).toBe("denied"));
  });

  it("maps non-permission failures to error", async () => {
    const failed = renderHook(() => useAsyncData(() => Promise.reject(new Error("offline"))));
    await waitFor(() => expect(failed.result.current.state).toBe("error"));
  });
});
