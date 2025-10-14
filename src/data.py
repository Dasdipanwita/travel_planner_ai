# src/data.py

MOCK_DARJEELING_DB = {
    "points_of_interest": [
        {"id": 1, "name": "Tiger Hill Sunrise Point", "type": "nature", "avg_time_min": 90, "cost": 40, "open": 4, "close": 18},
        {"id": 2, "name": "Batasia Loop", "type": "culture", "avg_time_min": 60, "cost": 20, "open": 5, "close": 20},
        {"id": 3, "name": "Padmaja Naidu Himalayan Zoological Park", "type": "nature", "avg_time_min": 180, "cost": 100, "open": 8, "close": 16},
        {"id": 4, "name": "Himalayan Mountaineering Institute", "type": "culture", "avg_time_min": 120, "cost": 60, "open": 9, "close": 17},
        {"id": 5, "name": "Keventer's Cafe", "type": "food", "avg_time_min": 75, "cost": 500, "open": 8, "close": 20},
        {"id": 6, "name": "Glenary's Bakery & Cafe", "type": "food", "avg_time_min": 90, "cost": 600, "open": 8, "close": 21},
        {"id": 7, "name": "Mahakal Temple", "type": "culture", "avg_time_min": 45, "cost": 0, "open": 6, "close": 19},
        {"id": 8, "name": "Darjeeling Ropeway", "type": "activity", "avg_time_min": 60, "cost": 250, "open": 10, "close": 16},
        {"id": 9, "name": "Local Momos Stall (Street Food)", "type": "food", "avg_time_min": 30, "cost": 150, "open": 11, "close": 21},
        {"id": 10, "name": "Chowrasta Mall Road", "type": "activity", "avg_time_min": 120, "cost": 0, "open": 0, "close": 24},
    ],
    "accommodation": [
        {"id": 101, "name": "Zostel Darjeeling", "type": "hostel", "cost_per_night": 700},
        {"id": 102, "name": "Wanderers Hostel", "type": "hostel", "cost_per_night": 650},
    ],
    "transport": {
        "shared_jeep": {"cost_per_trip": 30},
        "private_taxi": {"cost_per_trip": 200},
        "walk": {"cost_per_trip": 0}
    }
}