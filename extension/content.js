// Hosts the user just opened from a "cheaper option" link. We suppress the popup
// once on the destination page so they don't have to re-scan a result we found.
const OUTBOUND_SUPPRESS_KEY = "openscout_outbound_hosts";
const OUTBOUND_SUPPRESS_WINDOW_MS = 5 * 60 * 1000;

function _suppressionHost(url) {
    try {
        return new URL(url).hostname.toLowerCase().replace(/^www\./, "");
    } catch {
        return "";
    }
}

class OpenScoutApp {
    constructor() {
        this.ui = null;
        this._dismissed = false;
        this._href = window.location.href;
        this._syncTimer = null;
        this._parseInFlight = false;
        this._parseHref = null;
    }

    // Remember the store a clicked cheaper-option points to, so its product page
    // (which may open in a new tab) doesn't show the popup again.
    async recordOutbound(url) {
        const host = _suppressionHost(url);
        if (!host) return;
        try {
            const store = await browser.storage.local.get(OUTBOUND_SUPPRESS_KEY);
            const map = store?.[OUTBOUND_SUPPRESS_KEY] || {};
            const now = Date.now();
            map[host] = now + OUTBOUND_SUPPRESS_WINDOW_MS;
            for (const key of Object.keys(map)) {
                if (map[key] < now) delete map[key];
            }
            await browser.storage.local.set({ [OUTBOUND_SUPPRESS_KEY]: map });
        } catch {
            /* storage unavailable — non-fatal */
        }
    }

    // If this page's host was just opened from a cheaper-option link, suppress the
    // popup once (and consume the entry so later visits scan normally).
    async consumeOutboundSuppression() {
        const host = _suppressionHost(window.location.href);
        if (!host) return;
        try {
            const store = await browser.storage.local.get(OUTBOUND_SUPPRESS_KEY);
            const map = store?.[OUTBOUND_SUPPRESS_KEY] || {};
            const now = Date.now();
            let changed = false;
            if (map[host] && map[host] >= now) {
                this._dismissed = true;
                delete map[host];
                changed = true;
            }
            for (const key of Object.keys(map)) {
                if (map[key] < now) {
                    delete map[key];
                    changed = true;
                }
            }
            if (changed) await browser.storage.local.set({ [OUTBOUND_SUPPRESS_KEY]: map });
        } catch {
            /* storage unavailable — fail open and show the popup */
        }
    }

    teardown() {
        document.getElementById("openscout-modal")?.remove();
        this.ui = null;
    }

    onDismiss() {
        this._dismissed = true;
        this.teardown();
    }

    syncPage() {
        const href = window.location.href;
        const hrefChanged = href !== this._href;

        if (hrefChanged) {
            this._href = href;
            this._dismissed = false;
            this.teardown();
        }

        // Don't tear down / re-inject while Scout is running (avoids loading flicker).
        if (this._parseInFlight) {
            return;
        }

        if (!SupportedSites.isCurrentSiteSupported()) {
            if (hrefChanged) this.teardown();
            return;
        }

        if (!PageDetector.isProductPage()) {
            this.teardown();
            return;
        }

        if (this._dismissed) {
            return;
        }

        // Modal already on screen for this URL — skip re-inject (was causing 3–4 flickers).
        if (this.ui && document.getElementById("openscout-modal")) {
            return;
        }

        this.teardown();

        this.ui = new UIController(
            () => this.handleScoutClick(),
            () => this.onDismiss(),
            (url) => this.recordOutbound(url)
        );
        this.ui.inject();
    }

    scheduleSync() {
        clearTimeout(this._syncTimer);
        clearTimeout(this._syncLateTimer);
        this._syncTimer = setTimeout(() => this.syncPage(), 80);
        // One late pass for slow SPAs — only injects if the modal still isn't present.
        this._syncLateTimer = setTimeout(() => {
            if (!document.getElementById("openscout-modal") && !this._dismissed) {
                this.syncPage();
            }
        }, 450);
    }

    watchNavigation() {
        browser.runtime.onMessage.addListener((message) => {
            if (message.action === "page_navigated") {
                this.scheduleSync();
            }
        });

        window.addEventListener("popstate", () => this.scheduleSync());
        window.addEventListener("pageshow", () => this.scheduleSync());

        const wrapHistory = (method) => {
            const original = history[method];
            if (typeof original !== "function") return;
            history[method] = function (...args) {
                const result = original.apply(this, args);
                app.scheduleSync();
                return result;
            };
        };
        wrapHistory("pushState");
        wrapHistory("replaceState");
    }

    async init() {
        if (!SupportedSites.isCurrentSiteSupported()) return;
        await this.consumeOutboundSuppression();
        this.watchNavigation();
        this.syncPage();
    }

    async handleScoutClick() {
        if (this._parseInFlight || !this.ui) return;

        const ui = this.ui;
        this._parseInFlight = true;
        this._parseHref = window.location.href;

        try {
            const body = await new Promise((resolve, reject) => {
                browser.runtime.sendMessage(
                    { action: "parse_product", rawText: Scraper.extractData() },
                    (response) => {
                        if (browser.runtime.lastError) {
                            reject(new Error(browser.runtime.lastError.message));
                            return;
                        }
                        resolve(response?.result);
                    }
                );
            });
            if (!this.ui || this.ui !== ui) return;
            if (OpenScoutApi.isParseSuccess(body)) {
                ui.showResult(true, body);
            } else {
                console.error("OpenScout: parse request unsuccessful", {
                    body,
                    detail: body?.detail,
                });
                ui.showResult(false);
            }
        } catch (error) {
            console.error("OpenScout: parse request failed", error);
            if (this.ui === ui) {
                ui.showResult(false);
            }
        } finally {
            this._parseInFlight = false;
            this._parseHref = null;
        }
    }
}

const app = new OpenScoutApp();
app.init();
