const https = require('https');
const fs = require('fs');
const path = require('path');

const logos = [
    { name: 'chatgpt', url: 'https://unpkg.com/simple-icons@v11/icons/openai.svg', color: '#10A37F' },
    { name: 'midjourney', url: 'https://unpkg.com/simple-icons@v11/icons/midjourney.svg', color: '#FFFFFF' },
    { name: 'canva', url: 'https://unpkg.com/simple-icons@v11/icons/canva.svg', color: '#00C4CC' },
    { name: 'grammarly', url: 'https://unpkg.com/simple-icons@v11/icons/grammarly.svg', color: '#158356' },
    { name: 'notion', url: 'https://unpkg.com/simple-icons@v11/icons/notion.svg', color: '#FFFFFF' },
    { name: 'claude', url: 'https://unpkg.com/simple-icons@v11/icons/anthropic.svg', color: '#D97757' }
];

const outDir = path.join(__dirname, 'assets', 'images', 'logos');
if (!fs.existsSync(outDir)) {
    fs.mkdirSync(outDir, { recursive: true });
}

function get(url, logo) {
    https.get(url, (res) => {
        if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
            return get(res.headers.location.startsWith('http') ? res.headers.location : 'https://unpkg.com' + res.headers.location, logo);
        }
        let data = '';
        res.on('data', chunk => data += chunk);
        res.on('end', () => {
            let coloredSvg = data;
            if (coloredSvg.includes('<svg ')) {
                coloredSvg = coloredSvg.replace('<svg ', `<svg fill="${logo.color}" xmlns="http://www.w3.org/2000/svg" `);
            }
            fs.writeFileSync(path.join(outDir, `${logo.name}.svg`), coloredSvg);
            console.log(`Saved ${logo.name}.svg`);
        });
    }).on('error', e => console.error(`Error ${logo.name}:`, e.message));
}

logos.forEach(logo => get(logo.url, logo));
