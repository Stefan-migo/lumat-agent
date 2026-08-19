import "./primitives.css";

export interface AvatarProps {
  name: string;
  src?: string;
  className?: string;
}
const initials = (name: string) =>
  name
    .split(" ")
    .filter(Boolean)
    .map((part) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();

export function Avatar({ name, src, className = "" }: AvatarProps) {
  return (
    <span className={`avatar ${className}`.trim()}>
      {src ? <img src={src} alt={name} /> : initials(name)}
    </span>
  );
}
