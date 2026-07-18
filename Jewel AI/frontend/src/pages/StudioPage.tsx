import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  BadgeCheck,
  Check,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
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
  Wand2,
  X,
} from "lucide-react";
import { AppLayout } from "@/components/AppLayout";
import { ImageCropModal } from "@/components/studio/ImageCropModal";
import { BatchProgressPanel } from "@/components/studio/BatchProgressPanel";
import { ModelSelector } from "@/components/studio/ModelSelector";
import { ProductUploadGallery } from "@/components/studio/ProductUploadGallery";
import { UploadZone } from "@/components/studio/UploadZone";
import { jobStatusLabel, useJobStream } from "@/hooks/useJobStream";
import { api, mediaUrl } from "@/lib/api";
import {
  clearBrandKit,
  loadBrandKit,
  patchBrandKit,
} from "@/lib/brandKit";
import {
  clearStudioSession,
  loadStudioSession,
  mergeSessionJobs,
  saveStudioSession,
} from "@/lib/studioSession";
import type {
  Asset,
  BatchOut,
  ConfigOptions,
  Job,
  JobsListResponse,
  ModelDefinition,
  StylePreset,
} from "@/types";
import { STUDIO_SIDEBAR_WORKFLOWS, workflowLabel } from "@/types";

const WORKFLOW_ICONS: Record<string, typeof Gem> = {
  CATALOG_IMAGE: ImagePlus,
  VIRTUAL_TRY_ON: BadgeCheck,
  JEWELRY_ON_MODEL: Sparkles,
  GEMSTONE_COLOR_CHANGE: Gem,
  CUSTOMER_TRY_ON: BadgeCheck,
  REFERENCE_STYLE_MATCH: Images,
  BACKGROUND_REPLACEMENT: Layers3,
  LUXURY_ENHANCEMENT: Wand2,
  CUSTOM_PROMPT: Sparkles,
};

