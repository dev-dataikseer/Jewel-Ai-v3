import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  BadgeCheck,
  BarChart3,
  Check,
  ChevronDown,
  Download,
  Gem,
  Heart,
  History,
  ImagePlus,
  Images,
  Layers3,
  RefreshCcw,
  Settings,
  Sparkles,
  UploadCloud,
  Wand2,
  X,
} from "lucide-react";
import { AppLayout } from "@/components/AppLayout";
import { ModelSelector } from "@/components/studio/ModelSelector";
import { useJobStream } from "@/hooks/useJobStream";
import { api, mediaUrl } from "@/lib/api";
import type { Asset, ConfigOptions, Job, ModelDefinition, RateEntry, StylePreset } from "@/types";
import { WORKFLOWS, workflowLabel } from "@/types";

const WORKFLOW_ICONS: Record<string, typeof Gem> = {
  CATALOG_IMAGE: ImagePlus,
  JEWELRY_ON_MODEL: Sparkles,
  GEMSTONE_COLOR_CHANGE: Gem,
  CUSTOMER_TRY_ON: BadgeCheck,
  REFERENCE_STYLE_MATCH: Images,
  BACKGROUND_REPLACEMENT: Layers3,
  LUXURY_ENHANCEMENT: Wand2,
  CUSTOM_PROMPT: Sparkles,
  BULK_GENERATION: UploadCloud,
  RATE_TOOLS: BarChart3,
};

