const fs = require('fs');

let content = fs.readFileSync('frontend/src/pages/StudioPage.tsx', 'utf-8');

const sidebarTarget = `<main className="mx-auto max-w-[1600px] w-full px-4 sm:px-6 lg:px-8 py-6 flex-1">
        <div className="grid grid-cols-1 gap-5 items-start lg:grid-cols-[240px_minmax(0,1fr)_300px]">
          {/* Sidebar */}
          <aside className="hidden space-y-3 lg:sticky lg:top-[4.5rem] lg:block">
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
                    className={\`flex w-full items-center gap-2.5 rounded-jewel-md px-3 py-2.5 text-left text-[13px] transition-colors \${
                      active
                        ? "bg-jewel-accent text-white font-semibold"
                        : "text-jewel-ink-muted hover:bg-jewel-muted font-medium"
                    }\`}
                  >
                    <Icon className="size-3.5 shrink-0 opacity-90" />
                    <span className="leading-snug">{item.label}</span>
                  </button>
                );
              })}
            </div>
            <button
              type="button"
              onClick={clearWorkspace}
              className="w-full px-1 text-left text-[11px] font-semibold text-jewel-ink-muted hover:text-jewel-ink"
            >
              Clear workspace
              {sessionJobs.length > 0 ? \` · \${sessionJobs.length} jobs\` : ""}
              {activeJobs.length > 0 ? \` · \${activeJobs.length} active\` : ""}
            </button>
          </aside>

          {/* Canvas */}
          <section className="space-y-5 min-w-0">`;

console.log("Found sidebarTarget?", content.includes(sidebarTarget));
