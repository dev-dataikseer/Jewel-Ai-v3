const fs = require('fs');
const code = fs.readFileSync('d:\\\\Workspace\\\\Jewel AI\\\\Jewel AI\\\\frontend\\\\src\\\\pages\\\\StudioPage.tsx', 'utf-8');

const lines = code.split('\\n');
let divCount = 0;
for(let i=1126; i<1533; i++) {
    const line = lines[i];
    const opens = (line.match(/<div/g) || []).length;
    const closes = (line.match(/<\\/div>/g) || []).length;
    divCount += opens - closes;
}
console.log('Div balance between 1127 and 1533:', divCount);
