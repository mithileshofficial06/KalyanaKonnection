from flask import Blueprint, jsonify, request

from app.services.maps_service import geocode_place, suggest_places


common = Blueprint("common", __name__)


@common.route("/location/suggest")
def location_suggest():
    query = (request.args.get("q") or "").strip()
    return jsonify({"suggestions": suggest_places(query, limit=6)})


@common.route("/location/geocode")
def location_geocode():
    query = (request.args.get("q") or "").strip()
    geo = geocode_place(query)
    if not geo:
        return jsonify({"ok": False, "message": "Location not found"}), 404

    return jsonify({"ok": True, "location": geo})
