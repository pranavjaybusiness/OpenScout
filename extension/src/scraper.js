class Scraper {
    static extractData() {
        let scrapedData = {
            metadata: {},
            json_ld: [],
            identifiers: { url: window.location.href, potential_skus: {} },
            images: [],
            visible_text_fallback: ""
        };

        // 1. Images
        document.querySelectorAll('meta[property="og:image"], meta[name="twitter:image"], link[rel="image_src"]').forEach(tag => {
            const url = tag.getAttribute('content') || tag.getAttribute('href');
            if (url && !scrapedData.images.includes(url)) scrapedData.images.push(url);
        });

        // 2. Identifiers
        const idKeywords = ['sku', 'asin', 'item number', 'model', 'gtin', 'upc', 'tcin'];
        document.querySelectorAll('li, td, span, div').forEach(el => {
            if (el.children.length === 0) { 
                const text = el.innerText.toLowerCase();
                idKeywords.forEach(key => {
                    if (text.includes(key) && text.length < 60) {
                        scrapedData.identifiers.potential_skus[key] = el.innerText.trim();
                    }
                });
            }
        });

        // 3. Metadata & JSON-LD
        document.querySelectorAll('meta[property^="og:"], meta[property^="product:"], meta[name="description"]').forEach(tag => {
            const key = tag.getAttribute('property') || tag.getAttribute('name');
            const value = tag.getAttribute('content');
            if (key && value) scrapedData.metadata[key] = value;
        });

        document.querySelectorAll('script[type="application/ld+json"]').forEach(script => {
            try { scrapedData.json_ld.push(JSON.parse(script.innerText)); } catch (e) {}
        });

        // 4. Text Fallback
        let rawText = document.body.innerText;
        scrapedData.visible_text_fallback = rawText.replace(/\n{3,}/g, '\n\n').trim().substring(0, 10000); 

        return JSON.stringify(scrapedData);
    }
}