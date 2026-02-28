from app.services.maps_service import geocode_place
from app.utils.haversine import haversine_km


def filter_surplus_by_location(surplus_rows, receiver_location_query: str, radius_km: float):
	geo = geocode_place(receiver_location_query)
	if not geo:
		return [], None

	receiver_lat = geo["lat"]
	receiver_lon = geo["lon"]
	matched = []

	for row in surplus_rows:
		if row.provider_latitude is None or row.provider_longitude is None:
			continue

		distance = haversine_km(receiver_lat, receiver_lon, row.provider_latitude, row.provider_longitude)
		if distance <= radius_km:
			row.computed_distance_km = round(distance, 1)
			matched.append(row)

	matched.sort(key=lambda item: item.computed_distance_km)
	return matched, geo
