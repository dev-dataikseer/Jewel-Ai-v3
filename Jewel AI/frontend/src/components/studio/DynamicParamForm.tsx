import { useMemo } from "react";
import type { JsonSchema, JsonSchemaProperty } from "@/types";

const HIDDEN_FIELDS = new Set(["prompt", "instruction", "image_url", "image_urls", "negative_prompt"]);

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
    const max = prop.maximum ?? 100;
    return (
      <div>
        <label className="ui-label mb-1 flex justify-between">
          <span>{title}</span>
          <span className="normal-case tracking-normal text-slate-400 font-medium tabular-nums">{num}</span>
        </label>
        <input
          type="range"
          min={min}
          max={max}
          step={prop.type === "integer" ? 1 : 0.5}
          value={num}
          onChange={(e) => onChange(prop.type === "integer" ? parseInt(e.target.value, 10) : parseFloat(e.target.value))}
          className="w-full accent-blue-600"
        />
        <input
          type="number"
          min={min}
          max={max}
          step={prop.type === "integer" ? 1 : 0.5}
          value={num}
          onChange={(e) => onChange(prop.type === "integer" ? parseInt(e.target.value, 10) : parseFloat(e.target.value))}
          className="ui-input mt-1.5 h-9 text-xs"
        />
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
    return <p className="text-xs text-slate-400">No configurable parameters for this model.</p>;
  }

  const primary = fields.slice(0, 3);
  const advanced = fields.slice(3);

  const setField = (key: string, val: unknown) => {
    onChange({ ...values, [key]: val });
  };

  return (
    <div className={className}>
      <div className="space-y-3">
        {primary.map(([key, prop]) => (
          <FieldControl
            key={key}
            name={key}
            prop={prop}
            value={values[key] ?? defaults?.[key]}
            onChange={(v) => setField(key, v)}
          />
        ))}
      </div>
      {advanced.length > 0 && (
        <details className="mt-3 rounded-xl border border-slate-100 bg-slate-50/50 p-3">
          <summary className="ui-label mb-0 cursor-pointer">
            Advanced parameters
          </summary>
          <div className="mt-3 space-y-3">
            {advanced.map(([key, prop]) => (
              <FieldControl
                key={key}
                name={key}
                prop={prop}
                value={values[key] ?? defaults?.[key]}
                onChange={(v) => setField(key, v)}
              />
            ))}
          </div>
        </details>
      )}
    </div>
  );
}
