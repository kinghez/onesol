const fs = require('fs');
async function search() {
    try {
        const res = await fetch('https://svgl.app/api/svgs');
        const data = await res.json();
        const targets = ['copyai', 'jasper', 'suno', 'pictory', 'descript', 'elevenlabs'];
        
        const found = data.filter(d => targets.some(t => d.title.toLowerCase().includes(t)));
        fs.writeFileSync('svgl_results.json', JSON.stringify(found, null, 2));
        console.log('Search complete. Found:', found.length);
    } catch(e) {
        console.error('Fetch error:', e.message);
    }
}
search();
