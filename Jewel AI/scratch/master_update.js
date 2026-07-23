const fs = require('fs');

function assertAndReplace(content, target, replacement, name) {
    if (!content.includes(target)) {
        console.error(\`ERROR: Target not found for \${name}\`);
        console.error("TARGET WAS:\\n", target);
        process.exit(1);
    }
    return content.replace(target, replacement);
}

const studioPath = 'd:\\\\Workspace\\\\Jewel AI\\\\Jewel AI\\\\frontend\\\\src\\\\pages\\\\StudioPage.tsx';
let content = fs.readFileSync(studioPath, 'utf-8');

// 1. Imports
if (content.includes('import { Heart,')) {
    // skip
} else {
    // Original import
    const oldImport = 'import {\\n  BadgeCheck,\\n  ChevronDown,\\n  ChevronLeft,\\n  ChevronRight,\\n  Gem,\\n  History,\\n  ImagePlus,\\n  Images,\\n  Layers3,\\n  Menu,\\n  PanelRight,\\n  RefreshCcw,\\n  Settings,\\n  Sparkles,\\n  Wand2,\\n} from "lucide-react";';
    const newImport = 'import {\\n  BadgeCheck,\\n  ChevronDown,\\n  ChevronLeft,\\n  ChevronRight,\\n  Gem,\\n  History,\\n  ImagePlus,\\n  Images,\\n  Layers3,\\n  Menu,\\n  PanelRight,\\n  RefreshCcw,\\n  Settings,\\n  Sparkles,\\n  Wand2,\\n  Heart,\\n  CheckCircle2,\\n  Info,\\n  Crop,\\n  MoreHorizontal,\\n  UploadCloud\\n} from "lucide-react";';
    content = assertAndReplace(content, oldImport, newImport, "Imports");
}

// 2. Sidebar + Canvas Title Row
const mainStart = '<main className="mx-auto max-w-[1600px] w-full px-4 sm:px-6 lg:px-8 py-6 flex-1">';
if (!content.includes(mainStart)) {
    console.error("Could not find main element"); process.exit(1);
}
const canvasTitleEnd = '</button>\\n              </div>\\n            </div>\\n\\n            <>\\n              <div className="rounded-2xl border border-slate-200 bg-white shadow-sm overflow-hidden">';

const blockToReplace = content.substring(
    content.indexOf(mainStart),
    content.indexOf(canvasTitleEnd) + canvasTitleEnd.length
);

const newSidebarAndTitleAndShell = \`<main className="flex h-[calc(100vh-3.75rem-2rem)] w-full overflow-hidden bg-[var(--jewel-bg)]">
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
                        className={\\\`flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-[13px] font-medium transition-colors \\\${
                          active
                            ? "bg-[var(--jewel-accent-soft)] text-[var(--jewel-accent)]"
                            : "text-gray-600 hover:bg-gray-100/50"
                        }\\\`}
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
                  Clear workspace {sessionJobs.length > 0 ? \\\` (\\\${sessionJobs.length})\\\` : ""}
                </button>
              </div>

            </div>
          </aside>

          {/* Canvas — stage zone */}
          <section className="flex-1 flex flex-col overflow-y-auto bg-[var(--jewel-bg)] relative min-w-0">
            <div className="flex flex-col p-6 max-w-[1200px] mx-auto w-full gap-6">
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
            </div>

            <>
              <div className="relative grid grid-cols-1 lg:grid-cols-2 gap-4">
                {/* Compare toggle button (absolute center) */}
                <div 
                  className="hidden lg:flex absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-10 size-10 items-center justify-center rounded-full bg-white shadow-[0_2px_12px_rgba(0,0,0,0.1)] border border-gray-100 text-gray-400 hover:text-[var(--jewel-accent)] cursor-pointer transition-colors" 
                  onClick={() => setCompareMode(c => !c)}
                >
                  <ChevronLeft className="size-4 -mr-1" />
                  <ChevronRight className="size-4" />
                </div>\`;

content = content.replace(blockToReplace, newSidebarAndTitleAndShell);

// 3. Grid inner replacement (grid layout class was part of the old shell, so that's handled)
const oldGridDef = '                <div className="grid grid-cols-1 lg:grid-cols-2 divide-y lg:divide-y-0 lg:divide-x divide-slate-100">';
content = content.replace(oldGridDef, ''); // We replaced it inside the shell block above, wait, canvasTitleEnd actually INCLUDED the old shell start, but NOT the inner grid!
// Let me verify canvasTitleEnd. It ends with: <div className="rounded-2xl border border-slate-200 bg-white shadow-sm overflow-hidden">
// The next line in original is:                 <div className="grid grid-cols-1 lg:grid-cols-2 divide-y lg:divide-y-0 lg:divide-x divide-slate-100">
// We MUST replace that line with nothing!
content = assertAndReplace(content, oldGridDef, '', "Old Grid Def");

// 4. Input Replacement
const inputOld = \`                  {/* Input */}
                  <div className="p-5 min-h-[360px] flex flex-col min-w-0">
                    <div className="flex items-center justify-between border-b border-slate-100 pb-2 mb-3 shrink-0">
                      <span className="ui-label mb-0">Input</span>
                      {activeJob && (
                        <button
                          type="button"
                          onClick={() => setActiveJobId(null)}
                          className="text-xs font-semibold text-blue-600 hover:underline"
                        >
                          Edit inputs / New
                        </button>
                      )}
                    </div>\`;
const inputNew = \`                  {/* Input Card */}
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
                    <div className="flex-1 bg-[var(--jewel-bg)] relative flex flex-col p-4">\`;
content = assertAndReplace(content, inputOld, inputNew, "Input Old");

// 5. Output Replacement
// IMPORTANT: We need to CLOSE the new input div body BEFORE opening the output.
const outputOld = \`                  {/* Output */}
                  <div className="p-5 min-h-[360px] flex flex-col bg-slate-50/30">
                    <div className="flex items-center justify-between border-b border-slate-100 pb-2 mb-3">
                      <div className="flex items-center gap-2 min-w-0">
                        <span className="ui-label mb-0">Output</span>
                        {batchJobIds.length > 1 && batchJobIndex >= 0 && (
                          <span className="text-[10px] font-semibold tabular-nums text-slate-500">
                            Job {batchJobIndex + 1}/{batchJobIds.length}
                          </span>
                        )}
                      </div>\`;
const outputNew = \`                  </div>
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
                    <div className="flex-1 bg-[var(--jewel-bg)] relative flex flex-col p-4">\`;
content = assertAndReplace(content, outputOld, outputNew, "Output Old");

// 6. Section Close
// We replaced the wrapper of the grid:
// Original ends grid with:
//                   </div>
//                 </div>
//               </div>
// 
//               <ActionDock
// Let's replace the grid ending to also include the closing of the new output div.
const endGridOld = \`                  </div>
                </div>
              </div>

              <ActionDock\`;
const endGridNew = \`                  </div>
                </div>
              </div>

              <ActionDock\`;
content = assertAndReplace(content, endGridOld, endGridNew, "End Grid Old");

// AND we added a wrapper for the section: `<div className="flex flex-col p-6 max-w-[1200px] mx-auto w-full gap-6">`
// So we must close it before </section>.
const sectionCloseOld = \`            </>
          </section>\`;
const sectionCloseNew = \`            </>
            </div>
          </section>\`;
content = assertAndReplace(content, sectionCloseOld, sectionCloseNew, "Section Close");

fs.writeFileSync(studioPath, content);
console.log("Master layout updated successfully");

// 7. ResultsTray.tsx
const rtPath = 'd:\\\\Workspace\\\\Jewel AI\\\\Jewel AI\\\\frontend\\\\src\\\\components\\\\ui\\\\ResultsTray.tsx';
if (fs.existsSync(rtPath)) {
    let rt = fs.readFileSync(rtPath, 'utf-8');
    if (!rt.includes('onShare?: () => Promise<void>;')) {
        rt = rt.replace('mediaUrl: (url?: string) => string;', 'mediaUrl: (url?: string) => string;\\n  onShare?: () => Promise<void>;');
        rt = rt.replace('mediaUrl,\\n}: ResultsTrayProps', 'mediaUrl,\\n  onShare,\\n}: ResultsTrayProps');
        fs.writeFileSync(rtPath, rt);
        console.log("ResultsTray props updated");
    }
}
