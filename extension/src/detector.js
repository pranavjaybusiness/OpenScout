// Per-retailer URL rules. strict: true → only productPath counts; skip generic heuristics.

/** Shared path/query signals for site rules and fallback detection (non-strict sites). */
const URL_PRODUCT_SIGNALS = {
    productSearch: /(?:^|[?&])(?:productId|product_id|itemId|item_id)=/i,
    productPath:
        /(?:\/products?\/|\/p\/|\/prd\/|\/dp\/|\/ip\/|\/product-detail\/|\/gp\/product\/)/i,
    categoryPath:
        /(?:^|\/)(?:collections?|product-categories?|categories|category|cat|browse|search|catalog|department)(?:\/|$)/i,
};

/**
 * URL patterns shared verbatim by multiple retailers. Reusing one RegExp
 * instance is safe here because none use the global flag (matching is
 * stateless), so a single definition keeps the per-site rules below DRY.
 */
const SHARED_PATHS = {
    // Product paths
    P_SLASH: /\/p\//i, //                      ae, burton
    P_SLASH_ANY: /^\/p\/.+$/i, //              vitaminshoppe, worldmarket
    PRODUCT_SLASH_PAIR: /\/product\/[^/]+\/[^/]+/i, // carhartt, cdw
    PRODUCTS_SLUG: /^\/products\/[^/]+\/?$/i, // fentybeauty, glossier
    DASH_S_NUM_HTML: /-s\d+\.html$/i, //       americantrucks, autoanything
    // Category paths
    C_SLASH: /\/c\//i, //                      ae, burton, columbia
    C_SLASH_START: /^\/c\//i, //               dermstore, iherb, overstock
    C_SLASH_ANY: /^\/c\/.+$/i, //              target, vitaminshoppe, worldmarket
    B_START: /^\/b\//i, //                     chewy, homedepot
    SHOP_START: /^\/shop(?:\/|$)/i, //         landsend, patagonia
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
        productPath: SHARED_PATHS.P_SLASH,
        categoryPath: SHARED_PATHS.C_SLASH,
    },
    "alibaba.com": {
        strict: true,
        productPath: /\/product-detail\/.+\.html$/i,
        categoryPath: /\/trade\/search/i,
    },
    "amazon.com": {
        strict: true,
        // PDP only: /dp/ASIN, /gp/product/ASIN, /gp/aw/d/ASIN (not /s search or browse hubs).
        productPath: /(?:\/dp\/|\/gp\/(?:product\/|aw\/d\/))[A-Z0-9]{10}/i,
        categoryPath:
            /^\/(?:s|b|hz|cart|events|deals|stores|alm|shop|fresh|wholefoods|clothing|prime)(?:\/|$)|^\/gp\/(?:browse|bestsellers|new-releases|goldbox|help|video|warehouse-deals|coupon)/i,
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
        productPath: SHARED_PATHS.P_SLASH,
        categoryPath: SHARED_PATHS.C_SLASH,
    },
    "carhartt.com": {
        strict: true,
        productPath: SHARED_PATHS.PRODUCT_SLASH_PAIR,
    },
    "cdw.com": {
        strict: true,
        productPath: SHARED_PATHS.PRODUCT_SLASH_PAIR,
        categoryPath: /\/category\//i,
    },
    "chewy.com": {
        strict: true,
        productPath: /\/dp\/\d+/i,
        categoryPath: SHARED_PATHS.B_START,
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
        categoryPath: SHARED_PATHS.C_SLASH,
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
    "dermstore.com": {
        strict: true,
        productPath: /^\/p\/[^/]+\/\d+\/?$/i,
        categoryPath: SHARED_PATHS.C_SLASH_START,
    },
    "dickssportinggoods.com": {
        strict: true,
        productPath: /^\/p\/[^/]+\/[A-Za-z0-9]+\/?$/i,
        categoryPath: /^\/f\//i,
    },
    "duluthtrading.com": {
        strict: false,
        productPath: /^\/s\/DTC\/[^/]+-\d+\.html$/i,
    },
    "ebay.com": {
        strict: true,
        productPath: /^\/itm\//i,
        categoryPath: /^\/(?:sch|b|e|deals|globaldeals)\//i,
    },
    "esteelauder.com": {
        strict: true,
        productPath: /^\/product\/\d+\/\d+\//i,
    },
    "fentybeauty.com": {
        strict: true,
        productPath: SHARED_PATHS.PRODUCTS_SLUG,
    },
    "flightclub.com": {
        strict: false,
        productPath: /^\/[^/]+-[a-z]{1,4}\d{3,}[a-z0-9-]*\/?$/i,
    },
    "freepeople.com": {
        strict: false,
        productPath: /^\/shop\/[^/]+\/?$/i,
    },
    "gap.com": {
        strict: true,
        productPath: /^\/browse\/product\.do$/i,
    },
    "glossier.com": {
        strict: true,
        productPath: SHARED_PATHS.PRODUCTS_SLUG,
    },
    "gnc.com": {
        strict: true,
        productPath: /^\/[^/]+\/\d+\.html$/i,
        categoryPath: /^\/brands\//i,
    },
    "hm.com": {
        strict: true,
        productPath: /^\/[a-z]{2}_[a-z]{2}\/productpage\.\d+\.html$/i,
        categoryPath: /^\/[a-z]{2}_[a-z]{2}\/(?!productpage\.\d+\.html$).+\.html$/i,
    },
    "hollisterco.com": {
        strict: true,
        productPath: /^\/shop\/[a-z]{2}\/p\/[^/]+\/?$/i,
        categoryPath: /^\/shop\/[a-z]{2}\/(?!p\/).+/i,
    },
    "homedepot.com": {
        strict: true,
        productPath: /^\/p\/[^/]+\/\d+\/?$/i,
        categoryPath: SHARED_PATHS.B_START,
    },
    "hp.com": {
        strict: true,
        productPath: /^\/[a-z]{2}-[a-z]{2}\/shop\/pdp\//i,
        categoryPath: /^\/[a-z]{2}-[a-z]{2}\/shop\/(?:mlp|mdp)\//i,
    },
    "hydroflask.com": {
        strict: true,
        productPath: /^\/(?!shop\/)[^/]+\/?$/i,
        categoryPath: /^\/shop\//i,
    },
    "iherb.com": {
        strict: true,
        productPath: /^\/pr\//i,
        categoryPath: SHARED_PATHS.C_SLASH_START,
    },
    "jcpenney.com": {
        strict: true,
        productPath: /^\/p\//i,
        categoryPath: /^\/g\//i,
    },
    "jcrew.com": {
        strict: true,
        productPath: /^\/[mw]\/.+\/[A-Z0-9]{4,}(?:\/)?$/i,
        categoryPath: /^\/plp(?:\/|$)/i,
        productSearch: /(?:^|[?&])colorProductCode=/i,
    },
    "kiehls.com": {
        strict: true,
        productPath: /\/\d+\.html$/i,
        categoryPath: /\/view-all(?:-|\/|$)/i,
        productSearch: /(?:^|[?&])dwvar_/i,
    },
    "landsend.com": {
        strict: true,
        productPath: /^\/products\/.+\/id_\d+/i,
        categoryPath: SHARED_PATHS.SHOP_START,
    },
    "lego.com": {
        strict: true,
        productPath: /^\/[a-z]{2}-[a-z]{2}\/product\/[^/]+-\d+(?:\/)?$/i,
        categoryPath: /^\/[a-z]{2}-[a-z]{2}\/themes(?:\/|$)/i,
    },
    "lenovo.com": {
        strict: true,
        productPath: /^\/[a-z]{2}\/[a-z]{2}\/p\/.+$/i,
        categoryPath: /^\/[a-z]{2}\/[a-z]{2}\/(?!p\/).+/i,
    },
    "llbean.com": {
        strict: true,
        productPath: /^\/llb\/shop\/\d{7,}(?:\/)?$/i,
        categoryPath: /^\/llb\/shop\/\d{1,6}(?:\/)?$/i,
    },
    "lowes.com": {
        strict: true,
        productPath: /^\/pd\/[^/]+\/\d+(?:\/)?$/i,
        categoryPath: /^\/pl(?:\/|$)/i,
    },
    "lulus.com": {
        strict: true,
        productPath: /^\/products\/[^/]+\/\d+\.html$/i,
        categoryPath: /^\/(?:categories|shop|collections)(?:\/|$)/i,
    },
    "lush.com": {
        strict: true,
        productPath: /^\/[a-z]{2}\/[a-z]{2}(?:_[a-z]{2})?\/p\/[^/]+\/?$/i,
        categoryPath: /^\/[a-z]{2}\/[a-z]{2}(?:_[a-z]{2})?\/s(?:\/|$)/i,
    },
    "maccosmetics.com": {
        strict: true,
        productPath: /^\/product\/\d+\/\d+\/products\/.+$/i,
        categoryPath: /^\/(?!product\/)[^?]+$/i,
    },
    "madewell.com": {
        strict: true,
        productPath: /^\/p\/.+\/[A-Z0-9]+(?:\/)?$/i,
        categoryPath: /^\/(?!p\/).+$/i,
    },
    "microcenter.com": {
        strict: true,
        productPath: /^\/product\/\d+\/[^/]+\/?$/i,
    },
    "microsoft.com": {
        strict: true,
        productPath: /^\/[a-z]{2}-[a-z]{2}\/store\/configure\/[^/]+\/[^/]+\/?$/i,
        categoryPath: /^\/[a-z]{2}-[a-z]{2}\/store\/b\/.+$/i,
    },
    "oreillyauto.com": {
        strict: true,
        productPath: /^\/detail\/.+$/i,
        categoryPath: /^\/shop\/b\/.+$/i,
    },
    "overstock.com": {
        strict: true,
        productPath: /\/product\.html$/i,
        categoryPath: SHARED_PATHS.C_SLASH_START,
    },
    "patagonia.com": {
        strict: true,
        productPath: /^\/product\/.+\/\d+\.html$/i,
        categoryPath: SHARED_PATHS.SHOP_START,
        productSearch: /(?:^|[?&])dwvar_/i,
    },
    "petco.com": {
        strict: true,
        productPath: /^\/product\/[^/]+\/?$/i,
        categoryPath: /^\/category\/.+$/i,
    },
    "playstation.com": {
        strict: true,
        productPath: /^\/[a-z]{2}-[a-z]{2}\/buy-[^/]+\/[^/]+\/?$/i,
        categoryPath: /^\/[a-z]{2}-[a-z]{2}\/hardware\/.+$/i,
    },
    "puma.com": {
        strict: true,
        productPath: /^\/[a-z]{2}\/[a-z]{2}\/pd\/[^/]+\/\d+\/?$/i,
        categoryPath: /^\/[a-z]{2}\/[a-z]{2}\/(?!pd\/).+$/i,
    },
    "raymourflanigan.com": {
        strict: true,
        productPath: /^\/[^/]+\/[^/]+\/[^/]+-\d+\/?$/i,
    },
    "reebok.com": {
        strict: true,
        productPath: /^\/collections\/[^/]+\/products\/[^/]+\/?$/i,
        categoryPath: /^\/collections\/[^/]+\/?$/i,
    },
    "roomstogo.com": {
        strict: true,
        productPath: /^\/furniture\/product\/[^/]+\/\d+\/?$/i,
        categoryPath: /^\/furniture\/(?!product\/).+$/i,
    },
    "sallybeauty.com": {
        strict: true,
        productPath: /\/SBS-\d+\.html$/i,
        categoryPath: /^\/hair-color\/?$/i,
    },
    "samsung.com": {
        strict: true,
        productPath:
            /^\/us\/(?:[^/]+\/[^/]+\/[^/]+|[^/]+\/[^/]*-sku-[^/]+|(?:[^/]+\/)+buy\/[^/]+)\/?$/i,
        categoryPath: /^\/us\/[^/]+\/all-[^/]+\/?$/i,
    },
    "skechers.com": {
        strict: true,
        productPath: /^\/[^/]+\/[A-Za-z0-9]+_[A-Za-z0-9]+\.html$/i,
        categoryPath: /^\/(?:technologies|collections|sale|men|women|kids)(?:\/|$)/i,
    },
    "sony.com": {
        strict: true,
        productPath: /^\/.+\/p\/[a-z0-9]+\/?$/i,
        categoryPath: /^\/.+\/c\/.+$/i,
    },
    "target.com": {
        strict: true,
        productPath: /^\/p\/.+\/-\/A-\d+\/?$/i,
        categoryPath: SHARED_PATHS.C_SLASH_ANY,
    },
    "ulta.com": {
        strict: true,
        productPath: /^\/p\/[^/]+\/?$/i,
        categoryPath: /^\/shop\/.+$/i,
        productSearch: /(?:^|[?&])sku=/i,
    },
    "underarmour.com": {
        strict: true,
        productPath: /^\/[a-z]{2}-[a-z]{2}\/p\/.+\.html$/i,
        categoryPath: /^\/[a-z]{2}-[a-z]{2}\/c\/.+$/i,
    },
    "uniqlo.com": {
        strict: true,
        productPath: /^\/[a-z]{2}\/[a-z]{2}\/products\/.+$/i,
    },
    "vans.com": {
        strict: true,
        productPath: /^\/[a-z]{2}-[a-z]{2}\/p\/.+$/i,
        categoryPath: /^\/[a-z]{2}-[a-z]{2}\/c\/.+$/i,
    },
    "vitaminshoppe.com": {
        strict: true,
        productPath: SHARED_PATHS.P_SLASH_ANY,
        categoryPath: SHARED_PATHS.C_SLASH_ANY,
    },
    "walgreens.com": {
        strict: true,
        productPath: /\/store\/c\/.+\/ID=prod\d+-product$/i,
        categoryPath: /^\/store\/c\/productlist\//i,
    },
    "worldmarket.com": {
        strict: true,
        productPath: SHARED_PATHS.P_SLASH_ANY,
        categoryPath: SHARED_PATHS.C_SLASH_ANY,
    },
    "wrangler.com": {
        strict: true,
        productPath: /^\/shop\/[^/]+\.html$/i,
        categoryPath: /^\/shop\/[^/]+(?<!\.html)\/?$/i,
        productSearch: /(?:^|[?&])dwvar_/i,
    },
    "fergusonhome.com": {
        strict: true,
        productPath: /\/[^/]+\/s\d+/i,
    },
    "americantrucks.com": {
        strict: true,
        productPath: SHARED_PATHS.DASH_S_NUM_HTML,
    },
    "autoanything.com": {
        strict: false,
        productPath: SHARED_PATHS.DASH_S_NUM_HTML,
    },
};

function _urlSignalsVerdict(pathname, search, signals) {
    // Never treat a site's root URL as a product page.
    if (pathname === "/") {
        return false;
    }
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
