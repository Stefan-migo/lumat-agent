export function plainSummary(text: string): string {
  return text
    .replace(/!?\[([^\]]+)\]\([^)]+\)/g, "$1")
    .replace(/^\s*(?:[-*+]\s+|\d+\.\s+)/gm, "")
    .replace(/[*_`#]/g, "")
    .replace(/\s+/g, " ")
    .trim();
}
