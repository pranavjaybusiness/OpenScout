"""Append eBay Partner Network (EPN) tracking parameters to listing URLs.

Spec: https://developer.ebay.com/api-docs/buy/static/ref-epn-link.html
Primary structure:
  {target}&mkevt=1&mkcid=1&mkrid={rotation}&campid={id}&toolid={id}&customid={optional}
"""

from __future__ import annotations

from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from src.constants import (
    EBAY_AFFILIATE_CAMPID,
    EBAY_AFFILIATE_CUSTOMID,
    EBAY_AFFILIATE_MKCID,
    EBAY_AFFILIATE_MKEVT,
    EBAY_AFFILIATE_MKRID,
    EBAY_AFFILIATE_SITEID,
    EBAY_AFFILIATE_TOOLID,
)

# EPN-owned query keys — stripped before re-applying so tags are not duplicated.
_EPN_QUERY_KEYS = frozenset(
    {"mkcid", "mkrid", "siteid", "campid", "toolid", "mkevt", "customid", "amdata"}
)

# Rotation IDs by eBay marketplace host (from EPN documentation).
_MKRID_BY_HOST: dict[str, str] = {
    "ebay.com": "711-53200-19255-0",
    "ebay.at": "5221-53469-19255-0",
    "ebay.com.au": "705-53470-19255-0",
    "ebay.be": "1553-53471-19255-0",
    "ebay.ca": "706-53473-19255-0",
    "ebay.ch": "5222-53480-19255-0",
    "ebay.de": "707-53477-19255-0",
    "ebay.es": "1185-53479-19255-0",
    "ebay.fr": "709-53476-19255-0",
    "ebay.ie": "5282-53468-19255-0",
    "ebay.co.uk": "710-53481-19255-0",
    "ebay.it": "724-53478-19255-0",
    "ebay.nl": "1346-53482-19255-0",
    "ebay.pl": "4908-226936-19255-0",
}


def _host_mkrid(netloc: str) -> str | None:
    host = (netloc or "").lower().replace("www.", "")
    return _MKRID_BY_HOST.get(host)


def _epn_query_params(mkrid_override: str | None = None) -> list[tuple[str, str]] | None:
    """EPN params per eBay's affiliate URL structure, or None when not configured."""
    if not EBAY_AFFILIATE_CAMPID:
        return None

    params: list[tuple[str, str]] = [
        ("mkevt", EBAY_AFFILIATE_MKEVT or "1"),
        ("mkcid", EBAY_AFFILIATE_MKCID or "1"),
        ("mkrid", EBAY_AFFILIATE_MKRID or mkrid_override or "711-53200-19255-0"),
        ("campid", EBAY_AFFILIATE_CAMPID),
        ("toolid", EBAY_AFFILIATE_TOOLID or "10001"),
        ("customid", EBAY_AFFILIATE_CUSTOMID or "openscout"),
    ]
    if EBAY_AFFILIATE_SITEID:
        params.append(("siteid", EBAY_AFFILIATE_SITEID))
    return params


def wrap_ebay_affiliate_url(url: str) -> str:
    """
    Add EPN parameters when affiliate env is configured; otherwise return url unchanged.
    """
    if not (url or "").strip():
        return url

    parsed = urlparse(url.strip())
    if "ebay." not in (parsed.netloc or "").lower():
        return url

    epn = _epn_query_params(mkrid_override=_host_mkrid(parsed.netloc))
    if epn is None:
        return url

    kept = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if key.lower() not in _EPN_QUERY_KEYS
    ]
    query = urlencode([*kept, *epn])

    return urlunparse(
        (
            parsed.scheme or "https",
            parsed.netloc,
            parsed.path,
            "",
            query,
            "",
        )
    )
