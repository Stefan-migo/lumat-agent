import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";

/**
 * Renders assistant prose as formatted markdown.
 *
 * `react-markdown` builds React elements instead of going through
 * `dangerouslySetInnerHTML`, and raw HTML is NOT processed unless `rehype-raw`
 * is added — so model output cannot inject markup into the panel. Only the
 * agent's replies go through here: the operator's own message stays literal
 * text, so their punctuation and spacing are never reinterpreted.
 *
 * `remark-gfm` is what makes tables, task lists, strikethrough and autolinks
 * work; the model emits them and they read as noise when left literal.
 */
const components: Components = {
  // Replies routinely carry links; opening them in a new tab keeps the
  // conversation from being navigated away.
  a: ({ children, ...props }) => (
    <a {...props} target="_blank" rel="noopener noreferrer">
      {children}
    </a>
  ),
};

export interface MarkdownProps {
  content: string;
  className?: string;
}

export function Markdown({ content, className = "" }: MarkdownProps) {
  return (
    <div className={`markdown${className ? ` ${className}` : ""}`}>
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
        {content}
      </ReactMarkdown>
    </div>
  );
}