function MultiSelectDropdown({
  label,
  options,
  selectedValues,
  onChange,
  placeholder = "Select...",
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
      if (ref.current && !ref.current.contains(e.target as Node))
        setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const toggle = (val: string) => {
    onChange(
      selectedValues.includes(val)
        ? selectedValues.filter((v) => v !== val)
        : [...selectedValues, val],
    );
  };

  return (
    <div className="relative" ref={ref}>
      {label && <label className="ui-label">{label}</label>}
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="min-h-10 w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 flex items-center justify-between gap-2 outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-500/20"
      >
        <span className="flex flex-wrap gap-1 flex-1 text-left">
          {selectedValues.length === 0 ? (
            <span className="text-slate-400">{placeholder}</span>
          ) : (
            selectedValues.map((v) => (
              <span
                key={v}
                className="inline-flex items-center gap-0.5 rounded bg-slate-100 px-1.5 py-0.5 text-[11px]"
              >
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
        <ChevronDown
          className={`size-3.5 text-slate-400 transition-transform ${open ? "rotate-180" : ""}`}
        />
      </button>
      {open && (
        <div className="absolute z-50 mt-1 w-full max-h-48 overflow-y-auto rounded-lg border border-slate-200 bg-white p-1 shadow-lg">
          {options.map((opt) => (
            <button
              key={opt}
              type="button"
              onClick={() => toggle(opt)}
              className={`flex w-full items-center justify-between rounded px-2 py-1.5 text-xs ${
                selectedValues.includes(opt)
                  ? "bg-blue-50 text-blue-700 font-semibold"
                  : "hover:bg-slate-50"
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
  const [tryOnPreset, setTryOnPreset] = useState<"studio" | "customer">(
    "studio",
  );
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [jewelryTypes, setJewelryTypes] = useState<string[]>(["Ring"]);
  const [aspectRatio, setAspectRatio] = useState("1:1");
  const [personGeneration, setPersonGeneration] = useState("ALLOW_ADULT");
  const [numberOfImages, setNumberOfImages] = useState(1);
  const [modelEndpointId, setModelEndpointId] = useState("");
  const [selectedModel, setSelectedModel] = useState<ModelDefinition | null>(
    null,
  );
  const [modelParams, setModelParams] = useState<Record<string, unknown>>({});
  const [workflowVariantKey, setWorkflowVariantKey] = useState("");
  const [stylePresetId, setStylePresetId] = useState("");
  const [promptText, setPromptText] = useState("");
  const [primaryFiles, setPrimaryFiles] = useState<File[]>([]);
  const [referenceFile, setReferenceFile] = useState<File | null>(null);
  const [logoFile, setLogoFile] = useState<File | null>(null);
  const [favoriteIds, setFavoriteIds] = useState<Set<string>>(new Set());
  const [validationErrors, setValidationErrors] = useState<
    Record<string, string>
  >({});
  const [lightingStyle, setLightingStyle] = useState("");
  const [lastBatchId, setLastBatchId] = useState<string | null>(null);
  const [queueModeInline, setQueueModeInline] = useState(false);
  const [batchForceAllow, setBatchForceAllow] = useState(false);
  const [outputIndex, setOutputIndex] = useState(0);
  const [cropTarget, setCropTarget] = useState<{
    kind: "primary" | "reference" | "logo";
    src: string;
    name: string;
    index?: number;
  } | null>(null);

  const apiWorkflow =
    workflow === "VIRTUAL_TRY_ON"
      ? tryOnPreset === "customer"
        ? "CUSTOMER_TRY_ON"
        : "JEWELRY_ON_MODEL"
      : workflow;
  const isCatalog = workflow === "CATALOG_IMAGE";
  const supportsBulk = primaryFiles.length > 1;
  const isBulk = supportsBulk;
  const needsModelReference = workflow === "VIRTUAL_TRY_ON";
  const needsStyleReference = workflow === "REFERENCE_STYLE_MATCH" || isCatalog;
  const needsReference =
    needsModelReference || workflow === "REFERENCE_STYLE_MATCH";
  const [uploadProgress, setUploadProgress] = useState<string | null>(null);
  const [lockedUrls, setLockedUrls] = useState<{
    input?: string | null;
    reference?: string | null;
    model?: string | null;
    logo?: string | null;
    logoAssetId?: string | null;
    themeAssetId?: string | null;
    assetId?: string | null;
  }>({});
  const inputImageCount =
    primaryFiles.length > 0
      ? primaryFiles.length
      : lockedUrls.input || lockedUrls.assetId
        ? 1
        : 0;

  const { data: options } = useQuery({
    queryKey: ["config", "options"],
    queryFn: async () => (await api.get<ConfigOptions>("/config/options")).data,
    staleTime: 5 * 60_000,
  });

  const { data: variants = [] } = useQuery({
    queryKey: ["prompts", "variants"],
    queryFn: async () =>
      (
        await api.get<
          Array<{ workflow: string; variant_key: string; label: string }>
        >("/prompts/variants")
      ).data,
    staleTime: 5 * 60_000,
  });

  const promptVariants = useMemo(() => {
    const map: Record<
      string,
      Array<{ variant_key: string; label: string }>
    > = {};
    for (const v of variants) {
      if (!map[v.workflow]) map[v.workflow] = [];
      map[v.workflow].push({ variant_key: v.variant_key, label: v.label });
    }
    return map;
  }, [variants]);

  const workflowVariants = promptVariants[apiWorkflow] || [];

  const { data: stylePresets = [] } = useQuery({
    queryKey: ["style-presets", apiWorkflow],
    queryFn: async () => {
      const res = await api.get<StylePreset[]>("/prompts/presets", {
        params: { workflow: apiWorkflow },
      });
      return res.data.filter((p) => !p.workflow || p.workflow === apiWorkflow);
    },
    staleTime: 60_000,
  });

  const [sessionJobs, setSessionJobs] = useState<Job[]>([]);
  const sessionHydrated = useRef(false);

  const { data: recentJobs = [] } = useQuery({
    queryKey: ["recent-jobs"],
    queryFn: async () =>
      (await api.get<JobsListResponse>("/jobs", { params: { limit: 8 } })).data
        .items,
    staleTime: 20_000,
  });

  const { data: favoriteIdList = [] } = useQuery({
    queryKey: ["favorites"],
    queryFn: async () => (await api.get<string[]>("/favorites")).data,
    staleTime: 60_000,
  });

  useEffect(() => {
    setFavoriteIds(new Set(favoriteIdList));
  }, [favoriteIdList]);

  // Restore session workspace + brand kit once on mount
  useEffect(() => {
    if (sessionHydrated.current) return;
    sessionHydrated.current = true;
    const draft = loadStudioSession();
    const kit = loadBrandKit();
    if (draft) {
      setWorkflow(draft.workflow || "CATALOG_IMAGE");
      if (draft.tryOnPreset === "customer" || draft.tryOnPreset === "studio") {
        setTryOnPreset(draft.tryOnPreset);
      }
      if (draft.jewelryTypes?.length) setJewelryTypes(draft.jewelryTypes);
      if (draft.aspectRatio) setAspectRatio(draft.aspectRatio);
      if (draft.personGeneration) setPersonGeneration(draft.personGeneration);
      if (draft.numberOfImages) setNumberOfImages(draft.numberOfImages);
      if (draft.modelEndpointId) setModelEndpointId(draft.modelEndpointId);
      if (draft.modelParams) setModelParams(draft.modelParams);
      if (draft.workflowVariantKey) setWorkflowVariantKey(draft.workflowVariantKey);
      if (draft.stylePresetId) setStylePresetId(draft.stylePresetId);
      if (draft.promptText) setPromptText(draft.promptText);
      if (draft.lightingStyle) setLightingStyle(draft.lightingStyle);
      if (draft.activeJobId) setActiveJobId(draft.activeJobId);
      if (draft.lastBatchId) setLastBatchId(draft.lastBatchId);
      setLockedUrls({
        input: draft.lockedInputUrl,
        reference: draft.lockedReferenceUrl || kit?.themeUrl || null,
        model: draft.lockedModelUrl,
        logo: draft.lockedLogoUrl || kit?.logoUrl || null,
        logoAssetId: draft.lockedLogoAssetId || kit?.logoAssetId || null,
        themeAssetId: draft.lockedThemeAssetId || kit?.themeAssetId || null,
      });
      if (draft.sessionJobIds?.length) {
        api
          .get<JobsListResponse>("/jobs", {
            params: { ids: draft.sessionJobIds.slice(0, 40).join(","), limit: 40 },
          })
          .then((res) => setSessionJobs(res.data.items))
          .catch(() => undefined);
      }
    } else if (kit) {
      setLockedUrls((u) => ({
        ...u,
        reference: kit.themeUrl || null,
        logo: kit.logoUrl || null,
        logoAssetId: kit.logoAssetId || null,
        themeAssetId: kit.themeAssetId || null,
      }));
    }
  }, []);

  // Persist session draft (settings + job ids — not File blobs)
  useEffect(() => {
    if (!sessionHydrated.current) return;
    saveStudioSession({
      workflow,
      tryOnPreset,
      jewelryTypes,
      aspectRatio,
      personGeneration,
      numberOfImages,
      modelEndpointId,
      modelParams,
      workflowVariantKey,
      stylePresetId,
      promptText,
      lightingStyle,
      lastBatchId,
      sessionJobIds: sessionJobs.map((j) => j.id).slice(0, 40),
      activeJobId,
      lockedInputUrl: lockedUrls.input,
      lockedReferenceUrl: lockedUrls.reference,
      lockedModelUrl: lockedUrls.model,
      lockedThemeUrl: lockedUrls.reference,
      lockedLogoUrl: lockedUrls.logo,
      lockedLogoAssetId: lockedUrls.logoAssetId,
      lockedThemeAssetId: lockedUrls.themeAssetId,
    });
  }, [
    workflow,
    tryOnPreset,
    jewelryTypes,
    aspectRatio,
    personGeneration,
    numberOfImages,
    modelEndpointId,
    modelParams,
    workflowVariantKey,
    stylePresetId,
    promptText,
    lightingStyle,
    lastBatchId,
    sessionJobs,
    activeJobId,
    lockedUrls,
  ]);

  const streamingIds = useMemo(
    () =>
      sessionJobs
        .filter((j) => j.status === "PENDING" || j.status === "PROCESSING")
        .map((j) => j.id),
    [sessionJobs],
  );

  useJobStream(streamingIds, {
    onUpdate: (job) => {
      setSessionJobs((prev) =>
        prev.map((j) => (j.id === job.id ? { ...j, ...job } : j)),
      );
      if (job.status === "FAILED") {
        const msg = job.error_message?.includes("expected output")
          ? "Model rejected this prompt. Retry with the updated catalog prompt limits."
          : job.error_message?.includes("401")
            ? "fal.ai API key is invalid. Update it in Admin → Providers."
            : job.error_message || "Generation failed";
        toast.error(msg.slice(0, 180));
      }
    },
  });

  useEffect(() => {
    const jobId = searchParams.get("jobId");
    if (!jobId) return;
    api
      .get<Job>(`/jobs/${jobId}`)
      .then((res) => {
        const job = res.data;
        setActiveJobId(job.id);
        setSessionJobs((list) => mergeSessionJobs(list, [job]));
        // Restore editable draft from history job
        if (job.workflow === "CUSTOMER_TRY_ON") {
          setWorkflow("VIRTUAL_TRY_ON");
          setTryOnPreset("customer");
        } else if (job.workflow === "JEWELRY_ON_MODEL") {
          setWorkflow("VIRTUAL_TRY_ON");
          setTryOnPreset("studio");
        } else if (job.workflow) {
          setWorkflow(job.workflow);
        }
        if (job.jewelry_type) {
          setJewelryTypes(
            job.jewelry_type.split(",").map((s) => s.trim()).filter(Boolean),
          );
        }
        if (job.prompt_text) setPromptText(job.prompt_text);
        const meta = job.provider_metadata || {};
        if (typeof meta.modelEndpointId === "string") {
          setModelEndpointId(meta.modelEndpointId);
        }
        if (meta.modelParams && typeof meta.modelParams === "object") {
          setModelParams(meta.modelParams as Record<string, unknown>);
        }
        if (typeof meta.aspectRatio === "string") setAspectRatio(meta.aspectRatio);
        if (typeof meta.numberOfImages === "number") {
          setNumberOfImages(meta.numberOfImages);
        }
        setLockedUrls({
          input: job.input_url,
          reference: job.reference_url,
          model: job.model_url,
          logo: (job.provider_metadata as { logoUrl?: string } | null)?.logoUrl || null,
          logoAssetId:
            (job.provider_metadata as { logoAssetId?: string } | null)?.logoAssetId || null,
          assetId: job.asset_id || null,
        });
        toast.success("Loaded into Studio — settings restored. Regenerate anytime.");
      })
      .catch(() => toast.error("Could not load job from link"));
    searchParams.delete("jobId");
    setSearchParams(searchParams, { replace: true });
  }, [searchParams, setSearchParams]);

  useEffect(() => {
    const batchId = searchParams.get("batchId");
    if (!batchId) return;
    setLastBatchId(batchId);
    setBatchForceAllow(false);
    api
      .get<BatchOut>(`/jobs/batches/${batchId}`)
      .then((res) => {
        const jobs = res.data.jobs || [];
        if (jobs.length) {
          setSessionJobs((list) => mergeSessionJobs(list, jobs));
          const first =
            jobs.find((j) => j.status === "PROCESSING" || j.status === "PENDING") ||
            jobs[0];
          if (first) setActiveJobId(first.id);
        }
        toast.success("Batch loaded into Studio");
      })
      .catch(() => toast.error("Could not load batch"));
    searchParams.delete("batchId");
    setSearchParams(searchParams, { replace: true });
  }, [searchParams, setSearchParams]);

  useEffect(() => {
    setWorkflowVariantKey("");
    const first = workflowVariants[0];
    if (first) setWorkflowVariantKey(first.variant_key);
  }, [workflow, workflowVariants]);

  useEffect(() => {
    if (
      options?.jewelryTypes?.[0] &&
      jewelryTypes.length === 1 &&
      jewelryTypes[0] === "Ring"
    ) {
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

  const activeJob = activeJobId
    ? (allJobs.find((j) => j.id === activeJobId) ?? null)
    : null;
  const activeJobs = sessionJobs.filter(
    (j) => j.status === "PENDING" || j.status === "PROCESSING",
  );

  useEffect(() => {
    setOutputIndex(0);
  }, [activeJobId]);

  const [primaryPreviews, setPrimaryPreviews] = useState<
    { file: File; url: string }[]
  >([]);
  const [referencePreview, setReferencePreview] = useState("");
  const [logoPreview, setLogoPreview] = useState("");

  useEffect(() => {
    const urls = primaryFiles.map((file) => ({
      file,
      url: URL.createObjectURL(file),
    }));
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

  useEffect(() => {
    const url = logoFile ? URL.createObjectURL(logoFile) : "";
    setLogoPreview(url);
    return () => {
      if (url) URL.revokeObjectURL(url);
    };
  }, [logoFile]);

  const uploadOne = async (file: File, label = "image") => {
    const form = new FormData();
    form.append("file", file);
    setUploadProgress(`Uploading ${label}…`);
    return (
      await api.post<Asset>("/assets/upload", form, {
        onUploadProgress: (evt) => {
          if (!evt.total) return;
          const pct = Math.round((evt.loaded / evt.total) * 100);
          setUploadProgress(`Uploading ${label}… ${pct}%`);
        },
      })
    ).data;
  };

  const uploadMany = async (files: File[]) => {
    const form = new FormData();
    files.forEach((f) => form.append("files", f));
    setUploadProgress(`Uploading ${files.length} products…`);
    return (
      await api.post<Asset[]>("/assets/bulk-upload", form, {
        onUploadProgress: (evt) => {
          if (!evt.total) return;
          const pct = Math.round((evt.loaded / evt.total) * 100);
          setUploadProgress(`Uploading products… ${pct}%`);
        },
      })
    ).data;
  };

  const generateMutation = useMutation({
    mutationFn: async () => {
      const errors: Record<string, string> = {};
      if (primaryFiles.length === 0 && !lockedUrls.input && !lockedUrls.assetId)
        errors.productImage = "Upload at least one product image";
      if (needsReference && !referenceFile && !lockedUrls.reference && !lockedUrls.model) {
        errors.referenceImage = needsModelReference
          ? "Upload a model or customer portrait"
          : "Upload a style reference image";
      }
      if (isBulk && isCatalog && !referenceFile && !lockedUrls.reference) {
        errors.referenceImage =
          "Upload a theme/style reference for consistent bulk catalog output";
      }
      if (Object.keys(errors).length > 0) {
        setValidationErrors(errors);
        throw new Error(Object.values(errors)[0]);
      }
      setValidationErrors({});

      try {
        const referenceAsset = referenceFile
          ? await uploadOne(referenceFile, needsModelReference ? "portrait" : "theme")
          : null;
        const logoAsset = logoFile ? await uploadOne(logoFile, "logo") : null;
        const logoStorageUrl = logoAsset
          ? String(logoAsset.original_url || "").split("?")[0] || logoAsset.original_url
          : lockedUrls.logo || null;
        const selectedVariant = workflowVariants.find(
          (v) => v.variant_key === workflowVariantKey,
        );

        if (referenceAsset) {
          const themeUrl =
            String(referenceAsset.original_url || "").split("?")[0] ||
            referenceAsset.original_url;
          patchBrandKit({
            themeAssetId: referenceAsset.id,
            themeUrl,
            themeName: referenceFile?.name || null,
          });
          setLockedUrls((u) => ({
            ...u,
            reference: themeUrl,
            themeAssetId: referenceAsset.id,
          }));
        }
        if (logoAsset) {
          const url =
            String(logoAsset.original_url || "").split("?")[0] || logoAsset.original_url;
          patchBrandKit({
            logoAssetId: logoAsset.id,
            logoUrl: url,
            logoName: logoFile?.name || null,
          });
          setLockedUrls((u) => ({
            ...u,
            logo: url,
            logoAssetId: logoAsset.id,
          }));
        }

        const referenceUrl =
          referenceAsset?.original_url ||
          lockedUrls.reference ||
          (needsModelReference ? undefined : lockedUrls.model) ||
          undefined;
        const modelUrl = needsModelReference
          ? referenceAsset?.original_url || lockedUrls.model || lockedUrls.reference || undefined
          : undefined;

        const payload: Record<string, unknown> = {
          workflow: apiWorkflow,
          jewelry_type: jewelryTypes.join(", "),
          prompt_text: promptText || null,
          aspect_ratio: aspectRatio,
          person_generation: personGeneration,
          number_of_images: numberOfImages,
          model_endpoint_id: modelEndpointId || selectedModel?.endpoint_id,
          model_params: modelParams,
          reference_url: needsModelReference ? undefined : referenceUrl,
          model_url: modelUrl,
          ...(lightingStyle ? { lighting_style: lightingStyle } : {}),
          ...((logoAsset || lockedUrls.logoAssetId || lockedUrls.logo)
            ? {
                logo_asset_id: logoAsset?.id || lockedUrls.logoAssetId || undefined,
                logo_url: logoStorageUrl || undefined,
              }
            : {}),
          ...(stylePresetId ? { style_preset_id: stylePresetId } : {}),
          ...(apiWorkflow === "GEMSTONE_COLOR_CHANGE" && selectedVariant
            ? { gemstone_target_color: selectedVariant.label }
            : {}),
          ...(apiWorkflow === "BACKGROUND_REPLACEMENT" && selectedVariant
            ? { background_style: selectedVariant.label }
            : {}),
          ...(apiWorkflow === "LUXURY_ENHANCEMENT" && selectedVariant
            ? { metal_type: selectedVariant.label }
            : {}),
          ...(apiWorkflow === "REFERENCE_STYLE_MATCH" && selectedVariant
            ? { background_style: selectedVariant.label }
            : {}),
        };

        if (isBulk) {
          setUploadProgress("Creating bulk batch…");
          const assets = await uploadMany(primaryFiles);
          const res = await api.post<{
            jobIds: string[];
            jobs: Job[];
            batchId: string;
            queueMode?: string;
          }>("/jobs/bulk", {
            ...payload,
            workflow: apiWorkflow,
            asset_ids: assets.map((a) => a.id),
            ...(needsModelReference
              ? { model_url: modelUrl, reference_url: undefined }
              : { reference_url: referenceUrl }),
          });
          if (res.data.batchId) setLastBatchId(res.data.batchId);
          setQueueModeInline(res.data.queueMode === "inline");
          setBatchForceAllow(false);
          queryClient.invalidateQueries({ queryKey: ["batch", res.data.batchId] });
          queryClient.invalidateQueries({ queryKey: ["batches"] });
          return res.data.jobs?.length
            ? res.data.jobs
            : await Promise.all(
                res.data.jobIds.map((id) =>
                  api.get<Job>(`/jobs/${id}`).then((r) => r.data),
                ),
              );
        }

        setUploadProgress("Creating job…");
        let assetId: string;
        if (primaryFiles[0]) {
          const asset = await uploadOne(primaryFiles[0], "product");
          assetId = asset.id;
          setLockedUrls((u) => ({
            ...u,
            assetId: asset.id,
            input: asset.original_url || u.input,
          }));
        } else if (lockedUrls.assetId) {
          assetId = lockedUrls.assetId;
        } else {
          throw new Error("Upload a product image, or open a history job that has an asset");
        }
        const job = (
          await api.post<Job>("/jobs", { ...payload, asset_id: assetId })
        ).data;
        return [job];
      } finally {
        setUploadProgress(null);
      }
    },
    onSuccess: (jobs) => {
      setSessionJobs((prev) => mergeSessionJobs(prev, jobs));
      if (jobs[0]) setActiveJobId(jobs[0].id);
      setOutputIndex(0);
      queryClient.setQueryData<Job[]>(["recent-jobs"], (old) =>
        mergeSessionJobs(old || [], jobs).slice(0, 8),
      );
      toast.success(
        jobs.length > 1
          ? `${jobs.length} generations queued`
          : "Generation started",
      );
    },
    onError: (err: Error) => toast.error(err.message || "Generation failed"),
  });

  const regenerateMutation = useMutation({
    mutationFn: (jobId: string) =>
      api.post<Job>(`/jobs/${jobId}/regenerate`).then((r) => r.data),
    onSuccess: (job) => {
      setSessionJobs((prev) => mergeSessionJobs(prev, [job]));
      setActiveJobId(job.id);
      toast.success("Regeneration started — same settings, new job");
    },
    onError: () => toast.error("Regeneration failed"),
  });

  const retryMutation = useMutation({
    mutationFn: (jobId: string) =>
      api.post<Job>(`/jobs/${jobId}/retry`).then((r) => r.data),
    onSuccess: (job) => {
      setSessionJobs((prev) =>
        prev.map((j) => (j.id === job.id ? { ...j, ...job } : j)),
      );
      setActiveJobId(job.id);
      toast.success("Retry queued");
    },
    onError: () => toast.error("Retry failed"),
  });

  const cancelMutation = useMutation({
    mutationFn: (jobId: string) =>
      api.post<Job>(`/jobs/${jobId}/cancel`).then((r) => r.data),
    onSuccess: (job) => {
      setSessionJobs((prev) =>
        prev.map((j) => (j.id === job.id ? { ...j, ...job } : j)),
      );
      toast.message("Generation cancelled");
    },
    onError: () => toast.error("Could not cancel"),
  });

  const toggleFavorite = useCallback(
    async (job: Job) => {
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
    },
    [favoriteIds, queryClient],
  );

  const schemaProps = selectedModel?.input_schema?.properties ?? {};
  const showAspectRatio =
    "aspect_ratio" in schemaProps || "image_size" in schemaProps;
  const showPersonGeneration = Boolean(
    selectedModel?.capabilities?.person_generation,
  );
  const showNumberOfImages =
    "num_images" in schemaProps || "num_samples" in schemaProps;

  const modelMaxImages =
    selectedModel?.limits?.max_images ??
    selectedModel?.ui?.max_images ??
    (selectedModel?.capabilities?.multi_image === false ? 1 : 14);
  // Optimistic true until a model is selected (catalog default is multi-image).
  const modelSupportsMultiImage =
    selectedModel == null
      ? true
      : Boolean(selectedModel.capabilities?.multi_image) && modelMaxImages > 1;
  const hasThemeAttached = Boolean(referenceFile || lockedUrls.reference);
  const hasLogoAttached = Boolean(logoFile || lockedUrls.logo);
  const plannedSlots: { role: string; label: string }[] = [
    { role: "product", label: "Product → Image 1" },
  ];
  if (needsModelReference && (referenceFile || lockedUrls.model || lockedUrls.reference)) {
    plannedSlots.push({ role: "portrait", label: "Portrait → Image 2" });
  } else if (hasThemeAttached) {
    plannedSlots.push({
      role: "theme",
      label: `Theme → Image ${plannedSlots.length + 1}`,
    });
  }
  const logoAsModelRef =
    hasLogoAttached &&
    modelSupportsMultiImage &&
    plannedSlots.length < modelMaxImages;
  if (hasLogoAttached && logoAsModelRef) {
    plannedSlots.push({
      role: "logo",
      label: `Logo → Image ${plannedSlots.length + 1}`,
    });
  }
  const logoUsesComposeFallback = hasLogoAttached && !logoAsModelRef;

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

  const onPrimaryAppend = (incoming: File[]) => {
    if (!incoming.length) return;
    setPrimaryFiles((prev) => [...prev, ...incoming].slice(0, 30));
    setLockedUrls((u) => ({ ...u, input: null, assetId: null }));
    setValidationErrors((e) => ({ ...e, productImage: "" }));
  };

  const onPrimaryReplace = (incoming: File[]) => {
    setPrimaryFiles(incoming.slice(0, 30));
    setLockedUrls((u) => ({ ...u, input: null, assetId: null }));
    setValidationErrors((e) => ({ ...e, productImage: "" }));
  };

  const removePrimaryAt = (index: number) => {
    setPrimaryFiles((prev) => prev.filter((_, i) => i !== index));
    setLockedUrls((u) => ({ ...u, input: null, assetId: null }));
  };

  const clearPrimaryFiles = () => {
    setPrimaryFiles([]);
    setLockedUrls((u) => ({ ...u, input: null, assetId: null }));
  };

  const openCropForPrimary = (index = 0) => {
    const file = primaryFiles[index];
    if (!file) return;
    const src = URL.createObjectURL(file);
    setCropTarget({ kind: "primary", src, name: file.name, index });
  };

  const onReferencePick = (files: FileList | null) => {
    const file = files?.[0] || null;
    if (!file) return;
    setValidationErrors((e) => ({ ...e, referenceImage: "" }));
    setReferenceFile(file);
    setLockedUrls((u) => ({ ...u, reference: null, themeAssetId: null }));
  };

  const onLogoPick = (files: FileList | null) => {
    const file = files?.[0] || null;
    if (!file) return;
    setLogoFile(file);
    setLockedUrls((u) => ({ ...u, logo: null, logoAssetId: null }));
  };

  const onCropConfirm = (file: File) => {
    if (!cropTarget) return;
    if (cropTarget.kind === "primary") {
      const idx = cropTarget.index ?? 0;
      setPrimaryFiles((prev) => {
        const next = [...prev];
        next[idx] = file;
        return next;
      });
      setLockedUrls((u) => ({ ...u, input: null, assetId: null }));
    } else if (cropTarget.kind === "reference") {
      setReferenceFile(file);
      setLockedUrls((u) => ({ ...u, reference: null, themeAssetId: null }));
    } else {
      setLogoFile(file);
      setLockedUrls((u) => ({ ...u, logo: null, logoAssetId: null }));
    }
    URL.revokeObjectURL(cropTarget.src);
    setCropTarget(null);
  };

  const themePreviewSrc =
    referencePreview || (lockedUrls.reference ? mediaUrl(lockedUrls.reference) : "");
  const logoPreviewSrc =
    logoPreview || (lockedUrls.logo ? mediaUrl(lockedUrls.logo) : "");
  const productPreviewSrcs = primaryPreviews.length
    ? primaryPreviews.map((p) => p.url)
    : lockedUrls.input
      ? [mediaUrl(lockedUrls.input)]
      : [];

  const outputUrls = useMemo(() => {
    if (!activeJob) return [] as string[];
    const urls = (activeJob.output_urls || []).filter(Boolean) as string[];
    if (urls.length) return urls;
    return activeJob.output_url ? [activeJob.output_url] : [];
  }, [activeJob]);

  const activeOutputUrl = outputUrls[outputIndex] || outputUrls[0] || null;

  const { data: batchStatus } = useQuery({
    queryKey: ["batch", lastBatchId],
    queryFn: async () =>
      (await api.get<BatchOut>(`/jobs/batches/${lastBatchId}`)).data,
    enabled: Boolean(lastBatchId),
    refetchInterval: (q) => {
      const s = q.state.data?.status;
      return s === "PENDING" || s === "PROCESSING" ? 2500 : false;
    },
  });

  useEffect(() => {
    if (!batchStatus?.jobs?.length) return;
    setSessionJobs((prev) => mergeSessionJobs(prev, batchStatus.jobs || []));
  }, [batchStatus?.jobs, batchStatus?.updated_at, batchStatus?.completed_jobs]);

  const batchJobIds = useMemo(
    () => (batchStatus?.jobs || []).map((j) => j.id),
    [batchStatus?.jobs],
  );
  const batchJobIndex = activeJobId ? batchJobIds.indexOf(activeJobId) : -1;
  const batchActive =
    batchStatus?.status === "PENDING" || batchStatus?.status === "PROCESSING";
  const generateBlockedByBatch = Boolean(batchActive && !batchForceAllow);

  const selectWorkflow = (id: string) => {
    setWorkflow(id);
    setPrimaryFiles([]);
    setReferenceFile(null);
    setLogoFile(null);
    const kit = loadBrandKit();
    setLockedUrls({
      reference: kit?.themeUrl || null,
      logo: kit?.logoUrl || null,
      logoAssetId: kit?.logoAssetId || null,
      themeAssetId: kit?.themeAssetId || null,
    });
    setActiveJobId(null);
    setValidationErrors({});
  };

  const clearWorkspace = () => {
    setActiveJobId(null);
    setPrimaryFiles([]);
    setReferenceFile(null);
    setLogoFile(null);
    setLockedUrls({});
    setSessionJobs([]);
    setLastBatchId(null);
    clearStudioSession();
    toast.message("Workspace cleared");
  };

  const clearBrandAssets = () => {
    clearBrandKit();
    setReferenceFile(null);
    setLogoFile(null);
    setLockedUrls((u) => ({
      ...u,
      reference: null,
      logo: null,
      logoAssetId: null,
      themeAssetId: null,
    }));
    toast.message("Brand kit cleared");
  };

  const is4kSelected = useMemo(() => {
    const res = String(
      modelParams.resolution || modelParams.image_size || "",
    ).toUpperCase();
    return res.includes("4K") || res === "AUTO_4K";
  }, [modelParams]);

  const sidebarWorkflows = useMemo(() => {
    const fromApi = (options?.workflows || [])
      .filter(
        (w) =>
          ![
            "RATE_TOOLS",
            "BULK_GENERATION",
            "JEWELRY_ON_MODEL",
            "CUSTOMER_TRY_ON",
          ].includes(w.id),
      )
      .map((w) => ({ id: w.id, label: w.label }));
    if (fromApi.length) {
      // Ensure Virtual Try-On appears once near top
      const withoutDup = fromApi.filter((w) => w.id !== "VIRTUAL_TRY_ON");
      return [
        ...STUDIO_SIDEBAR_WORKFLOWS.filter(
          (w) => w.id === "CATALOG_IMAGE" || w.id === "VIRTUAL_TRY_ON",
        ),
        ...withoutDup.filter((w) => w.id !== "CATALOG_IMAGE"),
      ];
    }
    return [...STUDIO_SIDEBAR_WORKFLOWS];
  }, [options?.workflows]);

  return (
    <AppLayout>
      <main className="mx-auto max-w-[1600px] w-full px-4 sm:px-6 lg:px-8 py-6 flex-1">
        <div className="grid grid-cols-1 gap-5 items-start lg:grid-cols-[240px_minmax(0,1fr)_300px]">
          {/* Sidebar */}
          <aside className="space-y-3 lg:sticky lg:top-[4.5rem]">
            <p className="ui-label px-1 mb-0">Workflows</p>
            <div className="ui-card p-1.5 space-y-0.5">
              {sidebarWorkflows.map((item) => {
                const Icon = WORKFLOW_ICONS[item.id] || Sparkles;
                const active = workflow === item.id;
                return (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => selectWorkflow(item.id)}
                    className={`flex w-full items-center gap-2.5 rounded-xl px-3 py-2.5 text-left text-[13px] transition-colors ${
                      active
                        ? "bg-blue-600 text-white font-semibold shadow-sm shadow-blue-600/20"
                        : "text-slate-600 hover:bg-slate-100 font-medium"
                    }`}
                  >
                    <Icon className="size-3.5 shrink-0 opacity-90" />
                    <span className="leading-snug">{item.label}</span>
                  </button>
                );
              })}
            </div>
            <div className="ui-card p-3">
              <p className="ui-label mb-2">Workspace</p>
              <div className="grid grid-cols-2 gap-2 text-center">
                <div className="rounded-xl bg-slate-50 p-2.5">
                  <p className="text-[10px] font-medium text-slate-500">Jobs</p>
                  <p className="text-sm font-semibold tabular-nums text-slate-900">
                    {sessionJobs.length}
                  </p>
                </div>
                <div className="rounded-xl bg-slate-50 p-2.5">
                  <p className="text-[10px] font-medium text-slate-500">Active</p>
                  <p
                    className={`text-sm font-semibold tabular-nums ${
                      activeJobs.length ? "text-blue-600" : "text-slate-900"
                    }`}
                  >
                    {activeJobs.length}
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={clearWorkspace}
                className="mt-2 w-full text-[11px] font-semibold text-slate-500 hover:text-slate-800"
              >
                Clear workspace
              </button>
            </div>
          </aside>

          {/* Canvas */}
          <section className="space-y-5 min-w-0">
            <div>
              <h2 className="text-xl font-semibold text-slate-900 flex items-center gap-2">
                <Sparkles className="size-4 text-blue-600" />
                {workflowLabel(workflow, options)}
              </h2>
              {isCatalog && (
                <p className="text-sm text-slate-500 mt-1.5 max-w-2xl leading-relaxed">
                  Multi-upload for bulk catalog. Theme is required for bulk; optional for
                  single. Upload full-size images as-is — theme and logo stay in your brand
                  kit across visits.
                </p>
              )}
              {!isCatalog && (
                <p className="text-sm text-slate-500 mt-1.5 max-w-2xl leading-relaxed">
                  Multi-select products for bulk. Shared reference/portrait applies to every item.
                  Regenerate keeps this workspace — you do not need a new session.
                </p>
              )}
              {workflow === "VIRTUAL_TRY_ON" && (
                <p className="text-sm text-slate-500 mt-1.5 max-w-2xl leading-relaxed">
                  Upload jewelry product(s) and one portrait. Choose studio model look or customer photo in
                  Parameters.
                </p>
              )}
            </div>

            <>
              <div className="rounded-2xl border border-slate-200 bg-white shadow-sm overflow-hidden">
                <div className="grid grid-cols-1 lg:grid-cols-2 divide-y lg:divide-y-0 lg:divide-x divide-slate-100">
                  {/* Input */}
                  <div className="p-5 min-h-[360px] flex flex-col min-w-0">
                    <div className="flex items-center justify-between border-b border-slate-100 pb-2 mb-3 shrink-0">
                      <span className="ui-label mb-0">Input</span>
                      {activeJob && (
                        <button
                          type="button"
                          onClick={() => {
                            setActiveJobId(null);
                            setPrimaryFiles([]);
                            setReferenceFile(null);
                            setLockedUrls({});
                          }}
                          className="text-xs font-semibold text-blue-600 hover:underline"
                        >
                          Clear selection
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
                          <span className="text-xs text-slate-500">
                            No input
                          </span>
                        )}
                      </div>
                    ) : needsReference ? (
                      <div className="grid grid-cols-2 gap-3 flex-1 min-h-0">
                        <ProductUploadGallery
                          id="studio-product-upload"
                          label="Product (multi for bulk)"
                          files={primaryFiles}
                          previews={productPreviewSrcs}
                          error={validationErrors.productImage}
                          onAppend={onPrimaryAppend}
                          onReplace={onPrimaryReplace}
                          onRemoveAt={removePrimaryAt}
                          onClearAll={clearPrimaryFiles}
                          onCrop={
                            primaryFiles.length === 1
                              ? () => openCropForPrimary(0)
                              : undefined
                          }
                        />
                        <UploadZone
                          id="studio-reference-upload"
                          label={needsStyleReference ? "Reference" : "Portrait"}
                          error={validationErrors.referenceImage}
                          previews={themePreviewSrc ? [themePreviewSrc] : []}
                          onFiles={onReferencePick}
                          single
                          compact
                          fileName={referenceFile?.name || "Saved"}
                          onClear={() => {
                            setReferenceFile(null);
                            setLockedUrls((u) => ({
                              ...u,
                              reference: null,
                              model: null,
                              themeAssetId: null,
                            }));
                          }}
                        />
                      </div>
                    ) : (
                      <ProductUploadGallery
                        id="studio-product-upload"
                        label="Product (multi for bulk)"
                        files={primaryFiles}
                        previews={productPreviewSrcs}
                        error={validationErrors.productImage}
                        onAppend={onPrimaryAppend}
                        onReplace={onPrimaryReplace}
                        onRemoveAt={removePrimaryAt}
                        onClearAll={clearPrimaryFiles}
                        onCrop={
                          primaryFiles.length === 1
                            ? () => openCropForPrimary(0)
                            : undefined
                        }
                      />
                    )}
                  </div>

                  {/* Output */}
                  <div className="p-5 min-h-[360px] flex flex-col bg-slate-50/30">
                    <div className="flex items-center justify-between border-b border-slate-100 pb-2 mb-3">
                      <div className="flex items-center gap-2 min-w-0">
                        <span className="ui-label mb-0">Output</span>
                        {batchJobIds.length > 1 && batchJobIndex >= 0 && (
                          <span className="text-[10px] font-semibold tabular-nums text-slate-500">
                            Job {batchJobIndex + 1}/{batchJobIds.length}
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-1">
                        {batchJobIds.length > 1 && batchJobIndex >= 0 && (
                          <>
                            <button
                              type="button"
                              disabled={batchJobIndex <= 0}
                              onClick={() =>
                                setActiveJobId(batchJobIds[batchJobIndex - 1])
                              }
                              className="rounded p-1 text-slate-500 hover:bg-slate-100 disabled:opacity-30"
                              aria-label="Previous batch job"
                            >
                              <ChevronLeft className="size-3.5" />
                            </button>
                            <button
                              type="button"
                              disabled={batchJobIndex >= batchJobIds.length - 1}
                              onClick={() =>
                                setActiveJobId(batchJobIds[batchJobIndex + 1])
                              }
                              className="rounded p-1 text-slate-500 hover:bg-slate-100 disabled:opacity-30"
                              aria-label="Next batch job"
                            >
                              <ChevronRight className="size-3.5" />
                            </button>
                          </>
                        )}
                      {activeJob?.status === "COMPLETED" && (
                        <div className="flex gap-1">
                          <button
                            type="button"
                            onClick={() =>
                              regenerateMutation.mutate(activeJob.id)
                            }
                            disabled={regenerateMutation.isPending}
                            aria-label="Regenerate image"
                            className="text-xs font-semibold text-slate-600 px-2 py-1 rounded hover:bg-slate-100"
                          >
                            <RefreshCcw
                              className={`inline size-3 mr-1 ${regenerateMutation.isPending ? "animate-spin" : ""}`}
                            />
                            Regenerate
                          </button>
                          <button
                            type="button"
                            onClick={() => toggleFavorite(activeJob)}
                            aria-label={
                              favoriteIds.has(activeJob.id)
                                ? "Remove from favorites"
                                : "Add to favorites"
                            }
                            className="text-xs font-semibold text-slate-600 px-2 py-1 rounded hover:bg-slate-100"
                          >
                            <Heart
                              className={`inline size-3 mr-1 ${favoriteIds.has(activeJob.id) ? "fill-red-500 text-red-500" : ""}`}
                            />
                            Save
                          </button>
                          {activeOutputUrl && (
                            <a
                              href={mediaUrl(activeOutputUrl)}
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
                          <button
                            type="button"
                            onClick={async () => {
                              try {
                                const res = await api.post<{
                                  token: string;
                                  url?: string;
                                }>("/share-links", { job_id: activeJob.id });
                                const token = res.data.token;
                                const shareUrl = `${window.location.origin}/share/${token}`;
                                await navigator.clipboard.writeText(shareUrl);
                                toast.success("Share link copied");
                              } catch {
                                toast.error("Could not create share link");
                              }
                            }}
                            className="text-xs font-semibold text-slate-600 px-2 py-1 rounded hover:bg-slate-100"
                          >
                            Share
                          </button>
                        </div>
                      )}
                      {(activeJob?.status === "PENDING" ||
                        activeJob?.status === "PROCESSING") && (
                        <button
                          type="button"
                          onClick={() => cancelMutation.mutate(activeJob.id)}
                          disabled={cancelMutation.isPending}
                          className="text-xs font-semibold text-rose-600 px-2 py-1 rounded hover:bg-rose-50"
                        >
                          Cancel
                        </button>
                      )}
                      </div>
                    </div>
                    {!activeJob ? (
                      <div className="flex-1 flex flex-col items-center justify-center text-center p-6 rounded-xl border border-dashed border-slate-200 bg-white">
                        <Wand2 className="size-8 text-slate-300 mb-2" />
                        <p className="text-sm font-semibold text-slate-700">
                          Studio Standby
                        </p>
                        <p className="text-xs text-slate-500 mt-1">
                          Upload and click Generate
                        </p>
                      </div>
                    ) : activeJob.status === "FAILED" ||
                      activeJob.status === "CANCELLED" ? (
                      <div
                        className="flex-1 flex flex-col items-center justify-center text-center p-6 rounded-xl border border-rose-200 bg-rose-50 min-h-[240px]"
                        aria-live="polite"
                      >
                        <p className="text-sm font-semibold text-rose-800">
                          {activeJob.status === "CANCELLED"
                            ? "Cancelled"
                            : "Generation failed"}
                        </p>
                        <p className="text-xs text-rose-700 mt-2 max-w-md leading-relaxed">
                          {activeJob.error_message ||
                            "The model could not complete this request. Try again or switch model."}
                        </p>
                        <div className="flex gap-2 mt-4">
                          <button
                            type="button"
                            onClick={() => retryMutation.mutate(activeJob.id)}
                            disabled={retryMutation.isPending}
                            className="ui-btn-secondary border-rose-200 text-rose-800 hover:bg-rose-100"
                          >
                            <RefreshCcw
                              className={`size-3.5 ${retryMutation.isPending ? "animate-spin" : ""}`}
                            />
                            Retry same job
                          </button>
                          <button
                            type="button"
                            onClick={() =>
                              regenerateMutation.mutate(activeJob.id)
                            }
                            disabled={regenerateMutation.isPending}
                            className="ui-btn-secondary border-rose-200 text-rose-800 hover:bg-rose-100"
                          >
                            Duplicate &amp; run
                          </button>
                        </div>
                      </div>
                    ) : activeJob.status === "COMPLETED" ? (
                      <div className="flex-1 flex flex-col gap-2 min-h-[240px]">
                        <div className="flex-1 flex items-center justify-center rounded-xl bg-slate-950 p-3">
                          {activeOutputUrl ? (
                            <img
                              src={mediaUrl(activeOutputUrl)}
                              alt="Output"
                              className="max-h-full max-w-full object-contain rounded"
                            />
                          ) : (
                            <span className="text-xs text-slate-500">No output</span>
                          )}
                        </div>
                        {outputUrls.length > 1 && (
                          <div className="flex gap-1.5 overflow-x-auto pb-0.5">
                            {outputUrls.map((url, i) => (
                              <button
                                key={`${url}-${i}`}
                                type="button"
                                onClick={() => setOutputIndex(i)}
                                className={`size-12 shrink-0 overflow-hidden rounded-lg border ${
                                  outputIndex === i
                                    ? "border-blue-600 ring-2 ring-blue-500/20"
                                    : "border-slate-200"
                                }`}
                              >
                                <img
                                  src={mediaUrl(url)}
                                  alt=""
                                  className="size-full object-cover"
                                />
                              </button>
                            ))}
                          </div>
                        )}
                      </div>
                    ) : (
                      <div
                        className="flex-1 flex flex-col items-center justify-center text-center p-6 rounded-xl border border-blue-100 bg-blue-50/50 min-h-[240px]"
                        aria-live="polite"
                      >
                        <RefreshCcw className="size-6 text-blue-500 animate-spin mb-3" />
                        <p className="text-sm font-semibold text-slate-800">
                          {jobStatusLabel(activeJob)}
                        </p>
                        <p className="text-xs text-slate-500 mt-2 max-w-sm">
                          {activeJob.provider_metadata?.webhook_pending ||
                          activeJob.provider_metadata?.progressStage ===
                            "waiting_on_fal"
                            ? "Fal.ai is generating your image. This usually takes 20–60 seconds."
                            : "Preparing request in Jewel AI…"}
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* Sticky generate under canvas */}
              <div className="sticky bottom-3 z-20 hidden lg:flex items-center gap-3 rounded-2xl border border-slate-200 bg-white/95 px-4 py-3 shadow-lg backdrop-blur">
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-semibold text-slate-900 truncate">
                    {generateBlockedByBatch
                      ? "Batch running — wait or queue another"
                      : isBulk
                        ? `Ready to generate ${primaryFiles.length} images`
                        : lockedUrls.assetId && !primaryFiles.length
                          ? "Ready — using loaded product asset"
                          : "Ready when product is set"}
                  </p>
                  {uploadProgress && (
                    <p className="text-[11px] text-slate-500 truncate">{uploadProgress}</p>
                  )}
                  {generateBlockedByBatch && (
                    <button
                      type="button"
                      onClick={() => setBatchForceAllow(true)}
                      className="mt-0.5 text-[11px] font-semibold text-blue-600 hover:underline"
                    >
                      Queue another batch anyway
                    </button>
                  )}
                </div>
                <button
                  type="button"
                  onClick={() => generateMutation.mutate()}
                  disabled={
                    generateMutation.isPending ||
                    Boolean(uploadProgress) ||
                    generateBlockedByBatch
                  }
                  className="ui-btn-primary shrink-0"
                >
                  {generateMutation.isPending || uploadProgress ? (
                    <RefreshCcw className="size-4 animate-spin" />
                  ) : (
                    <Wand2 className="size-4" />
                  )}
                  {isBulk
                    ? `Generate Bulk (${primaryFiles.length})`
                    : "Generate"}
                </button>
              </div>

              {lastBatchId && (
                <BatchProgressPanel
                  batchId={lastBatchId}
                  activeJobId={activeJobId}
                  onSelectJob={(id) => {
                    setActiveJobId(id);
                    setOutputIndex(0);
                  }}
                  onDismiss={() => setLastBatchId(null)}
                  queueModeWarning={queueModeInline}
                />
              )}

              <input
                type="text"
                value={promptText}
                onChange={(e) => setPromptText(e.target.value)}
                placeholder="Optional instructions: lighting, mood, sparkles..."
                className="ui-input"
              />

              {/* Gallery strip */}
              <div className="ui-card p-4">
                <p className="ui-label mb-3 flex items-center gap-1.5">
                  <History className="size-3.5" /> Recent
                </p>
                <div className="flex gap-2 overflow-x-auto pb-1">
                  {[
                    ...sessionJobs,
                    ...recentJobs.filter(
                      (r) => !sessionJobs.some((s) => s.id === r.id),
                    ),
                  ]
                    .slice(0, 16)
                    .map((job) => (
                      <button
                        key={job.id}
                        type="button"
                        onClick={() => setActiveJobId(job.id)}
                        className={`relative size-14 shrink-0 rounded-lg overflow-hidden border ${
                          activeJobId === job.id
                            ? "border-blue-600 ring-2 ring-blue-500/20"
                            : "border-slate-200"
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
          </section>

          {/* Parameters */}
            <aside className="space-y-4 lg:sticky lg:top-[4.5rem]">
            <div className="ui-card p-4 space-y-4">
                <p className="ui-label flex items-center gap-1.5 mb-0">
                  <Settings className="size-3.5" /> Parameters
                </p>
              {workflow === "VIRTUAL_TRY_ON" && (
                <div>
                  <label className="ui-label">Try-On Mode</label>
                  <select
                    value={tryOnPreset}
                    onChange={(e) =>
                      setTryOnPreset(e.target.value as "studio" | "customer")
                    }
                    className="ui-input"
                  >
                    <option value="studio">Studio model look</option>
                    <option value="customer">Customer photo</option>
                  </select>
                </div>
              )}
              <MultiSelectDropdown
                label="Jewelry Type"
                options={options?.jewelryTypes ?? ["Ring"]}
                selectedValues={jewelryTypes}
                onChange={setJewelryTypes}
              />
              {jewelryTypes.length > 1 && (
                <p className="text-[11px] text-slate-500 -mt-1 leading-relaxed">
                  Prompt engine applies the workflow master plus each selected
                  type ({jewelryTypes.join(", ")}).
                </p>
              )}
              {isCatalog && (
                <div className="space-y-2">
                  <div className="flex items-center justify-between gap-2">
                    <p className="ui-label mb-0">Brand kit</p>
                    {(lockedUrls.reference ||
                      lockedUrls.logo ||
                      referenceFile ||
                      logoFile) && (
                      <button
                        type="button"
                        onClick={clearBrandAssets}
                        className="text-[10px] font-semibold text-slate-500 hover:text-slate-800"
                      >
                        Clear saved
                      </button>
                    )}
                  </div>
                  {(lockedUrls.reference || lockedUrls.logo) &&
                    !referenceFile &&
                    !logoFile && (
                      <p className="text-[11px] text-emerald-700 bg-emerald-50 border border-emerald-100 rounded-lg px-2 py-1.5">
                        Using saved theme/logo — Change anytime below.
                      </p>
                    )}
                  <UploadZone
                    id="studio-theme-ref"
                    label={
                      isBulk
                        ? "Theme / style (required for bulk)"
                        : "Theme / style (optional)"
                    }
                    error={validationErrors.referenceImage}
                    previews={themePreviewSrc ? [themePreviewSrc] : []}
                    onFiles={onReferencePick}
                    single
                    compact
                    fileName={referenceFile?.name || "Saved theme"}
                    hint={isBulk ? "Required for bulk" : "Optional · full size OK"}
                    onClear={() => {
                      setReferenceFile(null);
                      patchBrandKit({
                        themeAssetId: null,
                        themeUrl: null,
                        themeName: null,
                      });
                      setLockedUrls((u) => ({
                        ...u,
                        reference: null,
                        themeAssetId: null,
                      }));
                    }}
                  />
                  <UploadZone
                    id="studio-logo-upload"
                    label="Shop logo (reference — model places it)"
                    previews={logoPreviewSrc ? [logoPreviewSrc] : []}
                    onFiles={onLogoPick}
                    single
                    compact
                    fileName={logoFile?.name || "Saved logo"}
                    hint="Sent as a reference image when the model supports multi-image"
                    onClear={() => {
                      setLogoFile(null);
                      patchBrandKit({
                        logoAssetId: null,
                        logoUrl: null,
                        logoName: null,
                      });
                      setLockedUrls((u) => ({
                        ...u,
                        logo: null,
                        logoAssetId: null,
                      }));
                    }}
                  />
                  {(hasThemeAttached || hasLogoAttached) && (
                    <p className="text-[11px] text-slate-500 leading-relaxed">
                      Sent to the model:{" "}
                      {plannedSlots.map((s) => s.label).join(" · ")}
                      {logoUsesComposeFallback
                        ? " · Logo fallback: under output"
                        : ""}
                    </p>
                  )}
                  {logoUsesComposeFallback && (
                    <p className="text-[11px] text-amber-800 bg-amber-50 border border-amber-200 rounded-lg px-2 py-1.5 leading-relaxed">
                      This model only accepts a single image. Logo will be added
                      under the output (fallback). Choose a multi-image edit
                      model for in-frame logo placement.
                    </p>
                  )}
                </div>
              )}
              {!isCatalog && (
                <UploadZone
                  id="studio-logo-upload-single"
                  label="Shop logo (reference — model places it)"
                  previews={logoPreviewSrc ? [logoPreviewSrc] : []}
                  onFiles={onLogoPick}
                  single
                  compact
                  fileName={logoFile?.name || "Saved logo"}
                  hint="Optional · model places it when multi-image is supported"
                  onClear={() => {
                    setLogoFile(null);
                    patchBrandKit({
                      logoAssetId: null,
                      logoUrl: null,
                      logoName: null,
                    });
                    setLockedUrls((u) => ({
                      ...u,
                      logo: null,
                      logoAssetId: null,
                    }));
                  }}
                />
              )}
              {!isCatalog && logoUsesComposeFallback && (
                <p className="text-[11px] text-amber-800 bg-amber-50 border border-amber-200 rounded-lg px-2 py-1.5 leading-relaxed">
                  Logo will be added under the output for this model (fallback).
                </p>
              )}
              {(options?.lightingStyles?.length ?? 0) > 0 && (
                <div>
                  <label className="ui-label">Lighting style</label>
                  <select
                    value={lightingStyle}
                    onChange={(e) => setLightingStyle(e.target.value)}
                    className="ui-input"
                  >
                    <option value="">Default</option>
                    {options!.lightingStyles!.map((s) => (
                      <option key={s} value={s}>
                        {s}
                      </option>
                    ))}
                  </select>
                </div>
              )}
              {workflowVariantLabel && workflowVariants.length > 0 && (
                <div>
                  <label className="ui-label">{workflowVariantLabel}</label>
                  <select
                    value={workflowVariantKey}
                    onChange={(e) => setWorkflowVariantKey(e.target.value)}
                    className="ui-input"
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
                  <label className="ui-label">Style Preset</label>
                  <select
                    value={stylePresetId}
                    onChange={(e) => setStylePresetId(e.target.value)}
                    className="ui-input"
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
              <div className="space-y-2.5">
                {showAspectRatio && (
                  <select
                    value={aspectRatio}
                    onChange={(e) => setAspectRatio(e.target.value)}
                    className="ui-input"
                    aria-label="Aspect ratio"
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
                    className="ui-input"
                    aria-label="Person generation"
                  >
                    <option value="DONT_ALLOW">No people</option>
                    <option value="ALLOW_ADULT">Allow adults</option>
                    <option value="ALLOW_ALL">Allow all</option>
                  </select>
                )}
                {showNumberOfImages && (
                  <select
                    value={numberOfImages}
                    onChange={(e) => setNumberOfImages(Number(e.target.value))}
                    className="ui-input"
                    aria-label="Number of images"
                  >
                    {[1, 2, 3, 4].map((n) => (
                      <option key={n} value={n}>
                        {n} image{n > 1 ? "s" : ""}
                      </option>
                    ))}
                  </select>
                )}
                <ModelSelector
                  workflow={apiWorkflow}
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
                {is4kSelected && (
                  <p className="text-[11px] text-amber-800 bg-amber-50 border border-amber-200 rounded-xl px-3 py-2 leading-relaxed">
                    4K is slower (often 5-6+ minutes) and costs more. Prefer 1K
                    for catalog/bulk.
                  </p>
                )}
              </div>
            </div>
            <button
              type="button"
              onClick={() => generateMutation.mutate()}
              disabled={
                generateMutation.isPending ||
                Boolean(uploadProgress) ||
                generateBlockedByBatch
              }
              className="ui-btn-primary w-full lg:hidden"
            >
              {generateMutation.isPending || uploadProgress ? (
                <RefreshCcw className="size-4 animate-spin" />
              ) : (
                <Wand2 className="size-4" />
              )}
              {uploadProgress
                ? uploadProgress
                : generateMutation.isPending
                  ? "Queuing…"
                  : isBulk
                    ? `Generate Bulk (${primaryFiles.length})`
                    : "Generate"}
            </button>
            {activeJobs.length > 0 && (
              <p className="text-[11px] text-center text-slate-500">
                {activeJobs.length} running — queue more after upload finishes
              </p>
            )}
          </aside>
        </div>
      </main>
      {cropTarget && (
        <ImageCropModal
          open
          imageSrc={cropTarget.src}
          fileName={cropTarget.name}
          title={
            cropTarget.kind === "logo"
              ? "Crop logo"
              : cropTarget.kind === "reference"
                ? "Crop theme"
                : "Crop product"
          }
          onCancel={() => {
            URL.revokeObjectURL(cropTarget.src);
            setCropTarget(null);
          }}
          onConfirm={onCropConfirm}
        />
      )}
    </AppLayout>
  );
}
