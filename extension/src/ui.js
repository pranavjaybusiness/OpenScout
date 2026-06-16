const USER_FACING_ERROR_COPY =
    "We couldn't check prices right now. Please try again in a moment.";

function parsePrice(value) {
    if (value == null || value === "") return null;
    if (typeof value === "number" && !Number.isNaN(value)) return value;
    const parsed = parseFloat(String(value).replace(/[^0-9.]/g, ""));
    return Number.isFinite(parsed) ? parsed : null;
}

function truncateTitle(text, maxLen = 85) {
    const t = (text || "").trim();
    if (t.length <= maxLen) return t || "eBay listing";
    return `${t.slice(0, maxLen - 1)}…`;
}

function formatSavings(pagePrice, listingPrice) {
    if (pagePrice == null || listingPrice == null) return null;
    const savings = pagePrice - listingPrice;
    if (!Number.isFinite(savings) || savings <= 0) return null;
    return `Saving $${savings.toFixed(2)}`;
}

function _isBedBathBeyondHost() {
    const host = window.location.hostname.toLowerCase();
    return (
        host === "beyond.com" ||
        host.endsWith(".beyond.com") ||
        host === "bedbathandbeyond.com" ||
        host.endsWith(".bedbathandbeyond.com")
    );
}

class UIController {
    constructor(onScoutClick, onDismiss, onListingOpen) {
        this.onScoutClick = onScoutClick;
        this.onDismiss = onDismiss;
        this.onListingOpen = onListingOpen;
        this.modal = null;
        this.scoutBtn = null;
        this.dismissBtn = null;
        this.resultArea = null;
        this.lastProduct = null;
        this.scanId = null;
        this.feedbackPending = false;
        this.feedbackSubmitted = false;
    }

