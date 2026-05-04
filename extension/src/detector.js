class PageDetector {
    static isProductPage() {
        const ogType = document.querySelector('meta[property="og:type"]');
        if (ogType && (ogType.content === "product" || ogType.content.includes("product"))) return true;
        
        const url = window.location.href;
        if (url.includes('/dp/') || url.includes('/gp/product/') || url.includes('/itm/') || url.includes('/ip/')) return true; 

        const addToCartRegex = /add.*cart|buy.*now/i;
        const buttons = Array.from(document.querySelectorAll('button, a, input'));
        for (let btn of buttons) {
            const textToTest = btn.innerText || btn.value || btn.id || btn.name;
            if (textToTest && addToCartRegex.test(textToTest)) return true;
        }
        return false;
    }
}