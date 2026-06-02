"""Append eBay Partner Network (EPN) tracking parameters to listing URLs.

Spec: https://developer.ebay.com/api-docs/buy/static/ref-epn-link.html
Primary structure:
  {target}&mkevt=1&mkcid=1&mkrid={rotation}&campid={id}&toolid={id}&customid={optional}
"""

from __future__ import annotations

from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from src.constants import ebay_affiliate_query_params

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


def wrap_ebay_affiliate_url(url: str) -> str:
    """
    Add EPN parameters when affiliate env is configured; otherwise return url unchanged.
    """
    if not (url or "").strip():
        return url

    parsed = urlparse(url.strip())
    if "ebay." not in (parsed.netloc or "").lower():
        return url

    epn = ebay_affiliate_query_params(mkrid_override=_host_mkrid(parsed.netloc))
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
