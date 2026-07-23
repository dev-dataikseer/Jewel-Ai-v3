import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { useJobStream } from "@/hooks/useJobStream";
import { StudioInspectorPanel } from "@/components/studio/StudioInspectorPanel";
import { api, mediaUrl } from "@/lib/api";
import { apiErrorMessage } from "@/lib/apiError";
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
import { STUDIO_SIDEBAR_WORKFLOWS, WORKFLOWS } from "@/types";

import { createContext, useContext, ReactNode } from 'react';

export const StudioStateContext = createContext<any>(null);
export const StudioDispatchContext = createContext<any>(null);

export function useStudioState() {
  const context = useContext(StudioStateContext);
  if (!context) throw new Error("useStudioState must be used within a StudioProvider");
  return context;
}

export function useStudioDispatch() {
  const context = useContext(StudioDispatchContext);
  if (!context) throw new Error("useStudioDispatch must be used within a StudioProvider");
  return context;
}

export function StudioProvider({ children }: { children: ReactNode }) {

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

  const [catalogMode, setCatalogMode] = useState<"modern" | "reference_mirror" | "style_mood">(
    "modern",
  );
  const [compareMode, setCompareMode] = useState(false);
  const [workflowSheetOpen, setWorkflowSheetOpen] = useState(false);
  const [inspectorSheetOpen, setInspectorSheetOpen] = useState(false);
  const [inspectorTab, setInspectorTab] = useState<"settings" | "advanced">("settings");
  const [negativePrompt, setNegativePrompt] = useState("");
  const [inputZoom, setInputZoom] = useState(1);
  const [outputZoom, setOutputZoom] = useState(1);

  const apiWorkflow = workflow;
  const isCatalog = workflow === "CATALOG_IMAGE";
  const supportsBulk = primaryFiles.length > 1;
  const isBulk = supportsBulk;
  const needsModelReference = workflow === "VIRTUAL_TRY_ON";
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
  // V2: with/without reference is driven by uploads, not a Catalog mode dropdown
  const hasStyleOrLogoRef = Boolean(referenceFile || lockedUrls.reference || lockedUrls.logo);
  const needsStyleReference = isCatalog && hasStyleOrLogoRef;
  const needsReference = needsModelReference;
  const inputImageCount =
    primaryFiles.length > 0
      ? primaryFiles.length
      : lockedUrls.input || lockedUrls.assetId
        ? 1
        : 0;

  // Skip auto catalogMode when restoring history/session (set after hydrate that sets catalogMode)
  const historyHydratedRef = useRef(false);

  // Keep catalogMode aligned with uploads for API compatibility (V2 uses image packet)
  useEffect(() => {
    if (!isCatalog) return;
    if (historyHydratedRef.current) return;
    setCatalogMode(hasStyleOrLogoRef ? "reference_mirror" : "modern");
  }, [isCatalog, hasStyleOrLogoRef]);

  const {
    data: options,
    isError: optionsError,
    isFetching: optionsFetching,
  } = useQuery({
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
      if (
        draft.catalogMode === "modern" ||
        draft.catalogMode === "reference_mirror" ||
        draft.catalogMode === "style_mood"
      ) {
        setCatalogMode(draft.catalogMode);
        historyHydratedRef.current = true;
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

  // Refresh signed theme/logo URLs so previews survive page switches
  useEffect(() => {
    if (!sessionHydrated.current) return;
    const themeId = lockedUrls.themeAssetId;
    const logoId = lockedUrls.logoAssetId;
    if (!themeId && !logoId) return;
    let cancelled = false;
    void (async () => {
      try {
        const [themeRes, logoRes] = await Promise.all([
          themeId
            ? api.get<Asset>(`/assets/${themeId}`).catch(() => null)
            : Promise.resolve(null),
          logoId
            ? api.get<Asset>(`/assets/${logoId}`).catch(() => null)
            : Promise.resolve(null),
        ]);
        if (cancelled) return;
        if (themeRes?.data?.original_url) {
          const themeUrl = themeRes.data.original_url;
          patchBrandKit({ themeUrl, themeAssetId: themeId });
          setLockedUrls((u) =>
            u.themeAssetId === themeId ? { ...u, reference: themeUrl } : u,
          );
        }
        if (logoRes?.data?.original_url) {
          const logoUrl = logoRes.data.original_url;
          patchBrandKit({ logoUrl, logoAssetId: logoId });
          setLockedUrls((u) =>
            u.logoAssetId === logoId ? { ...u, logo: logoUrl } : u,
          );
        }
      } catch {
        /* keep cached URLs */
      }
    })();
    return () => {
      cancelled = true;
    };
    // Only re-run when asset ids change (not on every signed URL refresh)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lockedUrls.themeAssetId, lockedUrls.logoAssetId]);

  // Persist session draft (debounced — avoids lag when flipping option settings)
  useEffect(() => {
    if (!sessionHydrated.current) return;
    const timer = window.setTimeout(() => {
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
        catalogMode,
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
    }, 400);
    return () => window.clearTimeout(timer);
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
    catalogMode,
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

  const failedToastIdsRef = useRef(new Set<string>());

  useJobStream(streamingIds, {
    onUpdate: (job) => {
      setSessionJobs((prev) =>
        prev.map((j) => (j.id === job.id ? { ...j, ...job } : j)),
      );
      if (job.status === "FAILED") {
        if (failedToastIdsRef.current.has(job.id)) return;
        failedToastIdsRef.current.add(job.id);
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
    const ac = new AbortController();
    api
      .get<Job>(`/jobs/${jobId}`, { signal: ac.signal })
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
        } else if (job.workflow === "REFERENCE_STYLE_MATCH") {
          setWorkflow("CATALOG_IMAGE");
          setCatalogMode("style_mood");
          historyHydratedRef.current = true;
        } else if (job.workflow === "VIRTUAL_TRY_ON") {
          setWorkflow("VIRTUAL_TRY_ON");
          const tm = (job.provider_metadata as { tryOnMode?: string } | null)?.tryOnMode;
          setTryOnPreset(tm === "customer" ? "customer" : "studio");
        } else if (job.workflow) {
          setWorkflow(job.workflow);
        }
        const cm = (job.provider_metadata as { catalogMode?: string } | null)?.catalogMode;
        if (cm === "modern" || cm === "reference_mirror" || cm === "style_mood") {
          setCatalogMode(cm);
          historyHydratedRef.current = true;
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
      .catch(() => {
        if (ac.signal.aborted) return;
        toast.error("Could not load job from link");
      });
    searchParams.delete("jobId");
    setSearchParams(searchParams, { replace: true });
    return () => ac.abort();
  }, [searchParams, setSearchParams]);

  useEffect(() => {
    const preset = searchParams.get("preset");
    if (!preset) return;
    setStylePresetId(preset);
    searchParams.delete("preset");
    setSearchParams(searchParams, { replace: true });
  }, [searchParams, setSearchParams]);

  useEffect(() => {
    const batchId = searchParams.get("batchId");
    if (!batchId) return;
    const ac = new AbortController();
    setLastBatchId(batchId);
    setBatchForceAllow(false);
    api
      .get<BatchOut>(`/jobs/batches/${batchId}`, { signal: ac.signal })
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
      .catch(() => {
        if (ac.signal.aborted) return;
        toast.error("Could not load batch");
      });
    searchParams.delete("batchId");
    setSearchParams(searchParams, { replace: true });
    return () => ac.abort();
  }, [searchParams, setSearchParams]);

  useEffect(() => {
    const keys = new Set(workflowVariants.map((v) => v.variant_key));
    if (workflowVariantKey && keys.has(workflowVariantKey)) return;
    const first = workflowVariants[0];
    setWorkflowVariantKey(first ? first.variant_key : "");
  }, [workflow, workflowVariants, workflowVariantKey]);

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
        const logoStorageUrl = (
          (logoAsset?.original_url || lockedUrls.logo || "") as string
        ).split("?")[0] || null;
        const selectedVariant = workflowVariants.find(
          (v) => v.variant_key === workflowVariantKey,
        );

        if (referenceAsset) {
          const themeUrl = referenceAsset.original_url;
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
          const url = logoAsset.original_url;
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
          aspect_ratio: String(modelParams.aspect_ratio || aspectRatio),
          person_generation: personGeneration,
          number_of_images: Number(
            modelParams.num_images ?? modelParams.num_samples ?? numberOfImages,
          ) || 1,
          model_endpoint_id: modelEndpointId || selectedModel?.endpoint_id,
          model_params: {
            ...modelParams,
            ...(negativePrompt.trim() &&
            "negative_prompt" in (selectedModel?.input_schema?.properties ?? {})
              ? { negative_prompt: negativePrompt.trim() }
              : {}),
          },

          reference_url: needsModelReference ? undefined : referenceUrl,
          model_url: modelUrl,
          ...(workflow === "VIRTUAL_TRY_ON"
            ? { try_on_mode: tryOnPreset }
            : {}),
          ...(isCatalog
            ? {
                catalog_mode: referenceUrl
                  ? catalogMode === "modern"
                    ? "reference_mirror"
                    : catalogMode
                  : "modern",
              }
            : {}),
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
    onError: (err: Error) => toast.error(apiErrorMessage(err, "Generation failed")),
  });

  const regenerateMutation = useMutation({
    mutationFn: (jobId: string) =>
      api.post<Job>(`/jobs/${jobId}/regenerate`).then((r) => r.data),
    onSuccess: (job) => {
      setSessionJobs((prev) => mergeSessionJobs(prev, [job]));
      setActiveJobId(job.id);
      toast.success("Regeneration started — same settings, new job");
    },
    onError: (err: Error) => toast.error(apiErrorMessage(err, "Regeneration failed")),
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
    onError: (err: Error) => toast.error(apiErrorMessage(err, "Retry failed")),
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
    onError: (err: Error) => toast.error(apiErrorMessage(err, "Could not cancel")),
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
  const showPersonGeneration = Boolean(
    selectedModel?.capabilities?.person_generation,
  );

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
    setPrimaryPreviews([]);
    setLockedUrls((u) => ({ ...u, input: null, assetId: null }));
    setValidationErrors((e) => ({ ...e, productImage: "" }));
  };

  const clearGenerated = () => {
    setActiveJobId(null);
    setCompareMode(false);
    setOutputZoom(1);
    setOutputIndex(0);
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
    // Keep local File preview until upload finishes; clear stale locked URL
    if (needsModelReference) {
      setLockedUrls((u) => ({ ...u, reference: null, model: null }));
    } else {
      setLockedUrls((u) => ({ ...u, reference: null, themeAssetId: null }));
    }
    void (async () => {
      try {
        const asset = await uploadOne(
          file,
          needsModelReference ? "portrait" : "theme",
        );
        const url = asset.original_url;
        if (needsModelReference) {
          setLockedUrls((u) => ({
            ...u,
            reference: url,
            model: url,
          }));
        } else {
          patchBrandKit({
            themeAssetId: asset.id,
            themeUrl: url,
            themeName: file.name,
          });
          setLockedUrls((u) => ({
            ...u,
            reference: url,
            themeAssetId: asset.id,
          }));
        }
        // Drop local File once durable URL is saved (survives page switches)
        setReferenceFile(null);
      } catch (err) {
        toast.error(
          apiErrorMessage(err as Error, "Could not save theme/portrait image"),
        );
      } finally {
        setUploadProgress(null);
      }
    })();
  };

  const onLogoPick = (files: FileList | null) => {
    const file = files?.[0] || null;
    if (!file) return;
    setLogoFile(file);
    setLockedUrls((u) => ({ ...u, logo: null, logoAssetId: null }));
    void (async () => {
      try {
        const asset = await uploadOne(file, "logo");
        const url = asset.original_url;
        patchBrandKit({
          logoAssetId: asset.id,
          logoUrl: url,
          logoName: file.name,
        });
        setLockedUrls((u) => ({
          ...u,
          logo: url,
          logoAssetId: asset.id,
        }));
        setLogoFile(null);
      } catch (err) {
        toast.error(apiErrorMessage(err as Error, "Could not save logo image"));
      } finally {
        setUploadProgress(null);
      }
    })();
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
      URL.revokeObjectURL(cropTarget.src);
      setCropTarget(null);
      // Reuse pick path so cropped theme/portrait is uploaded + persisted
      const dt = new DataTransfer();
      dt.items.add(file);
      onReferencePick(dt.files);
      return;
    } else {
      URL.revokeObjectURL(cropTarget.src);
      setCropTarget(null);
      const dt = new DataTransfer();
      dt.items.add(file);
      onLogoPick(dt.files);
      return;
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
      : activeJob?.input_url
        ? [mediaUrl(activeJob.input_url)]
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
    // Jobs already update via SSE/poll in useJobStream — poll batch metadata less often.
    refetchInterval: (q) => {
      const s = q.state.data?.status;
      return s === "PENDING" || s === "PROCESSING" ? 8000 : false;
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
    if (id === workflow) return;
    setWorkflow(id);
    setActiveJobId(null);
    setValidationErrors({});
    setCompareMode(false);
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

  const sidebarWorkflows = useMemo(() => {
    const preferred = STUDIO_SIDEBAR_WORKFLOWS.map((w: any) => ({
      id: w.id as string,
      label: w.label,
      title: WORKFLOWS.find((x: any) => x.id === w.id)?.label || w.label,
    }));
    const preferredIds = new Set(preferred.map((w: any) => w.id));
    const fromApi = (options?.workflows || [])
      .filter(
        (w: any) =>
          ![
            "BULK_GENERATION",
            "JEWELRY_ON_MODEL",
            "CUSTOMER_TRY_ON",
          ].includes(w.id),
      )
      .map((w: any) => ({ id: w.id, label: w.label, title: w.label }));

    if (!fromApi.length) return preferred;

    const byId = new Map(fromApi.map((w: any) => [w.id, w] as const));
    // Keep short sidebar labels; only use API to confirm the workflow exists.
    const ordered = preferred
      .filter((w: any) => byId.has(w.id))
      .map((w: any) => ({ ...w, title: byId.get(w.id)?.title || w.title }));

    const extras = fromApi
      .filter((w: any) => !preferredIds.has(w.id))
      .sort((a: any, b: any) => a.label.localeCompare(b.label));

    return [...ordered, ...extras];
  }, [options?.workflows]);

  const schemaHasNegative = "negative_prompt" in schemaProps;

  // Keep generate payload in sync with Advanced model params
  useEffect(() => {
    const ar = modelParams.aspect_ratio;
    if (typeof ar === "string" && ar.trim()) setAspectRatio(ar);
    const n = modelParams.num_images ?? modelParams.num_samples;
    if (typeof n === "number" && n > 0) setNumberOfImages(n);
  }, [modelParams]);
  const footerModel = selectedModel?.display_name || selectedModel?.endpoint_id || null;

  const clearTheme = () => {
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
  };

  const clearLogo = () => {
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
  };

  const inspectorPanel = (
    <StudioInspectorPanel
      tab={inspectorTab}
      onTabChange={setInspectorTab}
      workflow={workflow}
      jewelryTypes={jewelryTypes}
      onJewelryTypesChange={setJewelryTypes}
      options={options}
      promptText={promptText}
      onPromptTextChange={setPromptText}
      negativePrompt={negativePrompt}
      onNegativePromptChange={setNegativePrompt}
      schemaHasNegative={schemaHasNegative}
      apiWorkflow={apiWorkflow}
      inputImageCount={inputImageCount}
      modelEndpointId={modelEndpointId}
      modelParams={modelParams}
      onModelChange={(endpointId: string, model: any) => {
        setModelEndpointId(endpointId);
        setSelectedModel(model);
      }}
      onParamsChange={setModelParams}
      isCatalog={isCatalog}
      tryOnPreset={tryOnPreset}
      onTryOnPresetChange={setTryOnPreset}
      catalogMode={catalogMode as any}
      onCatalogModeChange={(mode: any) => {
        historyHydratedRef.current = true;
        setCatalogMode(mode);
      }}
      workflowVariantLabel={workflowVariantLabel}
      workflowVariants={workflowVariants}
      workflowVariantKey={workflowVariantKey}
      onWorkflowVariantKeyChange={setWorkflowVariantKey}
      stylePresets={stylePresets}
      stylePresetId={stylePresetId}
      onStylePresetIdChange={setStylePresetId}
      lightingStyle={lightingStyle}
      onLightingStyleChange={setLightingStyle}
      showPersonGeneration={showPersonGeneration}
      personGeneration={personGeneration}
      onPersonGenerationChange={setPersonGeneration}
      themePreviewSrc={themePreviewSrc}
      logoPreviewSrc={logoPreviewSrc}
      referenceFile={referenceFile}
      logoFile={logoFile}
      onReferencePick={onReferencePick}
      onLogoPick={onLogoPick}
      clearBrandAssets={clearBrandAssets}
      clearTheme={clearTheme}
      clearLogo={clearLogo}
      validationErrors={validationErrors}
      isBulk={isBulk}
      lockedUrls={lockedUrls}
      onGenerate={() => generateMutation.mutate()}
      generating={generateMutation.isPending || Boolean(uploadProgress)}
      generateDisabled={generateBlockedByBatch}
      generateBlockedByBatch={generateBlockedByBatch}
      onForceBatch={() => setBatchForceAllow(true)}
      uploadProgress={uploadProgress}
      bulkCount={isBulk ? primaryFiles.length : undefined}
    />
  );

  
  const state = useMemo(() => ({
    activeJob,
    activeJobId,
    activeJobs,
    activeOutputUrl,
    allJobs,
    apiWorkflow,
    aspectRatio,
    batchActive,
    batchForceAllow,
    batchJobIds,
    batchJobIndex,
    catalogMode,
    compareMode,
    cropTarget,
    failedToastIdsRef,
    favoriteIdList,
    favoriteIds,
    footerModel,
    generateBlockedByBatch,
    hasStyleOrLogoRef,
    historyHydratedRef,
    inputImageCount,
    inputZoom,
    inspectorPanel,
    inspectorSheetOpen,
    inspectorTab,
    isBulk,
    isCatalog,
    jewelryTypes,
    lastBatchId,
    lightingStyle,
    lockedUrls,
    logoFile,
    logoPreview,
    logoPreviewSrc,
    modelEndpointId,
    modelParams,
    needsModelReference,
    needsReference,
    needsStyleReference,
    negativePrompt,
    numberOfImages,
    openCropForPrimary,
    options,
    optionsError,
    
    optionsFetching,
    outputIndex,
    outputUrls,
    outputZoom,
    personGeneration,
    primaryFiles,
    primaryPreviews,
    productPreviewSrcs,
    promptText,
    promptVariants,
    queryClient,
    queueModeInline,
    recentJobs,
    referenceFile,
    referencePreview,
    removePrimaryAt,
    schemaHasNegative,
    schemaProps,
    searchParams,
    selectWorkflow,
    selectedModel,
    sessionHydrated,
    sessionJobs,
    showPersonGeneration,
    sidebarWorkflows,
    streamingIds,
    stylePresetId,
    stylePresets,
    supportsBulk,
    themePreviewSrc,
    tryOnPreset,
    validationErrors,
    variants,
    workflow,
    workflowSheetOpen,
    workflowVariantKey,
    workflowVariantLabel,
    workflowVariants
  }), [activeJob, activeJobId, activeJobs, activeOutputUrl, allJobs, apiWorkflow, aspectRatio, batchActive, batchForceAllow, batchJobIds, batchJobIndex, catalogMode, compareMode, cropTarget, failedToastIdsRef, favoriteIdList, favoriteIds, footerModel, generateBlockedByBatch, hasStyleOrLogoRef, historyHydratedRef, inputImageCount, inputZoom, inspectorPanel, inspectorSheetOpen, inspectorTab, isBulk, isCatalog, jewelryTypes, lastBatchId, lightingStyle, lockedUrls, logoFile, logoPreview, logoPreviewSrc, modelEndpointId, modelParams, needsModelReference, needsReference, needsStyleReference, negativePrompt, numberOfImages, openCropForPrimary, options, optionsError,
     optionsFetching, outputIndex, outputUrls, outputZoom, personGeneration, primaryFiles, primaryPreviews, productPreviewSrcs, promptText, promptVariants, queryClient, queueModeInline, recentJobs, referenceFile, referencePreview, removePrimaryAt, schemaHasNegative, schemaProps, searchParams, selectWorkflow, selectedModel, sessionHydrated, sessionJobs, showPersonGeneration, sidebarWorkflows, streamingIds, stylePresetId, stylePresets, supportsBulk, themePreviewSrc, tryOnPreset, validationErrors, variants, workflow, workflowSheetOpen, workflowVariantKey, workflowVariantLabel, workflowVariants]);

  const dispatch = useMemo(() => ({
    cancelMutation,
    clearBrandAssets,
    clearGenerated,
    clearLogo,
    clearPrimaryFiles,
    clearTheme,
    clearWorkspace,
    generateMutation,
    onCropConfirm,
    onLogoPick,
    onPrimaryAppend,
    onPrimaryReplace,
    onReferencePick,
    regenerateMutation,
    retryMutation,
    setActiveJobId,
    setAspectRatio,
    setBatchForceAllow,
    setCatalogMode,
    setCompareMode,
    setCropTarget,
    setFavoriteIds,
    setInputZoom,
    setInspectorSheetOpen,
    setInspectorTab,
    setJewelryTypes,
    setLastBatchId,
    setLightingStyle,
    setLockedUrls,
    setLogoFile,
    setLogoPreview,
    setModelEndpointId,
    setModelParams,
    setNegativePrompt,
    setNumberOfImages,
    setOutputIndex,
    setOutputZoom,
    setPersonGeneration,
    setPrimaryFiles,
    setPrimaryPreviews,
    setPromptText,
    setQueueModeInline,
    setReferenceFile,
    setReferencePreview,
    setSearchParams,
    setSelectedModel,
    setSessionJobs,
    setStylePresetId,
    setTryOnPreset,
    setUploadProgress,
    setValidationErrors,
    setWorkflow,
    setWorkflowSheetOpen,
    setWorkflowVariantKey,
    toggleFavorite,
    uploadMany,
    uploadOne,
    uploadProgress
  }), [cancelMutation, clearBrandAssets, clearGenerated, clearLogo, clearPrimaryFiles, clearTheme, clearWorkspace, generateMutation, onCropConfirm, onLogoPick, onPrimaryAppend, onPrimaryReplace, onReferencePick, regenerateMutation, retryMutation, setActiveJobId, setAspectRatio, setBatchForceAllow, setCatalogMode, setCompareMode, setCropTarget, setFavoriteIds, setInputZoom, setInspectorSheetOpen, setInspectorTab, setJewelryTypes, setLastBatchId, setLightingStyle, setLockedUrls, setLogoFile, setLogoPreview, setModelEndpointId, setModelParams, setNegativePrompt, setNumberOfImages, setOutputIndex, setOutputZoom, setPersonGeneration, setPrimaryFiles, setPrimaryPreviews, setPromptText, setQueueModeInline, setReferenceFile, setReferencePreview, setSearchParams, setSelectedModel, setSessionJobs, setStylePresetId, setTryOnPreset, setUploadProgress, setValidationErrors, setWorkflow, setWorkflowSheetOpen, setWorkflowVariantKey, toggleFavorite, uploadMany, uploadOne, uploadProgress]);

  return (
    <StudioDispatchContext.Provider value={dispatch}>
      <StudioStateContext.Provider value={state}>
        {children}
      </StudioStateContext.Provider>
    </StudioDispatchContext.Provider>
  );
}
