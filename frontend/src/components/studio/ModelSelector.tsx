import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { DynamicParamForm } from "@/components/studio/DynamicParamForm";
import type { ModelDefinition } from "@/types";

const PREFS_KEY = "jewel:modelPrefs";

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
  const { data: models = [], isLoading } = useQuery({
    queryKey: ["models", "image_edit", workflow, hasInput, imageCount],
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
  });

  const selected = models.find((m) => m.endpoint_id === selectedEndpointId) ?? models[0] ?? null;

  useEffect(() => {
    if (models.length === 0) return;
    const saved = loadPrefs(workflow);
    const match = saved ? models.find((m) => m.endpoint_id === saved.endpoint_id) : null;
    const pick = match ?? models[0];
    if (pick && pick.endpoint_id !== selectedEndpointId) {
      onModelChange(pick.endpoint_id, pick);
      onParamsChange({ ...pick.default_params, ...(saved?.params ?? {}) });
    } else if (pick && Object.keys(modelParams).length === 0) {
      onParamsChange({ ...pick.default_params, ...(saved?.params ?? {}) });
    }
  }, [models, workflow]);

  useEffect(() => {
    if (selectedEndpointId && Object.keys(modelParams).length > 0) {
      savePrefs(workflow, { endpoint_id: selectedEndpointId, params: modelParams });
    }
  }, [workflow, selectedEndpointId, modelParams]);

  if (isLoading) {
    return <p className="text-xs text-slate-400">Loading models…</p>;
  }

  if (models.length === 0) {
    return <p className="text-xs text-amber-600">No image-edit models available. Check fal.ai settings in Admin.</p>;
  }

  const current = models.find((m) => m.endpoint_id === selectedEndpointId) ?? selected;
  const missingImage = !hasInput;

  return (
    <div className="space-y-3">
      <div>
        <label className="mb-1 block text-[10px] font-bold uppercase tracking-wider text-slate-500">
          AI Model
        </label>
        <select
          value={selectedEndpointId || current?.endpoint_id || ""}
          onChange={(e) => {
            const m = models.find((x) => x.endpoint_id === e.target.value);
            if (m) {
              onModelChange(m.endpoint_id, m);
              onParamsChange({ ...m.default_params });
            }
          }}
          className="h-10 w-full rounded-lg border border-slate-200 bg-white px-2.5 text-xs font-semibold text-slate-800"
        >
          {models.map((m) => (
            <option key={m.endpoint_id} value={m.endpoint_id}>
              {m.display_name}
            </option>
          ))}
        </select>
        {current && (
          <p className="mt-1 text-[10px] text-slate-400 font-mono truncate" title={current.endpoint_id}>
            {current.endpoint_id}
          </p>
        )}
        {missingImage && (
          <p className="mt-1 text-[10px] text-amber-600">Upload a product image to generate.</p>
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
