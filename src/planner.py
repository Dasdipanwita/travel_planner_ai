# src/planner.py
import logging
import math
from typing import Any, Dict, List, Optional

import requests

from src.config import Config
from src.llm_handler import call_llm_for_refinement

logger = logging.getLogger(__name__)


def _geocode_destination(destination: str, api_key: str) -> Dict[str, Any]:
    """Resolve a destination to coordinates using Geoapify with a Nominatim fallback."""
    headers = {"User-Agent": "NomadAI/1.0"}

    try:
        geocode_resp = requests.get(
            "https://api.geoapify.com/v1/geocode/search",
            params={"text": destination, "apiKey": api_key},
            headers=headers,
            timeout=10,
        )
        if geocode_resp.status_code == 200:
            geocode_response = geocode_resp.json()
            features = geocode_response.get("features") or []
            if features:
                coordinates = features[0].get("geometry", {}).get("coordinates", [])
                if len(coordinates) >= 2:
                    return {"lng": coordinates[0], "lat": coordinates[1], "source": "geoapify"}
            logger.warning("Geoapify geocoding returned no results for '%s'", destination)
        else:
            logger.warning("Geoapify geocoding failed for '%s' with status %s", destination, geocode_resp.status_code)
    except requests.exceptions.RequestException:
        logger.exception("Geoapify geocoding request failed for '%s'", destination)

    try:
        fallback_resp = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": destination, "format": "json", "limit": 1},
            headers=headers,
            timeout=10,
        )
        if fallback_resp.status_code == 200:
            fallback_results = fallback_resp.json()
            if fallback_results:
                first = fallback_results[0]
                return {
                    "lng": float(first["lon"]),
                    "lat": float(first["lat"]),
                    "source": "nominatim",
                }
        logger.warning("Nominatim geocoding returned no results for '%s'", destination)
    except (requests.exceptions.RequestException, ValueError, KeyError, TypeError):
        logger.exception("Nominatim geocoding request failed for '%s'", destination)

    return {"error": "Could not geocode the destination. Please check the destination name."}


def _haversine_km(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """Calculate great-circle distance between two points (km)."""
    lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))
    km = 6371 * c
    return km


def _safe_lower(value: Any) -> str:
    return str(value or "").lower()


