const fs = require('fs');
const path = 'd:\\Workspace\\Jewel AI\\Jewel AI\\frontend\\src\\pages\\StudioPage.tsx';

let content = fs.readFileSync(path, 'utf-8');

// 1. Sidebar and Header
const sidebarTarget = /<main className="mx-auto max-w-\[1600px\] w-full px-4 sm:px-6 lg:px-8 py-6 flex-1">[\s\S]*?<div className="flex shrink-0 gap-1 lg:hidden">\s*<button\s*type="button"\s*className="ui-btn-secondary"\s*onClick=\{[^}]*\}\s*aria-label="Open workflows"\s*>\s*<Menu className="size-3\.5" \/>\s*Workflow\s*<\/button>\s*<button\s*type="button"\s*className="ui-btn-secondary"\s*onClick=\{[^}]*\}\s*aria-label="Open parameters"\s*>\s*<PanelRight className="size-3\.5" \/>\s*Params\s*<\/button>\s*<\/div>\s*<\/div>/;

const sidebarReplacement = `<main className="flex h-[calc(100vh-3.75rem)] w-full overflow-hidden bg-[var(--jewel-bg)]">
        <div className="flex h-full w-full divide-x divide-gray-200">
          {/* Left Sidebar */}
          <aside className="hidden w-[260px] shrink-0 flex-col overflow-y-auto bg-[var(--jewel-bg)] lg:flex">
            <div className="p-4 flex flex-col h-full gap-6">
              
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-[0.05em] text-gray-500 mb-2 px-3">Create</p>
                <div className="space-y-0.5">
                  {sidebarWorkflows.map((item) => {
                    const Icon = WORKFLOW_ICONS[item.id] || Sparkles;
                    const active = workflow === item.id;
                    return (
                      <button
                        key={item.id}
                        type="button"
                        onClick={() => selectWorkflow(item.id)}
                        className={\`flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-[13px] font-medium transition-colors \${
                          active
                            ? "bg-[var(--jewel-accent-soft)] text-[var(--jewel-accent)]"
                            : "text-gray-600 hover:bg-gray-100/50"
                        }\`}
                      >
                        <Icon className="size-4 shrink-0" strokeWidth={active ? 2.5 : 2} />
                        <span className="leading-snug">{item.label}</span>
                      </button>
                    );
                  })}
                </div>
              </div>

              <div className="h-px w-full bg-gray-200" />

              <div>
                <p className="text-[11px] font-semibold uppercase tracking-[0.05em] text-gray-500 mb-2 px-3">Library</p>
                <div className="space-y-0.5">
                  <button className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-[13px] font-medium text-gray-600 hover:bg-gray-100/50 transition-colors">
                    <History className="size-4 shrink-0" strokeWidth={2} />
                    Recent Generations
                  </button>
                  <button className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-[13px] font-medium text-gray-600 hover:bg-gray-100/50 transition-colors">
                    <Heart className="size-4 shrink-0" strokeWidth={2} />
                    Favorites
                  </button>
                </div>
              </div>

              <div className="mt-auto pt-4">
                <button
                  type="button"
                  onClick={clearWorkspace}
                  className="w-full px-3 py-2 text-left text-[12px] font-semibold text-gray-500 hover:text-gray-900 transition-colors"
                >
                  Clear workspace {sessionJobs.length > 0 ? \` (\${sessionJobs.length})\` : ""}
                </button>
              </div>

            </div>
          </aside>

          {/* Canvas — stage zone */}
          <section className="flex-1 flex flex-col overflow-y-auto bg-[var(--jewel-bg)] relative min-w-0">
            <div className="flex flex-col p-6 max-w-[1200px] mx-auto w-full gap-6 flex-1">
            <div className="flex items-start justify-between gap-4">
              <div className="min-w-0">
                <div className="flex items-center gap-3">
                  <Sparkles className="size-5 text-[var(--jewel-accent)]" />
                  <h2 className="text-[22px] font-bold text-gray-900 tracking-tight">
                    {workflowLabel(workflow, options)}
                  </h2>
                  <span className="rounded-full bg-[var(--jewel-accent-soft)] px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider text-[var(--jewel-accent)]">Pro</span>
                </div>
                {isCatalog ? (
                  <p className="text-[13px] text-gray-500 mt-2 max-w-2xl leading-relaxed">
                    Upload products to generate consistent catalog imagery. 
                    Configure lighting and themes in the parameters panel.
                  </p>
                ) : (
                  <p className="text-[13px] text-gray-500 mt-2 max-w-2xl leading-relaxed">
                    Upload items and references for high-quality single generations.
                  </p>
                )}
              </div>
              <div className="flex shrink-0 gap-2">
                <button type="button" className="hidden lg:flex items-center justify-center h-9 px-4 rounded-lg border border-gray-200 text-[13px] font-medium text-gray-700 hover:bg-gray-50 transition-colors">
                  <Sparkles className="size-4 mr-2 text-gray-400" />
                  Presets
                </button>
                <button type="button" className="hidden lg:flex items-center justify-center h-9 px-4 rounded-lg bg-[image:var(--jewel-grad-cta)] text-[13px] font-medium text-white shadow-[0_2px_8px_rgba(236,72,153,0.25)] hover:shadow-[0_4px_12px_rgba(236,72,153,0.35)] transition-all">
                  <UploadCloud className="size-4 mr-2" />
                  Upload New
                </button>
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
            </div>`;
if (content.match(sidebarTarget)) {
    content = content.replace(sidebarTarget, sidebarReplacement);
    console.log("Sidebar and header replaced");
} else {
    console.log("Sidebar missing");
}

