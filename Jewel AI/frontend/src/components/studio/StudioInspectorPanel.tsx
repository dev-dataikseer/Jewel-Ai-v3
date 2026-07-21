import { Sparkles, Wand2 } from "lucide-react";
import { FacetMark } from "@/components/ui/FacetMark";
import { ModelSelector } from "@/components/studio/ModelSelector";
import { MultiSelectDropdown } from "@/components/ui/MultiSelectDropdown";
import { UploadZone } from "@/components/studio/UploadZone";
import { loadBrandKit } from "@/lib/brandKit";
import type { ConfigOptions, ModelDefinition, StylePreset } from "@/types";
import { workflowLabel } from "@/types";

const PROMPT_MAX = 500;

type Props = {
  tab: "settings" | "advanced";
  onTabChange: (t: "settings" | "advanced") => void;
  workflow: string;
  jewelryTypes: string[];
  onJewelryTypesChange: (v: string[]) => void;
  options: ConfigOptions | undefined;
  promptText: string;
  onPromptTextChange: (v: string) => void;
  negativePrompt: string;
  onNegativePromptChange: (v: string) => void;
  schemaHasNegative: boolean;
  apiWorkflow: string;
  inputImageCount: number;
  modelEndpointId: string;
  modelParams: Record<string, unknown>;
  onModelChange: (endpointId: string, model: ModelDefinition | null) => void;
  onParamsChange: (params: Record<string, unknown>) => void;
  isCatalog: boolean;
  tryOnPreset: "studio" | "customer";
  onTryOnPresetChange: (v: "studio" | "customer") => void;
  catalogMode: "modern" | "reference_mirror" | "style_mood";
  onCatalogModeChange: (v: "modern" | "reference_mirror" | "style_mood") => void;
  workflowVariantLabel: string | null;
  workflowVariants: { variant_key: string; label: string }[];
  workflowVariantKey: string;
  onWorkflowVariantKeyChange: (v: string) => void;
  stylePresets: StylePreset[];
  stylePresetId: string;
  onStylePresetIdChange: (v: string) => void;
  lightingStyle: string;
  onLightingStyleChange: (v: string) => void;
  showPersonGeneration: boolean;
  personGeneration: string;
  onPersonGenerationChange: (v: string) => void;
  themePreviewSrc: string;
  logoPreviewSrc: string;
  referenceFile: File | null;
  logoFile: File | null;
  onReferencePick: (files: FileList | null) => void;
  onLogoPick: (files: FileList | null) => void;
  clearBrandAssets: () => void;
  clearTheme: () => void;
  clearLogo: () => void;
  validationErrors: Record<string, string>;
  isBulk: boolean;
  lockedUrls: { reference?: string | null; logo?: string | null };
  onGenerate: () => void;
  generating: boolean;
  generateDisabled: boolean;
  generateBlockedByBatch: boolean;
  onForceBatch?: () => void;
  uploadProgress: string | null;
  bulkCount?: number;
};

function ReferencesSection(props: Props) {
  const {
    isCatalog,
    isBulk,
    themePreviewSrc,
    logoPreviewSrc,
    referenceFile,
    logoFile,
    onReferencePick,
    onLogoPick,
    clearBrandAssets,
    clearTheme,
    clearLogo,
    validationErrors,
    lockedUrls,
  } = props;

  const hasSaved =
    lockedUrls.reference || lockedUrls.logo || referenceFile || logoFile || themePreviewSrc || logoPreviewSrc;
  const kit = loadBrandKit();

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between gap-2">
        <p className="ui-section-label mb-0">References</p>
        {hasSaved ? (
          <button
            type="button"
            onClick={clearBrandAssets}
            className="text-[10px] font-semibold text-[var(--jewel-ink-muted)] hover:text-[var(--jewel-ink)]"
          >
            Clear
          </button>
        ) : null}
      </div>
      {isCatalog ? (
        <>
          <UploadZone
            id="studio-theme-ref"
            label={isBulk ? "Theme · required" : "Theme"}
            error={validationErrors.referenceImage}
            previews={themePreviewSrc ? [themePreviewSrc] : []}
            onFiles={onReferencePick}
            single
            compact
            fileName={referenceFile?.name || kit?.themeName || "Theme"}
            onClear={clearTheme}
          />
          <UploadZone
            id="studio-logo-upload"
            label="Logo"
            previews={logoPreviewSrc ? [logoPreviewSrc] : []}
            onFiles={onLogoPick}
            single
            compact
            fileName={logoFile?.name || kit?.logoName || "Logo"}
            onClear={clearLogo}
          />
        </>
      ) : (
        <UploadZone
          id="studio-logo-upload-single"
          label="Logo"
          previews={logoPreviewSrc ? [logoPreviewSrc] : []}
          onFiles={onLogoPick}
          single
          compact
          fileName={logoFile?.name || kit?.logoName || "Logo"}
          onClear={clearLogo}
        />
      )}
    </div>
  );
}

