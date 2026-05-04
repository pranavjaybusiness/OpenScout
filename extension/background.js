class ApiHandler {
    constructor(endpoint) {
        this.endpoint = endpoint;
    }

    async sendToBackend(text) {
        try {
            const response = await fetch(this.endpoint, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ raw_text: text })
            });
            return await response.json();
        } catch (error) {
            console.error("OpenScout Backend Error:", error);
            return null;
        }
    }
}
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
    // If the URL changed, tell the content script to re-evaluate the page
    if (changeInfo.url || changeInfo.status === 'complete') {
        chrome.tabs.sendMessage(tabId, { action: "page_navigated" }).catch(() => {});
    }
});
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "process_text") {
        const api = new ApiHandler("http://127.0.0.1:8000/parse");
        
        // Return true immediately to tell Chrome we will respond asynchronously
        api.sendToBackend(request.payload).then(data => {
            sendResponse({ result: data });
        });
        return true; 
    }
});