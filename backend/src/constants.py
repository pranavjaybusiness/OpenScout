import os
from pathlib import Path

from dotenv import load_dotenv

# Repo root .env (OpenScout/.env) — works whether the server is started from / or /backend
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(_REPO_ROOT / ".env")


def _env(name: str) -> str:
    return (os.environ.get(name) or "").strip()


GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# CloudWatch custom metrics
OPENSCOUT_METRIC_NAMESPACE = _env("OPENSCOUT_METRIC_NAMESPACE") or "OpenScout"
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

EBAY_CLIENT_ID = os.environ.get("EBAY_CLIENT_ID")
EBAY_CLIENT_SECRET = os.environ.get("EBAY_CLIENT_SECRET")
EBAY_MARKETPLACE_ID = os.environ.get("EBAY_MARKETPLACE_ID", "EBAY_US")


def is_ebay_affiliate_configured() -> bool:
    """Affiliate wrapping runs only when EBAY_AFFILIATE_CAMPID is set in .env."""
    return bool(_env("EBAY_AFFILIATE_CAMPID"))


def ebay_affiliate_query_params(*, mkrid_override: str | None = None) -> list[tuple[str, str]] | None:
    """
    EPN query parameters for listing URLs, or None when affiliate is not configured.

    Returns ordered pairs per eBay's documented affiliate URL structure.
    """
    campid = _env("EBAY_AFFILIATE_CAMPID")
    if not campid:
        return None

    mkrid = _env("EBAY_AFFILIATE_MKRID") or mkrid_override or "711-53200-19255-0"
    toolid = _env("EBAY_AFFILIATE_TOOLID") or "10001"

    params: list[tuple[str, str]] = [
        ("mkevt", _env("EBAY_AFFILIATE_MKEVT") or "1"),
        ("mkcid", _env("EBAY_AFFILIATE_MKCID") or "1"),
        ("mkrid", mkrid),
        ("campid", campid),
        ("toolid", toolid),
    ]

    # Sub-ID for EPN reports (filter by Custom ID to verify OpenScout traffic).
    customid = _env("EBAY_AFFILIATE_CUSTOMID") or "openscout"
    params.append(("customid", customid))

    # Not in the core EPN table but present in EPN Link Generator output; set if you use it.
    siteid = _env("EBAY_AFFILIATE_SITEID")
    if siteid:
        params.append(("siteid", siteid))

    return params
