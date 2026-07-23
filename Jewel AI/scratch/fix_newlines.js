const fs = require('fs');
const studioPath = 'd:\\Workspace\\Jewel AI\\Jewel AI\\frontend\\src\\pages\\StudioPage.tsx';
let content = fs.readFileSync(studioPath, 'utf-8');

// The input section body was missing a closing div
content = content.replace(
    '                  {/* Output */}',
    '                  </div>\\n                  {/* Output */}'
);

// The output section body was missing a closing div
// In original, the output section ended with the end of the grid:
//                   </div>
//                 </div>
//               </div>
// 
//               <ActionDock

const endGridStr = \`                  </div>
                </div>
              </div>

              <ActionDock\`;

const newEndGridStr = \`                  </div>
                  </div>
                </div>
              </div>

              <ActionDock\`;

if (content.includes(endGridStr)) {
    content = content.replace(endGridStr, newEndGridStr);
} else {
    // try a looser match
    content = content.replace(
        '                </div>\\n              </div>\\n\\n              <ActionDock',
        '                  </div>\\n                </div>\\n              </div>\\n\\n              <ActionDock'
    );
}

fs.writeFileSync(studioPath, content);
console.log("Fixed missing closing divs");
