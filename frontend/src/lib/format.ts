const UNITS = ["B", "KiB", "MiB", "GiB", "TiB", "PiB"];

export function formatBytes(n: number): string {
  if (!Number.isFinite(n) || n < 0) return "—";
  let v = n;
  let i = 0;
  while (v >= 1024 && i < UNITS.length - 1) {
    v /= 1024;
    i += 1;
  }
  const digits = i === 0 ? 0 : v >= 100 ? 0 : v >= 10 ? 1 : 2;
  return `${v.toFixed(digits)} ${UNITS[i]}`;
}

export function expiryBadge(expiryTime: number, daysLeft: number | null): {
  label: string;
  tone: "ok" | "warn" | "bad" | "delay";
} {
  if (expiryTime < 0) return { label: "starts on first use", tone: "delay" };
  if (expiryTime === 0) return { label: "never", tone: "ok" };
  if (daysLeft != null && daysLeft < 0) return { label: "expired", tone: "bad" };
  if (daysLeft != null && daysLeft < 3) return { label: `${daysLeft.toFixed(1)}d left`, tone: "warn" };
  return { label: daysLeft != null ? `${daysLeft.toFixed(0)}d left` : "—", tone: "ok" };
}
