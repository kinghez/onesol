const fs = require('fs');
const path = require('path');

const logos = [
    { name: 'chatgpt', color: '#10A37F' },
    { name: 'midjourney', color: '#FFFFFF' },
    { name: 'canva', color: '#00C4CC' },
    { name: 'grammarly', color: '#158356' },
    { name: 'notion', color: '#FFFFFF' },
    { name: 'claude', color: '#D97757' }
];

const outDir = path.join(__dirname, 'assets', 'images', 'logos');

logos.forEach(logo => {
    const file = path.join(outDir, `${logo.name}.svg`);
    if (fs.existsSync(file)) {
        let content = fs.readFileSync(file, 'utf8');
        if (!content.includes('fill=')) {
            content = content.replace('<svg ', `<svg fill="${logo.color}" `);
            fs.writeFileSync(file, content);
            console.log(`Injected color for ${logo.name}`);
        } else if (content.includes('fill="black"')) {
            content = content.replace('fill="black"', `fill="${logo.color}"`);
            fs.writeFileSync(file, content);
            console.log(`Replaced color for ${logo.name}`);
        }
    }
});
