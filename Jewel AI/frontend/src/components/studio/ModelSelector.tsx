import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { DynamicParamForm } from "@/components/studio/DynamicParamForm";
import type { ModelDefinition } from "@/types";

const PREFS_KEY = "jewel:modelPrefs:v3";

type ModelPrefs = {
  endpoint_id: string;
  params: Record<string, unknown>;
};

function loadPrefs(workflow: string): ModelPrefs | null {
  try {
    const raw = localStorage.getItem(`${PREFS_KEY}:${workflow}`);
    return raw ? (JSON.parse(raw) as ModelPrefs) : null;
  } catch {
    return null;
  }
}

function savePrefs(workflow: string, prefs: ModelPrefs) {
  localStorage.setItem(`${PREFS_KEY}:${workflow}`, JSON.stringify(prefs));
}

/** Drop stale saved params that no longer match the model schema (avoids 400s after catalog updates). */
function sanitizeParams(
  schema: ModelDefinition["input_schema"] | undefined,
  defaults: Record<string, unknown> | undefined,
  params: Record<string, unknown>
): Record<string, unknown> {
  const props = schema?.properties ?? {};
  const next: Record<string, unknown> = { ...(defaults ?? {}) };
  for (const [key, value] of Object.entries(params)) {
    const prop = props[key];
    if (!prop) continue;
    if (value === undefined || value === null || value === "") continue;
    if (prop.enum && !prop.enum.map(String).includes(String(value))) {
      next[key] = prop.default ?? defaults?.[key] ?? prop.enum[0];
      continue;
    }
    next[key] = value;
  }
  return next;
}

type Props = {
  workflow: string;
  hasInput: boolean;
  imageCount: number;
  selectedEndpointId: string;
  modelParams: Record<string, unknown>;
  onModelChange: (endpointId: string, model: ModelDefinition | null) => void;
  onParamsChange: (params: Record<string, unknown>) => void;
};

export function ModelSelector({
  workflow,
  hasInput,
  imageCount,
  selectedEndpointId,
  modelParams,
  onModelChange,
  onParamsChange,
}: Props) {
  const { data: models = [], isLoading, isError } = useQuery({
    queryKey: ["models", "image_edit", workflow, hasInput],
    queryFn: async () =>
      (
        await api.get<ModelDefinition[]>("/models", {
          params: {
            image_edit_only: true,
            workflow,
            has_input: hasInput,
            image_count: imageCount,
          },
        })
      ).data,
    retry: 2,
    staleTime: 60_000,
  });

  const selected =
    models.find((m) => m.endpoint_id === selectedEndpointId) ?? models[0] ?? null;

  useEffect(() => {
    if (models.length === 0) return;
    const saved = loadPrefs(workflow);
    const match = saved
      ? models.find((m) => m.endpoint_id === saved.endpoint_id)
      : null;
    // Prefer I2I when input present; otherwise keep saved / first
    const preferred =
      hasInput
        ? models.find((m) => m.ui?.supports_i2i || m.capabilities?.image_to_image) ??
          models[0]
        : models.find((m) => m.ui?.supports_t2i && !m.ui?.supports_i2i) ?? models[0];
    const pick = match ?? preferred ?? models[0];
    if (pick && pick.endpoint_id !== selectedEndpointId) {
      onModelChange(pick.endpoint_id, pick);
      onParamsChange(
        sanitizeParams(pick.input_schema, pick.default_params, {
          ...pick.default_params,
          ...(saved?.params ?? {}),
        })
      );
    } else if (pick && Object.keys(modelParams).length === 0) {
      onParamsChange(
        sanitizeParams(pick.input_schema, pick.default_params, {
          ...pick.default_params,
          ...(saved?.params ?? {}),
        })
      );
    }
  }, [models, workflow, hasInput]);

  useEffect(() => {
    if (selectedEndpointId && Object.keys(modelParams).length > 0) {
      savePrefs(workflow, {
        endpoint_id: selectedEndpointId,
        params: modelParams,
      });
    }
  }, [workflow, selectedEndpointId, modelParams]);

  // Repair stale localStorage params after catalog enum changes (e.g. GPT Image 2 sizes).
  useEffect(() => {
    const pick =
      models.find((m) => m.endpoint_id === selectedEndpointId) ?? models[0] ?? null;
    if (!pick || Object.keys(modelParams).length === 0) return;
    const props = pick.input_schema?.properties ?? {};
    const dirty = Object.entries(modelParams).some(([key, value]) => {
      const prop = props[key];
      return Boolean(
        prop?.enum &&
          value !== undefined &&
          value !== null &&
          value !== "" &&
          !prop.enum.map(String).includes(String(value))
      );
    });
    if (dirty) {
      onParamsChange(sanitizeParams(pick.input_schema, pick.default_params, modelParams));
    }
  }, [models, selectedEndpointId, modelParams, onParamsChange]);

  if (isLoading) {
    return <p className="text-xs text-slate-400">Loading…</p>;
  }

  if (isError) {
    return <p className="text-xs text-rose-600">Models unavailable</p>;
  }

  if (models.length === 0) {
    return <p className="text-xs text-amber-600">No models</p>;
  }

  const current =
    models.find((m) => m.endpoint_id === selectedEndpointId) ?? selected;
  const minImages = current?.limits?.min_images ?? current?.ui?.min_images ?? 1;
  const maxImages = current?.limits?.max_images ?? current?.ui?.max_images ?? 14;
  const needsImage =
    (current?.capabilities?.requires_image ?? true) &&
    !(current?.ui?.supports_t2i && !current?.ui?.supports_i2i);
  const missingImage = needsImage && imageCount < minImages;
  const overMax = imageCount > maxImages;

  return (
    <div className="space-y-3">
      <div>
        <select
          value={selectedEndpointId || current?.endpoint_id || ""}
          onChange={(e) => {
            const m = models.find((x) => x.endpoint_id === e.target.value);
            if (m) {
              onModelChange(m.endpoint_id, m);
              onParamsChange(sanitizeParams(m.input_schema, m.default_params, { ...m.default_params }));
            }
          }}
          className="ui-input text-xs font-semibold"
          aria-label="Model"
        >
          {models.map((m) => {
            const badge = m.ui?.badge ? ` · ${m.ui.badge}` : "";
            return (
              <option key={m.endpoint_id} value={m.endpoint_id}>
                {m.display_name}
                {badge}
              </option>
            );
          })}
        </select>
        {missingImage ? (
          <p className="mt-1 text-[10px] text-amber-600">
            Need {minImages}+ image{minImages > 1 ? "s" : ""}
          </p>
        ) : null}
        {overMax ? (
          <p className="mt-1 text-[10px] text-amber-600">Max {maxImages} images</p>
        ) : null}
      </div>
      {current ? (
        <DynamicParamForm
          schema={current.input_schema}
          values={modelParams}
          defaults={current.default_params}
          onChange={onParamsChange}
        />
      ) : null}
    </div>
  );
}
