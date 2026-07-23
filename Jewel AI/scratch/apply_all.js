const fs = require('fs');

let content = fs.readFileSync('d:\\Workspace\\Jewel AI\\Jewel AI\\frontend\\src\\pages\\StudioPage.tsx', 'utf-8');

// 1. UPDATE SIDEBAR AND WRAPPER
const oldSidebarStart = content.indexOf('<main className="mx-auto max-w-[1600px] w-full px-4 sm:px-6 lg:px-8 py-6 flex-1">');
if (oldSidebarStart === -1) {
    console.log("Could not find sidebar start!");
    process.exit(1);
}

let currentIdx = oldSidebarStart;
let sectionCount = 0;
while (currentIdx < content.length) {
    if (content.substring(currentIdx, currentIdx + 8) === '<section') sectionCount++;
    if (content.substring(currentIdx, currentIdx + 9) === '</section') {
        sectionCount--;
    }
    // We just want to replace up to the start of the `<section` tag for the canvas.
    // Wait, let's just use string replace.
    currentIdx++;
}

// Actually, let's just do exact string replacements!
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

if (content.indexOf(sidebarTarget) === -1) {
    console.log("Could not find exact sidebar target!");
    process.exit(1);
}
content = content.replace(sidebarTarget, sidebarReplacement);

// 2. CANVAS HEADERS
const headersTarget = `              <div className="min-w-0">
              <h2 className="text-xl font-semibold text-jewel-ink flex items-center gap-2">
                <Sparkles className="size-4 text-jewel-accent" />
                {workflowLabel(workflow, options)}
              </h2>
              {isCatalog && (
                <p className="text-sm text-slate-500 mt-1.5 max-w-2xl leading-relaxed">
                  Multi-upload for bulk catalog. Theme is required for bulk; optional for
                  single. Upload full-size images as-is — theme and logo stay in your brand
                  kit across visits.
                </p>
              )}
              {!isCatalog && (
                <p className="text-sm text-slate-500 mt-1.5 max-w-2xl leading-relaxed">
                  Multi-select products for bulk. Shared reference/portrait applies to every item.
                  Regenerate keeps this workspace — you do not need a new session.
                </p>
              )}
              </div>
            </div>`;

const headersReplacement = `              <div className="min-w-0">
                <h2 className="text-[22px] font-semibold text-gray-900 flex items-center gap-2 tracking-tight">
                  {workflowLabel(workflow, options)}
                </h2>
                {isCatalog && (
                  <p className="text-[13px] text-gray-500 mt-1 max-w-2xl leading-relaxed">
                    Upload products to generate consistent catalog imagery. 
                    Configure lighting and themes in the parameters panel.
                  </p>
                )}
                {!isCatalog && (
                  <p className="text-[13px] text-gray-500 mt-1 max-w-2xl leading-relaxed">
                    Upload items and references for high-quality single generations.
                  </p>
                )}
              </div>
            </div>`;

if (content.indexOf(headersTarget) === -1) {
    console.log("Could not find exact headers target!");
    process.exit(1);
}
content = content.replace(headersTarget, headersReplacement);

// 3. CANVAS END / RIGHT INSPECTOR
const inspectorJS = fs.readFileSync('C:/Users/Amir.Ali/.gemini/antigravity-ide/brain/39f18643-7986-4f00-99e8-e896fea153a7/scratch/update_inspector.js', 'utf8');
const newInspectorMatch = inspectorJS.match(/const newInspector = \`([\s\S]*?)\`;\n\n\/\/ Note/);
let newInspector = newInspectorMatch[1];
newInspector = newInspector.replace(/\\\${/g, '${').replace(/\\`/g, '\`');

const oldInspectorStart = content.indexOf('<aside className="hidden space-y-4 lg:sticky lg:top-[4.5rem] lg:block">');
if (oldInspectorStart === -1) {
    console.log("Could not find old inspector start!");
    process.exit(1);
}

let asideCount = 0;
let idx = oldInspectorStart;
let oldInspectorEnd = -1;
while (idx < content.length) {
    if (content.substring(idx, idx + 6) === '<aside') asideCount++;
    if (content.substring(idx, idx + 7) === '</aside') {
        asideCount--;
        if (asideCount === 0) {
            oldInspectorEnd = idx + 8; // length of </aside>
            break;
        }
    }
    idx++;
}

// Before we replace the inspector, we MUST add the closing div for the canvas that we opened in step 1!
// Wait! Step 1 opened `<div className="flex flex-col p-6 max-w-[1200px] mx-auto w-full gap-6">`
// Where does it close? Right before `</section>`!
// Let's find `</section>` which is right before `oldInspectorStart`.
const sectionEndTarget = `            </>
          </section>`;
const sectionEndReplacement = `            </>
            </div>
          </section>`;
content = content.replace(sectionEndTarget, sectionEndReplacement);

// Now replace the inspector
content = content.substring(0, oldInspectorStart) + newInspector + content.substring(oldInspectorEnd);

// Fix imports
if (!content.includes('Settings2')) {
  content = content.replace('import {', 'import { Settings2, SlidersHorizontal, Info, Heart, History,');
}

fs.writeFileSync('d:\\Workspace\\Jewel AI\\Jewel AI\\frontend\\src\\pages\\StudioPage.tsx', content);
console.log("SUCCESS!");