// 2. Canvas Shell
const shellTarget = /<div className="rounded-2xl border border-slate-200 bg-white shadow-sm overflow-hidden">\s*<div className="grid grid-cols-1 lg:grid-cols-2 divide-y lg:divide-y-0 lg:divide-x divide-slate-100">/;
const shellReplacement = `<div className="relative grid grid-cols-1 lg:grid-cols-2 gap-4 flex-1">
                {/* Compare toggle button */}
                <div 
                  className="hidden lg:flex absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-10 size-10 items-center justify-center rounded-full bg-white shadow-[0_2px_12px_rgba(0,0,0,0.1)] border border-gray-100 text-gray-400 hover:text-[var(--jewel-accent)] cursor-pointer transition-colors" 
                  onClick={() => setCompareMode(c => !c)}
                >
                  <ChevronLeft className="size-4 -mr-1" />
                  <ChevronRight className="size-4" />
                </div>`;
if (content.match(shellTarget)) {
    content = content.replace(shellTarget, shellReplacement);
    console.log("Shell replaced");
} else {
    console.log("Shell missing");
}

// 3. Input 
const inputTarget = /\{\/\* Input \*\/\}\s*<div className="p-5 min-h-\[360px\] flex flex-col min-w-0">\s*<div className="flex items-center justify-between border-b border-slate-100 pb-2 mb-3 shrink-0">\s*<span className="ui-label mb-0">Input<\/span>\s*\{activeJob && \(\s*<button\s*type="button"\s*onClick=\{[^}]*\}\s*className="text-xs font-semibold text-blue-600 hover:underline"\s*>\s*Edit inputs \/ New\s*<\/button>\s*\)\}\s*<\/div>/;
const inputReplacement = `{/* Input Card */}
                  <div className="flex flex-col bg-white rounded-xl border border-gray-200 overflow-hidden min-h-[400px]">
                    <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100 bg-white shrink-0">
                      <div className="flex items-center gap-2">
                        <span className="text-[11px] font-bold uppercase tracking-wider text-gray-900">INPUT IMAGE</span>
                        <Info className="size-3.5 text-gray-400" />
                      </div>
                      <div className="flex items-center gap-1">
                        <button className="p-1.5 text-gray-400 hover:bg-gray-50 rounded">
                          <Crop className="size-4" />
                        </button>
                        <button className="p-1.5 text-gray-400 hover:bg-gray-50 rounded">
                          <MoreHorizontal className="size-4" />
                        </button>
                      </div>
                    </div>
                    <div className="flex-1 bg-[var(--jewel-bg)] relative flex flex-col p-4">
                      {activeJob && (
                        <div className="mb-3 flex justify-end">
                          <button
                            type="button"
                            onClick={() => setActiveJobId(null)}
                            className="text-[11px] font-semibold text-[var(--jewel-accent)] hover:underline"
                          >
                            Edit inputs / New
                          </button>
                        </div>
                      )}`;
if (content.match(inputTarget)) {
    content = content.replace(inputTarget, inputReplacement);
    console.log("Input replaced");
} else {
    console.log("Input missing");
}

// 4. Output
const outputTarget = /\{\/\* Output \*\/\}\s*<div className="p-5 min-h-\[360px\] flex flex-col bg-slate-50\/30">\s*<div className="flex items-center justify-between border-b border-slate-100 pb-2 mb-3">\s*<div className="flex items-center gap-2 min-w-0">\s*<span className="ui-label mb-0">Output<\/span>\s*\{batchJobIds\.length > 1 && batchJobIndex >= 0 && \(\s*<span className="text-\[10px\] font-semibold tabular-nums text-slate-500">\s*Job \{batchJobIndex \+ 1\}\/\{batchJobIds\.length\}\s*<\/span>\s*\)\}\s*<\/div>/;
const outputReplacement = `</div>
                  {/* Generated Card */}
                  <div className="flex flex-col bg-white rounded-xl border border-gray-200 overflow-hidden min-h-[400px]">
                    <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100 bg-white shrink-0">
                      <div className="flex items-center gap-2">
                        <span className="text-[11px] font-bold uppercase tracking-wider text-gray-900">GENERATED IMAGE</span>
                        <Info className="size-3.5 text-gray-400" />
                      </div>
                      {activeJob?.status === "COMPLETED" ? (
                        <span className="flex items-center gap-1.5 rounded-full bg-emerald-50 px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider text-emerald-700">
                          <Sparkles className="size-3 text-emerald-500" />
                          Completed
                        </span>
                      ) : (
                        batchJobIds.length > 1 && batchJobIndex >= 0 && (
                          <span className="text-[10px] font-bold uppercase tracking-wider text-gray-500">
                            Job {batchJobIndex + 1}/{batchJobIds.length}
                          </span>
                        )
                      )}
                    </div>
                    <div className="flex-1 bg-[var(--jewel-bg)] relative flex flex-col p-4">`;
if (content.match(outputTarget)) {
    content = content.replace(outputTarget, outputReplacement);
    console.log("Output replaced");
} else {
    console.log("Output missing");
}

// 5. Canvas Wrapper Closure
const canvasClosureTarget = /<\/div>\s*<\/div>\s*<\/div>\s*<ActionDock/;
const canvasClosureReplacement = `</div>
                </div>
              </div>
            </div>
              <ActionDock`;
// wait, the above closures are `</div>` 3 times before ActionDock.
// I just need to add ONE `</div>` right before `</>`
const endTarget = /<\/div>\s*<\/>\s*<\/section>/;
const endReplacement = `</div>
            </>
            </div>
          </section>`;
if (content.match(endTarget)) {
    content = content.replace(endTarget, endReplacement);
    console.log("End replaced");
} else {
    console.log("End missing");
}

fs.writeFileSync(path, content);
