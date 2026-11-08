from datetime import date

from .parse import normalize


class FakeDiscovery:
    """Synthetic examples only; never evidence of live race dates."""

    async def __call__(self, query: str, hints: dict) -> list[dict]:
        if not any(hints.get(k) for k in ["distance", "city", "country", "months"]):
            return []
        fixtures = [
            ("Milan", "Italy", "marathon", 4, 8),
            ("Rome", "Italy", "marathon", 3, 18),
            ("Florence", "Italy", "marathon", 5, 12),
            ("Zermatt", "Switzerland", "trail", 7, 10),
            ("Lausanne", "Switzerland", "trail", 6, 20),
            ("Interlaken", "Switzerland", "trail", 8, 15),
            ("Lisbon", "Portugal", "half", 3, 14),
            ("Chamonix", "France", "ultra", None, None),
        ]
        results = []
        months = hints.get("months", [])
        for city, country, distance, month, day in fixtures:
            if any(
                hints.get(k) and normalize(hints[k]) != normalize(v)
                for k, v in [("city", city), ("country", country), ("distance", distance)]
            ):
                continue
            matching = [m for m in months if int(m[-2:]) == month]
            if months and not matching:
                continue
            year = int(matching[0][:4]) if matching else hints.get("year", 2027)
            race_date = date(year, month, day) if month else None
            results.append(
                {
                    "id": city.lower(),
                    "name": f"[Synthétique / Synthetic] {city} {distance}",
                    "edition": str(year),
                    "distance_km": {"marathon": 42.195, "half": 21.1, "trail": 30, "ultra": 80}[
                        distance
                    ],
                    "distance_label": {
                        "marathon": "Marathon",
                        "half": "Semi-marathon",
                        "trail": "Trail 30 km",
                        "ultra": "Ultra 80 km",
                    }[distance],
                    "city": city,
                    "country": country,
                    "race_date": race_date.isoformat() if race_date else None,
                    "date_status": "unverified" if race_date else "unknown",
                    "official_url": f"https://example.org/{city.lower()}",
                    "source_urls": ["https://example.org/synthetic"],
                    "synthetic": True,
                }
            )
        return results
