// Per-retailer URL rules. strict: true → only productPath counts; skip generic heuristics.

/** Shared path/query signals for site rules and fallback detection (non-strict sites). */
const URL_PRODUCT_SIGNALS = {
    productSearch: /(?:^|[?&])(?:productId|product_id|itemId|item_id)=/i,
    productPath:
        /(?:\/products?\/|\/p\/|\/prd\/|\/dp\/|\/ip\/|\/product-detail\/|\/gp\/product\/)/i,
    categoryPath:
        /(?:^|\/)(?:collections?|product-categories?|categories|category|cat|browse|search|catalog|department)(?:\/|$)/i,
};

const SITE_PRODUCT_PAGE_RULES = {
    "abt.com": {
        strict: true,
        productPath: /\/p\/\d+\.html$/i,
        categoryPath: /\/c\/\d+\.html$/i,
    },
    "academy.com": {
        strict: true,
        productPath: /^\/p\/[^/]+$/i,
    },
    "adorama.com": {
        strict: true,
        productPath: /\/p\/[^/]+$/i,
    },
    "advanceautoparts.com": {
        strict: true,
        productPath: /^\/p\/[^/]+\/[^/]+-P$/i,
        categoryPath: /^\/c\d+\//i,
    },
    "ae.com": {
        strict: true,
        productPath: /\/p\//i,
        categoryPath: /\/c\//i,
    },
    "alibaba.com": {
        strict: true,
        productPath: /\/product-detail\/.+\.html$/i,
        categoryPath: /\/trade\/search/i,
    },
    "asos.com": {
        strict: true,
        productPath: /\/prd\//i,
        categoryPath: /\/cat\//i,
    },
    "backmarket.com": {
        strict: true,
        productPath: /\/p\/[^/]+/i,
        categoryPath: /\/l\//i,
    },
    "bestbuy.com": {
        strict: true,
        productPath: /(?:\/product\/[^/]+\/[^/]+|\/site\/[^/]+\/\d+\.p)/i,
        categoryPath: /\/site\/searchpage|\/browse\//i,
    },
    "bhphotovideo.com": {
        strict: true,
        productPath: /\/c\/product\//i,
        categoryPath: /\/c\/buy\//i,
    },
    "brooksbrothers.com": {
        strict: true,
        productPath: /\/[^/]+\/[A-Za-z0-9]+\.html$/i,
    },
    "burton.com": {
        strict: true,
        productPath: /\/p\//i,
        categoryPath: /\/c\//i,
    },
    "carhartt.com": {
        strict: true,
        productPath: /\/product\/[^/]+\/[^/]+/i,
    },
    "cdw.com": {
        strict: true,
        productPath: /\/product\/[^/]+\/[^/]+/i,
        categoryPath: /\/category\//i,
    },
    "chewy.com": {
        strict: true,
        productPath: /\/dp\/\d+/i,
        categoryPath: /^\/b\//i,
    },
    "clinique.com": {
        strict: true,
        productPath: /^\/product\//i,
    },
    "colourpop.com": {
        strict: true,
        productPath: /\/products\/[^/]+\/?$/i,
        categoryPath: /\/collections\//i,
    },
    "columbia.com": {
        strict: true,
        productPath: /\/p\/[^/]+\.html$/i,
        categoryPath: /\/c\//i,
    },
    "containerstore.com": {
        strict: true,
        categoryPath: /^\/s\/.+\/\d+\/?$/i,
        productPath: /^\/s\/(?:[^/]+\/)+[^/]*[a-zA-Z][^/]*\/?$/i,
        productSearch: URL_PRODUCT_SIGNALS.productSearch,
    },
    "converse.com": {
        strict: true,
        productPath: /^\/shop\/p\/[^/]+\/[^/]+\.html$/i,
        categoryPath: /^\/shop\/?$|^\/shop\/(?!p\/)/i,
    },
    "crutchfield.com": {
        strict: true,
        productPath: /^\/p_[^/]+\/[^/]+\.html$/i,
        categoryPath: /^\/g_[^/]+\/[^/]+\.html$/i,
    },
    "cvs.com": {
        strict: true,
        productPath: /^\/shop\/[^/]+-prodid-\d+\/?$/i,
        categoryPath: /^\/shop\/(?!.*-prodid-\d)[^/]+\/?$/i,
    },
    "dell.com": {
        strict: true,
        productPath: /\/spd\//i,
        categoryPath: /\/scr\//i,
    },
    "fergusonhome.com": {
        strict: true,
        productPath: /\/[^/]+\/s\d+/i,
    },
    "americantrucks.com": {
        strict: true,
        productPath: /-s\d+\.html$/i,
    },
    "autoanything.com": {
        strict: false,
        productPath: /-s\d+\.html$/i,
    },
};

function _urlSignalsVerdict(pathname, search, signals) {
    if (signals.categoryPath?.test(pathname)) {
        return false;
    }
    if (signals.productSearch?.test(search)) {
        return true;
    }
    if (signals.productPath?.test(pathname)) {
        return true;
    }
    return null;
}

class PageDetector {
    static _rootDomainForRules(hostname) {
        const host = (hostname || "").toLowerCase().replace(/^www\./, "");
        if (!host) return null;
        for (const root of Object.keys(SITE_PRODUCT_PAGE_RULES)) {
            if (host === root || host.endsWith(`.${root}`)) {
                return root;
            }
        }
        return null;
    }

    /** @returns {boolean | null} null = no site-specific rule applies */
    static _siteProductPageVerdict(url) {
        const root = PageDetector._rootDomainForRules(new URL(url).hostname);
        if (!root) return null;

        const rules = SITE_PRODUCT_PAGE_RULES[root];
        const parsed = new URL(url);
        const verdict = _urlSignalsVerdict(parsed.pathname, parsed.search, rules);
        if (verdict !== null) {
            return verdict;
        }
        if (rules.strict) {
            return false;
        }
        return null;
    }

    /** Fallback for supported retailers without strict site rules. */
    static _genericUrlVerdict(url) {
        const parsed = new URL(url);
        return _urlSignalsVerdict(parsed.pathname, parsed.search, URL_PRODUCT_SIGNALS);
    }

    static isProductPage() {
        if (!SupportedSites.isCurrentSiteSupported()) return false;

        const url = window.location.href;
        const siteVerdict = PageDetector._siteProductPageVerdict(url);
        if (siteVerdict !== null) {
            return siteVerdict;
        }

        const genericUrlVerdict = PageDetector._genericUrlVerdict(url);
        if (genericUrlVerdict !== null) {
            return genericUrlVerdict;
        }

        const ogType = document.querySelector('meta[property="og:type"]');
        if (ogType && (ogType.content === "product" || ogType.content.includes("product"))) {
            return true;
        }

        const addToCartRegex = /add\s*(?:to\s*)?(?:cart|bag|basket)|buy\s*now/i;
        const buttons = Array.from(document.querySelectorAll("button, a, input"));
        for (const btn of buttons) {
            const textToTest = btn.innerText || btn.value || btn.id || btn.name;
            if (textToTest && addToCartRegex.test(textToTest)) return true;
        }
        return false;
    }
}
