const fs = require('fs');
const content = fs.readFileSync('frontend/src/pages/StudioPage.tsx', 'utf-8');

const lines = content.split('\n');

// Find line 1317 (which is index 1316)
if (lines[1316].trim() === '</div>') {
    lines.splice(1316, 1);
    // Add </div> at line 1456 (which becomes 1455 after the splice)
    lines.splice(1455, 0, '                      </div>');
    
    fs.writeFileSync('frontend/src/pages/StudioPage.tsx', lines.join('\n'));
    console.log('Fixed early close tag');
} else {
    console.log('Line 1317 is not </div>:', lines[1316]);
}
