// ==========================================
/** Shown on any failure path; technical details are never surfaced here (production). */
const USER_FACING_ERROR_COPY =
    "We couldn't check prices right now. Please try again in a moment.";

class UIController {
    constructor(onScoutClick) {
        this.onScoutClick = onScoutClick;
        this.modal = null;
        this.scoutBtn = null;
        this.dismissBtn = null;
        this.resultArea = null;
    }

    inject() {
        const style = document.createElement('style');
        style.innerHTML = `
            @keyframes os-slide-down { from { transform: translateY(-20px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
            .os-btn { padding: 8px 16px; border: none; border-radius: 6px; font-weight: bold; cursor: pointer; transition: background 0.2s; }
            .os-btn-primary { background: #2563EB; color: white; }
            .os-btn-primary:hover { background: #1D4ED8; }
            .os-btn-secondary { background: #E5E7EB; color: #374151; }
            .os-btn-secondary:hover { background: #D1D5DB; }
        `;
        document.head.appendChild(style);

        this.modal = document.createElement("div");
        this.modal.id = "openscout-modal";
        Object.assign(this.modal.style, {
            position: "fixed", top: "20px", right: "20px", zIndex: "999999", width: "360px",
            backgroundColor: "white", borderRadius: "12px", boxShadow: "0 10px 25px rgba(0,0,0,0.2)",
            padding: "20px", fontFamily: "sans-serif", animation: "os-slide-down 0.4s ease-out", border: "1px solid #E5E7EB",
            contain: "paint",
            isolation: "isolate",
        });

        this.modal.innerHTML = `
            <div id="os-drag" style="touch-action: none; display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; cursor: grab; padding-bottom: 5px; border-bottom: 1px solid #E5E7EB;">
                <h3 style="margin: 0; color: #111827; font-size: 16px; pointer-events: none;">🔍 OpenScout</h3>
                <button id="os-close" style="background: none; border: none; cursor: pointer; font-size: 16px; color: #9CA3AF;">✕</button>
            </div>
            <p style="margin: 0 0 16px 0; color: #4B5563; font-size: 14px;">Product detected! Check for a cheaper price?</p>
            <div style="display: flex; gap: 10px;">
                <button id="os-scout" class="os-btn os-btn-primary" style="flex: 1;">Scout It</button>
                <button id="os-dismiss" class="os-btn os-btn-secondary">Dismiss</button>
            </div>
            <div id="os-result" style="display: none; background: #F9FAFB; padding: 12px; border-radius: 8px; font-size: 13px; margin-top: 15px; max-height: 420px; overflow-y: auto; border: 1px solid #E5E7EB; color: #111827;"></div>
        `;
        document.body.appendChild(this.modal);

        this.scoutBtn = document.getElementById("os-scout");
        this.dismissBtn = document.getElementById("os-dismiss");
        this.resultArea = document.getElementById("os-result");

        this.attachListeners();
    }

    attachListeners() {
        const closeBtn = document.getElementById("os-close");
        const removeModal = () => this.modal.remove();
        
        closeBtn.addEventListener("click", removeModal);
        this.dismissBtn.addEventListener("click", removeModal);
        
        this.scoutBtn.addEventListener("click", () => {
            this.setLoadingState();
            this.onScoutClick(); // Trigger the callback passed from the main app
        });

        // Drag: pointer capture + passive pointermove + translate3d + rAF.
        // Avoids document mousemove + preventDefault (forces sync scroll/layout on fast moves).
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
        this.scoutBtn.innerText = "⏳ Parsing...";
        this.scoutBtn.disabled = true;
        this.scoutBtn.style.opacity = "0.7";
        this.dismissBtn.style.display = "none";
    }

