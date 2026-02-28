from functools import lru_cache

import requests


NOMINATIM_BASE = "https://nominatim.openstreetmap.org"
USER_AGENT = "kalyana-connection/1.0"


@lru_cache(maxsize=256)
def geocode_place(location_query: str):
	query = (location_query or "").strip()
	if not query:
		return None

	try:
		response = requests.get(
			f"{NOMINATIM_BASE}/search",
			params={
				"q": query,
				"format": "json",
				"addressdetails": 1,
				"limit": 1,
				"countrycodes": "in",
			},
			headers={"User-Agent": USER_AGENT},
			timeout=12,
		)
		response.raise_for_status()
	except requests.RequestException:
		return None

	items = response.json() or []
	if not items:
		return None

	item = items[0]
	return {
		"display_name": item.get("display_name") or query,
		"lat": float(item.get("lat")),
		"lon": float(item.get("lon")),
	}


def suggest_places(partial_query: str, limit: int = 6):
	query = (partial_query or "").strip()
	if not query:
		return []

	try:
		response = requests.get(
			f"{NOMINATIM_BASE}/search",
			params={
				"q": query,
				"format": "json",
				"addressdetails": 1,
				"limit": max(1, min(limit, 10)),
				"countrycodes": "in",
			},
			headers={"User-Agent": USER_AGENT},
			timeout=12,
		)
		response.raise_for_status()
	except requests.RequestException:
		return []

	output = []
	for row in response.json() or []:
		display_name = row.get("display_name")
		if display_name:
			output.append(display_name)

	seen = set()
	unique = []
	for label in output:
		key = label.lower()
		if key in seen:
			continue
		seen.add(key)
		unique.append(label)

	return unique[:limit]
