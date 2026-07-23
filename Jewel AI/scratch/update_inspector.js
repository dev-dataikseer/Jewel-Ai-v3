const fs = require('fs');

const studioPath = 'd:\\\\Workspace\\\\Jewel AI\\\\Jewel AI\\\\frontend\\\\src\\\\pages\\\\StudioPage.tsx';
let content = fs.readFileSync(studioPath, 'utf-8');

// 1. Replace state
content = content.replace(
    'const [advancedOpen, setAdvancedOpen] = useState(false);',
    'const [inspectorTab, setInspectorTab] = useState<"settings" | "advanced">("settings");'
);

// 2. Extract specific parts of the old inspector to preserve logic
const asideStart = '{/* Parameters — desktop inspector */}';
const asideEnd = '</aside>';
const asideBlockStartIdx = content.indexOf(asideStart);
const asideBlockEndIdx = content.indexOf(asideEnd, asideBlockStartIdx) + asideEnd.length;

if (asideBlockStartIdx === -1 || content.indexOf(asideEnd, asideBlockStartIdx) === -1) {
    console.error("Could not find aside block");
    process.exit(1);
}

const oldAsideBlock = content.substring(asideBlockStartIdx, asideBlockEndIdx);

const newAsideBlock = \`{/* Parameters — desktop inspector */}
          <aside className="hidden w-[300px] shrink-0 flex-col overflow-y-auto bg-white border-l border-gray-200 lg:flex relative">
            <div className="flex items-center gap-6 px-6 pt-5 border-b border-gray-100 sticky top-0 bg-white z-10">
              <button
                type="button"
                onClick={() => setInspectorTab("settings")}
                className={\\\`text-[13px] font-semibold tracking-wide transition-all pb-3 \\\${
                  inspectorTab === "settings"
                    ? "text-[var(--jewel-accent)] border-b-[2.5px] border-[var(--jewel-accent)]"
                    : "text-gray-500 hover:text-gray-900 border-b-[2.5px] border-transparent"
                }\\\`}
              >
                Settings
              </button>
              <button
                type="button"
                onClick={() => setInspectorTab("advanced")}
                className={\\\`text-[13px] font-semibold tracking-wide transition-all pb-3 \\\${
                  inspectorTab === "advanced"
                    ? "text-[var(--jewel-accent)] border-b-[2.5px] border-[var(--jewel-accent)]"
                    : "text-gray-500 hover:text-gray-900 border-b-[2.5px] border-transparent"
                }\\\`}
              >
                Advanced
              </button>
            </div>

            <div className="p-6 flex flex-col gap-6">
              {inspectorTab === "settings" && (
                <div className="space-y-6">
                  {workflow === "VIRTUAL_TRY_ON" && (
                    <div className="space-y-2">
                      <label className="text-[12px] font-semibold uppercase tracking-wider text-gray-500">Try-On Mode</label>
                      <select
                        value={tryOnPreset}
                        onChange={(e) => setTryOnPreset(e.target.value as "studio" | "customer")}
                        className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-[13px] text-gray-900 shadow-sm focus:border-[var(--jewel-accent)] focus:outline-none focus:ring-1 focus:ring-[var(--jewel-accent)] transition-shadow"
                      >
                        <option value="studio">Studio model look</option>
                        <option value="customer">Customer photo</option>
                      </select>
                    </div>
                  )}

                  {isCatalog && (
                    <div className="space-y-2">
                      <label className="text-[12px] font-semibold uppercase tracking-wider text-gray-500">Catalog Mode</label>
                      <select
                        value={catalogMode}
                        onChange={(e) => setCatalogMode(e.target.value as "modern" | "reference_mirror" | "style_mood")}
                        className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-[13px] text-gray-900 shadow-sm focus:border-[var(--jewel-accent)] focus:outline-none focus:ring-1 focus:ring-[var(--jewel-accent)] transition-shadow"
                      >
                        <option value="modern">Modern catalog (auto environment)</option>
                        <option value="reference_mirror">Match reference environment</option>
                        <option value="style_mood">Match lighting / mood only</option>
                      </select>
                    </div>
                  )}

                  <div className="space-y-2">
                    <MultiSelectDropdown
                      label="Jewelry Type"
                      options={options?.jewelryTypes ?? ["Ring"]}
                      selectedValues={jewelryTypes}
                      onChange={setJewelryTypes}
                    />
                    {jewelryTypes.length > 1 && (
                      <p className="text-[11px] text-gray-500 leading-relaxed mt-1">
                        Applies each selected type ({jewelryTypes.join(", ")}).
                      </p>
                    )}
                  </div>

                  <div className="space-y-2">
                    <label className="text-[12px] font-semibold uppercase tracking-wider text-gray-500" htmlFor="studio-prompt">
                      Optional instructions
                    </label>
                    <textarea
                      id="studio-prompt"
                      value={promptText}
                      onChange={(e) => setPromptText(e.target.value)}
                      placeholder="Lighting, mood, sparkles…"
                      rows={3}
                      className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2.5 text-[13px] text-gray-900 shadow-sm placeholder:text-gray-400 focus:border-[var(--jewel-accent)] focus:outline-none focus:ring-1 focus:ring-[var(--jewel-accent)] transition-shadow resize-none"
                    />
                  </div>

                  <div className="h-px w-full bg-gray-100" />

                  <div className="space-y-4">
                    <div className="space-y-2">
                      <label className="text-[12px] font-semibold uppercase tracking-wider text-gray-500">Model Configuration</label>
                      
                      {showAspectRatio && (
                        <select
                          value={aspectRatio}
                          onChange={(e) => setAspectRatio(e.target.value)}
                          className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-[13px] text-gray-900 shadow-sm focus:border-[var(--jewel-accent)] focus:outline-none focus:ring-1 focus:ring-[var(--jewel-accent)] transition-shadow mb-3"
                          aria-label="Aspect ratio"
                        >
                          {(options?.aspectRatios ?? ["1:1"]).map((r) => (
                            <option key={r} value={r}>Aspect {r}</option>
                          ))}
                        </select>
                      )}

                      {showPersonGeneration && (
                        <select
                          value={personGeneration}
                          onChange={(e) => setPersonGeneration(e.target.value)}
                          className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-[13px] text-gray-900 shadow-sm focus:border-[var(--jewel-accent)] focus:outline-none focus:ring-1 focus:ring-[var(--jewel-accent)] transition-shadow mb-3"
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
                          className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-[13px] text-gray-900 shadow-sm focus:border-[var(--jewel-accent)] focus:outline-none focus:ring-1 focus:ring-[var(--jewel-accent)] transition-shadow mb-3"
                          aria-label="Number of images"
                        >
                          {[1, 2, 3, 4].map((n) => (
                            <option key={n} value={n}>{n} image{n > 1 ? "s" : ""}</option>
                          ))}
                        </select>
                      )}

                      <div className="pt-2">
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
                      </div>
                      {is4kSelected && (
                        <p className="text-[11px] text-amber-800 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2 leading-relaxed mt-2">
                          4K is slower and costs more. Prefer 1K for catalog/bulk.
                        </p>
                      )}
                    </div>
                  </div>
                </div>
              )}

              {inspectorTab === "advanced" && (
                <div className="space-y-6">
                  {isCatalog && (
                    <div className="space-y-4">
                      <div className="flex items-center justify-between gap-2">
                        <label className="text-[12px] font-semibold uppercase tracking-wider text-gray-500">Brand Kit</label>
                        {(lockedUrls.reference || lockedUrls.logo || referenceFile || logoFile) && (
                          <button
                            type="button"
                            onClick={clearBrandAssets}
                            className="text-[10px] font-semibold text-gray-400 hover:text-gray-700"
                          >
                            Clear saved
                          </button>
                        )}
                      </div>
                      
                      {(lockedUrls.reference || lockedUrls.logo) && !referenceFile && !logoFile && (
                        <p className="text-[11px] text-emerald-700 bg-emerald-50 border border-emerald-100 rounded-lg px-3 py-2">
                          Using saved theme/logo — Change anytime below.
                        </p>
                      )}

                      <UploadZone
                        id="studio-theme-ref"
                        label={isBulk ? "Theme / style (required for bulk)" : "Theme / style (optional)"}
                        error={validationErrors.referenceImage}
                        previews={themePreviewSrc ? [themePreviewSrc] : []}
                        onFiles={onReferencePick}
                        single
                        compact
                        fileName={referenceFile?.name || "Saved theme"}
                        hint={isBulk ? "Required for bulk" : "Optional · full size OK"}
                        onClear={() => {
                          setReferenceFile(null);
                          patchBrandKit({ themeAssetId: null, themeUrl: null, themeName: null });
                          setLockedUrls((u) => ({ ...u, reference: null, themeAssetId: null }));
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
                          patchBrandKit({ logoAssetId: null, logoUrl: null, logoName: null });
                          setLockedUrls((u) => ({ ...u, logo: null, logoAssetId: null }));
                        }}
                      />

                      {(hasThemeAttached || hasLogoAttached) && (
                        <p className="text-[11px] text-gray-500 leading-relaxed bg-gray-50 rounded-lg px-3 py-2 border border-gray-100">
                          Sent to the model: {plannedSlots.map((s) => s.label).join(" · ")}
                          {logoUsesComposeFallback ? " · Logo fallback: under output" : ""}
                        </p>
                      )}

                      {logoUsesComposeFallback && (
                        <p className="text-[11px] text-amber-800 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2 leading-relaxed">
                          This model only accepts a single image. Logo will be added under the output (fallback). Choose a multi-image edit model for in-frame logo placement.
                        </p>
                      )}
                    </div>
                  )}

                  {!isCatalog && (
                    <div className="space-y-4">
                      <label className="text-[12px] font-semibold uppercase tracking-wider text-gray-500">Brand Kit</label>
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
                          patchBrandKit({ logoAssetId: null, logoUrl: null, logoName: null });
                          setLockedUrls((u) => ({ ...u, logo: null, logoAssetId: null }));
                        }}
                      />
                      {logoUsesComposeFallback && (
                        <p className="text-[11px] text-amber-800 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2 leading-relaxed">
                          Logo will be added under the output for this model (fallback).
                        </p>
                      )}
                    </div>
                  )}

                  <div className="h-px w-full bg-gray-100" />

                  {(options?.lightingStyles?.length ?? 0) > 0 && (
                    <div className="space-y-2">
                      <label className="text-[12px] font-semibold uppercase tracking-wider text-gray-500">Lighting style</label>
                      <select
                        value={lightingStyle}
                        onChange={(e) => setLightingStyle(e.target.value)}
                        className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-[13px] text-gray-900 shadow-sm focus:border-[var(--jewel-accent)] focus:outline-none focus:ring-1 focus:ring-[var(--jewel-accent)] transition-shadow"
                      >
                        <option value="">Default</option>
                        {options!.lightingStyles!.map((s) => (
                          <option key={s} value={s}>{s}</option>
                        ))}
                      </select>
                    </div>
                  )}

                  {workflowVariantLabel && workflowVariants.length > 0 && (
                    <div className="space-y-2">
                      <label className="text-[12px] font-semibold uppercase tracking-wider text-gray-500">{workflowVariantLabel}</label>
                      <select
                        value={workflowVariantKey}
                        onChange={(e) => setWorkflowVariantKey(e.target.value)}
                        className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-[13px] text-gray-900 shadow-sm focus:border-[var(--jewel-accent)] focus:outline-none focus:ring-1 focus:ring-[var(--jewel-accent)] transition-shadow"
                      >
                        {workflowVariants.map((v) => (
                          <option key={v.variant_key} value={v.variant_key}>{v.label}</option>
                        ))}
                      </select>
                    </div>
                  )}

                  {stylePresets.length > 0 && (
                    <div className="space-y-2">
                      <label className="text-[12px] font-semibold uppercase tracking-wider text-gray-500">Style Preset</label>
                      <select
                        value={stylePresetId}
                        onChange={(e) => setStylePresetId(e.target.value)}
                        className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-[13px] text-gray-900 shadow-sm focus:border-[var(--jewel-accent)] focus:outline-none focus:ring-1 focus:ring-[var(--jewel-accent)] transition-shadow"
                      >
                        <option value="">None</option>
                        {stylePresets.map((p) => (
                          <option key={p.id} value={p.id}>{p.name}</option>
                        ))}
                      </select>
                    </div>
                  )}

                </div>
              )}
            </div>

            {activeJobs.length > 0 && (
              <div className="mt-auto p-4 border-t border-gray-100 bg-gray-50">
                <p className="text-[11px] text-center font-medium text-gray-500">
                  {activeJobs.length} running — queue more after upload finishes
                </p>
              </div>
            )}
          </aside>\`;

content = content.replace(oldAsideBlock, newAsideBlock);

fs.writeFileSync(studioPath, content);
console.log("Inspector updated to tabbed interface.");