    inject() {
        const style = document.createElement("style");
        style.innerHTML = `
            @keyframes os-slide-down {
                from { transform: translateY(-12px); opacity: 0; }
                to { transform: translateY(0); opacity: 1; }
            }
            #openscout-modal,
            #openscout-modal * {
                box-sizing: border-box;
            }
            #openscout-modal {
                --os-text: #111827;
                --os-muted: #6b7280;
                --os-ebay: #0064d2;
                --os-ebay-hover: #0052b3;
                --os-shein: #111827;
                --os-shein-hover: #374151;
                --os-radius: 12px;
                --os-shadow-modal: 0 8px 32px rgba(15, 23, 42, 0.12);
                --os-shadow-card: 0 2px 14px rgba(15, 23, 42, 0.08);
                font-size: 15px;
                line-height: 1.4;
                overflow: visible;
                max-height: none;
            }
            #openscout-modal button {
                font-family: inherit;
                line-height: 1.25;
                min-height: 44px;
                overflow: visible;
                text-transform: none;
                letter-spacing: normal;
                appearance: none;
                -webkit-appearance: none;
            }
            #openscout-modal #os-actions {
                display: flex;
                gap: 10px;
                align-items: stretch;
                flex-shrink: 0;
            }
            #openscout-modal #os-scout {
                flex: 1 1 auto;
                min-width: 0;
            }
            #openscout-modal #os-dismiss {
                flex: 0 0 auto;
                white-space: nowrap;
            }
            #openscout-modal .os-btn {
                display: inline-flex;
                align-items: center;
                justify-content: center;
                padding: 11px 18px;
                border: none;
                border-radius: 8px;
                font-weight: 600;
                font-size: 15px;
                cursor: pointer;
                transition: background 0.15s ease, box-shadow 0.15s ease, color 0.15s ease;
            }
            #openscout-modal .os-btn-primary {
                background: #111827;
                color: #fff;
            }
            #openscout-modal .os-btn-primary:hover:not(:disabled) {
                background: #1f2937;
            }
            #openscout-modal .os-btn-secondary {
                background: #fff;
                color: var(--os-text);
                box-shadow: 0 1px 3px rgba(15, 23, 42, 0.08);
            }
            #openscout-modal .os-btn-secondary:hover {
                background: #f9fafb;
            }
            #openscout-modal .os-btn:disabled {
                opacity: 0.65;
                cursor: not-allowed;
            }
            #openscout-modal #os-result {
                display: flex;
                flex-direction: column;
                gap: 0;
                scrollbar-width: thin;
                scrollbar-color: #d1d5db transparent;
            }
            #openscout-modal #os-result::-webkit-scrollbar {
                width: 6px;
            }
            #openscout-modal #os-result::-webkit-scrollbar-track {
                background: transparent;
            }
            #openscout-modal #os-result::-webkit-scrollbar-thumb {
                background: #d1d5db;
                border-radius: 999px;
            }
            #openscout-modal #os-result::-webkit-scrollbar-thumb:hover {
                background: #9ca3af;
            }
            /* Section title */
            #openscout-modal .os-section-title {
                margin: 20px 2px 12px;
                font-size: 18px;
                font-weight: 700;
                color: var(--os-text);
                letter-spacing: -0.01em;
            }
            /* Cheaper option list */
            #openscout-modal .os-list {
                display: flex;
                flex-direction: column;
                gap: 12px;
            }
            #openscout-modal .os-row-card {
                background: #fff;
                border-radius: 14px;
                box-shadow: var(--os-shadow-card);
                overflow: hidden;
            }
            #openscout-modal .os-row-card--close {
                box-shadow: 0 2px 14px rgba(30, 64, 175, 0.12);
            }
            #openscout-modal a.os-row {
                display: flex;
                align-items: center;
                gap: 16px;
                padding: 18px 18px;
                text-decoration: none;
                color: inherit;
            }
            #openscout-modal a.os-row:hover {
                background: #fafafa;
            }
            #openscout-modal .os-row__media {
                flex: 0 0 88px;
                width: 88px;
                height: 88px;
                border-radius: 12px;
                overflow: hidden;
                background: #f3f4f6;
            }
            #openscout-modal .os-row__media img {
                width: 100%;
                height: 100%;
                object-fit: cover;
                display: block;
            }
            #openscout-modal .os-row__main {
                flex: 1;
                min-width: 0;
                display: flex;
                flex-direction: column;
                gap: 3px;
            }
            #openscout-modal .os-row__title {
                font-size: 15px;
                font-weight: 600;
                color: var(--os-text);
                line-height: 1.35;
                display: -webkit-box;
                -webkit-line-clamp: 2;
                -webkit-box-orient: vertical;
                overflow: hidden;
            }
            #openscout-modal .os-row__seller {
                font-size: 13px;
                font-weight: 700;
                color: var(--os-text);
            }
            #openscout-modal .os-row__right {
                flex: 0 0 auto;
                display: flex;
                flex-direction: column;
                align-items: flex-end;
                gap: 2px;
                text-align: right;
            }
            #openscout-modal .os-row__price {
                font-size: 16px;
                font-weight: 700;
                color: var(--os-text);
            }
            #openscout-modal .os-row__less {
                font-size: 13px;
                font-weight: 600;
                color: #047857;
            }
            #openscout-modal .os-pill-close {
                align-self: flex-start;
                font-size: 11px;
                font-weight: 600;
                letter-spacing: 0.02em;
                text-transform: uppercase;
                padding: 3px 9px;
                border-radius: 999px;
                background: #eff6ff;
                color: #1d4ed8;
            }
            #openscout-modal .os-status {
                margin: 0;
                font-size: 15px;
                line-height: 1.55;
                color: var(--os-muted);
            }
            #openscout-modal .os-loading {
                margin-top: 4px;
            }
            #openscout-modal .os-no-new-notice {
                margin: 0;
                padding: 14px 16px;
                font-size: 15px;
                line-height: 1.5;
                color: #92400e;
                background: #fffbeb;
                border-radius: 10px;
                box-shadow: 0 1px 4px rgba(146, 64, 14, 0.08);
            }
            #openscout-modal .os-close-match-banner {
                margin: 0;
                padding: 14px 16px;
                font-size: 15px;
                line-height: 1.5;
                color: #1e40af;
                background: #eff6ff;
                border-radius: 10px;
                box-shadow: 0 1px 4px rgba(30, 64, 175, 0.08);
            }
            #openscout-modal .os-condition-badge--close {
                background: #eff6ff;
                color: #1d4ed8;
            }
            #openscout-modal .os-close-match-note {
                font-size: 14px;
                line-height: 1.45;
                color: #1e40af;
                margin: 0;
            }
            #openscout-modal .os-ebay-card--close {
                box-shadow: 0 2px 14px rgba(30, 64, 175, 0.12);
            }
            #openscout-modal .os-error {
                margin: 0;
                color: #b91c1c;
                font-size: 15px;
                line-height: 1.5;
            }
            #openscout-modal .os-feedback {
                display: flex;
                align-items: center;
                gap: 10px;
                padding: 10px 16px 12px;
                border-top: 1px solid #f3f4f6;
            }
            #openscout-modal .os-feedback__label {
                flex: 1;
                font-size: 13px;
                font-weight: 600;
                color: var(--os-muted);
            }
            #openscout-modal .os-feedback__actions {
                display: flex;
                gap: 8px;
                flex: 0 0 auto;
            }
            #openscout-modal .os-feedback__btn {
                flex: 0 0 auto;
                min-height: 0;
                padding: 6px 16px;
                border-radius: 999px;
                border: 1px solid #e5e7eb;
                background: #fff;
                font-size: 13px;
                font-weight: 600;
                cursor: pointer;
                transition: background 0.15s ease, border-color 0.15s ease, color 0.15s ease;
            }
            #openscout-modal .os-feedback__btn:hover:not(:disabled) {
                background: #f9fafb;
            }
            #openscout-modal .os-feedback__btn--yes:hover:not(:disabled) {
                border-color: #86efac;
                color: #047857;
            }
            #openscout-modal .os-feedback__btn--no:hover:not(:disabled) {
                border-color: #fca5a5;
                color: #b91c1c;
            }
            #openscout-modal .os-feedback__btn:disabled {
                opacity: 0.55;
                cursor: default;
            }
            #openscout-modal .os-feedback__thanks {
                font-size: 14px;
                color: var(--os-muted);
                margin: 0;
            }
            /* Bed Bath & Beyond / beyond.com — aggressive host button CSS */
            #openscout-modal.openscout-modal--bbb {
                min-width: 400px !important;
            }
            #openscout-modal.openscout-modal--bbb #os-actions {
                display: flex !important;
                flex-direction: row !important;
                flex-wrap: nowrap !important;
                align-items: stretch !important;
                gap: 10px !important;
                width: 100% !important;
            }
            #openscout-modal.openscout-modal--bbb #os-scout,
            #openscout-modal.openscout-modal--bbb #os-dismiss {
                display: inline-flex !important;
                flex-direction: row !important;
                align-items: center !important;
                justify-content: center !important;
                width: auto !important;
                max-width: none !important;
                min-height: 44px !important;
                height: auto !important;
                white-space: nowrap !important;
                word-break: normal !important;
                overflow-wrap: normal !important;
                writing-mode: horizontal-tb !important;
                text-transform: none !important;
                letter-spacing: normal !important;
                line-height: 1.25 !important;
                padding: 11px 16px !important;
                margin: 0 !important;
            }
            #openscout-modal.openscout-modal--bbb #os-scout {
                flex: 1 1 0 !important;
                min-width: 160px !important;
            }
            #openscout-modal.openscout-modal--bbb #os-dismiss {
                flex: 0 0 auto !important;
            }
        `;
        if (!document.getElementById("openscout-styles")) {
            style.id = "openscout-styles";
            document.head.appendChild(style);
        }

        this.modal = document.createElement("div");
        this.modal.id = "openscout-modal";
        if (_isBedBathBeyondHost()) {
            this.modal.classList.add("openscout-modal--bbb");
        }
        Object.assign(this.modal.style, {
            position: "fixed",
            top: "20px",
            right: "20px",
            zIndex: "999999",
            width: "560px",
            backgroundColor: "#ffffff",
            borderRadius: "14px",
            boxShadow: "0 8px 32px rgba(15, 23, 42, 0.12)",
            padding: "24px",
            fontFamily:
                '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif',
            animation: "os-slide-down 0.35s ease-out",
            border: "none",
            isolation: "isolate",
            overflow: "visible",
            maxHeight: "none",
        });

        this.modal.innerHTML = `
            <div id="os-drag" style="touch-action: none; display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; cursor: grab; padding-bottom: 4px;">
                <h3 style="margin: 0; color: #111827; font-size: 22px; font-weight: 700; pointer-events: none; letter-spacing: -0.02em;">OpenScout</h3>
                <button id="os-close" type="button" aria-label="Close" style="display: inline-flex; align-items: center; justify-content: center; width: 36px; height: 36px; min-height: 36px; border-radius: 999px; background: #f3f4f6; border: none; cursor: pointer; font-size: 18px; color: #4b5563; line-height: 1; padding: 0;">✕</button>
            </div>
            <div id="os-actions">
                <button id="os-scout" type="button" class="os-btn os-btn-primary">Scout Cheaper Products</button>
                <button id="os-dismiss" type="button" class="os-btn os-btn-secondary">Dismiss</button>
            </div>
            <div id="os-result" style="display: none; flex-direction: column; margin-top: 20px; max-height: 640px; overflow-y: auto;"></div>
        `;
        document.body.appendChild(this.modal);

        this.scoutBtn = document.getElementById("os-scout");
        this.dismissBtn = document.getElementById("os-dismiss");
        this.resultArea = document.getElementById("os-result");

        this.attachListeners();
    }

