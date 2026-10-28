import { fireEvent, render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { useStickToBottom } from "./useStickToBottom";

function Thread({ content, threadId = 1 }: { content: string; threadId?: number }) {
  const { scrollRef, onScroll } = useStickToBottom(threadId, content);
  return (
    <div ref={scrollRef} onScroll={onScroll} data-testid="messages">
      <div>{content}</div>
    </div>
  );
}

function setScrollMetrics(element: HTMLElement, scrollHeight: number, clientHeight: number) {
  Object.defineProperties(element, {
    scrollHeight: { configurable: true, value: scrollHeight },
    clientHeight: { configurable: true, value: clientHeight },
  });
}

describe("useStickToBottom", () => {
  it("follows the bottom as content grows", () => {
    const { getByTestId, rerender } = render(<Thread content="first" />);
    const messages = getByTestId("messages");
    setScrollMetrics(messages, 400, 200);

    rerender(<Thread content="a longer streamed response" />);
    expect(messages.scrollTop).toBe(400);
  });

  it("stops following after the user scrolls up", () => {
    const { getByTestId, rerender } = render(<Thread content="first" />);
    const messages = getByTestId("messages");
    setScrollMetrics(messages, 400, 200);
    messages.scrollTop = 100;
    fireEvent.scroll(messages);

    rerender(<Thread content="more streamed response" />);
    expect(messages.scrollTop).toBe(100);
  });

  it("resumes following when the user returns to the bottom", () => {
    const { getByTestId, rerender } = render(<Thread content="first" />);
    const messages = getByTestId("messages");
    setScrollMetrics(messages, 400, 200);
    messages.scrollTop = 100;
    fireEvent.scroll(messages);

    messages.scrollTop = 200;
    fireEvent.scroll(messages);
    rerender(<Thread content="more streamed response" />);

    expect(messages.scrollTop).toBe(400);
  });

  it("follows the bottom again after the user scrolled up in another thread", () => {
    const { getByTestId, rerender } = render(<Thread threadId={1} content="first" />);
    const messages = getByTestId("messages");
    setScrollMetrics(messages, 400, 200);
    messages.scrollTop = 100;
    fireEvent.scroll(messages);

    rerender(<Thread threadId={1} content="still reading the same thread" />);
    expect(messages.scrollTop).toBe(100);

    rerender(<Thread threadId={2} content="a different thread opened" />);

    expect(messages.scrollTop).toBe(400);
  });
});