function MultiSelectDropdown({
  label,
  options,
  selectedValues,
  onChange,
  placeholder = "Select…",
}: {
  label?: string;
  options: string[];
  selectedValues: string[];
  onChange: (values: string[]) => void;
  placeholder?: string;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const toggle = (val: string) => {
    onChange(
      selectedValues.includes(val)
        ? selectedValues.filter((v) => v !== val)
        : [...selectedValues, val]
    );
  };

  return (
    <div className="relative" ref={ref}>
      {label && (
        <label className="mb-1 block text-[11px] font-bold uppercase tracking-wider text-slate-500">
          {label}
        </label>
      )}
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="min-h-9 w-full rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs font-medium text-slate-700 flex items-center justify-between gap-2"
      >
        <span className="flex flex-wrap gap-1 flex-1 text-left">
          {selectedValues.length === 0 ? (
            <span className="text-slate-400">{placeholder}</span>
          ) : (
            selectedValues.map((v) => (
              <span key={v} className="inline-flex items-center gap-0.5 rounded bg-slate-100 px-1.5 py-0.5 text-[11px]">
                {v}
                <X
                  className="size-2.5 cursor-pointer"
                  onClick={(e) => {
                    e.stopPropagation();
                    toggle(v);
                  }}
                />
              </span>
            ))
          )}
        </span>
        <ChevronDown className={`size-3.5 text-slate-400 transition-transform ${open ? "rotate-180" : ""}`} />
      </button>
      {open && (
        <div className="absolute z-50 mt-1 w-full max-h-48 overflow-y-auto rounded-lg border border-slate-200 bg-white p-1 shadow-lg">
          {options.map((opt) => (
            <button
              key={opt}
              type="button"
              onClick={() => toggle(opt)}
              className={`flex w-full items-center justify-between rounded px-2 py-1.5 text-xs ${
                selectedValues.includes(opt) ? "bg-blue-50 text-blue-700 font-semibold" : "hover:bg-slate-50"
              }`}
            >
              {opt}
              {selectedValues.includes(opt) && <Check className="size-3" />}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export function StudioPage() {
  const queryClient = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();

  const [workflow, setWorkflow] = useState("CATALOG_IMAGE");
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [jewelryTypes, setJewelryTypes] = useState<string[]>(["Ring"]);
  const [aspectRatio, setAspectRatio] = useState("1:1");
  const [personGeneration, setPersonGeneration] = useState("ALLOW_ADULT");
  const [numberOfImages, setNumberOfImages] = useState(1);
  const [modelEndpointId, setModelEndpointId] = useState("");
  const [selectedModel, setSelectedModel] = useState<ModelDefinition | null>(null);
  const [modelParams, setModelParams] = useState<Record<string, unknown>>({});
  const [workflowVariantKey, setWorkflowVariantKey] = useState("");
  const [stylePresetId, setStylePresetId] = useState("");
  const [promptText, setPromptText] = useState("");
  const [primaryFiles, setPrimaryFiles] = useState<File[]>([]);
  const [referenceFile, setReferenceFile] = useState<File | null>(null);
  const [favoriteIds, setFavoriteIds] = useState<Set<string>>(new Set());
  const [validationErrors, setValidationErrors] = useState<Record<string, string>>({});

  const isBulk = workflow === "BULK_GENERATION";
  const needsModelReference = workflow === "JEWELRY_ON_MODEL" || workflow === "CUSTOMER_TRY_ON";
  const needsStyleReference = workflow === "REFERENCE_STYLE_MATCH";
  const needsReference = needsModelReference || needsStyleReference;
  const inputImageCount =
    primaryFiles.length + (needsReference && referenceFile ? 1 : 0);

  const { data: options } = useQuery({
    queryKey: ["config", "options"],
    queryFn: async () => (await api.get<ConfigOptions>("/config/options")).data,
  });

  const { data: variants = [] } = useQuery({
    queryKey: ["prompts", "variants"],
    queryFn: async () =>
      (await api.get<Array<{ workflow: string; variant_key: string; label: string }>>("/prompts/variants")).data,
  });

  const promptVariants = useMemo(() => {
    const map: Record<string, Array<{ variant_key: string; label: string }>> = {};
    for (const v of variants) {
      if (!map[v.workflow]) map[v.workflow] = [];
      map[v.workflow].push({ variant_key: v.variant_key, label: v.label });
    }
    return map;
  }, [variants]);

  const workflowVariants = promptVariants[workflow] || [];

  const { data: stylePresets = [] } = useQuery({
    queryKey: ["style-presets", workflow],
    queryFn: async () => {
      if (workflow === "RATE_TOOLS" || workflow === "BULK_GENERATION") return [];
      const res = await api.get<StylePreset[]>("/prompts/presets", { params: { workflow } });
      return res.data.filter((p) => !p.workflow || p.workflow === workflow);
    },
    enabled: workflow !== "RATE_TOOLS" && workflow !== "BULK_GENERATION",
  });

  const [sessionJobs, setSessionJobs] = useState<Job[]>([]);

  const { data: recentJobs = [] } = useQuery({
    queryKey: ["recent-jobs"],
    queryFn: async () => (await api.get<JobsListResponse>("/jobs", { params: { limit: 8 } })).data.items,
  });

  const { data: rates = [] } = useQuery({
    queryKey: ["rates"],
    queryFn: async () => (await api.get<RateEntry[]>("/rates")).data,
    enabled: workflow === "RATE_TOOLS",
  });

  const { data: liveRates } = useQuery({
    queryKey: ["rates", "live"],
    queryFn: async () => (await api.get("/rates/live")).data,
    enabled: workflow === "RATE_TOOLS",
  });

  useQuery({
    queryKey: ["favorites"],
    queryFn: async () => {
      const ids = (await api.get<string[]>("/favorites")).data;
      setFavoriteIds(new Set(ids));
      return ids;
    },
  });

  const streamingIds = useMemo(
    () =>
      sessionJobs
        .filter((j) => j.status === "PENDING" || j.status === "PROCESSING")
        .map((j) => j.id),
    [sessionJobs]
  );

  useJobStream(streamingIds, {
    onUpdate: (job) => {
      setSessionJobs((prev) => prev.map((j) => (j.id === job.id ? { ...j, ...job } : j)));
      if (job.status === "COMPLETED" || job.status === "FAILED") {
        queryClient.invalidateQueries({ queryKey: ["recent-jobs"] });
      }
    },
  });

  useEffect(() => {
    const jobId = searchParams.get("jobId");
    if (!jobId) return;
    api
      .get<Job>(`/jobs/${jobId}`)
      .then((res) => {
        setActiveJobId(res.data.id);
        setSessionJobs((list) =>
          list.some((j) => j.id === res.data.id) ? list : [res.data, ...list]
        );
      })
      .catch(() => toast.error("Could not load job from link"));
    searchParams.delete("jobId");
    setSearchParams(searchParams, { replace: true });
  }, [searchParams, setSearchParams, setSessionJobs]);

  useEffect(() => {
    setWorkflowVariantKey("");
    const first = workflowVariants[0];
    if (first) setWorkflowVariantKey(first.variant_key);
  }, [workflow, workflowVariants]);

  useEffect(() => {
    if (options?.jewelryTypes?.[0] && jewelryTypes.length === 1 && jewelryTypes[0] === "Ring") {
      setJewelryTypes([options.jewelryTypes[0]]);
    }
  }, [options?.jewelryTypes]);

  const allJobs = useMemo(() => {
    const map = new Map<string, Job>();
    sessionJobs.forEach((j) => map.set(j.id, j));
    recentJobs.forEach((j) => {
      if (!map.has(j.id)) map.set(j.id, j);
    });
    return Array.from(map.values());
  }, [sessionJobs, recentJobs]);

  const activeJob = activeJobId ? allJobs.find((j) => j.id === activeJobId) ?? null : null;
  const activeJobs = sessionJobs.filter((j) => j.status === "PENDING" || j.status === "PROCESSING");

  const [primaryPreviews, setPrimaryPreviews] = useState<{ file: File; url: string }[]>([]);
  const [referencePreview, setReferencePreview] = useState("");

  useEffect(() => {
    const urls = primaryFiles.map((file) => ({ file, url: URL.createObjectURL(file) }));
    setPrimaryPreviews(urls);
    return () => urls.forEach((item) => URL.revokeObjectURL(item.url));
  }, [primaryFiles]);

  useEffect(() => {
    const url = referenceFile ? URL.createObjectURL(referenceFile) : "";
    setReferencePreview(url);
    return () => {
      if (url) URL.revokeObjectURL(url);
    };
  }, [referenceFile]);

  const uploadOne = async (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return (await api.post<Asset>("/assets/upload", form)).data;
  };

  const uploadMany = async (files: File[]) => {
    const form = new FormData();
    files.forEach((f) => form.append("files", f));
    return (await api.post<Asset[]>("/assets/bulk-upload", form)).data;
  };

  const generateMutation = useMutation({
    mutationFn: async () => {
      const errors: Record<string, string> = {};
      if (primaryFiles.length === 0) errors.productImage = "Upload at least one product image";
      if (needsReference && !referenceFile) {
        errors.referenceImage = needsStyleReference
          ? "Upload a style reference image"
          : "Upload a model portrait";
      }
      if (Object.keys(errors).length > 0) {
        setValidationErrors(errors);
        throw new Error(Object.values(errors)[0]);
      }
      setValidationErrors({});

      const referenceAsset = referenceFile ? await uploadOne(referenceFile) : null;
      const selectedVariant = workflowVariants.find((v) => v.variant_key === workflowVariantKey);

      const payload: Record<string, unknown> = {
        workflow,
        jewelry_type: jewelryTypes.join(", "),
        prompt_text: promptText || null,
        aspect_ratio: aspectRatio,
        person_generation: personGeneration,
        number_of_images: numberOfImages,
        model_endpoint_id: modelEndpointId || selectedModel?.endpoint_id,
        model_params: modelParams,
        reference_url: referenceAsset?.original_url,
        ...(stylePresetId ? { style_preset_id: stylePresetId } : {}),
        ...(workflow === "GEMSTONE_COLOR_CHANGE" && selectedVariant
          ? { gemstone_target_color: selectedVariant.label }
          : {}),
        ...(workflow === "BACKGROUND_REPLACEMENT" && selectedVariant
          ? { background_style: selectedVariant.label }
          : {}),
        ...(workflow === "LUXURY_ENHANCEMENT" && selectedVariant
          ? { metal_type: selectedVariant.label }
          : {}),
        ...(workflow === "REFERENCE_STYLE_MATCH" && selectedVariant
          ? { background_style: selectedVariant.label }
          : {}),
      };

      if (isBulk || primaryFiles.length > 1) {
        const assets = await uploadMany(primaryFiles);
        const res = await api.post<{ jobIds: string[] }>("/jobs/bulk", {
          ...payload,
          workflow: "CATALOG_IMAGE",
          asset_ids: assets.map((a) => a.id),
        });
        const jobs = await Promise.all(
          res.data.jobIds.map((id) => api.get<Job>(`/jobs/${id}`).then((r) => r.data))
        );
        return jobs;
      }

      const asset = await uploadOne(primaryFiles[0]);
      const job = (await api.post<Job>("/jobs", { ...payload, asset_id: asset.id })).data;
      return [job];
    },
    onSuccess: (jobs) => {
      setSessionJobs((prev) => [...jobs, ...prev]);
      if (jobs[0]) setActiveJobId(jobs[0].id);
      queryClient.invalidateQueries({ queryKey: ["recent-jobs"] });
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
      toast.success(jobs.length > 1 ? "Bulk batch started" : "Generation started");
    },
    onError: (err: Error) => toast.error(err.message || "Generation failed"),
  });

  const regenerateMutation = useMutation({
    mutationFn: (jobId: string) => api.post<Job>(`/jobs/${jobId}/regenerate`).then((r) => r.data),
    onSuccess: (job) => {
      setSessionJobs((prev) => [job, ...prev]);
      setActiveJobId(job.id);
      toast.success("Regeneration started");
    },
    onError: () => toast.error("Regeneration failed"),
  });

  const toggleFavorite = useCallback(async (job: Job) => {
    const isFav = favoriteIds.has(job.id);
    try {
      if (isFav) {
        await api.delete(`/favorites/${job.id}`);
        setFavoriteIds((s) => {
          const n = new Set(s);
          n.delete(job.id);
          return n;
        });
      } else {
        await api.post(`/favorites/${job.id}`);
        setFavoriteIds((s) => new Set(s).add(job.id));
      }
      queryClient.invalidateQueries({ queryKey: ["favorites"] });
    } catch {
      toast.error("Could not update favorite");
    }
  }, [favoriteIds, queryClient]);

  const schemaProps = selectedModel?.input_schema?.properties ?? {};
  const showAspectRatio = "aspect_ratio" in schemaProps || "image_size" in schemaProps;
  const showPersonGeneration = Boolean(selectedModel?.capabilities?.person_generation);
  const showNumberOfImages =
    "num_images" in schemaProps || "num_samples" in schemaProps;

  const workflowVariantLabel =
    workflow === "GEMSTONE_COLOR_CHANGE"
      ? "Target Gemstone Color"
      : workflow === "BACKGROUND_REPLACEMENT"
        ? "Background Style"
        : workflow === "LUXURY_ENHANCEMENT"
          ? "Metal Type"
          : workflow === "REFERENCE_STYLE_MATCH"
            ? "Match Focus"
            : null;

  const onPrimaryInput = (files: FileList | null) => {
    if (!files?.length) return;
    const list = Array.from(files);
    setPrimaryFiles(isBulk ? list.slice(0, 30) : list.slice(0, 1));
  };

  const selectWorkflow = (id: string) => {
    setWorkflow(id);
    setSessionJobs([]);
    setPrimaryFiles([]);
    setReferenceFile(null);
    setActiveJobId(null);
  };

  return (
    <AppLayout>
      <main className="mx-auto max-w-[1600px] w-full px-4 lg:px-6 py-6 flex-1">
        <div
          className={`grid grid-cols-1 gap-5 items-start ${
            workflow === "RATE_TOOLS" ? "lg:grid-cols-[220px_1fr]" : "lg:grid-cols-[220px_1fr_300px]"
          }`}
        >
          {/* Sidebar */}
          <aside className="space-y-3 lg:sticky lg:top-20">
            <p className="text-[11px] font-bold uppercase tracking-wider text-slate-500 px-1">Workflows</p>
            <div className="space-y-1">
              {WORKFLOWS.map((item) => {
                const Icon = WORKFLOW_ICONS[item.id] || Sparkles;
                const active = workflow === item.id;
                return (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => selectWorkflow(item.id)}
                    className={`flex w-full items-center gap-2.5 rounded-lg px-3 py-2.5 text-left text-sm transition-colors ${
                      active
                        ? "bg-blue-600 text-white font-semibold shadow-sm"
                        : "text-slate-600 hover:bg-slate-100 font-medium"
                    }`}
                  >
                    <Icon className="size-3.5 shrink-0" />
                    {item.label}
                  </button>
                );
              })}
            </div>
            <div className="rounded-xl border border-slate-200 bg-white p-3 mt-4">
              <p className="text-[10px] font-bold uppercase text-slate-500">Session</p>
              <div className="grid grid-cols-2 gap-2 mt-2 text-center">
                <div className="rounded-lg bg-slate-50 p-2">
                  <p className="text-[10px] text-slate-500">Jobs</p>
                  <p className="text-sm font-bold">{sessionJobs.length}</p>
                </div>
                <div className="rounded-lg bg-slate-50 p-2">
                  <p className="text-[10px] text-slate-500">Active</p>
                  <p className={`text-sm font-bold ${activeJobs.length ? "text-blue-600" : ""}`}>
                    {activeJobs.length}
                  </p>
                </div>
              </div>
            </div>
          </aside>

          {/* Canvas */}
          <section className="space-y-5 min-w-0">
            <div>
              <h2 className="text-xl font-semibold text-slate-900 flex items-center gap-2">
                <Sparkles className="size-4 text-blue-600" />
                {workflowLabel(workflow)} Studio
              </h2>
            </div>

            {workflow === "RATE_TOOLS" ? (
              <div className="space-y-4">
                <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                  <h3 className="text-sm font-bold text-slate-800 mb-3">Live Spot Rates</h3>
                  {liveRates?.gold_pkr_per_gram != null ? (
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
                      <div className="rounded-lg border border-slate-100 bg-slate-50 p-3">
                        <p className="text-slate-500 text-xs">Gold (PKR/g)</p>
                        <p className="font-bold text-lg">{liveRates.gold_pkr_per_gram.toLocaleString()}</p>
                      </div>
                      <div className="rounded-lg border border-slate-100 bg-slate-50 p-3">
                        <p className="text-slate-500 text-xs">Silver (PKR/g)</p>
                        <p className="font-bold text-lg">{liveRates.silver_pkr_per_gram?.toLocaleString()}</p>
                      </div>
                    </div>
                  ) : (
                    <p className="text-sm text-slate-400">Live feed unavailable.</p>
                  )}
                </div>
                <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                  <h3 className="text-sm font-bold text-slate-800 mb-3">Local Rates</h3>
                  {rates.length ? (
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                      {rates.map((r) => (
                        <div key={r.id} className="rounded-lg border border-slate-100 p-3 text-xs">
                          <p className="font-bold">{r.rate_type}</p>
                          <p className="text-blue-600 font-bold mt-1">
                            {r.currency} {r.value.toLocaleString()}
                          </p>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-slate-400">Add rates in Admin → Rates.</p>
                  )}
                </div>
              </div>
            ) : (
              <>
                <div className="rounded-2xl border border-slate-200 bg-white shadow-sm overflow-hidden">
                  <div className="grid grid-cols-1 lg:grid-cols-2 divide-y lg:divide-y-0 lg:divide-x divide-slate-100">
                    {/* Input */}
                    <div className="p-5 min-h-[360px] flex flex-col">
                      <div className="flex items-center justify-between border-b border-slate-100 pb-2 mb-3">
                        <span className="text-[11px] font-bold uppercase text-slate-500">Input</span>
                        {activeJob && (
                          <button
                            type="button"
                            onClick={() => {
                              setActiveJobId(null);
                              setPrimaryFiles([]);
                              setReferenceFile(null);
                            }}
                            className="text-xs font-semibold text-blue-600 hover:underline"
                          >
                            New session
                          </button>
                        )}
                      </div>
                      {activeJob ? (
                        <div className="flex-1 flex items-center justify-center rounded-xl bg-slate-950 p-3 min-h-[240px]">
                          {activeJob.input_url ? (
                            <img
                              src={mediaUrl(activeJob.input_url)}
                              alt="Input"
                              className="max-h-full max-w-full object-contain rounded"
                            />
                          ) : (
                            <span className="text-xs text-slate-500">No input</span>
                          )}
                        </div>
                      ) : needsReference ? (
                        <div className="grid grid-cols-2 gap-3 flex-1">
                          <UploadZone
                            id="studio-product-upload"
                            label="Product"
                            error={validationErrors.productImage}
                            previews={primaryPreviews.map((p) => p.url)}
                            onFiles={(files) => {
                              setValidationErrors((e) => ({ ...e, productImage: "" }));
                              onPrimaryInput(files);
                            }}
                          />
                          <UploadZone
                            id="studio-reference-upload"
                            label={needsStyleReference ? "Reference" : "Portrait"}
                            error={validationErrors.referenceImage}
                            previews={referencePreview ? [referencePreview] : []}
                            onFiles={(files) => {
                              setValidationErrors((e) => ({ ...e, referenceImage: "" }));
                              setReferenceFile(files?.[0] || null);
                            }}
                            single
                          />
                        </div>
                      ) : (
                        <UploadZone
                          id="studio-product-upload"
                          label={`Product${isBulk ? " (up to 30)" : ""}`}
                          error={validationErrors.productImage}
                          previews={primaryPreviews.map((p) => p.url)}
                          onFiles={(files) => {
                            setValidationErrors((e) => ({ ...e, productImage: "" }));
                            onPrimaryInput(files);
                          }}
                          multiple={isBulk}
                        />
                      )}
                    </div>

                    {/* Output */}
                    <div className="p-5 min-h-[360px] flex flex-col bg-slate-50/30">
                      <div className="flex items-center justify-between border-b border-slate-100 pb-2 mb-3">
                        <span className="text-[11px] font-bold uppercase text-slate-500">Output</span>
                        {activeJob?.status === "COMPLETED" && (
                          <div className="flex gap-1">
                            <button
                              type="button"
                              onClick={() => regenerateMutation.mutate(activeJob.id)}
                              disabled={regenerateMutation.isPending}
                              aria-label="Regenerate image"
                              className="text-xs font-semibold text-slate-600 px-2 py-1 rounded hover:bg-slate-100"
                            >
                              <RefreshCcw className={`inline size-3 mr-1 ${regenerateMutation.isPending ? "animate-spin" : ""}`} />
                              Retry
                            </button>
                            <button
                              type="button"
                              onClick={() => toggleFavorite(activeJob)}
                              aria-label={favoriteIds.has(activeJob.id) ? "Remove from favorites" : "Add to favorites"}
                              className="text-xs font-semibold text-slate-600 px-2 py-1 rounded hover:bg-slate-100"
                            >
                              <Heart
                                className={`inline size-3 mr-1 ${favoriteIds.has(activeJob.id) ? "fill-red-500 text-red-500" : ""}`}
                              />
                              Save
                            </button>
                            {activeJob.output_url && (
                              <a
                                href={mediaUrl(activeJob.output_url)}
                                download
                                target="_blank"
                                rel="noreferrer"
                                aria-label="Download generated image"
                                className="text-xs font-semibold text-slate-600 px-2 py-1 rounded hover:bg-slate-100"
                              >
                                <Download className="inline size-3 mr-1" />
                                Download
                              </a>
                            )}
                          </div>
                        )}
                      </div>
                      {!activeJob ? (
                        <div className="flex-1 flex flex-col items-center justify-center text-center p-6 rounded-xl border border-dashed border-slate-200 bg-white">
                          <Wand2 className="size-8 text-slate-300 mb-2" />
                          <p className="text-sm font-semibold text-slate-700">Studio Standby</p>
                          <p className="text-xs text-slate-500 mt-1">Upload and click Generate</p>
                        </div>
                      ) : (
                        <div className="flex-1 flex items-center justify-center rounded-xl bg-slate-950 p-3 min-h-[240px]">
                          {activeJob.status === "COMPLETED" && activeJob.output_url ? (
                            <img
                              src={mediaUrl(activeJob.output_url)}
                              alt="Output"
                              className="max-h-full max-w-full object-contain rounded"
                            />
                          ) : (
                            <div className="text-center" aria-live="polite">
                              <RefreshCcw
                                className={`size-8 text-blue-500 mx-auto ${
                                  activeJob.status === "PROCESSING" || activeJob.status === "PENDING"
                                    ? "animate-spin"
                                    : ""
                                }`}
                              />
                              {activeJob.status === "FAILED" && (
                                <p className="text-xs text-rose-500 font-bold mt-2">{activeJob.error_message}</p>
                              )}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                </div>

                <input
                  type="text"
                  value={promptText}
                  onChange={(e) => setPromptText(e.target.value)}
                  placeholder="Optional instructions: lighting, mood, sparkles…"
                  className="h-10 w-full rounded-lg border border-slate-200 bg-white px-4 text-xs font-medium outline-none focus:ring-1 focus:ring-blue-500"
                />

                {/* Gallery strip */}
                <div className="rounded-xl border border-slate-200 bg-white p-4">
                  <p className="text-[11px] font-bold uppercase text-slate-500 mb-3 flex items-center gap-1">
                    <History className="size-3.5" /> Recent
                  </p>
                  <div className="flex gap-2 overflow-x-auto pb-1">
                    {[...sessionJobs, ...recentJobs.filter((r) => !sessionJobs.some((s) => s.id === r.id))]
                      .slice(0, 16)
                      .map((job) => (
                        <button
                          key={job.id}
                          type="button"
                          onClick={() => setActiveJobId(job.id)}
                          className={`relative size-14 shrink-0 rounded-lg overflow-hidden border ${
                            activeJobId === job.id ? "border-blue-600 ring-2 ring-blue-500/20" : "border-slate-200"
                          }`}
                        >
                          {(job.output_url || job.input_url) && (
                            <img
                              src={mediaUrl(job.output_url || job.input_url)}
                              alt=""
                              className="w-full h-full object-cover"
                            />
                          )}
                        </button>
                      ))}
                  </div>
                </div>
              </>
            )}
          </section>

          {/* Parameters */}
          {workflow !== "RATE_TOOLS" && (
            <aside className="space-y-4 lg:sticky lg:top-20">
              <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm space-y-4">
                <p className="text-[11px] font-bold uppercase text-slate-500 flex items-center gap-1">
                  <Settings className="size-3.5" /> Parameters
                </p>
                <MultiSelectDropdown
                  label="Jewelry Type"
                  options={options?.jewelryTypes ?? ["Ring"]}
                  selectedValues={jewelryTypes}
                  onChange={setJewelryTypes}
                />
                {workflowVariantLabel && workflowVariants.length > 0 && (
                  <div>
                    <label className="mb-1 block text-[11px] font-bold uppercase text-slate-500">
                      {workflowVariantLabel}
                    </label>
                    <select
                      value={workflowVariantKey}
                      onChange={(e) => setWorkflowVariantKey(e.target.value)}
                      className="h-9 w-full rounded-lg border border-slate-200 px-2.5 text-xs font-medium"
                    >
                      {workflowVariants.map((v) => (
                        <option key={v.variant_key} value={v.variant_key}>
                          {v.label}
                        </option>
                      ))}
                    </select>
                  </div>
                )}
                {stylePresets.length > 0 && (
                  <div>
                    <label className="mb-1 block text-[11px] font-bold uppercase text-slate-500">
                      Style Preset
                    </label>
                    <select
                      value={stylePresetId}
                      onChange={(e) => setStylePresetId(e.target.value)}
                      className="h-9 w-full rounded-lg border border-slate-200 px-2.5 text-xs font-medium"
                    >
                      <option value="">None</option>
                      {stylePresets.map((p) => (
                        <option key={p.id} value={p.id}>
                          {p.name}
                        </option>
                      ))}
                    </select>
                  </div>
                )}
                <div className="space-y-2">
                  {showAspectRatio && (
                    <select
                      value={aspectRatio}
                      onChange={(e) => setAspectRatio(e.target.value)}
                      className="h-9 w-full rounded-lg border border-slate-200 px-2.5 text-xs"
                    >
                      {(options?.aspectRatios ?? ["1:1"]).map((r) => (
                        <option key={r} value={r}>
                          Aspect {r}
                        </option>
                      ))}
                    </select>
                  )}
                  {showPersonGeneration && (
                    <select
                      value={personGeneration}
                      onChange={(e) => setPersonGeneration(e.target.value)}
                      className="h-9 w-full rounded-lg border border-slate-200 px-2.5 text-xs"
                    >
                      <option value="DONT_ALLOW">DONT_ALLOW</option>
                      <option value="ALLOW_ADULT">ALLOW_ADULT</option>
                      <option value="ALLOW_ALL">ALLOW_ALL</option>
                    </select>
                  )}
                  {showNumberOfImages && (
                    <select
                      value={numberOfImages}
                      onChange={(e) => setNumberOfImages(Number(e.target.value))}
                      className="h-9 w-full rounded-lg border border-slate-200 px-2.5 text-xs"
                    >
                      {[1, 2, 3, 4].map((n) => (
                        <option key={n} value={n}>
                          {n} image{n > 1 ? "s" : ""}
                        </option>
                      ))}
                    </select>
                  )}
                  <ModelSelector
                    workflow={workflow}
                    hasInput={inputImageCount > 0}
                    imageCount={inputImageCount}
                    selectedEndpointId={modelEndpointId}
                    modelParams={modelParams}
                    onModelChange={(endpointId, model) => {
                      setModelEndpointId(endpointId);
                      setSelectedModel(model);
                    }}
                    onParamsChange={setModelParams}
                  />
                </div>
              </div>
              <button
                type="button"
                onClick={() => generateMutation.mutate()}
                disabled={generateMutation.isPending || activeJobs.length > 0}
                className="w-full h-11 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 text-white text-sm font-semibold shadow-md hover:from-blue-700 hover:to-indigo-700 disabled:opacity-60 flex items-center justify-center gap-2"
              >
                {generateMutation.isPending || activeJobs.length > 0 ? (
                  <RefreshCcw className="size-4 animate-spin" />
                ) : (
                  <Wand2 className="size-4" />
                )}
                {generateMutation.isPending ? "Processing…" : "Generate"}
              </button>
            </aside>
          )}
        </div>
      </main>
    </AppLayout>
  );
}

type JobsListResponse = { items: Job[]; next_cursor: string | null };

function UploadZone({
  id,
  label,
  previews,
  onFiles,
  single,
  multiple,
  error,
}: {
  id: string;
  label: string;
  previews: string[];
  onFiles: (files: FileList | null) => void;
  single?: boolean;
  multiple?: boolean;
  error?: string;
}) {
  const inputId = `${id}-input`;
  const helpId = `${id}-help`;
  return (
    <div className="flex flex-col flex-1">
      <label htmlFor={inputId} className="text-[11px] font-bold uppercase text-slate-500 mb-1.5">
        {label}
      </label>
      <label
        htmlFor={inputId}
        className={`flex-1 min-h-[140px] cursor-pointer rounded-xl border-2 border-dashed bg-slate-50/50 p-4 flex flex-col items-center justify-center hover:border-blue-400 hover:bg-blue-50/20 transition-colors ${
          error ? "border-red-400" : "border-slate-200"
        }`}
      >
        <UploadCloud className="size-6 text-blue-600 mb-2" aria-hidden="true" />
        <span className="text-xs font-bold text-slate-700">Click to upload</span>
        <input
          id={inputId}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          className="hidden"
          aria-describedby={helpId}
          multiple={multiple && !single}
          onChange={(e) => {
            onFiles(e.target.files);
            e.target.value = "";
          }}
        />
      </label>
      <p id={helpId} className="sr-only">
        Upload {label.toLowerCase()} image as JPEG, PNG, or WebP
      </p>
      {error && <p className="mt-1 text-xs text-red-600">{error}</p>}
      {previews.length > 0 && (
        <div className="mt-2 flex gap-1 flex-wrap">
          {previews.slice(0, 4).map((url) => (
            <img key={url} src={url} alt="" className="size-12 rounded border object-cover" />
          ))}
        </div>
      )}
    </div>
  );
}