    _buildAlternativeEntries(product, alternatives) {
        const pagePrice =
            parsePrice(product.numeric_price) ?? parsePrice(product.price);
        const items = [];
        if (!Array.isArray(alternatives) || pagePrice == null) {
            return { items, showCloseMatchBanner: false };
        }

        for (const listing of alternatives) {
            if (!listing || typeof listing !== "object") continue;
            const listingPrice = parsePrice(listing.price);
            if (listingPrice == null || listingPrice >= pagePrice) continue;
            items.push({
                listing,
                matchQuality: listing.match_quality || "exact",
                closeMatchNote: listing.close_match_note || "",
                geminiMatchReason: listing.gemini_match_reason || "",
                savingsLabel: formatSavings(pagePrice, listingPrice),
                conditionKey: listing.condition_type || listing.condition_bucket || "new",
            });
        }

        items.sort(
            (a, b) =>
                (parsePrice(a.listing.price) ?? Infinity) -
                (parsePrice(b.listing.price) ?? Infinity)
        );

        const hasExact = items.some((entry) => entry.matchQuality === "exact");
        const hasClose = items.some((entry) => entry.matchQuality === "close");
        return {
            items,
            showCloseMatchBanner: hasClose && !hasExact,
        };
    }

    _maybeRecordFeedbackSkipped() {
        if (!this.feedbackPending || this.feedbackSubmitted || !this.scanId) {
            return;
        }
        this.feedbackPending = false;
        browser.runtime.sendMessage({
            action: "feedback_skipped",
            payload: {
                scan_id: this.scanId,
                product_url: window.location.href,
            },
        });
    }

