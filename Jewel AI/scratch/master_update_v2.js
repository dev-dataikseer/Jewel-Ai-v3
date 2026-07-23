const fs = require('fs');
let content = fs.readFileSync('frontend/src/pages/StudioPage.tsx', 'utf-8');

// 1. canvas shell
const regexCanvasShell = /<div className="rounded-2xl border border-slate-200 bg-white shadow-sm overflow-hidden">\s*<div className="grid grid-cols-1 lg:grid-cols-2 divide-y lg:divide-y-0 lg:divide-x divide-slate-100">/;
const newCanvasShell = `<div className="relative grid grid-cols-1 lg:grid-cols-2 gap-4">
                {/* Compare toggle button */}
                <div 
                  className="hidden lg:flex absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-10 size-10 items-center justify-center rounded-full bg-white shadow-[0_2px_12px_rgba(0,0,0,0.1)] border border-gray-100 text-gray-400 hover:text-[var(--jewel-accent)] cursor-pointer transition-colors" 
                  onClick={() => setCompareMode(c => !c)}
                >
                  <ChevronLeft className="size-4 -mr-1" />
                  <ChevronRight className="size-4" />
                </div>`;
content = content.replace(regexCanvasShell, newCanvasShell);

// 2. Input
const regexInput = /\{\/\* Input \*\/\}\s*<div className="p-5 min-h-\[360px\] flex flex-col min-w-0">\s*<div className="flex items-center justify-between border-b border-slate-100 pb-2 mb-3 shrink-0">[\s\S]*?<\/div>/;
const newInput = `{/* Input Card */}
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
content = content.replace(regexInput, newInput);

// 3. Output
const regexOutput = /\{\/\* Output \*\/\}\s*<div className="p-5 min-h-\[360px\] flex flex-col bg-slate-50\/30">\s*<div className="flex items-center justify-between border-b border-slate-100 pb-2 mb-3">[\s\S]*?<\/div>\s*<\/div>\s*<div className="flex items-center gap-1">[\s\S]*?<\/div>\s*<\/div>/;

// Actually let's just find the exact boundary using split or string replace with flexible whitespace.
// A simpler way:
// Since I know exactly what needs to be replaced, I'll just do it manually through multi_replace or custom script.
fs.writeFileSync('frontend/src/pages/StudioPage.tsx', content);
