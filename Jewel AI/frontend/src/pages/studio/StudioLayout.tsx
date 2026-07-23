// @ts-nocheck
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  BadgeCheck,
  ChevronLeft,
  ChevronRight,
  Clock,
  Crop,
  Gem,
  Heart,
  ImagePlus,
  Images,
  Layers3,
  Menu,
  PanelRight,
  Sparkles,
  UploadCloud,
  Wand2,
} from "lucide-react";
import { AppLayout } from "@/components/AppLayout";
import { ImageCropModal } from "@/components/studio/ImageCropModal";
import { BatchProgressPanel } from "@/components/studio/BatchProgressPanel";
import { ImageStageControls } from "@/components/studio/ImageStageControls";
import { ProductUploadGallery } from "@/components/studio/ProductUploadGallery";
import { StudioInspectorPanel } from "@/components/studio/StudioInspectorPanel";
import { UploadZone } from "@/components/studio/UploadZone";
import { ActionDock } from "@/components/ui/ActionDock";
import { FacetMark } from "@/components/ui/FacetMark";
import { JobStageBar, resolveJobStage } from "@/components/ui/JobStageBar";
import { ResultsTray } from "@/components/ui/ResultsTray";
import { Sheet } from "@/components/ui/Sheet";
import { jobStatusLabel, useJobStream } from "@/hooks/useJobStream";
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
import { STUDIO_SIDEBAR_WORKFLOWS, WORKFLOWS, workflowLabel } from "@/types";

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


import { useStudioState, useStudioDispatch } from "./StudioContext";