    attachListeners() {
        const closeBtn = document.getElementById("os-close");
        const removeModal = () => {
            this._maybeRecordFeedbackSkipped();
            if (this.onDismiss) {
                this.onDismiss();
            } else {
                this.modal.remove();
            }
        };

        closeBtn.addEventListener("click", removeModal);
        this.dismissBtn.addEventListener("click", removeModal);

        this.scoutBtn.addEventListener("click", () => {
            this.setLoadingState();
            this.onScoutClick();
        });

        const dragHandle = document.getElementById("os-drag");
        let isDragging = false;
        let activePointerId = null;
        let grabOffsetX = 0;
        let grabOffsetY = 0;
        let baseLeft = 0;
        let baseTop = 0;
        let pendingTx = 0;
        let pendingTy = 0;
        let dragRafId = null;

        const flushDrag = () => {
            dragRafId = null;
            if (!isDragging) return;
            this.modal.style.transform = `translate3d(${pendingTx}px, ${pendingTy}px, 0)`;
        };

        const scheduleDrag = (e) => {
            pendingTx = e.clientX - grabOffsetX - baseLeft;
            pendingTy = e.clientY - grabOffsetY - baseTop;
            if (dragRafId == null) {
                dragRafId = requestAnimationFrame(flushDrag);
            }
        };

        const endDrag = () => {
            if (!isDragging) return;
            isDragging = false;
            activePointerId = null;
            if (dragRafId != null) {
                cancelAnimationFrame(dragRafId);
                dragRafId = null;
            }
            dragHandle.style.cursor = "grab";
            document.body.style.userSelect = "";

            const r = this.modal.getBoundingClientRect();
            this.modal.style.left = `${r.left}px`;
            this.modal.style.top = `${r.top}px`;
            this.modal.style.transform = "";
            this.modal.style.willChange = "auto";
        };

        dragHandle.addEventListener("pointerdown", (e) => {
            if (e.pointerType === "mouse" && e.button !== 0) return;
            if (e.target.id === "os-close") return;
            isDragging = true;
            activePointerId = e.pointerId;
            dragHandle.style.cursor = "grabbing";
            try {
                dragHandle.setPointerCapture(e.pointerId);
            } catch {
                endDrag();
                return;
            }
            const rect = this.modal.getBoundingClientRect();
            grabOffsetX = e.clientX - rect.left;
            grabOffsetY = e.clientY - rect.top;
            baseLeft = rect.left;
            baseTop = rect.top;
            this.modal.style.left = `${rect.left}px`;
            this.modal.style.top = `${rect.top}px`;
            this.modal.style.right = "auto";
            this.modal.style.bottom = "auto";
            this.modal.style.animation = "none";
            this.modal.style.willChange = "transform";
            this.modal.style.transform = "translate3d(0, 0, 0)";
            document.body.style.userSelect = "none";
        });

        dragHandle.addEventListener(
            "pointermove",
            (e) => {
                if (!isDragging || e.pointerId !== activePointerId) return;
                scheduleDrag(e);
            },
            { passive: true }
        );

        dragHandle.addEventListener("pointerup", (e) => {
            if (e.pointerId !== activePointerId) return;
            try {
                dragHandle.releasePointerCapture(e.pointerId);
            } catch {
                /* already released */
            }
            endDrag();
        });

        dragHandle.addEventListener("pointercancel", (e) => {
            if (e.pointerId !== activePointerId) return;
            endDrag();
        });

        dragHandle.addEventListener("lostpointercapture", (e) => {
            if (e.pointerId !== activePointerId) return;
            if (isDragging) endDrag();
        });
    }

