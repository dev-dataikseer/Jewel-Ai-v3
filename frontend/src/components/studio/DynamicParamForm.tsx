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
    return (
      <div>
        <label className="mb-1 block text-[10px] font-bold uppercase tracking-wider text-slate-500">{title}</label>
        <select
          value={String(value ?? prop.default ?? prop.enum[0] ?? "")}
          onChange={(e) => onChange(e.target.value)}
          className="h-9 w-full rounded-lg border border-slate-200 px-2.5 text-xs"
        >
          {prop.enum.map((opt) => (
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
      <label className="flex items-center gap-2 text-xs text-slate-700">
        <input
          type="checkbox"
          checked={Boolean(value ?? prop.default ?? false)}
          onChange={(e) => onChange(e.target.checked)}
          className="rounded border-slate-300"
        />
        <span className="font-semibold">{title}</span>
      </label>
    );
  }

  if (prop.type === "integer" || prop.type === "number") {
    const num = value !== undefined && value !== null && value !== "" ? Number(value) : Number(prop.default ?? prop.minimum ?? 0);
    const min = prop.minimum ?? 0;
    const max = prop.maximum ?? 100;
    return (
      <div>
        <label className="mb-1 flex justify-between text-[10px] font-bold uppercase tracking-wider text-slate-500">
          <span>{title}</span>
          <span className="text-slate-400">{num}</span>
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
          className="mt-1 h-8 w-full rounded-lg border border-slate-200 px-2 text-xs"
        />
      </div>
    );
  }

  return (
    <div>
      <label className="mb-1 block text-[10px] font-bold uppercase tracking-wider text-slate-500">{title}</label>
      <input
        type="text"
        value={String(value ?? prop.default ?? "")}
        onChange={(e) => onChange(e.target.value)}
        className="h-9 w-full rounded-lg border border-slate-200 px-2.5 text-xs"
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
        <details className="mt-3 rounded-lg border border-slate-100 bg-slate-50/50 p-3">
          <summary className="cursor-pointer text-[10px] font-bold uppercase tracking-wider text-slate-500">
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
