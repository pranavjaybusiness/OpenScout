class OpenScoutApp {
    constructor() {
        this.ui = null;
        this._dismissed = false;
        this._href = window.location.href;
        this._syncTimer = null;
        this._parseInFlight = false;
        this._parseHref = null;
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
        if (href !== this._href) {
            this._href = href;
            this._dismissed = false;
        }

        if (this._parseInFlight && href === this._parseHref) {
            return;
        }

        this.teardown();

        if (!SupportedSites.isCurrentSiteSupported()) return;
        if (!PageDetector.isProductPage()) return;
        if (this._dismissed) return;

        this.ui = new UIController(
            () => this.handleScoutClick(),
            () => this.onDismiss()
        );
        this.ui.inject();
    }

    scheduleSync() {
        clearTimeout(this._syncTimer);
        this._syncTimer = setTimeout(() => this.syncPage(), 80);
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

    init() {
        if (!SupportedSites.isCurrentSiteSupported()) return;
        this.watchNavigation();
        this.syncPage();
    }

    async handleScoutClick() {
        if (this._parseInFlight || !this.ui) return;

        const ui = this.ui;
        this._parseInFlight = true;
        this._parseHref = window.location.href;

        try {
            const body = await OpenScoutApi.parseProduct(Scraper.extractData());
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
