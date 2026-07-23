const fs = require('fs');
let content = fs.readFileSync('d:\\Workspace\\Jewel AI\\Jewel AI\\frontend\\src\\pages\\StudioPage.tsx', 'utf-8');
const lines = content.split('\n');

const newInspectorStr = fs.readFileSync('d:\\Workspace\\Jewel AI\\Jewel AI\\scratch\\newInspector.txt', 'utf-8');

// Find the line that starts the right inspector
let start = -1;
let end = -1;
let asideCount = 0;
for (let i = 0; i < lines.length; i++) {
    if (start === -1 && lines[i].includes('<aside className="hidden space-y-4 lg:sticky lg:top-[4.5rem] lg:block">')) {
        start = i;
        asideCount = 1;
        continue;
    }
    
    if (start !== -1) {
        if (lines[i].includes('<aside')) asideCount++;
        if (lines[i].includes('</aside>')) {
            asideCount--;
            if (asideCount === 0) {
                end = i;
                break;
            }
        }
    }
}

if (start === -1 || end === -1) {
    console.log("Could not find start/end bounds of right inspector", start, end);
    process.exit(1);
}

lines.splice(start, end - start + 1, newInspectorStr);

let newContent = lines.join('\n');
if (!newContent.includes('Settings2')) {
  newContent = newContent.replace('import {', 'import { Settings2, SlidersHorizontal, Info, Heart, History,');
}

fs.writeFileSync('d:\\Workspace\\Jewel AI\\Jewel AI\\frontend\\src\\pages\\StudioPage.tsx', newContent);
console.log("Replaced from", start, "to", end);
