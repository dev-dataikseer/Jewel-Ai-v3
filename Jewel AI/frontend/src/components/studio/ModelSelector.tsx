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
  const { data: models = [], isLoading, isError, error } = useQuery({
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
      onParamsChange({ ...pick.default_params, ...(saved?.params ?? {}) });
    } else if (pick && Object.keys(modelParams).length === 0) {
      onParamsChange({ ...pick.default_params, ...(saved?.params ?? {}) });
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

  if (isLoading) {
    return <p className="text-xs text-slate-400">Loading models…</p>;
  }

  if (isError) {
    const msg =
      (error as { friendlyMessage?: string })?.friendlyMessage ||
      (error as Error)?.message ||
      "Could not load models";
    return (
      <p className="text-xs text-rose-600">
        {msg}. Check that the API is running and you are logged in.
      </p>
    );
  }

  if (models.length === 0) {
    return (
      <p className="text-xs text-amber-600">
        No models in catalog. Open Admin → Providers and confirm FAL_KEY is set,
        then restart the API.
      </p>
    );
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
        <label className="ui-label">AI Model</label>
        <select
          value={selectedEndpointId || current?.endpoint_id || ""}
          onChange={(e) => {
            const m = models.find((x) => x.endpoint_id === e.target.value);
            if (m) {
              onModelChange(m.endpoint_id, m);
              onParamsChange({ ...m.default_params });
            }
          }}
          className="ui-input text-xs font-semibold"
        >
          {models.map((m, i) => {
            const badge = m.ui?.badge ? ` [${m.ui.badge}]` : "";
            return (
              <option key={m.endpoint_id} value={m.endpoint_id}>
                {i + 1}. {m.display_name}
                {badge}
              </option>
            );
          })}
        </select>
        {current && (
          <div className="mt-1.5 space-y-0.5">
            <div className="flex flex-wrap items-center gap-1.5">
              {current.ui?.badge && (
                <span className="inline-flex rounded-md bg-blue-50 px-1.5 py-0.5 text-[10px] font-semibold text-blue-700 border border-blue-100">
                  {current.ui.badge}
                </span>
              )}
              {current.ui?.provider_label && (
                <span className="text-[10px] font-medium text-slate-500">
                  {current.ui.provider_label}
                </span>
              )}
              {typeof current.ui?.max_images === "number" && (
                <span className="text-[10px] text-slate-400">
                  max {current.ui.max_images} imgs
                </span>
              )}
              {typeof (current.limits?.max_prompt_chars ?? current.ui?.max_prompt_chars) ===
                "number" && (
                <span
                  className="text-[10px] text-slate-400"
                  title={
                    current.limits?.official_prompt_note ||
                    (current.limits?.official_max_prompt_chars
                      ? `Official max ${current.limits.official_max_prompt_chars} chars (${current.limits.official_prompt_status || "documented"})`
                      : "Recommended packing budget (not always an official API hard limit)")
                  }
                >
                  prompt ~
                  {current.limits?.max_prompt_chars ?? current.ui?.max_prompt_chars}{" "}
                  chars
                  {current.limits?.official_max_prompt_chars
                    ? ` / official ${current.limits.official_max_prompt_chars}`
                    : current.limits?.official_prompt_status === "undocumented"
                      ? " (undocumented official)"
                      : ""}
                </span>
              )}
            </div>
            <p
              className="text-[10px] text-slate-400 font-mono truncate"
              title={current.endpoint_id}
            >
              {current.endpoint_id}
            </p>
            {(current.ui?.pricing_note || current.model_info?.pricing) && (
              <p className="text-[10px] text-slate-500">
                {current.ui?.pricing_note || current.model_info?.pricing}
              </p>
            )}
            {current.model_info?.key_strengths && (
              <p
                className="text-[10px] text-slate-500 line-clamp-2"
                title={current.model_info.key_strengths}
              >
                {current.model_info.key_strengths}
              </p>
            )}
          </div>
        )}
        {missingImage && (
          <p className="mt-1 text-[10px] text-amber-600">
            Upload at least {minImages} image
            {minImages > 1 ? "s" : ""} to generate with this model.
          </p>
        )}
        {overMax && (
          <p className="mt-1 text-[10px] text-amber-600">
            This model accepts at most {maxImages} images.
          </p>
        )}
      </div>
      {current && (
        <DynamicParamForm
          schema={current.input_schema}
          values={modelParams}
          defaults={current.default_params}
          onChange={onParamsChange}
        />
      )}
    </div>
  );
}
