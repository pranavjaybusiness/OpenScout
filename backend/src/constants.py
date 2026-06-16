import os
from pathlib import Path

from dotenv import load_dotenv

# Repo root .env (OpenScout/.env) — works whether the server is started from / or /backend
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(_REPO_ROOT / ".env")


def _env(name: str, default: str = "") -> str:
    return (os.environ.get(name) or default).strip()


# Gemini
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# CloudWatch custom metrics
OPENSCOUT_METRIC_NAMESPACE = _env("OPENSCOUT_METRIC_NAMESPACE", "OpenScout")
FEEDBACK_MATCH_YES_METRIC = "FeedbackMatchYes"
FEEDBACK_MATCH_NO_METRIC = "FeedbackMatchNo"
FEEDBACK_NO_RESPONSE_METRIC = "FeedbackNoResponse"
NEGATIVE_MATCH_FEEDBACK_METRIC = "NegativeMatchFeedback"

# Optional comma-separated browser origins, e.g. chrome-extension://YOUR_EXTENSION_ID
OPENSCOUT_ALLOWED_ORIGINS = [
    part.strip()
    for part in _env("OPENSCOUT_ALLOWED_ORIGINS").split(",")
    if part.strip()
]

# Marketplace toggles (set to "false" in .env to skip during dev)
ENABLE_EBAY = _env("OPENSCOUT_ENABLE_EBAY").lower() != "false"
ENABLE_SHOPPING = _env("OPENSCOUT_ENABLE_SHOPPING").lower() != "false"

# eBay Browse API
EBAY_CLIENT_ID = os.environ.get("EBAY_CLIENT_ID")
EBAY_CLIENT_SECRET = os.environ.get("EBAY_CLIENT_SECRET")
EBAY_MARKETPLACE_ID = os.environ.get("EBAY_MARKETPLACE_ID", "EBAY_US")

# eBay Partner Network affiliate
EBAY_AFFILIATE_CAMPID = _env("EBAY_AFFILIATE_CAMPID")
EBAY_AFFILIATE_MKRID = _env("EBAY_AFFILIATE_MKRID")
EBAY_AFFILIATE_TOOLID = _env("EBAY_AFFILIATE_TOOLID")
EBAY_AFFILIATE_MKEVT = _env("EBAY_AFFILIATE_MKEVT")
EBAY_AFFILIATE_MKCID = _env("EBAY_AFFILIATE_MKCID")
EBAY_AFFILIATE_CUSTOMID = _env("EBAY_AFFILIATE_CUSTOMID")
EBAY_AFFILIATE_SITEID = _env("EBAY_AFFILIATE_SITEID")

# SearchAPI.io — Google Shopping
SEARCHAPI_API_KEY = os.environ.get("SEARCHAPI_API_KEY")
GOOGLE_SHOPPING_GL = _env("GOOGLE_SHOPPING_GL", "us")
GOOGLE_SHOPPING_HL = _env("GOOGLE_SHOPPING_HL", "en")
GOOGLE_SHOPPING_LOCATION = _env("GOOGLE_SHOPPING_LOCATION", "United States")
GOOGLE_SHOPPING_PRODUCT_ENGINE = _env("GOOGLE_SHOPPING_PRODUCT_ENGINE", "google_product")

# SHEIN KOC affiliate (no SHEIN API call; applied to SHEIN URLs returned by Google Shopping)
SHEIN_DOMAIN = _env("SHEIN_DOMAIN", "us.shein.com")
SHEIN_AFFILIATE_KOC_ID = _env("SHEIN_AFFILIATE_KOC_ID")
SHEIN_AFFILIATE_CAMPAIGN_ID = _env("SHEIN_AFFILIATE_CAMPAIGN_ID")
SHEIN_AFFILIATE_ONELINK = _env("SHEIN_AFFILIATE_ONELINK")
