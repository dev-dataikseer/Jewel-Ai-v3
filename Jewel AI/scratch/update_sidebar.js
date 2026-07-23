const fs = require('fs');

const path = 'd:\\Workspace\\Jewel AI\\Jewel AI\\frontend\\src\\pages\\StudioPage.tsx';
let content = fs.readFileSync(path, 'utf-8');

// Add imports if missing
if (!content.includes('Heart,')) {
    content = content.replace('import {', 'import { Heart, History, CheckCircle2, Info, Crop, MoreHorizontal, UploadCloud,');
}

const mainStart = content.indexOf('<main className="mx-auto max-w-[1600px] w-full px-4 sm:px-6 lg:px-8 py-6 flex-1">');
const canvasSectionStart = content.indexOf('<section className="space-y-5 min-w-0">', mainStart);

if (mainStart === -1 || canvasSectionStart === -1) {
    console.error("Could not find boundaries for main wrapper / sidebar.");
    process.exit(1);
}

const newSidebar = `<main className="flex h-[calc(100vh-3.75rem-2rem)] w-full overflow-hidden bg-[var(--jewel-bg)]">
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
          <section className="flex-1 flex flex-col overflow-y-auto bg-[var(--jewel-bg)] relative min-w-0">`;

content = content.substring(0, mainStart) + newSidebar + content.substring(canvasSectionStart + '<section className="space-y-5 min-w-0">'.length);

fs.writeFileSync(path, content);
console.log("Successfully replaced left sidebar wrapper");
