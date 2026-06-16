"""SHEIN KOC affiliate link wrapping (used by marketplace/offer_links).

No SHEIN search API is called; this only tags SHEIN URLs returned by Google Shopping.
"""

from src.services.shein.affiliate import wrap_shein_affiliate_url

__all__ = ["wrap_shein_affiliate_url"]
