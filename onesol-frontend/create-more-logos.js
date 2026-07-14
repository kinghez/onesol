const fs = require('fs');
const path = require('path');

const outDir = path.join(__dirname, 'assets', 'images', 'logos');
if (!fs.existsSync(outDir)) fs.mkdirSync(outDir, { recursive: true });

const svgs = {
    copyai: `<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <linearGradient id="copyGrad" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stop-color="#8D63FF" stop-opacity="0.2"/>
          <stop offset="100%" stop-color="#6848FF" stop-opacity="0.05"/>
        </linearGradient>
      </defs>
      <rect x="5" y="5" width="90" height="90" rx="20" fill="url(#copyGrad)" stroke="#8D63FF" stroke-width="2" stroke-opacity="0.3"/>
      <text x="50" y="54" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif" font-weight="700" font-size="20" fill="#FFFFFF" text-anchor="middle" dominant-baseline="middle">copy.ai</text>
    </svg>`,

    jasper: `<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <linearGradient id="jasperGrad" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stop-color="#6848FF"/>
          <stop offset="50%" stop-color="#8D63FF"/>
          <stop offset="100%" stop-color="#00C4CC"/>
        </linearGradient>
      </defs>
      <path d="M25 65 C10 65, 10 35, 30 25 C40 15, 60 15, 70 25 C90 35, 90 65, 75 65" fill="none" stroke="url(#jasperGrad)" stroke-width="14" stroke-linecap="round"/>
      <path d="M40 75 Q50 85, 60 75" fill="none" stroke="#FFFFFF" stroke-width="6" stroke-linecap="round"/>
      <circle cx="35" cy="50" r="4" fill="#FFFFFF"/>
      <circle cx="65" cy="50" r="4" fill="#FFFFFF"/>
    </svg>`,

    suno: `<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <linearGradient id="sunoGrad" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stop-color="#F4C84B"/>
          <stop offset="100%" stop-color="#E7A93B"/>
        </linearGradient>
      </defs>
      <path d="M45 45 Q35 25, 25 35 Q15 45, 25 55 L35 55 L35 65 C35 75, 25 75, 25 75" fill="none" stroke="url(#sunoGrad)" stroke-width="10" stroke-linecap="round"/>
      <circle cx="20" cy="75" r="5" fill="url(#sunoGrad)"/>
      <text x="45" y="60" font-family="Arial, sans-serif" font-weight="bold" font-size="28" fill="url(#sunoGrad)">Suno</text>
    </svg>`,

    pictory: `<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <radialGradient id="pictoryGrad" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stop-color="#A855F7"/>
          <stop offset="100%" stop-color="#6B21A8"/>
        </radialGradient>
      </defs>
      <circle cx="50" cy="45" r="25" fill="url(#pictoryGrad)"/>
      <circle cx="40" cy="40" r="4" fill="#000"/>
      <circle cx="60" cy="40" r="4" fill="#000"/>
      <path d="M45 50 Q50 55, 55 50" fill="none" stroke="#000" stroke-width="3" stroke-linecap="round"/>
      <path d="M25 65 Q35 85, 45 65" fill="none" stroke="url(#pictoryGrad)" stroke-width="8" stroke-linecap="round"/>
      <path d="M40 68 Q50 90, 60 68" fill="none" stroke="url(#pictoryGrad)" stroke-width="8" stroke-linecap="round"/>
      <path d="M55 65 Q65 85, 75 65" fill="none" stroke="url(#pictoryGrad)" stroke-width="8" stroke-linecap="round"/>
      <path d="M15 50 Q20 70, 30 60" fill="none" stroke="url(#pictoryGrad)" stroke-width="8" stroke-linecap="round"/>
      <path d="M85 50 Q80 70, 70 60" fill="none" stroke="url(#pictoryGrad)" stroke-width="8" stroke-linecap="round"/>
    </svg>`,

    descript: `<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <linearGradient id="descGrad" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stop-color="#60A5FA"/>
          <stop offset="100%" stop-color="#2563EB"/>
        </linearGradient>
      </defs>
      <rect x="25" y="20" width="35" height="12" rx="6" fill="url(#descGrad)"/>
      <rect x="25" y="44" width="50" height="12" rx="6" fill="url(#descGrad)"/>
      <rect x="25" y="68" width="35" height="12" rx="6" fill="url(#descGrad)"/>
      
      <rect x="68" y="20" width="12" height="12" rx="6" fill="url(#descGrad)"/>
      <rect x="80" y="44" width="12" height="12" rx="6" fill="url(#descGrad)"/>
      <rect x="68" y="68" width="12" height="12" rx="6" fill="url(#descGrad)"/>
    </svg>`,

    elevenlabs: `<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
      <rect x="35" y="20" width="12" height="60" rx="2" fill="#FFFFFF"/>
      <rect x="55" y="20" width="12" height="60" rx="2" fill="#FFFFFF"/>
    </svg>`
};

for (const [name, content] of Object.entries(svgs)) {
    fs.writeFileSync(path.join(outDir, `${name}.svg`), content);
    console.log(`Generated ${name}.svg successfully.`);
}
