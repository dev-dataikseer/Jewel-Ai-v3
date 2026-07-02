import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import { ImagePlus, Wand2 } from "lucide-react";
import { api, mediaUrl } from "@/lib/api";
import { ModelSelector } from "@/components/studio/ModelSelector";
import { variantPayloadField } from "@/lib/promptUtils";
import type { ConfigOptions } from "@/types";

type Props = {
  options?: ConfigOptions;
};

export function PromptSandbox({ options }: Props) {
  const [workflow, setWorkflow] = useState("CATALOG_IMAGE");
  const [jewelryType, setJewelryType] = useState("Ring");
  const [promptText, setPromptText] = useState("");
  const [variantLabel, setVariantLabel] = useState("");
  const [composedPrompt, setComposedPrompt] = useState("");
  const [debug, setDebug] = useState<unknown>(null);
  const [outputUrl, setOutputUrl] = useState("");
  const [modelEndpointId, setModelEndpointId] = useState("");
  const [modelParams, setModelParams] = useState<Record<string, unknown>>({});
  const [testImage, setTestImage] = useState<File | null>(null);
  const [testImageUrl, setTestImageUrl] = useState("");

  const { data: variants = [] } = useQuery({
    queryKey: ["prompts", "variants", workflow],
    queryFn: async () =>
      (
        await api.get<Array<{ workflow: string; variant_key: string; label: string }>>("/prompts/variants", {
          params: { workflow },
        })
      ).data,
  });

  const composeMutation = useMutation({
    mutationFn: async () => {
      const body: Record<string, unknown> = {
        workflow,
        jewelry_type: jewelryType,
        prompt_text: promptText || null,
        ...(variantLabel ? variantPayloadField(workflow, variantLabel) : {}),
      };
      const res = await api.post<{ prompt: string; debug: unknown }>("/prompts/test", body);
      return res.data;
    },
    onSuccess: (data) => {
      setComposedPrompt(data.prompt);
      setDebug(data.debug);
      toast.success("Prompt composed");
    },
    onError: () => toast.error("Compose failed"),
  });

  const generateMutation = useMutation({
    mutationFn: async () => {
      if (!testImage && !testImageUrl) {
        throw new Error("Upload a test product image first");
      }
      let imageUrl = testImageUrl;
      if (testImage) {
        const form = new FormData();
        form.append("file", testImage);
        const uploaded = await api.post<{ original_url: string }>("/assets/upload", form);
        imageUrl = uploaded.data.original_url;
        setTestImageUrl(imageUrl);
      }
      const body: Record<string, unknown> = {
        workflow,
        jewelry_type: jewelryType,
        prompt_text: promptText || null,
        model_endpoint_id: modelEndpointId || undefined,
        model_params: modelParams,
        image_url: imageUrl,
        ...(variantLabel ? variantPayloadField(workflow, variantLabel) : {}),
      };
      const res = await api.post<{
        output_url: string;
        prompt: string;
        model: string;
        version_ids: Record<string, string | null>;
      }>("/prompts/test/generate", body);
      return res.data;
    },
    onSuccess: (data) => {
      setComposedPrompt(data.prompt);
      setOutputUrl(data.output_url);
      toast.success(`Generated with ${data.model}`);
    },
    onError: () => toast.error("Test generation failed"),
  });

  const workflows = (options?.workflows ?? []).filter((w) => w.id !== "RATE_TOOLS");

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
      <div className="rounded-2xl border border-slate-200 bg-white p-5 space-y-4">
        <h3 className="text-xs font-bold uppercase text-slate-500">Workflow</h3>
        <select
          value={workflow}
          onChange={(e) => setWorkflow(e.target.value)}
          className="h-10 w-full rounded-lg border border-slate-200 px-3 text-xs"
        >
          {workflows.map((w) => (
            <option key={w.id} value={w.id}>
              {w.label}
            </option>
          ))}
        </select>
        <select
          value={jewelryType}
          onChange={(e) => setJewelryType(e.target.value)}
          className="h-10 w-full rounded-lg border border-slate-200 px-3 text-xs"
        >
          {(options?.jewelryTypes ?? ["Ring"]).map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
        {variants.length > 0 && (
          <select
            value={variantLabel}
            onChange={(e) => setVariantLabel(e.target.value)}
            className="h-10 w-full rounded-lg border border-slate-200 px-3 text-xs"
          >
            <option value="">— variant —</option>
            {variants.map((v) => (
              <option key={v.variant_key} value={v.label}>
                {v.label}
              </option>
            ))}
          </select>
        )}
        <textarea
          value={promptText}
          onChange={(e) => setPromptText(e.target.value)}
          placeholder="Optional user instruction…"
          className="min-h-[80px] w-full rounded-lg border border-slate-200 p-3 text-xs font-mono"
        />
        <button
          type="button"
          onClick={() => composeMutation.mutate()}
          disabled={composeMutation.isPending}
          className="w-full h-10 rounded-lg border border-slate-200 text-xs font-bold text-slate-700 hover:bg-slate-50"
        >
          {composeMutation.isPending ? "Composing…" : "Preview composed prompt"}
        </button>
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white p-5 space-y-3">
        <h3 className="text-xs font-bold uppercase text-slate-500">Composed prompt</h3>
        <pre className="min-h-[200px] max-h-[320px] overflow-auto rounded-lg bg-slate-50 p-3 text-[11px] font-mono text-slate-700 whitespace-pre-wrap">
          {composedPrompt || "Run preview to see assembled prompt…"}
        </pre>
        {composedPrompt && (
          <p className="text-[10px] text-slate-400">{composedPrompt.length} characters</p>
        )}
        {debug != null && (
          <details className="text-[10px]">
            <summary className="cursor-pointer font-bold text-slate-500">Debug trace</summary>
            <pre className="mt-2 overflow-auto rounded bg-slate-50 p-2 font-mono">
              {JSON.stringify(debug, null, 2)}
            </pre>
          </details>
        )}
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white p-5 space-y-4">
        <h3 className="text-xs font-bold uppercase text-slate-500">Live generation</h3>
        <div>
          <label htmlFor="sandbox-test-image" className="mb-1 block text-xs font-semibold text-slate-600">
            Test product image (required)
          </label>
          <input
            id="sandbox-test-image"
            type="file"
            accept="image/jpeg,image/png,image/webp"
            className="block w-full text-xs text-slate-600"
            onChange={(e) => setTestImage(e.target.files?.[0] || null)}
          />
        </div>
        <ModelSelector
          workflow={workflow}
          hasInput={Boolean(testImage || testImageUrl)}
          imageCount={testImage || testImageUrl ? 1 : 0}
          selectedEndpointId={modelEndpointId}
          modelParams={modelParams}
          onModelChange={(id) => setModelEndpointId(id)}
          onParamsChange={setModelParams}
        />
        <button
          type="button"
          onClick={() => generateMutation.mutate()}
          disabled={generateMutation.isPending}
          className="w-full h-11 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 text-white text-xs font-bold flex items-center justify-center gap-2"
        >
          <Wand2 className="size-4" />
          {generateMutation.isPending ? "Generating…" : "Test generate"}
        </button>
        {outputUrl ? (
          <div className="rounded-xl border border-slate-100 overflow-hidden">
            <img src={mediaUrl(outputUrl)} alt="Test output" className="w-full object-contain max-h-64 bg-slate-50" />
            <a
              href={mediaUrl(outputUrl)}
              target="_blank"
              rel="noreferrer"
              className="flex items-center justify-center gap-1 py-2 text-[10px] font-bold text-blue-600 hover:underline"
            >
              <ImagePlus className="size-3" />
              Open full size
            </a>
          </div>
        ) : (
          <p className="text-xs text-slate-400 text-center py-8">Output will appear here</p>
        )}
      </div>
    </div>
  );
}
