from datetime import datetime, timezone

def _parse_steam_release_date(release_data: dict) -> datetime | None:
    """Parse release date from Steam API response."""
    if not release_data:
        return None
    # Steam returns release_date as a dict with 'date' and 'coming_soon' fields
    date_str = release_data.get("date")
    coming_soon = release_data.get("coming_soon", False)
    if coming_soon or not date_str:
        return None
    # Date format examples: "Oct 21, 2022", "21 Oct, 2022", "2022-10-21"
    formats = [
        "%b %d, %Y",
        "%d %b, %Y",
        "%Y-%m-%d",
        "%B %d, %Y",
        "%d %B, %Y",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None