class OpenScoutApp {
    constructor() {
        this.ui = null;
    }

    init() {
        // Because detector.js was loaded first in the manifest, 
        // PageDetector is available right here.
        if (PageDetector.isProductPage()) {
            console.log("OpenScout: Product detected. Injecting UI...");
            
            this.ui = new UIController(() => this.handleScoutClick());
            this.ui.inject();
        }
    }

    handleScoutClick() {
        // Scraper is also globally available
        const payload = Scraper.extractData();

        chrome.runtime.sendMessage({ action: "process_text", payload: payload }, (response) => {
            if (chrome.runtime.lastError) {
                console.error("OpenScout: message to background failed", chrome.runtime.lastError.message);
                this.ui.showResult(false);
                return;
            }
            const body = response?.result;
            if (body && body.status === "success" && body.data) {
                this.ui.showResult(true, body);
            } else {
                console.error("OpenScout: parse request unsuccessful", {
                    body,
                    detail: body?.detail,
                });
                this.ui.showResult(false);
            }
        });
    }
}

// Bootstrap the extension
const app = new OpenScoutApp();
app.init();