    showResult(success, dataOrError) {
        this.scoutBtn.style.display = "none";
        this.resultArea.style.display = "block";
        this.resultArea.replaceChildren();

        if (!success) {
            this.scoutBtn.style.display = "";
            this.scoutBtn.innerText = "Retry";
            this.scoutBtn.disabled = false;
            this.scoutBtn.style.opacity = "1";
            this.dismissBtn.style.display = "";

            const err = document.createElement("p");
            err.style.margin = "0 0 12px 0";
            err.style.color = "#B91C1C";
            err.style.fontSize = "13px";
            err.style.lineHeight = "1.45";
            err.textContent = USER_FACING_ERROR_COPY;
            this.resultArea.appendChild(err);
            return;
        }

        const payload = dataOrError;
        const product = payload.data || {};
        const ebay = payload.ebay || {};

        const productBlock = document.createElement("div");
        productBlock.style.marginBottom = "14px";
        const pTitle = document.createElement("div");
        pTitle.style.fontWeight = "600";
        pTitle.style.fontSize = "14px";
        pTitle.style.marginBottom = "6px";
        pTitle.textContent = "On this page";
        productBlock.appendChild(pTitle);

        const addRow = (label, value) => {
            const row = document.createElement("div");
            row.style.display = "grid";
            row.style.gridTemplateColumns = "88px 1fr";
            row.style.gap = "6px 10px";
            row.style.fontSize = "12px";
            row.style.marginBottom = "4px";
            const l = document.createElement("span");
            l.style.color = "#6B7280";
            l.textContent = label;
            const v = document.createElement("span");
            v.style.color = "#111827";
            v.textContent = value || "—";
            row.appendChild(l);
            row.appendChild(v);
            productBlock.appendChild(row);
        };

        addRow("Name", product.name);
        addRow("Price", product.price);
        addRow("Brand", product.brand);
        this.resultArea.appendChild(productBlock);

        const ebayTitle = document.createElement("div");
        ebayTitle.style.fontWeight = "600";
        ebayTitle.style.fontSize = "14px";
        ebayTitle.style.marginBottom = "8px";
        ebayTitle.style.paddingTop = "10px";
        ebayTitle.style.borderTop = "1px solid #E5E7EB";
        ebayTitle.textContent = "eBay price check";
        this.resultArea.appendChild(ebayTitle);

        const ebayBody = document.createElement("div");
        ebayBody.style.fontSize = "13px";
        ebayBody.style.lineHeight = "1.45";

        if (!ebay.searched) {
            const p = document.createElement("p");
            p.style.margin = "0";
            p.style.color = "#4B5563";
            p.textContent =
                "No comparable on-page price was found, so we did not search eBay for a cheaper match.";
            ebayBody.appendChild(p);
        } else if (!ebay.found) {
            const p = document.createElement("p");
            p.style.margin = "0";
            p.style.color = "#4B5563";
            p.textContent = "No cheaper alternative was found on eBay from the queries we tried.";
            ebayBody.appendChild(p);
        } else {
            const listing = ebay.listing || {};
            if (listing.image_url) {
                const wrap = document.createElement("a");
                wrap.href = listing.url || "#";
                wrap.target = "_blank";
                wrap.rel = "noopener noreferrer";
                wrap.style.display = "block";
                wrap.style.marginBottom = "10px";
                wrap.style.borderRadius = "8px";
                wrap.style.overflow = "hidden";
                wrap.style.border = "1px solid #E5E7EB";
                wrap.style.background = "#fff";
                const img = document.createElement("img");
                img.src = listing.image_url;
                img.alt = listing.title || "eBay listing preview";
                img.referrerPolicy = "no-referrer";
                img.style.width = "100%";
                img.style.maxHeight = "160px";
                img.style.objectFit = "cover";
                img.style.display = "block";
                wrap.appendChild(img);
                ebayBody.appendChild(wrap);
            }

            const nameEl = document.createElement("div");
            nameEl.style.fontWeight = "600";
            nameEl.style.marginBottom = "6px";
            nameEl.textContent = listing.title || "eBay listing";
            ebayBody.appendChild(nameEl);

            const meta = document.createElement("div");
            meta.style.color = "#374151";
            meta.style.fontSize = "12px";
            meta.style.marginBottom = "10px";
            meta.textContent = `${listing.price || ""} · Save ${listing.savings || ""} vs this page`;
            ebayBody.appendChild(meta);

            const link = document.createElement("a");
            link.href = listing.url || "#";
            link.target = "_blank";
            link.rel = "noopener noreferrer";
            link.style.color = "#2563EB";
            link.style.fontWeight = "600";
            link.style.fontSize = "13px";
            link.textContent = "Open listing on eBay";
            ebayBody.appendChild(link);
        }

        this.resultArea.appendChild(ebayBody);
    }
}