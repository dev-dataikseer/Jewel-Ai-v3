const fs = require('fs');
const studioPath = 'd:\\Workspace\\Jewel AI\\Jewel AI\\frontend\\src\\pages\\StudioPage.tsx';
let content = fs.readFileSync(studioPath, 'utf-8');

// Remove from 'react' import if they are there
content = content.replace(
    'import { Heart, History, CheckCircle2, Info, Crop, MoreHorizontal, UploadCloud,',
    'import {'
);

// Add to lucide-react
const match = content.match(/import \{([^}]+)\} from "lucide-react";/);
if (match) {
    let imports = match[1];
    const newIcons = ['Heart', 'CheckCircle2', 'Info', 'Crop', 'MoreHorizontal', 'UploadCloud'];
    for (const icon of newIcons) {
        if (!imports.includes(icon)) {
            imports += `, ${icon}`;
        }
    }
    content = content.replace(match[0], 'import {' + imports + '} from "lucide-react";');
}

// History is already in lucide-react import in original StudioPage.tsx. Wait! The previous error said Duplicate identifier 'History'.
// So I don't need to add History.

fs.writeFileSync(studioPath, content);
console.log("Fixed StudioPage imports");

// Add onShare to ResultsTrayProps
const rtPath = 'd:\\Workspace\\Jewel AI\\Jewel AI\\frontend\\src\\components\\ui\\ResultsTray.tsx';
if (fs.existsSync(rtPath)) {
    let rt = fs.readFileSync(rtPath, 'utf-8');
    if (!rt.includes('onShare?: () => Promise<void>;') && !rt.includes('onShare?: () => void;')) {
        rt = rt.replace('mediaUrl: (url?: string) => string;', 'mediaUrl: (url?: string) => string;\\n  onShare?: () => Promise<void>;');
        // also add to props destructuring
        rt = rt.replace('mediaUrl,\\n}: ResultsTrayProps', 'mediaUrl,\\n  onShare,\\n}: ResultsTrayProps');
        
        // Add the button if it's not there, actually if it's there we just bind it.
        // Wait, did I add onShare to StudioPage or was it always there?
        // Phase 1 had onShare added!
        
        fs.writeFileSync(rtPath, rt);
        console.log("Fixed ResultsTray onShare");
    }
}

// Fix AppLayout.tsx LogOut
const appLayoutPath = 'd:\\Workspace\\Jewel AI\\Jewel AI\\frontend\\src\\components\\AppLayout.tsx';
if (fs.existsSync(appLayoutPath)) {
    let appContent = fs.readFileSync(appLayoutPath, 'utf-8');
    appContent = appContent.replace('LogOut, ', '');
    appContent = appContent.replace(', LogOut', '');
    fs.writeFileSync(appLayoutPath, appContent);
}

// Fix ProductUploadGallery.tsx ImagePlus, label
const pugPath = 'd:\\Workspace\\Jewel AI\\Jewel AI\\frontend\\src\\components\\studio\\ProductUploadGallery.tsx';
if (fs.existsSync(pugPath)) {
    let pugContent = fs.readFileSync(pugPath, 'utf-8');
    pugContent = pugContent.replace('ImagePlus, ', '');
    pugContent = pugContent.replace(', ImagePlus', '');
    pugContent = pugContent.replace('id, label, files', 'id, files');
    pugContent = pugContent.replace('label: string;', '');
    fs.writeFileSync(pugPath, pugContent);
}
