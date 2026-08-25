import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError } from "../api";

export type AsyncDataState = "loading" | "ready" | "empty" | "error" | "denied";

export interface AsyncData<T> {
  data: T | null;
  state: AsyncDataState;
  retry: () => void;
}

function isEmpty<T>(data: T): boolean {
  return Array.isArray(data) && data.length === 0;
}

export function useAsyncData<T>(fetcher: () => Promise<T>, enabled = true): AsyncData<T> {
  const [data, setData] = useState<T | null>(null);
  const [state, setState] = useState<AsyncDataState>("loading");
  const [attempt, setAttempt] = useState(0);
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;
  const retry = useCallback(() => setAttempt((current) => current + 1), []);

  useEffect(() => {
    if (!enabled) return;
    let active = true;
    setState("loading");
    fetcherRef.current().then(
      (next) => {
        if (!active) return;
        setData(next);
        setState(isEmpty(next) ? "empty" : "ready");
      },
      (error: unknown) => {
        if (!active) return;
        setState(error instanceof ApiError && error.status === 403 ? "denied" : "error");
      },
    );
    return () => {
      active = false;
    };
  }, [attempt, enabled]);

  return { data, state, retry };
}
