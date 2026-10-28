import { useCallback, useLayoutEffect, useRef, type RefObject } from "react";

const BOTTOM_THRESHOLD_PX = 24;

export function useStickToBottom<T extends HTMLElement = HTMLDivElement>(
  resetKey: unknown,
  ...content: unknown[]
): {
  scrollRef: RefObject<T | null>;
  onScroll: () => void;
} {
  const scrollRef = useRef<T>(null);
  const followingRef = useRef(true);
  const resetKeyRef = useRef(resetKey);

  const onScroll = useCallback(() => {
    const element = scrollRef.current;
    if (!element) return;
    followingRef.current =
      element.scrollHeight - element.clientHeight - element.scrollTop <= BOTTOM_THRESHOLD_PX;
  }, []);

  useLayoutEffect(() => {
    // A different thread is a new reading position: whatever the user scrolled in the
    // previous one must not keep the new thread pinned where the old one was left.
    if (resetKeyRef.current !== resetKey) {
      resetKeyRef.current = resetKey;
      followingRef.current = true;
    }
    const element = scrollRef.current;
    if (element && followingRef.current) {
      element.scrollTop = element.scrollHeight;
    }
  }, [resetKey, ...content]);

  return { scrollRef, onScroll };
}