export function StudioInspectorPanel(props: Props) {
  const {
    tab,
    onTabChange,
    jewelryTypes,
    onJewelryTypesChange,
    options,
    promptText,
    onPromptTextChange,
    negativePrompt,
    onNegativePromptChange,
    schemaHasNegative,
    apiWorkflow,
    onGenerate,
    generating,
    generateDisabled,
    generateBlockedByBatch,
    onForceBatch,
    uploadProgress,
    bulkCount,
  } = props;

  return (
    <div className="flex h-full min-h-0 flex-col rounded-xl border border-[var(--jewel-border)] bg-white overflow-hidden">
      <div className="flex border-b border-[var(--jewel-border)] shrink-0">
        <button
          type="button"
          onClick={() => onTabChange("settings")}
          className={`flex-1 inline-flex items-center justify-center gap-1.5 py-3 text-[13px] font-semibold transition-colors relative ${
            tab === "settings"
              ? "text-[var(--jewel-accent)]"
              : "text-[var(--jewel-ink-muted)] hover:text-[var(--jewel-ink)]"
          }`}
        >
          <Sparkles className="size-3.5" />
          Settings
          {tab === "settings" && (
            <span
              className="absolute bottom-0 left-4 right-4 h-0.5 rounded-t"
              style={{ backgroundImage: "var(--jewel-grad-brand)" }}
            />
          )}
        </button>
        <button
          type="button"
          onClick={() => onTabChange("advanced")}
          className={`flex-1 inline-flex items-center justify-center gap-1.5 py-3 text-[13px] font-semibold transition-colors relative ${
            tab === "advanced"
              ? "text-[var(--jewel-accent)]"
              : "text-[var(--jewel-ink-muted)] hover:text-[var(--jewel-ink)]"
          }`}
        >
          Advanced
          {tab === "advanced" && (
            <span
              className="absolute bottom-0 left-4 right-4 h-0.5 rounded-t"
              style={{ backgroundImage: "var(--jewel-grad-brand)" }}
            />
          )}
        </button>
      </div>

      <div
        className="flex-1 min-h-0 overflow-y-auto overscroll-contain p-4 space-y-4"
        onWheel={(e) => e.stopPropagation()}
      >
        {tab === "settings" ? (
          <>
            <ReferencesSection {...props} />

            <MultiSelectDropdown
              label="Jewelry"
              options={[...(options?.jewelryTypes ?? ["Ring"])].sort((a, b) =>
                a.localeCompare(b),
              )}
              selectedValues={jewelryTypes}
              onChange={onJewelryTypesChange}
            />

            <WorkflowPromptControls {...props} />

            <div>
              <label className="ui-label" htmlFor="studio-prompt-ref">
                Prompt
              </label>
              <div className="relative">
                <textarea
                  id="studio-prompt-ref"
                  value={promptText}
                  onChange={(e) => onPromptTextChange(e.target.value.slice(0, PROMPT_MAX))}
                  placeholder="Studio lighting, clean catalog…"
                  rows={4}
                  className="ui-input h-auto min-h-[6rem] py-2 pb-6 resize-y"
                />
                <span className="absolute bottom-2 right-2 text-[10px] text-[var(--jewel-ink-faint)] tabular-nums">
                  {promptText.length}/{PROMPT_MAX}
                </span>
              </div>
            </div>

            {schemaHasNegative ? (
              <div>
                <label className="ui-label" htmlFor="studio-neg-prompt">
                  Negative
                </label>
                <div className="relative">
                  <textarea
                    id="studio-neg-prompt"
                    value={negativePrompt}
                    onChange={(e) =>
                      onNegativePromptChange(e.target.value.slice(0, PROMPT_MAX))
                    }
                    placeholder="blurry, watermark…"
                    rows={2}
                    className="ui-input h-auto min-h-[3.5rem] py-2 pb-6 resize-y"
                  />
                  <span className="absolute bottom-2 right-2 text-[10px] text-[var(--jewel-ink-faint)] tabular-nums">
                    {negativePrompt.length}/{PROMPT_MAX}
                  </span>
                </div>
              </div>
            ) : null}
          </>
        ) : (
          <AdvancedTab {...props} />
        )}
      </div>

      <div className="shrink-0 border-t border-[var(--jewel-border)] p-4 space-y-2">
        {uploadProgress ? (
          <p className="text-[11px] text-center text-[var(--jewel-ink-muted)]">
            {uploadProgress}
          </p>
        ) : null}
        {generateBlockedByBatch && onForceBatch ? (
          <button
            type="button"
            onClick={onForceBatch}
            className="w-full text-[11px] font-semibold text-[var(--jewel-accent)] hover:underline"
          >
            Queue anyway
          </button>
        ) : null}
        <button
          type="button"
          onClick={onGenerate}
          disabled={generateDisabled || generating}
          aria-busy={generating}
          className="ui-btn-primary w-full h-11"
        >
          {generating ? (
            <FacetMark variant="spin" size={16} className="text-white" />
          ) : (
            <Wand2 className="size-4" />
          )}
          {generating
            ? "Generating…"
            : bulkCount && bulkCount > 1
              ? `Generate ${bulkCount}`
              : "Generate"}
        </button>
        <p className="sr-only">{workflowLabel(apiWorkflow, options)}</p>
      </div>
    </div>
  );
}

