export type TimeUnit = "minute" | "hour" | "day" | "week" | "month";

export type RangeMode = "preset" | "last" | "relative" | "absolute";

/** Preset ids: `m` = minutes, `h` = hours, `d` = days, `y` = years. */
export type RangePreset = "12m" | "1h" | "48h" | "7d" | "30d" | "90d" | "1y";

export type RelativeOffset = {
  amount: number;
  unit: TimeUnit;
};

export type UsageRange = {
  mode: RangeMode;
  preset?: RangePreset;
  /** Last N units ending now */
  last?: RelativeOffset;
  /** From farther-ago offset → nearer-ago offset (both relative to now) */
  relativeFrom?: RelativeOffset;
  relativeTo?: RelativeOffset;
  /** Absolute ISO bounds */
  from?: string;
  to?: string;
};

export const TIME_UNITS: TimeUnit[] = ["minute", "hour", "day", "week", "month"];

export const PRESETS: RangePreset[] = ["12m", "1h", "48h", "7d", "30d", "90d", "1y"];

const PRESET_MS: Record<RangePreset, number> = {
  "12m": 12 * 60 * 1000,
  "1h": 60 * 60 * 1000,
  "48h": 48 * 60 * 60 * 1000,
  "7d": 7 * 24 * 60 * 60 * 1000,
  "30d": 30 * 24 * 60 * 60 * 1000,
  "90d": 90 * 24 * 60 * 60 * 1000,
  // Fallback only — resolveRange("1y") uses calendar months.
  "1y": 365 * 24 * 60 * 60 * 1000,
};

/** Subtract calendar months (handles month-length / year boundaries). */
export function monthsAgoDate(months: number, now = new Date()): Date {
  const d = new Date(now.getTime());
  d.setMonth(d.getMonth() - Math.max(0, months));
  return d;
}

const UNIT_MS: Record<TimeUnit, number> = {
  minute: 60 * 1000,
  hour: 60 * 60 * 1000,
  day: 24 * 60 * 60 * 1000,
  week: 7 * 24 * 60 * 60 * 1000,
  month: 30 * 24 * 60 * 60 * 1000,
};

export function offsetMs(offset: RelativeOffset): number {
  const amount = Math.max(0, Number(offset.amount) || 0);
  return amount * UNIT_MS[offset.unit];
}

export function agoIso(offset: RelativeOffset, now = new Date()): string {
  return new Date(now.getTime() - offsetMs(offset)).toISOString();
}

export function resolveRange(range: UsageRange, now = new Date()): { from?: string; to?: string } {
  switch (range.mode) {
    case "preset": {
      const preset = range.preset ?? "48h";
      if (preset === "1y") {
        return {
          from: monthsAgoDate(12, now).toISOString(),
          to: now.toISOString(),
        };
      }
      return {
        from: new Date(now.getTime() - PRESET_MS[preset]).toISOString(),
        to: now.toISOString(),
      };
    }
    case "last": {
      const last = range.last ?? { amount: 48, unit: "hour" };
      return { from: agoIso(last, now), to: now.toISOString() };
    }
    case "relative": {
      const fromOff = range.relativeFrom ?? { amount: 30, unit: "minute" };
      const toOff = range.relativeTo ?? { amount: 0, unit: "minute" };
      let fromMs = now.getTime() - offsetMs(fromOff);
      let toMs = now.getTime() - offsetMs(toOff);
      // If user puts nearer time first, swap so from < to
      if (fromMs > toMs) {
        const tmp = fromMs;
        fromMs = toMs;
        toMs = tmp;
      }
      return {
        from: new Date(fromMs).toISOString(),
        to: new Date(toMs).toISOString(),
      };
    }
    case "absolute":
      return {
        from: range.from || undefined,
        to: range.to || undefined,
      };
    default:
      return {};
  }
}

/** Best single-series granularity for a closed historical / long present window. */
export function pickGranularity(spanMs: number): "hour" | "day" | "month" {
  const hour = 60 * 60 * 1000;
  const day = 24 * hour;
  if (spanMs <= 3 * day) return "hour";
  if (spanMs <= 120 * day) return "day";
  return "month";
}

/** True when the observation window ends at (or very near) now. */
export function rangeEndsAtPresent(
  range: UsageRange,
  resolved: { from?: string; to?: string },
  now = new Date(),
  slackMs = 2 * 60 * 1000,
): boolean {
  if (range.mode === "preset" || range.mode === "last") return true;
  if (range.mode === "relative") {
    const toOff = range.relativeTo ?? { amount: 0, unit: "minute" };
    return offsetMs(toOff) <= slackMs;
  }
  // absolute: empty "to" means API uses now; otherwise compare clock
  if (!resolved.to) return true;
  return Math.abs(now.getTime() - new Date(resolved.to).getTime()) <= slackMs;
}

/**
 * Compact stats view: one chart + range totals.
 * - Last mode (any span)
 * - Windows that do not end at present
 * - Long present windows at month grain (e.g. 1y preset)
 */
export function isCompactUsageView(
  range: UsageRange,
  resolved: { from?: string; to?: string },
): boolean {
  if (range.mode === "last") return true;
  if (!rangeEndsAtPresent(range, resolved)) return true;
  if (resolved.from && resolved.to) {
    const span =
      new Date(resolved.to).getTime() - new Date(resolved.from).getTime();
    if (pickGranularity(span) === "month") return true;
  }
  return false;
}

export function sumPoints(
  points?: Array<{ up: number; down: number }>,
): { up: number; down: number; total: number } {
  let up = 0;
  let down = 0;
  for (const p of points ?? []) {
    up += p.up;
    down += p.down;
  }
  return { up, down, total: up + down };
}

export function formatOffset(offset: RelativeOffset): string {
  const n = Math.max(0, Number(offset.amount) || 0);
  const unit = n === 1 ? offset.unit : `${offset.unit}s`;
  return `${n} ${unit} ago`;
}

export function rangeLabel(range: UsageRange): string {
  switch (range.mode) {
    case "preset":
      return range.preset ?? "48h";
    case "last":
      return `last ${formatOffset(range.last ?? { amount: 0, unit: "minute" }).replace(" ago", "")}`;
    case "relative": {
      const a = formatOffset(range.relativeFrom ?? { amount: 30, unit: "minute" });
      const b = formatOffset(range.relativeTo ?? { amount: 0, unit: "minute" });
      return `${a} → ${b === "0 minutes ago" ? "now" : b}`;
    }
    case "absolute": {
      if (!range.from && !range.to) return "default windows";
      const a = range.from ? new Date(range.from).toLocaleString() : "…";
      const b = range.to ? new Date(range.to).toLocaleString() : "now";
      return `${a} → ${b}`;
    }
    default:
      return "—";
  }
}

export function toDatetimeLocalValue(iso?: string): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

export function fromDatetimeLocalValue(value: string): string | undefined {
  if (!value) return undefined;
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return undefined;
  return d.toISOString();
}

export const defaultRange = (): UsageRange => ({
  mode: "preset",
  preset: "48h",
  last: { amount: 2, unit: "hour" },
  relativeFrom: { amount: 30, unit: "minute" },
  relativeTo: { amount: 20, unit: "minute" },
});