export function StudioLayout() {
  const state = useStudioState();
  const dispatch = useStudioDispatch();
  const {
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
    data,
    failedToastIdsRef,
    favoriteIdList,
    favoriteIds,
    footerModel,
    generateBlockedByBatch,
                inputZoom,
    inspectorPanel,
    inspectorSheetOpen,
        isBulk,
            lastBatchId,
        lockedUrls,
                            needsReference,
    needsStyleReference,
            openCropForPrimary,
    options,
    optionsError,
    refetchOptions,
    optionsFetching,
    outputIndex,
    outputUrls,
    outputZoom,
        primaryFiles,
        productPreviewSrcs,
                queueModeInline,
    recentJobs,
    referenceFile,
        removePrimaryAt,
                selectWorkflow,
            sessionJobs,
        sidebarWorkflows,
                    themePreviewSrc,
        validationErrors,
        workflow,
    workflowSheetOpen,
            
  } = state;
  const {
    cancelMutation,
        clearGenerated,
        clearPrimaryFiles,
        clearWorkspace,
    generateMutation,
    onCropConfirm,
        onPrimaryAppend,
    onPrimaryReplace,
    onReferencePick,
    regenerateMutation,
    retryMutation,
    setActiveJobId,
        setBatchForceAllow,
        setCompareMode,
    setCropTarget,
        setInputZoom,
    setInspectorSheetOpen,
            setLastBatchId,
        setLockedUrls,
                            setOutputIndex,
    setOutputZoom,
                        setReferenceFile,
                                        setWorkflowSheetOpen,
        toggleFavorite,
            uploadProgress
  } = dispatch;

return (
    <AppLayout subtitle="AI Creative Suite" footerModel={footerModel}>
      <main className="flex flex-1 min-h-0 w-full overflow-hidden bg-[var(--jewel-bg)]">
        <div className="flex h-full w-full min-h-0">
          {/* Left sidebar */}
          <aside className="hidden w-[220px] xl:w-[240px] shrink-0 flex-col overflow-hidden bg-[var(--jewel-surface-muted)] lg:flex border-r border-[var(--jewel-border)] min-h-0 self-stretch">
            <div className="p-3 flex flex-col h-full min-h-0 gap-4 overflow-y-auto overscroll-contain">
              <div>
                <p className="ui-section-label mb-1.5 px-2.5">Create</p>
                <div className="space-y-0.5">
                  {sidebarWorkflows.map((item: any) => {
                    const Icon = WORKFLOW_ICONS[item.id] || Sparkles;
                    const active = workflow === item.id;
                    return (
                      <button
                        key={item.id}
                        type="button"
                        title={item.title || item.label}
                        onClick={() => selectWorkflow(item.id)}
                        className={`flex w-full min-w-0 items-center gap-2.5 rounded-lg px-2.5 py-2 text-left text-[13px] font-medium transition-colors ${
                          active
                            ? "bg-[var(--jewel-accent-soft)] text-[var(--jewel-accent)] shadow-sm"
                            : "text-jewel-ink-muted hover:bg-[var(--jewel-surface-muted)] hover:text-jewel-ink"
                        }`}
                      >
                        <Icon className="size-4 shrink-0 stroke-[1.75]" strokeWidth={1.75} />
                        <span className="min-w-0 flex-1 leading-snug">{item.label}</span>
                      </button>
                    );
                  })}
                </div>
              </div>
              <div className="h-px w-full bg-[var(--jewel-hairline)] shrink-0" />
              <div>
                <p className="ui-section-label mb-1.5 px-2.5">Library</p>
                <div className="space-y-0.5">
                  <Link
                    to="/history"
                    className="flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-left text-[13px] font-medium text-jewel-ink-muted hover:bg-[var(--jewel-surface-muted)] hover:text-jewel-ink transition-colors"
                  >
                    <Clock className="size-4 shrink-0 stroke-[1.75]" />
                    Recent Generations
                  </Link>
                  <Link
                    to="/history"
                    className="flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-left text-[13px] font-medium text-jewel-ink-muted hover:bg-[var(--jewel-surface-muted)] hover:text-jewel-ink transition-colors"
                  >
                    <Heart className="size-4 shrink-0 stroke-[1.75]" />
                    Favorites
                  </Link>
                </div>
              </div>
              <div className="mt-auto pt-2 border-t border-[var(--jewel-hairline)]">
                <button
                  type="button"
                  onClick={clearWorkspace}
                  className="w-full px-2.5 py-2 text-left text-[12px] font-semibold text-jewel-ink-muted hover:text-jewel-ink transition-colors rounded-lg hover:bg-[var(--jewel-surface-muted)]"
                >
                  Clear workspace {sessionJobs.length > 0 ? ` (${sessionJobs.length})` : ""}
                </button>
              </div>
            </div>
          </aside>

          {/* Center canvas */}
          <section className="flex-1 flex flex-col overflow-hidden bg-[var(--jewel-bg)] relative min-w-0 min-h-0">
            <div className="flex flex-col p-4 xl:p-5 w-full gap-3 flex-1 min-h-0 overflow-y-auto overscroll-contain">
              <div className="flex items-start justify-between gap-4 shrink-0">
                <div className="min-w-0 flex items-center gap-3 flex-wrap">
                  <Sparkles className="size-5 text-[var(--jewel-accent)]" />
                  <h2 className="text-[20px] font-semibold text-jewel-ink tracking-tight">
                    {workflowLabel(workflow, options)}
                  </h2>
                  <span className="ui-pill-pro">Pro</span>
                </div>
                <div className="flex shrink-0 gap-2">
                  <button
                    type="button"
                    className="ui-btn-secondary lg:hidden"
                    onClick={() => setWorkflowSheetOpen(true)}
                    aria-label="Open workflows"
                  >
                    <Menu className="size-3.5" />
                  </button>
                  <button
                    type="button"
                    className="ui-btn-secondary lg:hidden"
                    onClick={() => setInspectorSheetOpen(true)}
                    aria-label="Open parameters"
                  >
                    <PanelRight className="size-3.5" />
                  </button>
                </div>
              </div>

              <div className="relative grid grid-cols-1 md:grid-cols-2 gap-4 w-full min-w-0 shrink-0 items-stretch">
                {compareMode ? (
                  <button
                    type="button"
                    className="hidden md:flex absolute left-1/2 top-[38%] -translate-x-1/2 -translate-y-1/2 z-10 size-9 items-center justify-center rounded-full bg-white shadow-card border border-[var(--jewel-border)] text-[var(--jewel-accent)]"
                    onClick={() => setCompareMode(false)}
                    aria-pressed={true}
                    aria-label="Exit compare mode"
                  >
                    <ChevronLeft className="size-4 -mr-1" />
                    <ChevronRight className="size-4" />
                  </button>
                ) : null}

                {/* Input card */}
                <div className="flex h-full min-h-0 flex-col bg-white rounded-xl border border-[var(--jewel-border)] w-full overflow-hidden shadow-sm">
                  <div className="flex h-11 shrink-0 items-center justify-between gap-2 px-3 border-b border-[var(--jewel-hairline)]">
                    <span className="text-[11px] font-semibold tracking-wide uppercase text-jewel-ink">
                      Input
                    </span>
                    <div className="flex items-center gap-1.5">
                      {primaryFiles.length === 1 ? (
                        <button
                          type="button"
                          className="ui-btn-secondary h-8 px-2.5 text-[11px]"
                          onClick={() => openCropForPrimary(0)}
                          aria-label="Crop image"
                          title="Crop image"
                        >
                          <Crop className="size-3.5" />
                          Crop
                        </button>
                      ) : null}
                      <button
                        type="button"
                        className="ui-btn-secondary h-8 px-2.5 text-[11px]"
                        onClick={() => {
                          const el =
                            document.getElementById(
                              "studio-product-upload-empty-input",
                            ) ||
                            document.getElementById(
                              "studio-product-upload-add-input",
                            );
                          el?.click();
                        }}
                      >
                        <UploadCloud className="size-3.5" />
                        Upload images
                      </button>
                      {primaryFiles.length > 0 || productPreviewSrcs.length > 0 ? (
                        <button
                          type="button"
                          className="text-[11px] font-semibold text-rose-600 hover:text-rose-700 bg-rose-50 hover:bg-rose-100 h-8 px-2.5 rounded-lg transition-colors flex items-center gap-1"
                          onClick={clearPrimaryFiles}
                          title="Clear all input images"
                        >
                          <X className="size-3.5" strokeWidth={2.5} />
                          Clear
                        </button>
                      ) : null}
                    </div>
                  </div>

                  <div className="aspect-square w-full bg-[var(--jewel-surface-muted)] relative flex flex-col min-h-0 overflow-hidden p-3">
                    {optionsError ? (
                      <div className="absolute inset-x-3 top-3 z-10 rounded-lg border border-amber-200 bg-amber-50 px-2 py-1.5 text-[10px] text-amber-900">
                        Options failed.{" "}
                        <button
                          type="button"
                          className="font-bold underline"
                          onClick={() => void refetchOptions()}
                          disabled={optionsFetching}
                        >
                          Retry
                        </button>
                      </div>
                    ) : null}
                    {needsReference ? (
                      <div className="grid grid-cols-2 gap-2 flex-1 min-h-0 items-stretch">
                        <div className="min-h-0 h-full flex flex-col">
                          <ProductUploadGallery
                            id="studio-product-upload"
                            emptyTitle="Product"
                            files={primaryFiles}
                            previews={productPreviewSrcs}
                            error={validationErrors.productImage}
                            onAppend={onPrimaryAppend}
                            onReplace={onPrimaryReplace}
                            onRemoveAt={removePrimaryAt}
                            onClearAll={clearPrimaryFiles}
                            imageZoom={inputZoom}
                            onCropAt={
                              primaryFiles.length > 0 ? openCropForPrimary : undefined
                            }
                          />
                        </div>
                        <div className="min-h-0 h-full flex flex-col">
                          <UploadZone
                            id="studio-reference-upload"
                            label={needsStyleReference ? "Reference" : "Portrait"}
                            error={validationErrors.referenceImage}
                            previews={themePreviewSrc ? [themePreviewSrc] : []}
                            onFiles={onReferencePick}
                            single
                            stage
                            fileName={referenceFile?.name || "Portrait"}
                            onCrop={
                              referenceFile
                                ? () => {
                                    const src = URL.createObjectURL(referenceFile);
                                    setCropTarget({
                                      kind: "reference",
                                      src,
                                      name: referenceFile.name,
                                    });
                                  }
                                : undefined
                            }
                            onClear={() => {
                              setReferenceFile(null);
                              setLockedUrls((u: any) => ({
                                ...u,
                                reference: null,
                                model: null,
                                themeAssetId: null,
                              }));
                            }}
                          />
                        </div>
                      </div>
                    ) : (
                      <ProductUploadGallery
                        id="studio-product-upload"
                        emptyTitle="Product"
                        files={primaryFiles}
                        previews={productPreviewSrcs}
                        error={validationErrors.productImage}
                        onAppend={onPrimaryAppend}
                        onReplace={onPrimaryReplace}
                        onRemoveAt={removePrimaryAt}
                        onClearAll={clearPrimaryFiles}
                        imageZoom={inputZoom}
                        onCropAt={
                          primaryFiles.length > 0 ? openCropForPrimary : undefined
                        }
                      />
                    )}
                  </div>

                  <div className="shrink-0 border-t border-[var(--jewel-hairline)] bg-white">
                    <div className="relative h-10 px-1">
                      <ImageStageControls
                        variant="bar"
                        zoom={inputZoom}
                        onZoomChange={setInputZoom}
                        onFullscreen={
                          productPreviewSrcs[0]
                            ? () =>
                                window.open(
                                  productPreviewSrcs[0],
                                  "_blank",
                                  "noopener,noreferrer",
                                )
                            : undefined
                        }
                      />
                    </div>
                    <div className="flex h-10 items-center gap-1.5 border-t border-[var(--jewel-hairline)] px-2.5">
                      {primaryFiles.length > 1 ? (
                        <span className="text-[11px] font-medium text-jewel-ink-muted tabular-nums">
                          {primaryFiles.length} images
                        </span>
                      ) : (
                        <span className="text-[11px] font-medium text-jewel-ink-muted">
                          Product
                        </span>
                      )}
                      {primaryFiles.length > 0 || productPreviewSrcs.length > 0 ? (
                        <button
                          type="button"
                          onClick={clearPrimaryFiles}
                          className="ml-auto text-[11px] font-semibold text-jewel-ink-muted hover:text-jewel-ink"
                        >
                          Clear
                        </button>
                      ) : null}
                    </div>
                  </div>
                </div>

                {/* Generated card */}
                <div className="flex h-full min-h-0 flex-col bg-white rounded-xl border border-[var(--jewel-border)] w-full overflow-hidden shadow-sm">
                  <div className="flex h-11 shrink-0 items-center justify-between gap-2 px-3 border-b border-[var(--jewel-hairline)]">
                    <span className="text-[11px] font-semibold tracking-wide uppercase text-jewel-ink">
                      Generated
                    </span>
                    <div className="flex items-center gap-1.5">
                      {activeJob ? (
                        <button
                          type="button"
                          onClick={clearGenerated}
                          className="text-[11px] font-semibold text-jewel-ink-muted hover:text-jewel-ink"
                          title="Clear generated preview"
                        >
                          Clear
                        </button>
                      ) : null}
                      {activeJob?.status === "COMPLETED" ? (
                        <span className="ui-pill-success">Done</span>
                      ) : null}
                      {batchJobIds.length > 1 && batchJobIndex >= 0 ? (
                        <div className="flex items-center gap-0.5">
                          <span className="text-[10px] font-semibold tabular-nums text-jewel-ink-muted px-1">
                            {batchJobIndex + 1}/{batchJobIds.length}
                          </span>
                          <button
                            type="button"
                            disabled={batchJobIndex <= 0}
                            onClick={() =>
                              setActiveJobId(batchJobIds[batchJobIndex - 1])
                            }
                            className="rounded p-1 text-jewel-ink-faint hover:text-jewel-ink disabled:opacity-30"
                            aria-label="Previous job"
                          >
                            <ChevronLeft className="size-3.5" />
                          </button>
                          <button
                            type="button"
                            disabled={batchJobIndex >= batchJobIds.length - 1}
                            onClick={() =>
                              setActiveJobId(batchJobIds[batchJobIndex + 1])
                            }
                            className="rounded p-1 text-jewel-ink-faint hover:text-jewel-ink disabled:opacity-30"
                            aria-label="Next job"
                          >
                            <ChevronRight className="size-3.5" />
                          </button>
                        </div>
                      ) : null}
                    </div>
                  </div>

                  <div className="aspect-square w-full bg-[var(--jewel-surface-muted)] relative flex flex-col min-h-0 overflow-hidden p-3">
                    {activeJob &&
                    (activeJob.status === "PENDING" ||
                      activeJob.status === "PROCESSING") ? (
                      <div className="flex-1 flex flex-col min-h-0 rounded-lg border border-[var(--jewel-border)] bg-white p-3">
                        <JobStageBar
                          stage={resolveJobStage(activeJob)}
                          label={jobStatusLabel(activeJob)}
                          detail={
                            activeJob.provider_metadata?.webhook_pending ||
                            activeJob.provider_metadata?.progressStage ===
                              "waiting_on_fal"
                              ? "Generating…"
                              : "Preparing…"
                          }
                        />
                        <div className="flex-1 flex items-center justify-center">
                          <FacetMark
                            variant="spin"
                            size={28}
                            className="text-[var(--jewel-accent)]"
                          />
                        </div>
                        <button
                          type="button"
                          className="ui-btn-ghost h-8 text-[11px] mx-auto"
                          disabled={cancelMutation.isPending}
                          onClick={() => cancelMutation.mutate(activeJob.id)}
                        >
                          {cancelMutation.isPending ? "Cancelling…" : "Cancel"}
                        </button>
                      </div>
                    ) : !activeJob ? (
                      <div className="flex-1 flex flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed border-[var(--jewel-border)] bg-white text-center">
                        <Wand2 className="size-8 text-[var(--jewel-ink-faint)]" />
                        <span className="text-sm font-semibold text-jewel-ink">Output</span>
                        <span className="text-[11px] text-jewel-ink-muted">
                          Generate to preview
                        </span>
                      </div>
                    ) : activeJob.status === "FAILED" ||
                      activeJob.status === "CANCELLED" ? (
                      <div
                        className="flex-1 flex flex-col items-center justify-center gap-2 rounded-lg border border-rose-200 bg-rose-50 text-center p-4"
                        aria-live="polite"
                      >
                        <p className="text-sm font-semibold text-rose-800">
                          {activeJob.status === "CANCELLED" ? "Cancelled" : "Failed"}
                        </p>
                        <div className="flex flex-wrap gap-1.5 justify-center">
                          <button
                            type="button"
                            onClick={() => retryMutation.mutate(activeJob.id)}
                            disabled={retryMutation.isPending}
                            className="ui-btn-secondary h-8 px-2.5 text-[11px]"
                          >
                            Retry
                          </button>
                          <button
                            type="button"
                            onClick={() => regenerateMutation.mutate(activeJob.id)}
                            disabled={regenerateMutation.isPending}
                            className="ui-btn-secondary h-8 px-2.5 text-[11px]"
                          >
                            Duplicate
                          </button>
                        </div>
                      </div>
                    ) : (
                      <div className="flex-1 flex flex-col min-h-0 rounded-lg border border-[var(--jewel-border)] bg-white overflow-hidden">
                        <div className="flex-1 relative min-h-0 flex items-center justify-center p-3">
                          {compareMode ? (
                            <div className="grid h-full w-full grid-cols-2 gap-2">
                              <div className="flex items-center justify-center overflow-hidden rounded-md bg-[var(--jewel-surface-muted)]">
                                {activeJob.input_url || productPreviewSrcs[0] ? (
                                  <img
                                    src={mediaUrl(
                                      activeJob.input_url || productPreviewSrcs[0],
                                    )}
                                    alt="Input"
                                    className="max-h-full max-w-full object-contain"
                                  />
                                ) : null}
                              </div>
                              <div className="flex items-center justify-center overflow-hidden rounded-md bg-[var(--jewel-surface-muted)]">
                                {activeOutputUrl ? (
                                  <img
                                    src={mediaUrl(activeOutputUrl)}
                                    alt="Output"
                                    className="max-h-full max-w-full object-contain"
                                    style={{ transform: `scale(${outputZoom})` }}
                                  />
                                ) : null}
                              </div>
                            </div>
                          ) : activeOutputUrl ? (
                            <img
                              src={mediaUrl(activeOutputUrl)}
                              alt="Output"
                              className="max-h-full max-w-full object-contain animate-precious-flash"
                              style={{ transform: `scale(${outputZoom})` }}
                            />
                          ) : (
                            <span className="text-xs text-jewel-ink-muted">No output</span>
                          )}
                        </div>
                        {outputUrls.length > 1 ? (
                          <div className="flex gap-1.5 overflow-x-auto border-t border-[var(--jewel-hairline)] px-2 py-1.5 shrink-0">
                            {outputUrls.map((url: any, i: number) => (
                              <button
                                key={`${url}-${i}`}
                                type="button"
                                onClick={() => setOutputIndex(i)}
                                className={`size-10 shrink-0 overflow-hidden rounded-md border ${
                                  outputIndex === i
                                    ? "border-jewel-accent ring-2 ring-jewel-accent/20"
                                    : "border-jewel-border"
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
                        ) : null}
                      </div>
                    )}
                  </div>

                  <div className="shrink-0 border-t border-[var(--jewel-hairline)] bg-white">
                    <div className="relative h-10 px-1">
                      <ImageStageControls
                        variant="bar"
                        zoom={outputZoom}
                        onZoomChange={setOutputZoom}
                        onFullscreen={
                          activeOutputUrl
                            ? () =>
                                window.open(
                                  mediaUrl(activeOutputUrl),
                                  "_blank",
                                  "noopener,noreferrer",
                                )
                            : undefined
                        }
                      />
                    </div>
                    <div className="flex h-10 items-center border-t border-[var(--jewel-hairline)] px-2.5 min-w-0">
                      {activeJob?.status === "COMPLETED" ? (
                        <>
                          <ResultsTray
                            onRegenerate={() =>
                              regenerateMutation.mutate(activeJob.id)
                            }
                            regenerating={regenerateMutation.isPending}
                            onDownload={activeOutputUrl}
                            onFavorite={() => void toggleFavorite(activeJob)}
                            favorited={favoriteIds.has(activeJob.id)}
                            onUseAsReference={
                              activeOutputUrl
                                ? () => {
                                    setLockedUrls((u: any) => ({
                                      ...u,
                                      reference: mediaUrl(activeOutputUrl),
                                    }));
                                    toast.success("Output set as reference image");
                                  }
                                : undefined
                            }
                            onCopyPrompt={
                              activeJob.final_prompt || activeJob.prompt_text
                                ? async () => {
                                    const text =
                                      activeJob.final_prompt || activeJob.prompt_text;
                                    if (text) {
                                      await navigator.clipboard.writeText(text);
                                      toast.success("Prompt copied to clipboard");
                                    }
                                  }
                                : undefined
                            }
                            onShare={async () => {
                              try {
                                const res = await api.post<{ token: string }>(
                                  "/share-links",
                                  { job_id: activeJob.id },
                                );
                                const shareUrl = `${window.location.origin}/share/${res.data.token}`;
                                await navigator.clipboard.writeText(shareUrl);
                                toast.success("Share link copied");
                              } catch (err) {
                                toast.error(
                                  apiErrorMessage(
                                    err as Error,
                                    "Could not create share link",
                                  ),
                                );
                              }
                            }}
                            compareActive={compareMode}
                            onToggleCompare={() => setCompareMode((c: any) => !c)}
                            mediaUrl={mediaUrl}
                          />
                          <button
                            type="button"
                            onClick={clearGenerated}
                            className="ml-auto shrink-0 text-[11px] font-semibold text-jewel-ink-muted hover:text-jewel-ink"
                          >
                            Clear
                          </button>
                        </>
                      ) : activeJob ? (
                        <button
                          type="button"
                          onClick={clearGenerated}
                          className="ml-auto text-[11px] font-semibold text-jewel-ink-muted hover:text-jewel-ink"
                        >
                          Clear
                        </button>
                      ) : (
                        <span className="text-[11px] font-medium text-jewel-ink-muted">
                          Output
                        </span>
                      )}
                    </div>
                  </div>
                </div>
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

              {/* Recent generations */}
              <div className="ui-card p-4 shrink-0 overflow-hidden">
                <div className="mb-3 flex items-center justify-between gap-2">
                  <p className="ui-label mb-0 flex items-center gap-1.5">
                    <Clock className="size-3.5" /> Recent Generations
                    {sessionJobs.length > 0 && (
                      <span className="normal-case tracking-normal font-medium text-jewel-ink-muted">
                        · {sessionJobs.length} in session
                        {activeJobs.length > 0
                          ? ` · ${activeJobs.length} active`
                          : ""}
                      </span>
                    )}
                  </p>
                  <Link
                    to="/history"
                    className="text-[12px] font-semibold text-[var(--jewel-accent)] hover:underline"
                  >
                    View All
                  </Link>
                </div>
                <div className="flex items-center gap-2 overflow-x-auto pb-1">
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
                        onClick={() => {
                          setActiveJobId(job.id);
                          setOutputIndex(0);
                          setInputZoom(1);
                          setOutputZoom(1);
                          if (primaryFiles.length === 0) {
                            setLockedUrls((u: any) => ({
                              ...u,
                              input: job.input_url || u.input,
                              reference: job.reference_url || u.reference,
                              model: job.model_url || u.model,
                              assetId: job.asset_id || u.assetId,
                            }));
                          }
                        }}
                        aria-label={`${jobStatusLabel(job)} ${job.workflow || ""}`.trim()}
                        className={`relative size-14 shrink-0 rounded-lg overflow-hidden border transition duration-150 hover:-translate-y-0.5 hover:shadow-card ${
                          activeJobId === job.id
                            ? "border-jewel-accent ring-2 ring-jewel-accent/20"
                            : "border-jewel-border"
                        }`}
                      >
                        {(job.output_url || job.input_url) && (
                          <img
                            src={mediaUrl(job.output_url || job.input_url)}
                            alt=""
                            className="w-full h-full object-cover"
                          />
                        )}
                        {favoriteIds.has(job.id) && (
                          <span className="absolute top-1 right-1 rounded-full bg-white/90 p-0.5 shadow-sm">
                            <Heart className="size-2.5 fill-[var(--jewel-precious)] text-[var(--jewel-precious)]" />
                          </span>
                        )}
                      </button>
                    ))}
                  <Link
                    to="/history"
                    className="flex size-14 shrink-0 items-center justify-center rounded-lg border border-dashed border-jewel-border text-jewel-ink-faint hover:text-[var(--jewel-accent)] hover:border-[var(--jewel-accent)] transition-colors"
                    aria-label="View all history"
                  >
                    <ChevronRight className="size-4" />
                  </Link>
                </div>
              </div>

              <div className="lg:hidden sticky bottom-3 z-20">
                <ActionDock
                  className="lg:hidden"
                  label={
                    generateBlockedByBatch
                      ? "Batch running — wait or queue another"
                      : isBulk
                        ? `Ready to generate ${primaryFiles.length} images`
                        : lockedUrls.assetId && !primaryFiles.length
                          ? "Ready — using loaded product asset"
                          : "Ready when product is set"
                  }
                  hint={uploadProgress}
                  batchBlocked={generateBlockedByBatch}
                  onForceBatch={() => setBatchForceAllow(true)}
                  onGenerate={() => generateMutation.mutate()}
                  generating={
                    generateMutation.isPending || Boolean(uploadProgress)
                  }
                  disabled={generateBlockedByBatch}
                  bulkCount={isBulk ? primaryFiles.length : undefined}
                />
              </div>
            </div>
          </section>

          {/* Right inspector */}
          <aside className="hidden w-[280px] xl:w-[300px] shrink-0 overflow-hidden p-0 lg:flex lg:flex-col bg-white border-l border-[var(--jewel-border)] min-h-0 self-stretch h-full">
            <div className="flex h-full min-h-0 flex-col p-3 xl:p-4">
              {inspectorPanel}
            </div>
          </aside>
        </div>
      </main>

      <Sheet
        open={workflowSheetOpen}
        onClose={() => setWorkflowSheetOpen(false)}
        title="Workflows"
        side="left"
      >
        <div className="space-y-0.5">
          {sidebarWorkflows.map((item: any) => {
            const Icon = WORKFLOW_ICONS[item.id] || Sparkles;
            const active = workflow === item.id;
            return (
              <button
                key={item.id}
                type="button"
                title={item.title || item.label}
                onClick={() => {
                  selectWorkflow(item.id);
                  setWorkflowSheetOpen(false);
                }}
                className={`flex w-full min-w-0 items-center gap-2.5 rounded-jewel-md px-3 py-2.5 text-left text-[13px] ${
                  active
                    ? "bg-[var(--jewel-accent-soft)] text-[var(--jewel-accent)] font-semibold"
                    : "text-jewel-ink-muted hover:bg-jewel-muted font-medium"
                }`}
              >
                <Icon className="size-3.5 shrink-0" />
                <span className="min-w-0 leading-snug">{item.title || item.label}</span>
              </button>
            );
          })}
        </div>
      </Sheet>
      <Sheet
        open={inspectorSheetOpen}
        onClose={() => setInspectorSheetOpen(false)}
        title="Parameters"
        side="right"
      >
        <div className="h-[min(80vh,720px)] min-h-0">{inspectorPanel}</div>
      </Sheet>
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
