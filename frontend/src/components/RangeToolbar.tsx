import {
  PRESETS,
  TIME_UNITS,
  fromDatetimeLocalValue,
  toDatetimeLocalValue,
  type RangeMode,
  type RelativeOffset,
  type TimeUnit,
  type UsageRange,
} from "../lib/ranges";

const MODES: { id: RangeMode; label: string }[] = [
  { id: "preset", label: "Preset" },
  { id: "last", label: "Last" },
  { id: "relative", label: "Relative" },
  { id: "absolute", label: "Absolute" },
];

export default function RangeToolbar({
  range,
  onChange,
  title = "Observation range",
  hint,
}: {
  range: UsageRange;
  onChange: (next: UsageRange) => void;
  title?: string;
  hint?: string | null;
}) {
  return (
    <div className="xui-card p-4">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-sm font-semibold text-panel-text">{title}</h2>
        <div className="xui-segment">
          {MODES.map((m) => (
            <button
              key={m.id}
              type="button"
              onClick={() => onChange({ ...range, mode: m.id })}
              className={`xui-segment-item ${range.mode === m.id ? "is-active" : ""}`}
            >
              {m.label}
            </button>
          ))}
        </div>
      </div>

      {range.mode === "preset" && (
        <div className="flex flex-wrap gap-2">
          {PRESETS.map((preset) => (
            <button
              key={preset}
              type="button"
              onClick={() => onChange({ ...range, mode: "preset", preset })}
              title={
                preset === "12m"
                  ? "Last 12 minutes"
                  : preset === "1y"
                    ? "Last 12 calendar months"
                    : undefined
              }
              className={`rounded-md border px-3 py-1.5 text-sm transition-colors ${
                range.preset === preset
                  ? "border-primary bg-primary-soft text-primary"
                  : "border-panel-line bg-panel-card text-panel-muted hover:border-primary hover:text-primary"
              }`}
            >
              {preset}
            </button>
          ))}
        </div>
      )}

      {range.mode === "last" && (
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-sm text-panel-muted">Past</span>
          <OffsetInputs
            value={range.last ?? { amount: 2, unit: "hour" }}
            onChange={(last) => onChange({ ...range, last })}
          />
        </div>
      )}

      {range.mode === "relative" && (
        <div className="space-y-3">
          <div className="flex flex-wrap items-center gap-2">
            <span className="w-10 text-sm text-panel-muted">From</span>
            <OffsetInputs
              value={range.relativeFrom ?? { amount: 30, unit: "minute" }}
              onChange={(relativeFrom) => onChange({ ...range, relativeFrom })}
            />
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <span className="w-10 text-sm text-panel-muted">To</span>
            <OffsetInputs
              value={range.relativeTo ?? { amount: 20, unit: "minute" }}
              onChange={(relativeTo) => onChange({ ...range, relativeTo })}
            />
          </div>
          <p className="text-xs text-panel-muted">
            Both values are offsets from now — e.g. 30 minutes ago → 20 minutes ago.
          </p>
        </div>
      )}

      {range.mode === "absolute" && (
        <div className="flex flex-wrap items-center gap-3">
          <label className="flex items-center gap-2 text-sm">
            <span className="text-panel-muted">From</span>
            <input
              type="datetime-local"
              className="xui-input"
              value={toDatetimeLocalValue(range.from)}
              onChange={(e) =>
                onChange({
                  ...range,
                  from: fromDatetimeLocalValue(e.target.value),
                })
              }
            />
          </label>
          <label className="flex items-center gap-2 text-sm">
            <span className="text-panel-muted">To</span>
            <input
              type="datetime-local"
              className="xui-input"
              value={toDatetimeLocalValue(range.to)}
              onChange={(e) =>
                onChange({
                  ...range,
                  to: fromDatetimeLocalValue(e.target.value),
                })
              }
            />
          </label>
        </div>
      )}

      {hint && <p className="mt-3 text-xs text-primary">{hint}</p>}
    </div>
  );
}

function OffsetInputs({
  value,
  onChange,
}: {
  value: RelativeOffset;
  onChange: (next: RelativeOffset) => void;
}) {
  return (
    <div className="flex items-center gap-1.5">
      <input
        type="number"
        min={0}
        step={1}
        className="xui-input w-20 font-mono"
        value={value.amount}
        onChange={(e) =>
          onChange({
            ...value,
            amount: Math.max(0, Number(e.target.value) || 0),
          })
        }
        aria-label="Amount"
      />
      <select
        className="xui-input"
        value={value.unit}
        onChange={(e) => onChange({ ...value, unit: e.target.value as TimeUnit })}
        aria-label="Unit"
      >
        {TIME_UNITS.map((unit) => (
          <option key={unit} value={unit}>
            {unit}
          </option>
        ))}
      </select>
      <span className="text-sm text-panel-muted">ago</span>
    </div>
  );
}
