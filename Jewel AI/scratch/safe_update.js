const fs = require('fs');
let content = fs.readFileSync('frontend/src/pages/StudioPage.tsx', 'utf-8');

// 1. apply_all sidebar replacement (because we reverted to very original)
const sidebarTarget = /<main className="mx-auto max-w-\[1600px\] w-full px-4 sm:px-6 lg:px-8 py-6 flex-1">[\s\S]*?<section className="space-y-5 min-w-0">/;
const sidebarReplacement = `<main className="flex h-[calc(100vh-3.75rem)] w-full overflow-hidden bg-[var(--jewel-bg)]">
        <div className="grid h-full w-full grid-cols-1 lg:grid-cols-[260px_minmax(0,1fr)_340px] divide-x divide-gray-200">
          <aside className="hidden h-full flex-col overflow-y-auto bg-[var(--jewel-bg)] lg:flex border-r border-jewel-border">
            <div className="p-4 flex flex-col h-full">
              <p className="text-[10px] font-bold uppercase tracking-wider text-jewel-ink-muted mb-2 px-3">Create</p>
              <div className="space-y-0.5 mb-8">
                {sidebarWorkflows.map((item) => {
                  const Icon = WORKFLOW_ICONS[item.id] || Sparkles;
                  const active = workflow === item.id;
                  return (
                    <button
                      key={item.id}
                      type="button"
                      onClick={() => selectWorkflow(item.id)}
                      className={\`flex w-full items-center gap-2.5 rounded-lg px-3 py-2.5 text-left text-[13px] font-medium transition-colors \${
                        active
                          ? "bg-blue-50 text-blue-700"
                          : "text-gray-600 hover:bg-gray-100/50"
                      }\`}
                    >
                      <Icon className="size-4 shrink-0" strokeWidth={active ? 2.5 : 2} />
                      <span className="leading-snug">{item.label}</span>
                    </button>
                  );
                })}
              </div>

              <p className="text-[10px] font-bold uppercase tracking-wider text-jewel-ink-muted mb-2 px-3">Library</p>
              <div className="space-y-0.5">
                <button className="flex w-full items-center gap-2.5 rounded-lg px-3 py-2.5 text-left text-[13px] font-medium text-gray-600 hover:bg-gray-100/50 transition-colors">
                  <History className="size-4 shrink-0" />
                  Recent Generations
                </button>
                <button className="flex w-full items-center gap-2.5 rounded-lg px-3 py-2.5 text-left text-[13px] font-medium text-gray-600 hover:bg-gray-100/50 transition-colors">
                  <Heart className="size-4 shrink-0" />
                  Favorites
                </button>
              </div>

              <div className="mt-auto pt-4">
                <button
                  type="button"
                  onClick={clearWorkspace}
                  className="w-full rounded-lg bg-white border border-gray-200 py-2.5 text-[12px] font-medium text-gray-700 hover:bg-gray-50 shadow-sm"
                >
                  Clear workspace {sessionJobs.length > 0 ? \` (\${sessionJobs.length})\` : ""}
                </button>
              </div>
            </div>
          </aside>

          {/* Canvas — stage zone */}
          <section className="flex h-full flex-col overflow-y-auto bg-[var(--jewel-bg)] relative">
            <div className="flex flex-col p-6 max-w-[1200px] mx-auto w-full gap-6">`;
if (content.match(sidebarTarget)) {
    content = content.replace(sidebarTarget, sidebarReplacement);
    console.log("Sidebar replaced");
} else {
    console.log("Sidebar missing");
}

// 2. Canvas Headers
const headersTarget = /<div className="min-w-0">\s*<h2 className="text-xl font-semibold text-jewel-ink flex items-center gap-2">\s*<Sparkles className="size-4 text-jewel-accent" \/>\s*\{workflowLabel\(workflow, options\)\}\s*<\/h2>[\s\S]*?<\/div>/;
const headersReplacement = `<div className="min-w-0">
                <h2 className="text-[22px] font-semibold text-gray-900 flex items-center gap-2 tracking-tight">
                  {workflowLabel(workflow, options)}
                </h2>
                {isCatalog ? (
                  <p className="text-[13px] text-gray-500 mt-1 max-w-2xl leading-relaxed">
                    Upload products to generate consistent catalog imagery. 
                    Configure lighting and themes in the parameters panel.
                  </p>
                ) : (
                  <p className="text-[13px] text-gray-500 mt-1 max-w-2xl leading-relaxed">
                    Upload items and references for high-quality single generations.
                  </p>
                )}
              </div>`;
if (content.match(headersTarget)) {
    content = content.replace(headersTarget, headersReplacement);
    console.log("Headers replaced");
} else {
    console.log("Headers missing");
}

// 3. Canvas Shell
const shellTarget = /<div className="rounded-2xl border border-slate-200 bg-white shadow-sm overflow-hidden">\s*<div className="grid grid-cols-1 lg:grid-cols-2 divide-y lg:divide-y-0 lg:divide-x divide-slate-100">/;
const shellReplacement = `<div className="relative grid grid-cols-1 lg:grid-cols-2 gap-4">
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
}

// 4. Input Shell
const inputTarget = /\{\/\* Input \*\/\}\s*<div className="p-5 min-h-\[360px\] flex flex-col min-w-0">\s*<div className="flex items-center justify-between border-b border-slate-100 pb-2 mb-3 shrink-0">\s*<span className="ui-label mb-0">Input<\/span>/;
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
                    <div className="flex-1 bg-[var(--jewel-bg)] relative flex flex-col p-4">`;
if (content.match(inputTarget)) {
    // wait, we must also replace the closing div for the old header!
    // we'll just replace the start, and then we need to remove the closing div of the old header if there is one.
    // Actually the old header closed with `</div>`. And the new header ALSO closes with `</div>` right before `flex-1`.
    // Wait, the regex `inputTarget` does NOT include the end of the header!
    // So if we replace it, we get TWO headers!
    // Let's use a better regex!
}

fs.writeFileSync('frontend/src/pages/StudioPage.tsx', content);