    setLoadingState() {
        this.feedbackPending = false;
        this.feedbackSubmitted = false;
        this.scoutBtn.innerText = "Checking prices…";
        this.scoutBtn.disabled = true;
        this.dismissBtn.style.display = "none";
        this.resultArea.style.display = "flex";
        this.resultArea.replaceChildren();
        const loading = document.createElement("p");
        loading.className = "os-status os-loading";
        loading.textContent =
            "Searching for cheaper options… This usually takes 15–30 seconds.";
        this.resultArea.appendChild(loading);
    }

    _submitMatchFeedback(sameProduct, entry, product, feedbackRoot) {
        const buttons = feedbackRoot.querySelectorAll(".os-feedback__btn");
        buttons.forEach((btn) => {
            btn.disabled = true;
        });

        if (!this.scanId) {
            feedbackRoot.replaceChildren();
            const err = document.createElement("p");
            err.className = "os-feedback__thanks";
            err.textContent = "Couldn't save feedback. Please run Scout again.";
            feedbackRoot.appendChild(err);
            return;
        }

        browser.runtime.sendMessage(
            {
                action: "submit_feedback",
                payload: {
                    scan_id: this.scanId,
                    product_url: window.location.href,
                    user_feedback: sameProduct ? "yes" : "no",
                },
            },
            (response) => {
                const ok = response?.result?.status === "success";
                if (ok) {
                    this.feedbackSubmitted = true;
                    this.feedbackPending = false;
                }
                feedbackRoot.replaceChildren();
                const thanks = document.createElement("p");
                thanks.className = "os-feedback__thanks";
                thanks.textContent = ok
                    ? "Thanks — your feedback was saved."
                    : "Couldn't save feedback. Please try again.";
                feedbackRoot.appendChild(thanks);
            }
        );
    }

    _renderFeedbackBlock(entry, product) {
        const block = document.createElement("div");
        block.className = "os-feedback";

        const label = document.createElement("div");
        label.className = "os-feedback__label";
        label.textContent = "Same product?";
        block.appendChild(label);

        const actions = document.createElement("div");
        actions.className = "os-feedback__actions";

        const yesBtn = document.createElement("button");
        yesBtn.type = "button";
        yesBtn.className = "os-feedback__btn os-feedback__btn--yes";
        yesBtn.textContent = "Yes";
        yesBtn.addEventListener("click", () =>
            this._submitMatchFeedback(true, entry, product, block)
        );

        const noBtn = document.createElement("button");
        noBtn.type = "button";
        noBtn.className = "os-feedback__btn os-feedback__btn--no";
        noBtn.textContent = "No";
        noBtn.addEventListener("click", () =>
            this._submitMatchFeedback(false, entry, product, block)
        );

        actions.appendChild(yesBtn);
        actions.appendChild(noBtn);
        block.appendChild(actions);
        return block;
    }

