importScripts("src/browser.js", "src/config.js", "src/api.js");

browser.tabs.onUpdated.addListener((tabId, changeInfo) => {
    if (changeInfo.url || changeInfo.status === "complete") {
        browser.tabs.sendMessage(tabId, { action: "page_navigated" }).catch(() => {});
    }
});

browser.runtime.onMessage.addListener((request, _sender, sendResponse) => {
    if (request.action === "submit_feedback") {
        (async () => {
            const data = await OpenScoutApi.submitFeedback(request.payload);
            sendResponse({ result: data });
        })();
        return true;
    }
    if (request.action === "feedback_skipped") {
        (async () => {
            const data = await OpenScoutApi.feedbackSkipped(request.payload);
            sendResponse({ result: data });
        })();
        return true;
    }
});
