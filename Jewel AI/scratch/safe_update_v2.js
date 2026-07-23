const fs = require('fs');
let content = fs.readFileSync('frontend/src/pages/StudioPage.tsx', 'utf-8');

// 1. apply_all sidebar replacement (because we reverted to very original)
const sidebarTarget = \`<main className="mx-auto max-w-[1600px] w-full px-4 sm:px-6 lg:px-8 py-6 flex-1">\`;
const oldSidebarEnd = \`<section className="space-y-5 min-w-0">\`;

const mainStart = content.indexOf(sidebarTarget);
const sectionEnd = content.indexOf(oldSidebarEnd);

if (mainStart !== -1 && sectionEnd !== -1) {
    const oldSidebar = content.substring(mainStart, sectionEnd + oldSidebarEnd.length);
    const sidebarReplacement = \`<main className="flex h-[calc(100vh-3.75rem)] w-full overflow-hidden bg-[var(--jewel-bg)]">
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
            <div className="flex flex-col p-6 max-w-[1200px] mx-auto w-full gap-6">\`;
    content = content.replace(oldSidebar, sidebarReplacement);
    console.log("Sidebar replaced");
} else {
    console.log("Sidebar missing");
}

// 2. Canvas Headers
const headersStart = \`<div className="min-w-0">\`;
const headersEnd = \`</div>
              <div className="flex shrink-0 gap-1 lg:hidden">\`;

const hStart = content.indexOf(headersStart);
const hEnd = content.indexOf(headersEnd);
if (hStart !== -1 && hEnd !== -1) {
    const oldHeaders = content.substring(hStart, hEnd + headersStart.length); // wait, + headersStart.length? No.
    // just use replace with string
}

// Easier way: Since we reverted to original, let's just use replace_file_content!