function WorkflowPromptControls(props: Props) {
  const {
    isCatalog,
    tryOnPreset,
    onTryOnPresetChange,
    catalogMode,
    onCatalogModeChange,
    workflow,
    workflowVariantLabel,
    workflowVariants,
    workflowVariantKey,
    onWorkflowVariantKeyChange,
    stylePresets,
    stylePresetId,
    onStylePresetIdChange,
    lightingStyle,
    onLightingStyleChange,
    options,
    showPersonGeneration,
    personGeneration,
    onPersonGenerationChange,
  } = props;

  return (
    <div className="space-y-3">
      {workflow === "VIRTUAL_TRY_ON" ? (
        <div>
          <label className="ui-label">Try-on mode</label>
          <select
            value={tryOnPreset}
            onChange={(e) => onTryOnPresetChange(e.target.value as "studio" | "customer")}
            className="ui-input"
          >
            <option value="studio">Studio</option>
            <option value="customer">Customer</option>
          </select>
        </div>
      ) : null}

      {isCatalog ? (
        <div>
          <label className="ui-label">Catalog mode</label>
          <select
            value={catalogMode}
            onChange={(e) =>
              onCatalogModeChange(e.target.value as "modern" | "reference_mirror" | "style_mood")
            }
            className="ui-input"
          >
            <option value="modern">Modern</option>
            <option value="reference_mirror">Match reference</option>
            <option value="style_mood">Match mood</option>
          </select>
        </div>
      ) : null}

      {(options?.lightingStyles?.length ?? 0) > 0 ? (
        <div>
          <label className="ui-label">Lighting</label>
          <select
            value={lightingStyle}
            onChange={(e) => onLightingStyleChange(e.target.value)}
            className="ui-input"
          >
            <option value="">Default</option>
            {[...options!.lightingStyles!].sort((a, b) => a.localeCompare(b)).map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>
      ) : null}

      {workflowVariantLabel && workflowVariants.length > 0 ? (
        <div>
          <label className="ui-label">{workflowVariantLabel}</label>
          <select
            value={workflowVariantKey}
            onChange={(e) => onWorkflowVariantKeyChange(e.target.value)}
            className="ui-input"
          >
            {workflowVariants.map((v) => (
              <option key={v.variant_key} value={v.variant_key}>
                {v.label}
              </option>
            ))}
          </select>
        </div>
      ) : null}

      {stylePresets.length > 0 ? (
        <div>
          <label className="ui-label" htmlFor="studio-style-preset">
            Style preset
          </label>
          <select
            id="studio-style-preset"
            value={stylePresetId}
            onChange={(e) => onStylePresetIdChange(e.target.value)}
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
      ) : null}

      {showPersonGeneration ? (
        <div>
          <label className="ui-label">People</label>
          <select
            value={personGeneration}
            onChange={(e) => onPersonGenerationChange(e.target.value)}
            className="ui-input"
          >
            <option value="DONT_ALLOW">None</option>
            <option value="ALLOW_ADULT">Adults</option>
            <option value="ALLOW_ALL">All</option>
          </select>
        </div>
      ) : null}
    </div>
  );
}

/** Advanced = fal model picker + that model's real API parameters only. */
function AdvancedTab(props: Props) {
  const {
    apiWorkflow,
    inputImageCount,
    modelEndpointId,
    modelParams,
    onModelChange,
    onParamsChange,
  } = props;

  return (
    <div className="space-y-3">
      <div>
        <p className="ui-section-label">Model</p>
        <p className="mb-2 text-[11px] text-[var(--jewel-ink-muted)] leading-snug">
          Parameters change with the selected model (fal schema).
        </p>
        <ModelSelector
          workflow={apiWorkflow}
          hasInput={inputImageCount > 0}
          imageCount={inputImageCount}
          selectedEndpointId={modelEndpointId}
          modelParams={modelParams}
          onModelChange={onModelChange}
          onParamsChange={onParamsChange}
        />
      </div>
    </div>
  );
}
