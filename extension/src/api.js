/** HTTP client for OpenScout backend (content script + service worker). */
const OpenScoutApi = {
    base() {
        return OPENSCOUT_API_BASE.replace(/\/$/, "");
    },

    isParseSuccess(body) {
        if (!body || body.status !== "success") return false;
        if (body.data != null && typeof body.data === "object") return true;
        if (body.ebay != null && typeof body.ebay === "object") return true;
        return false;
    },

    async _post(path, payload) {
        const response = await fetch(`${this.base()}${path}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
            console.error("OpenScout API HTTP", response.status, path, data);
        }
        return data;
    },

    async parseProduct(rawText) {
        return this._post("/parse", { raw_text: rawText });
    },

    async submitFeedback(payload) {
        return this._post("/feedback", payload);
    },

    async feedbackSkipped(payload) {
        return this._post("/feedback/skipped", payload);
    },
};
