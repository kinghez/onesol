const fs = require('fs');
const path = require('path');
const https = require('https');

const outDir = path.join(__dirname, 'assets', 'images', 'logos');
if (!fs.existsSync(outDir)) fs.mkdirSync(outDir, { recursive: true });

// Download Social SVGs from unpkg/jsdelivr
const socialLogos = [
    { name: 'facebook', url: 'https://cdn.jsdelivr.net/npm/simple-icons@v11/icons/facebook.svg' },
    { name: 'x', url: 'https://cdn.jsdelivr.net/npm/simple-icons@v11/icons/x.svg' },
    { name: 'instagram', url: 'https://cdn.jsdelivr.net/npm/simple-icons@v11/icons/instagram.svg' },
    { name: 'linkedin', url: 'https://cdn.jsdelivr.net/npm/simple-icons@v11/icons/linkedin.svg' }
];

function downloadFile(url, dest) {
    return new Promise((resolve, reject) => {
        https.get(url, (res) => {
            if (res.statusCode === 301 || res.statusCode === 302) {
                return downloadFile(res.headers.location, dest).then(resolve).catch(reject);
            }
            if (res.statusCode !== 200) {
                return reject(new Error(`Failed to get '${url}' (${res.statusCode})`));
            }
            let data = '';
            res.on('data', chunk => data += chunk);
            res.on('end', () => {
                // inject white fill
                data = data.replace('<svg ', '<svg fill="#FFFFFF" ');
                fs.writeFileSync(dest, data);
                console.log(`Downloaded ${path.basename(dest)}`);
                resolve();
            });
        }).on('error', reject);
    });
}

const customSvgs = {
    paystack: `<svg viewBox="0 0 120 24" xmlns="http://www.w3.org/2000/svg">
        <rect x="0" y="2" width="10" height="4" fill="#0BA4DB"/>
        <rect x="0" y="8" width="14" height="4" fill="#0BA4DB"/>
        <rect x="0" y="14" width="18" height="4" fill="#0BA4DB"/>
        <rect x="0" y="20" width="12" height="4" fill="#0BA4DB"/>
        <text x="24" y="18" font-family="-apple-system, sans-serif" font-weight="700" font-size="16" fill="#FFFFFF">paystack</text>
    </svg>`,
    flutterwave: `<svg viewBox="0 0 140 24" xmlns="http://www.w3.org/2000/svg">
        <path d="M12 4 Q16 10, 10 16 Q6 10, 12 4 Z" fill="#F5A623"/>
        <path d="M4 12 Q10 18, 16 12 Q10 6, 4 12 Z" fill="#F8E71C" opacity="0.8"/>
        <path d="M10 12 Q14 16, 18 12 Q14 8, 10 12 Z" fill="#F5A623"/>
        <text x="24" y="18" font-family="-apple-system, sans-serif" font-weight="700" font-size="16" fill="#FFFFFF">flutterwave</text>
    </svg>`,
    ssl_secure: `<svg viewBox="0 0 100 30" xmlns="http://www.w3.org/2000/svg">
        <path d="M15 2 L25 5 L25 15 Q25 25, 15 28 Q5 25, 5 15 L5 5 Z" fill="#10B981"/>
        <path d="M12 12 h6 v6 h-6 z" fill="#FFFFFF"/>
        <path d="M12 12 v-2 a3 3 0 0 1 6 0 v2" fill="none" stroke="#FFFFFF" stroke-width="2"/>
        <text x="32" y="14" font-family="-apple-system, sans-serif" font-weight="700" font-size="13" fill="#FFFFFF">SSL</text>
        <text x="32" y="26" font-family="-apple-system, sans-serif" font-size="11" fill="#AEB5CA">Secure</text>
    </svg>`,
    pci_compliant: `<svg viewBox="0 0 100 30" xmlns="http://www.w3.org/2000/svg">
        <path d="M5 5 h20 l-5 20 h-20 z" fill="#0BA4DB"/>
        <text x="8" y="19" font-family="-apple-system, sans-serif" font-weight="700" font-size="11" fill="#FFFFFF">PCI</text>
        <text x="32" y="14" font-family="-apple-system, sans-serif" font-weight="700" font-size="13" fill="#FFFFFF">DSS</text>
        <text x="32" y="26" font-family="-apple-system, sans-serif" font-size="11" fill="#AEB5CA">Compliant</text>
    </svg>`
};

async function run() {
    for (const logo of socialLogos) {
        await downloadFile(logo.url, path.join(outDir, `${logo.name}.svg`)).catch(console.error);
    }
    for (const [name, content] of Object.entries(customSvgs)) {
        fs.writeFileSync(path.join(outDir, `${name}.svg`), content);
        console.log(`Generated ${name}.svg`);
    }
}
run();