    _renderListingCard(entry, product) {
        const listing = entry.listing || {};
        const isClose = entry.matchQuality === "close";
        const platform = (listing.platform || "Store").trim();

        const card = document.createElement("div");
        card.className = isClose ? "os-row-card os-row-card--close" : "os-row-card";

        const row = document.createElement("a");
        row.className = "os-row";
        row.href = listing.url || "#";
        row.target = "_blank";
        row.rel = "noopener noreferrer";
        row.addEventListener("click", () => {
            if (this.onListingOpen) this.onListingOpen(listing.url || "");
        });

        if (listing.image_url) {
            const media = document.createElement("div");
            media.className = "os-row__media";
            const img = document.createElement("img");
            img.alt = listing.title || `${platform} listing`;
            img.referrerPolicy = "no-referrer";
            img.decoding = "async";
            img.width = 88;
            img.height = 88;
            img.src = listing.image_url;
            media.appendChild(img);
            row.appendChild(media);
        }

        const main = document.createElement("div");
        main.className = "os-row__main";

        if (isClose) {
            const pill = document.createElement("span");
            pill.className = "os-pill-close";
            pill.textContent = "Close match";
            main.appendChild(pill);
        }

        const titleEl = document.createElement("div");
        titleEl.className = "os-row__title";
        titleEl.textContent = truncateTitle(listing.title, 70);
        main.appendChild(titleEl);

        const sellerEl = document.createElement("div");
        sellerEl.className = "os-row__seller";
        sellerEl.textContent = platform;
        main.appendChild(sellerEl);

        if (isClose && entry.closeMatchNote) {
            const note = document.createElement("p");
            note.className = "os-close-match-note";
            note.textContent = entry.closeMatchNote;
            main.appendChild(note);
        }

        row.appendChild(main);

        const right = document.createElement("div");
        right.className = "os-row__right";

        const priceEl = document.createElement("div");
        priceEl.className = "os-row__price";
        priceEl.textContent = listing.price || "—";
        right.appendChild(priceEl);

        if (entry.savingsLabel) {
            const lessEl = document.createElement("div");
            lessEl.className = "os-row__less";
            lessEl.textContent = entry.savingsLabel;
            right.appendChild(lessEl);
        }

        row.appendChild(right);
        card.appendChild(row);

        card.appendChild(this._renderFeedbackBlock(entry, product));

        return card;
    }

    _renderAlternativesSection(product, alternatives, labels) {
        const fragment = document.createDocumentFragment();

        const heading = document.createElement("h3");
        heading.className = "os-section-title";
        heading.textContent = labels.heading;
        fragment.appendChild(heading);

        const { items, showCloseMatchBanner } = this._buildAlternativeEntries(
            product,
            alternatives
        );

        if (items.length > 0) {
            if (showCloseMatchBanner && labels.closeBanner) {
                const banner = document.createElement("p");
                banner.className = "os-close-match-banner";
                banner.textContent = labels.closeBanner;
                fragment.appendChild(banner);
            }
            const list = document.createElement("div");
            list.className = "os-list";
            items.forEach((entry) => {
                list.appendChild(this._renderListingCard(entry, product));
            });
            fragment.appendChild(list);
            return fragment;
        }

        const p = document.createElement("p");
        p.className = "os-status";
        p.textContent = labels.notFound;
        fragment.appendChild(p);
        return fragment;
    }

    showResult(success, dataOrError) {
        const actions = document.getElementById("os-actions");
        const content = document.createDocumentFragment();

        if (!success) {
            this.scoutBtn.style.display = "";
            if (actions) actions.style.display = "flex";
            this.scoutBtn.innerText = "Try again";
            this.scoutBtn.disabled = false;
            this.dismissBtn.style.display = "";

            const err = document.createElement("p");
            err.className = "os-error";
            err.textContent = USER_FACING_ERROR_COPY;
            content.appendChild(err);
            this.resultArea.style.display = "flex";
            this.resultArea.replaceChildren(content);
            return;
        }

        const payload = dataOrError;
        const product = payload.data || {};
        const alternatives = payload.alternatives || [];
        this.lastProduct = product;
        this.scanId = payload.scan_id ?? null;
        this.feedbackSubmitted = false;
        this.feedbackPending =
            this._buildAlternativeEntries(product, alternatives).items.length > 0;

        this.scoutBtn.style.display = "none";
        if (actions) actions.style.display = "none";

        const pagePrice =
            parsePrice(product.numeric_price) ?? parsePrice(product.price);
        const notFoundCopy =
            pagePrice == null
                ? "We couldn't read a price on this page, so we didn't search for deals."
                : "No cheaper verified matches found right now.";

        content.appendChild(
            this._renderAlternativesSection(product, alternatives, {
                heading: "Cheaper options",
                closeBanner:
                    "No exact matches — here are close options. Check the notes if you're flexible on small differences.",
                notFound: notFoundCopy,
            })
        );

        this.resultArea.style.display = "flex";
        this.resultArea.replaceChildren(content);
    }
}
