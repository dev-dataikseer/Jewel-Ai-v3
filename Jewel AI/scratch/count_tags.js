const fs = require('fs');
const content = fs.readFileSync('frontend/src/pages/StudioPage.tsx', 'utf-8');

const lines = content.split('\n');

let depth = 0;
for (let i = 1120; i < 1550; i++) {
    const line = lines[i];
    if (!line) continue;
    
    let lineDepth = 0;
    
    // Count open div
    const openMatches = line.match(/<div/g);
    if (openMatches) {
        depth += openMatches.length;
        lineDepth += openMatches.length;
    }
    
    // Count close div
    const closeMatches = line.match(/<\/div/g);
    if (closeMatches) {
        depth -= closeMatches.length;
        lineDepth -= closeMatches.length;
    }
    
    if (lineDepth !== 0 || line.includes('<>') || line.includes('</>')) {
        console.log(`[${i + 1}] (${depth}) ${line.trim()}`);
    }
}
