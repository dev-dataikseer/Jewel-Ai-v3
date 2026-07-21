import { useMemo } from "react";
import type { JsonSchema, JsonSchemaProperty } from "@/types";

const HIDDEN_FIELDS = new Set([
  // Prompt text lives in Settings / composed by the prompt engine
  "prompt",
  "instruction",
  "negative_prompt",
  "system_prompt",
  // Images come from Studio uploads, not Advanced
  "image_url",
  "image_urls",
  "mask_image_url",
  "model_image",
  "garment_image",
  "person_image_url",
  "clothing_image_url",
  "human_image_url",
  "garment_image_url",
  "reference_image_url",
  // Internal / async queue flags — not studio-facing
  "sync_mode",
]);

type Props = {
  schema: JsonSchema;
  values: Record<string, unknown>;
  defaults?: Record<string, unknown>;
  onChange: (values: Record<string, unknown>) => void;
  className?: string;
};

function FieldControl({
  name,
  prop,
  value,
  onChange,
}: {
  name: string;
  prop: JsonSchemaProperty;
  value: unknown;
  onChange: (v: unknown) => void;
}) {
  const title = prop.title || name.replace(/_/g, " ");

  if (prop.enum) {
    const options = prop.enum.map(String);
    const raw = value ?? prop.default ?? options[0] ?? "";
    const selected = options.includes(String(raw)) ? String(raw) : String(prop.default ?? options[0] ?? "");
    return (
      <div>
        <label className="ui-label">{title}</label>
        <select
          value={selected}
          onChange={(e) => onChange(e.target.value)}
          className="ui-input text-xs"
        >
          {options.map((opt) => (
            <option key={opt} value={opt}>
              {opt}
            </option>
          ))}
        </select>
      </div>
    );
  }

  if (prop.type === "boolean") {
    return (
      <label className="flex items-center gap-2 text-sm text-slate-700">
        <input
          type="checkbox"
          checked={Boolean(value ?? prop.default ?? false)}
          onChange={(e) => onChange(e.target.checked)}
          className="size-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500/30"
        />
        <span className="font-medium">{title}</span>
      </label>
    );
  }

  if (prop.type === "integer" || prop.type === "number") {
    const num = value !== undefined && value !== null && value !== "" ? Number(value) : Number(prop.default ?? prop.minimum ?? 0);
    const min = prop.minimum ?? 0;
    const max = prop.maximum ?? (name === "seed" ? 2147483647 : 100);
    const isSeed = name.toLowerCase().includes("seed");
    if (isSeed) {
      return (
        <div>
          <label className="ui-label">{title}</label>
          <div className="flex gap-2">
            <input
              type="number"
              min={min}
              max={max}
              value={num}
              onChange={(e) => onChange(parseInt(e.target.value, 10) || 0)}
              className="ui-input text-xs flex-1"
            />
            <button
              type="button"
              className="ui-btn-secondary h-9 w-9 shrink-0 p-0"
              aria-label="Randomize seed"
              onClick={() =>
                onChange(Math.floor(Math.random() * Math.min(max, 999999999)))
              }
            >
              <svg viewBox="0 0 24 24" className="size-3.5" fill="none" stroke="currentColor" strokeWidth="2">
                <rect x="3" y="3" width="18" height="18" rx="2" />
                <circle cx="8" cy="8" r="1" fill="currentColor" />
                <circle cx="16" cy="8" r="1" fill="currentColor" />
                <circle cx="8" cy="16" r="1" fill="currentColor" />
                <circle cx="16" cy="16" r="1" fill="currentColor" />
                <circle cx="12" cy="12" r="1" fill="currentColor" />
              </svg>
            </button>
          </div>
        </div>
      );
    }
    return (
      <div>
        <label className="ui-label mb-1 flex justify-between">
          <span>{title}</span>
          <span className="normal-case tracking-normal text-[var(--jewel-ink-faint)] font-medium tabular-nums">{num}</span>
        </label>
        <div className="flex items-center gap-2">
          <input
            type="range"
            min={min}
            max={max}
            step={prop.type === "integer" ? 1 : 0.05}
            value={num}
            onChange={(e) => onChange(prop.type === "integer" ? parseInt(e.target.value, 10) : parseFloat(e.target.value))}
            className="w-full accent-[var(--jewel-accent)]"
          />
          <input
            type="number"
            min={min}
            max={max}
            step={prop.type === "integer" ? 1 : 0.05}
            value={num}
            onChange={(e) => onChange(prop.type === "integer" ? parseInt(e.target.value, 10) : parseFloat(e.target.value))}
            className="ui-input h-9 w-16 shrink-0 text-xs px-2"
          />
        </div>
      </div>
    );
  }

  return (
    <div>
      <label className="ui-label">{title}</label>
      <input
        type="text"
        value={String(value ?? prop.default ?? "")}
        onChange={(e) => onChange(e.target.value)}
        className="ui-input text-xs"
      />
    </div>
  );
}

export function DynamicParamForm({ schema, values, defaults, onChange, className }: Props) {
  const fields = useMemo(() => {
    const props = schema?.properties ?? {};
    return Object.entries(props).filter(([key]) => !HIDDEN_FIELDS.has(key));
  }, [schema]);

  if (fields.length === 0) {
    return <p className="text-xs text-slate-400">No parameters</p>;
  }

  const setField = (key: string, val: unknown) => {
    onChange({ ...values, [key]: val });
  };

  return (
    <div className={className}>
      <div className="space-y-3">
        {fields.map(([key, prop]) => (
          <FieldControl
            key={key}
            name={key}
            prop={prop}
            value={values[key] ?? defaults?.[key]}
            onChange={(v) => setField(key, v)}
          />
        ))}
      </div>
    </div>
  );
}
