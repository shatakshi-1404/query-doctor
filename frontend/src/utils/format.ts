export function formatMs(ms: number): string {
  return ms < 1 ? ms.toFixed(2) : ms.toFixed(1);
}

export function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
}
