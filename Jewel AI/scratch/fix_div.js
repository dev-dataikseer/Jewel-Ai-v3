const fs = require('fs');
let content = fs.readFileSync('frontend/src/pages/StudioPage.tsx', 'utf-8');

const target = `              </div>
            </>
          </section>`;
          
const replacement = `              </div>
            </>
            </div>
          </section>`;

if (content.includes(target)) {
    content = content.replace(target, replacement);
    fs.writeFileSync('frontend/src/pages/StudioPage.tsx', content);
    console.log("Fixed missing div successfully.");
} else {
    console.log("Could not find exact target block.");
}
