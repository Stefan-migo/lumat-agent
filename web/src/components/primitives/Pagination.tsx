import { Button } from "./Button";

export interface PaginationProps {
  page: number;
  pageCount: number;
  onPageChange: (page: number) => void;
  ariaLabel?: string;
}

function pageWindow(page: number, pageCount: number): (number | "ellipsis")[] {
  const wanted = [1, page - 1, page, page + 1, pageCount].filter((p) => p >= 1 && p <= pageCount);
  const sorted = [...new Set(wanted)].sort((a, b) => a - b);
  const out: (number | "ellipsis")[] = [];
  let prev = 0;
  for (const p of sorted) {
    if (prev && p - prev > 1) out.push("ellipsis");
    out.push(p);
    prev = p;
  }
  return out;
}

export function Pagination({ page, pageCount, onPageChange, ariaLabel = "Paginación" }: PaginationProps) {
  return (
    <nav className="table-footer__pagination" aria-label={ariaLabel}>
      <Button variant="secondary" aria-label="Página anterior" disabled={page <= 1} onClick={() => onPageChange(page - 1)}>‹</Button>
      {pageWindow(page, pageCount).map((entry, index) =>
        entry === "ellipsis"
          ? <span key={`e-${index}`} className="pagination__ellipsis" aria-hidden="true">…</span>
          : entry === page
            ? <span key={entry} className="table-footer__page" aria-current="page">{entry}</span>
            : <Button key={entry} variant="secondary" aria-label={`Página ${entry}`} onClick={() => onPageChange(entry)}>{entry}</Button>
      )}
      <Button variant="secondary" aria-label="Página siguiente" disabled={page >= pageCount} onClick={() => onPageChange(page + 1)}>›</Button>
    </nav>
  );
}
