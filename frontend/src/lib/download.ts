/** Triggers a browser download for a blob response's binary payload. */
export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

/**
 * Pulls a filename out of a Content-Disposition header (attachment; filename=foo.xlsx),
 * falling back to the provided default when the header is missing or unparsable.
 */
export function filenameFromContentDisposition(header: string | undefined, fallback: string): string {
  if (!header) return fallback;
  const match = /filename="?([^";]+)"?/i.exec(header);
  return match?.[1]?.trim() || fallback;
}
