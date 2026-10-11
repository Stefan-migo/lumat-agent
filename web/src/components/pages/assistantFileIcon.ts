import { File as FileIcon, FileCode, FileText, Image, Table, type LucideIcon } from "lucide-react";

export function assistantFileIcon(filename: string, contentType = ""): LucideIcon {
  const extension = filename.split(".").pop()?.toLocaleLowerCase("en-US") ?? "";
  const type = contentType.toLocaleLowerCase("en-US");

  if (type.startsWith("image/") || ["png", "jpg", "jpeg", "gif", "webp", "svg"].includes(extension)) return Image;
  if (extension === "pdf" || ["doc", "docx"].includes(extension)) return FileText;
  if (["xlsx", "xls", "csv"].includes(extension) || type.includes("spreadsheet") || type === "text/csv") return Table;
  if (extension === "md" || extension === "markdown" || type === "text/markdown") return FileCode;
  return FileIcon;
}
