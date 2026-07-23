const fs = require('fs');
let content = fs.readFileSync('d:\\Workspace\\Jewel AI\\Jewel AI\\frontend\\src\\pages\\StudioPage.tsx', 'utf-8');
const lines = content.split('\n');
const start = 1503; // line 1504 (0-indexed)
const end = 1820; // line 1821

const inspectorJS = fs.readFileSync('C:/Users/Amir.Ali/.gemini/antigravity-ide/brain/39f18643-7986-4f00-99e8-e896fea153a7/scratch/update_inspector.js', 'utf8');
const newInspectorMatch = inspectorJS.match(/const newInspector = `([\s\S]*?)`;\n\n\/\/ Note/);
if (!newInspectorMatch) {
  console.log("Could not find newInspector string in update_inspector.js");
  process.exit(1);
}
let newInspector = newInspectorMatch[1];
newInspector = newInspector.replace(/\\\${/g, '${').replace(/\\`/g, '`');

lines.splice(start, end - start + 1, newInspector);
fs.writeFileSync('d:\\Workspace\\Jewel AI\\Jewel AI\\frontend\\src\\pages\\StudioPage.tsx', lines.join('\n'));
console.log("Replaced Right Inspector!");