def fetch_real_data(destination: str, interests: Optional[List[str]] = None) -> Dict[str, Any]:
    """Fetch real data from Geoapify API for the given destination.

    Uses interests to limit category queries when possible.
    """
    api_key = Config.GEOAPIFY_API_KEY
    if not api_key:
        return {"error": "Geoapify API key is missing. Please set it in your .env file."}

    try:
        location_data = _geocode_destination(destination, api_key)
        if "error" in location_data:
            return location_data

        lng = location_data["lng"]
        lat = location_data["lat"]
        location = [lng, lat]

        category_mapping = {
            "nature": "natural",
            "culture": "tourism.sights,entertainment.museum",
            "food": "catering.restaurant,catering.cafe",
            "activity": "activity,entertainment",
        }

        points_of_interest = []
        id_counter = 1
        selected_interests = interests if interests else list(category_mapping.keys())
        categories_to_fetch = ",".join([category_mapping[i] for i in selected_interests if i in category_mapping])

        places_url = f"https://api.geoapify.com/v2/places?categories={categories_to_fetch}&filter=circle:{lng},{lat},5000&limit=20&apiKey={api_key}"
        places_response = requests.get(places_url).json()

        if places_response.get("features"):
            for place in places_response["features"]:
                props = place["properties"]
                place_type = "activity"
                for interest, geo_cat in category_mapping.items():
                    if any(cat in props.get("categories", []) for cat in geo_cat.split(",")):
                        place_type = interest
                        break

                def get_real_activity_cost(place_type, props, destination):
                    destination_lower = _safe_lower(destination)
                    real_price = None

                    price_fields = [
                        props.get("price"), props.get("entrance_fee"), props.get("fee"),
                        props.get("cost"), props.get("rate"), props.get("charge"),
                    ]

                    for field in price_fields:
                        if field:
                            price_str = str(field).replace("₹", "").replace("$", "").replace("USD", "").replace("INR", "").replace("free", "0")
                            try:
                                extracted_price = float(price_str)
                                if 0 <= extracted_price <= 1000:
                                    real_price = extracted_price
                                    break
                            except ValueError:
                                continue

                    if real_price is None:
                        if place_type == "food":
                            if "restaurant" in str(props.get("categories", "")).lower():
                                if destination_lower in ["delhi", "mumbai", "bangalore"]:
                                    return 300
                                return 200
                            return 150

                        if place_type == "culture":
                            place_name = _safe_lower(props.get("name", ""))
                            if any(word in place_name for word in ["museum", "fort", "palace", "temple"]):
                                if destination_lower in ["kashmir", "rajasthan", "kerala"]:
                                    return 200
                                return 100
                            return 50

                        if place_type == "activity":
                            place_name = _safe_lower(props.get("name", ""))
                            if any(word in place_name for word in ["trekking", "boating", "rafting", "camping"]):
                                if destination_lower in ["kashmir", "himachal", "kerala"]:
                                    return 500
                                return 300
                            return 150

                        place_name = _safe_lower(props.get("name", ""))
                        if any(word in place_name for word in ["national park", "sanctuary", "garden"]):
                            return 100
                        return 20

                    return int(real_price) if real_price is not None else 0

                activity_cost = get_real_activity_cost(place_type, props, destination)
                poi = {
                    "id": id_counter,
                    "name": props.get("name", props.get("street", "Unknown Place")),
                    "type": place_type,
                    "avg_time_min": 60,
                    "cost": activity_cost,
                    "open": 9,
                    "close": 18,
                }
                points_of_interest.append(poi)
                id_counter += 1

        accommodation = []

        def get_accommodation_cost(destination):
            destination_lower = _safe_lower(destination)
            if destination_lower in ["kashmir", "goa", "kerala", "rajasthan", "himachal pradesh"]:
                return 800
            if destination_lower in ["delhi", "mumbai", "bangalore", "chennai", "kolkata", "pune"]:
                return 600
            if destination_lower in ["shimla", "manali", "darjeeling", "ooty", "nainital"]:
                return 700
            if destination_lower in ["jaipur", "agra", "varanasi", "amritsar", "mysore"]:
                return 550
            return 400

        hostel_url = f"https://api.geoapify.com/v2/places?categories=accommodation.hostel&filter=circle:{lng},{lat},5000&limit=2&apiKey={api_key}"
        hostel_response = requests.get(hostel_url).json()

        if hostel_response.get("features"):
            for place in hostel_response["features"]:
                props = place["properties"]
                base_price = 400
                price_indicators = [
                    props.get("price"),
                    props.get("price_range"),
                    props.get("cost"),
                    props.get("rate"),
                ]

                for indicator in price_indicators:
                    if indicator:
                        price_str = str(indicator).replace("₹", "").replace("$", "").replace("USD", "").replace("INR", "")
                        try:
                            extracted_price = float(price_str)
                            if 100 <= extracted_price <= 2000:
                                base_price = extracted_price
                                break
                        except ValueError:
                            continue

                if base_price == 400:
                    base_price = get_accommodation_cost(destination)

                acc = {
                    "id": id_counter,
                    "name": props.get("name", "Hostel"),
                    "type": "hostel",
                    "cost_per_night": int(base_price),
                }
                accommodation.append(acc)
                id_counter += 1
        else:
            accommodation.append({
                "id": id_counter,
                "name": "Standard Hostel",
                "type": "hostel",
                "cost_per_night": get_accommodation_cost(destination),
            })
            id_counter += 1

        def calculate_transport_costs(destination, location_data):
            destination_lower = _safe_lower(destination)
            lng, lat = location_data

            if destination_lower in ["kashmir", "himachal pradesh", "uttarakhand"]:
                return {
                    "shared_taxi": {"cost_per_trip": 80, "description": "Shared taxi (sumo/tempo)"},
                    "local_bus": {"cost_per_trip": 40, "description": "Local bus"},
                    "auto_rickshaw": {"cost_per_trip": 30, "description": "Auto rickshaw"},
                    "private_taxi": {"cost_per_trip": 400, "description": "Private taxi (full day)"},
                }
            if destination_lower in ["delhi", "mumbai", "bangalore", "chennai", "kolkata", "pune"]:
                return {
                    "metro": {"cost_per_trip": 30, "description": "Metro rail"},
                    "local_bus": {"cost_per_trip": 25, "description": "City bus"},
                    "auto_rickshaw": {"cost_per_trip": 50, "description": "Auto rickshaw"},
                    "ride_share": {"cost_per_trip": 100, "description": "Uber/Ola"},
                    "private_taxi": {"cost_per_trip": 300, "description": "Private taxi"},
                }
            if destination_lower in ["goa", "kerala"]:
                return {
                    "local_bus": {"cost_per_trip": 35, "description": "Local bus"},
                    "auto_rickshaw": {"cost_per_trip": 40, "description": "Auto rickshaw"},
                    "scooter_rental": {"cost_per_trip": 200, "description": "Scooter rental (per day)"},
                    "private_taxi": {"cost_per_trip": 250, "description": "Private taxi"},
                }
            return {
                "local_bus": {"cost_per_trip": 30, "description": "Local bus"},
                "auto_rickshaw": {"cost_per_trip": 35, "description": "Auto rickshaw"},
                "shared_taxi": {"cost_per_trip": 50, "description": "Shared taxi"},
                "private_taxi": {"cost_per_trip": 200, "description": "Private taxi"},
            }

        transport = calculate_transport_costs(destination, location)

        return {
            "points_of_interest": points_of_interest,
            "accommodation": accommodation,
            "transport": transport,
        }

    except requests.exceptions.RequestException as e:
        return {"error": f"Network error while fetching data: {e}"}
    except Exception as e:
        return {"error": f"An unexpected error occurred: {e}"}


