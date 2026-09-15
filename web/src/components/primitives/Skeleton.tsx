import type { CSSProperties } from "react";
import "./primitives.css";

export interface SkeletonProps {
  width?: CSSProperties["width"];
  height?: CSSProperties["height"];
}

export function Skeleton({ width, height }: SkeletonProps) {
  return (
    <span
      className="skeleton"
      aria-hidden="true"
      style={{ width, height }}
    />
  );
}
