const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

/** "2026-05" -> "May ’26" */
export function monthLabel(label: string): string {
  const [y, m] = label.split("-");
  return `${MONTHS[Number(m) - 1]} ’${y.slice(2)}`;
}
