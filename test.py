import json
from vin_parser import parse_gibdd_response, search_reviews_enhanced, search_board_journals

data = json.load(open("gibdd_response.json"))          # ваш JSON
vehicle_info = parse_gibdd_response(data["response"])   # VehicleInfo
reviews = search_reviews_enhanced({"vehicle_info": vehicle_info, "max_reviews": 20})
journals = search_board_journals({"vehicle_info": vehicle_info, "max_entries": 20})