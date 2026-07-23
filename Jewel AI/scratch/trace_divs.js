const fs = require('fs');
const lines = fs.readFileSync('frontend/src/pages/StudioPage.tsx', 'utf-8').split('\n');

let depth = 0;
for (let i = 1071; i < lines.length; i++) {
    const line = lines[i];
    
    // Ignore self-closing divs
    let processedLine = line.replace(/<div[^>]*\/>/g, '');
    
    const opens = (processedLine.match(/<div/g) || []).length;
    const closes = (processedLine.match(/<\/div>/g) || []).length;
    
    depth += opens;
    depth -= closes;
    
    if (opens > 0 || closes > 0) {
        console.log(`[${i+1}] (${depth}) ${line.trim()}`);
    }
}