def retrieve_candidates(interests, db):
    """Filters POIs based on user interests."""
    return [poi for poi in db["points_of_interest"] if poi["type"] in interests]


def cost_estimator(plan_activities, db, days):
    """Estimates the total cost of a structured plan."""
    total_cost = 0

    accommodation_cost = 0
    if db.get("accommodation"):
        hostel_cost = db["accommodation"][0]["cost_per_night"]
        accommodation_cost = hostel_cost * (days - 1)
        total_cost += accommodation_cost
        print(f"🏨 Accommodation: {accommodation_cost} (₹{hostel_cost}/night × {days-1} nights)")

    activity_cost = 0
    for item in plan_activities:
        item_cost = item.get("cost", 0)
        activity_cost += item_cost
        if item_cost > 0:
            print(f"🎯 Activity {item.get('name', 'Unknown')}: ₹{item_cost}")
    total_cost += activity_cost

    trips_per_day = max(0, (len(plan_activities) / days) - 1)
    transport_options = db["transport"]
    available_transport = [t for t in transport_options.values() if t["cost_per_trip"] > 0]

    if available_transport:
        cheapest_transport = min(available_transport, key=lambda x: x["cost_per_trip"])
        transport_cost_per_trip = cheapest_transport["cost_per_trip"]
        transport_type = next(t for t in transport_options.keys() if transport_options[t] == cheapest_transport)
        print(f"🚗 Using {transport_type}: ₹{transport_cost_per_trip} per trip")
    else:
        transport_cost_per_trip = 0
        print("🚶 No paid transport options available")

    transport_cost = transport_cost_per_trip * trips_per_day * days
    total_cost += transport_cost
    print(f"💰 Total estimated cost: ₹{total_cost}")

    return total_cost


def generate_itinerary(user_request):
    """Main orchestrator function for generating the travel plan."""
    db = fetch_real_data(user_request["destination"], user_request.get("interests"))

    if not db or (isinstance(db, dict) and "error" in db):
        return db

    candidates = retrieve_candidates(user_request["interests"], db)
    if not candidates:
        return {"error": "No activities found for the selected interests."}

    days = user_request["duration_days"]
    pois_per_day = (len(candidates) + days - 1) // days

    structured_plan = {}
    for i in range(days):
        day_pois = candidates[i * pois_per_day:(i + 1) * pois_per_day]
        structured_plan[f"day{i + 1}"] = day_pois

    refined_itinerary = call_llm_for_refinement(structured_plan, user_request)
    if "error" in refined_itinerary:
        return refined_itinerary

    estimated_cost = cost_estimator(candidates, db, days)
    num_people = int(user_request.get("num_people", 1) or 1)
    refined_itinerary["estimated_total_cost"] = f"₹{estimated_cost:,.2f}"
    refined_itinerary["estimated_per_person"] = f"₹{(estimated_cost / num_people):,.2f}"
    refined_itinerary["estimate_range"] = f"₹{estimated_cost * 0.90:,.2f} - ₹{estimated_cost * 1.15:,.2f}"
    refined_itinerary["budget_compliance"] = "✅ Within Budget" if estimated_cost <= user_request["budget_inr"] else "⚠️ Over Budget"
    refined_itinerary["has_beach"] = any(poi.get("is_beach") for poi in db.get("points_of_interest", []))

    return refined_itinerary
