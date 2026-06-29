"""Apply Gemini bucket verdicts to collected marketplace listings."""


def _valid_indices(raw_indices: object, candidate_count: int) -> list[int]:
    if not isinstance(raw_indices, list):
        return []
    out: list[int] = []
    seen: set[int] = set()
    for item in raw_indices:
        if not isinstance(item, int) or not (0 <= item < candidate_count):
            continue
        if item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


def _parse_close_matches(raw: object, candidate_count: int) -> list[tuple[int, str]]:
    if not isinstance(raw, list):
        return []
    out: list[tuple[int, str]] = []
    seen: set[int] = set()
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        index = entry.get("index")
        if not isinstance(index, int) or not (0 <= index < candidate_count):
            continue
        if index in seen:
            continue
        seen.add(index)
        difference = (entry.get("difference") or "").strip()
        out.append((index, difference))
    return out


def listings_from_bucket_verdict(
    bucket_candidates: list[dict],
    bucket_verdict: dict,
    *,
    source: str = "",
    bucket: str = "",
) -> list[dict]:
    """Return every exact (or close) match Gemini approved in this bucket."""
    reason = (bucket_verdict.get("reason") or "").strip()[:2000]

    exact_indices = _valid_indices(
        bucket_verdict.get("exact_indices"), len(bucket_candidates)
    )
    if not exact_indices and bucket_verdict.get("exact_index") is not None:
        legacy = bucket_verdict.get("exact_index")
        if isinstance(legacy, int) and 0 <= legacy < len(bucket_candidates):
            exact_indices = [legacy]

    close_matches = _parse_close_matches(
        bucket_verdict.get("close_matches"), len(bucket_candidates)
    )
    if not close_matches and exact_indices == []:
        close_index = bucket_verdict.get("close_index")
        close_difference = (bucket_verdict.get("close_difference") or "").strip()
        if isinstance(close_index, int) and 0 <= close_index < len(bucket_candidates):
            close_matches = [(close_index, close_difference)]

    # An index marked exact takes precedence over the same index marked close.
    exact_set = set(exact_indices)

    listings: list[dict] = []

    for index in exact_indices:
        listing = dict(bucket_candidates[index])
        listing["match_quality"] = "exact"
        if source:
            listing["source"] = source
        if bucket:
            listing["condition_bucket"] = bucket
        if reason:
            listing["gemini_match_reason"] = reason
        listings.append(listing)

    # Close matches surface ALONGSIDE exact matches (different-variant alternatives,
    # e.g. another color). build_alternatives later drops close matches that are not
    # cheaper than the best exact match.
    for index, difference in close_matches:
        if index in exact_set:
            continue
        listing = dict(bucket_candidates[index])
        listing["match_quality"] = "close"
        listing["close_match_note"] = (
            difference
            or "Different color/finish from what you're viewing."
        )
        if source:
            listing["source"] = source
        if bucket:
            listing["condition_bucket"] = bucket
        if reason:
            listing["gemini_match_reason"] = reason
        listings.append(listing)

    return listings


def listing_from_bucket_verdict(
    bucket_candidates: list[dict], bucket_verdict: dict
) -> dict | None:
    """First match in a bucket (legacy single-pick)."""
    matches = listings_from_bucket_verdict(bucket_candidates, bucket_verdict)
    return matches[0] if matches else None
