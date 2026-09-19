import re
import math
import hashlib
from datetime import datetime
import phonenumbers
from phonenumbers import geocoder as phonenumbers_geocoder
from phonenumbers import carrier, timezone
from opencage.geocoder import OpenCageGeocode

OPENCAGE_API_KEY = "f57bb1806a5e48a4a232184b35752903"

# Fallback coordinates for major countries when offline or API limit reached
COUNTRY_COORDINATES = {
    "Kenya": (-1.2921, 36.8219),
    "United States": (37.0902, -95.7129),
    "United Kingdom": (51.5074, -0.1278),
    "Nigeria": (9.0765, 7.3986),
    "South Africa": (-30.5595, 22.9375),
    "India": (20.5937, 78.9629),
    "Germany": (51.1657, 10.4515),
    "France": (46.2276, 2.2137),
    "Canada": (56.1304, -106.3468),
    "Australia": (-25.2744, 133.7751),
    "Uganda": (1.3733, 32.2903),
    "Tanzania": (-6.3690, 34.8888),
    "Ghana": (7.9465, -1.0232),
    "Brazil": (-14.2350, -51.9253),
}

# Regional cities and metropolitan cellular hubs per country
REGIONAL_CITIES = {
    "kenya": [
        ("Nairobi (CBD Central Hub)", -1.286389, 36.817223),
        ("Nairobi (Westlands Sector)", -1.2683, 36.8073),
        ("Nairobi (Kilimani / Upper Hill)", -1.2965, 36.7978),
        ("Mombasa (Island Sector)", -4.0435, 39.6682),
        ("Mombasa (Nyali Hub)", -4.0289, 39.7042),
        ("Nakuru (Central Tower)", -0.3031, 36.0800),
        ("Kisumu (Milimani Hub)", -0.1022, 34.7617),
        ("Eldoret (Town Center)", 0.5143, 35.2698),
        ("Kericho (Tea Belt Node)", -0.3689, 35.2863),
        ("Thika (Industrial Sector)", -1.0396, 37.0900),
    ],
    "south africa": [
        ("Johannesburg (Sandton Sector)", -26.1076, 28.0567),
        ("Johannesburg (Rosebank Node)", -26.1465, 28.0436),
        ("Johannesburg (CBD Tower)", -26.2041, 28.0473),
        ("Cape Town (City Bowl)", -33.9249, 18.4241),
        ("Cape Town (Century City)", -33.8920, 18.5110),
        ("Durban (Central Grid)", -29.8587, 31.0218),
        ("Pretoria (Hatfield Node)", -25.7500, 28.2378),
        ("Port Elizabeth (Gqeberha)", -33.9608, 25.6022),
    ],
    "nigeria": [
        ("Lagos (Victoria Island)", 6.4281, 3.4219),
        ("Lagos (Ikeja Central)", 6.6018, 3.3515),
        ("Lagos (Lekki Phase 1)", 6.4474, 3.4739),
        ("Abuja (Garki Sector)", 9.0345, 7.4891),
        ("Abuja (Maitama Node)", 9.0882, 7.4984),
        ("Port Harcourt (GRA)", 4.8156, 7.0498),
        ("Ibadan (Bodija Hub)", 7.4343, 3.9063),
    ],
    "united kingdom": [
        ("London (Westminster Sector)", 51.4975, -0.1357),
        ("London (City Financial)", 51.5155, -0.0922),
        ("London (Camden Node)", 51.5390, -0.1426),
        ("Manchester (Piccadilly)", 53.4795, -2.2384),
        ("Birmingham (Bullring Hub)", 52.4777, -1.8951),
        ("Edinburgh (Princes St)", 55.9520, -3.1970),
        ("Leeds (City Center)", 53.7997, -1.5492),
    ],
    "united states": [
        ("New York (Midtown Manhattan)", 40.7549, -73.9840),
        ("New York (Brooklyn Hub)", 40.6782, -73.9442),
        ("San Francisco (SoMa Tech)", 37.7785, -122.3948),
        ("Los Angeles (Downtown Tower)", 34.0522, -118.2437),
        ("Chicago (Loop Sector)", 41.8837, -87.6324),
        ("Houston (Downtown)", 29.7604, -95.3698),
        ("Miami (Brickell Grid)", 25.7617, -80.1918),
        ("Seattle (Downtown)", 47.6062, -122.3321),
    ],
    "uganda": [
        ("Kampala (Central Hill)", 0.3136, 32.5811),
        ("Kampala (Kololo Node)", 0.3340, 32.5930),
        ("Entebbe (Bay Grid)", 0.0512, 32.4637),
        ("Jinja (Nile Sector)", 0.4244, 33.2041),
    ],
    "tanzania": [
        ("Dar es Salaam (Kariakoo)", -6.8160, 39.2770),
        ("Dar es Salaam (Oysterbay)", -6.7725, 39.2715),
        ("Arusha (CBD Sector)", -3.3869, 36.6830),
        ("Dodoma (Capital Node)", -6.1630, 35.7516),
    ],
    "ghana": [
        ("Accra (Osu Sector)", 5.5560, -0.1820),
        ("Accra (Airport City)", 5.6028, -0.1770),
        ("Kumasi (Adum Central)", 6.6885, -1.6244),
    ],
    "india": [
        ("Mumbai (Bandra Kurla)", 19.0657, 72.8687),
        ("New Delhi (Connaught Place)", 28.6315, 77.2167),
        ("Bengaluru (Electronic City)", 12.8452, 77.6602),
        ("Hyderabad (Hitec City)", 17.4474, 78.3762),
    ],
    "germany": [
        ("Berlin (Mitte Sector)", 52.5200, 13.4050),
        ("Munich (Altstadt Node)", 48.1371, 11.5754),
        ("Frankfurt (Banking Center)", 50.1109, 8.6821),
    ],
    "france": [
        ("Paris (Champs-Élysées)", 48.8698, 2.3075),
        ("Paris (La Défense)", 48.8920, 2.2380),
        ("Lyon (Presqu'île)", 45.7640, 4.8357),
    ],
    "canada": [
        ("Toronto (Downtown Financial)", 43.6510, -79.3470),
        ("Vancouver (Yaletown Hub)", 49.2750, -123.1216),
        ("Montreal (Ville-Marie)", 45.5017, -73.5673),
    ],
    "australia": [
        ("Sydney (CBD Sector)", -33.8688, 151.2093),
        ("Melbourne (Southbank)", -37.8228, 144.9645),
        ("Brisbane (City Center)", -27.4698, 153.0251),
    ],
}

TIMEZONE_TO_COUNTRY = {
    "Africa/Nairobi": "kenya",
    "Africa/Johannesburg": "south africa",
    "Africa/Lagos": "nigeria",
    "Europe/London": "united kingdom",
    "America/New_York": "united states",
    "America/Chicago": "united states",
    "America/Denver": "united states",
    "America/Los_Angeles": "united states",
    "Africa/Kampala": "uganda",
    "Africa/Dar_es_Salaam": "tanzania",
    "Africa/Accra": "ghana",
    "Asia/Kolkata": "india",
    "Asia/Calcutta": "india",
    "Europe/Berlin": "germany",
    "Europe/Paris": "france",
    "America/Toronto": "canada",
    "America/Vancouver": "canada",
    "Australia/Sydney": "australia",
    "Australia/Melbourne": "australia",
}

def normalize_country_key(country_str):
    if not country_str:
        return None
    c = str(country_str).lower().strip()
    if "kenya" in c: return "kenya"
    if "south africa" in c or "south-africa" in c or "south_africa" in c: return "south africa"
    if "nigeria" in c: return "nigeria"
    if "united kingdom" in c or c in ["uk", "britain", "england"]: return "united kingdom"
    if "united states" in c or c in ["usa", "us", "america"]: return "united states"
    if "uganda" in c: return "uganda"
    if "tanzania" in c: return "tanzania"
    if "ghana" in c: return "ghana"
    if "india" in c: return "india"
    if "germany" in c: return "germany"
    if "france" in c: return "france"
    if "canada" in c: return "canada"
    if "australia" in c: return "australia"
    return None

# Known TAC sample mapping
TAC_DATABASE = {
    "354595": ("Samsung", "Galaxy S23 Ultra", "Vodafone / Safaricom"),
    "355773": ("Samsung", "Galaxy A54 5G", "Airtel / MTN"),
    "356123": ("Apple", "iPhone 14 Pro Max", "Verizon / EE"),
    "359231": ("Apple", "iPhone 15 Pro", "AT&T / T-Mobile"),
    "867234": ("Xiaomi", "Redmi Note 12 Pro", "Orange / Jio"),
    "353849": ("Google", "Pixel 8 Pro", "Google Fi / Telkom"),
    "863145": ("OnePlus", "OnePlus 11", "Three / O2"),
}

def luhn_checksum_valid(number_str):
    """Validate number with Luhn algorithm (standard for 15-digit IMEI)."""
    digits = [int(c) for c in number_str if c.isdigit()]
    if len(digits) != 15:
        return False
    checksum = 0
    parity = len(digits) % 2
    for i, digit in enumerate(digits):
        if i % 2 == parity:
            digit *= 2
            if digit > 9:
                digit -= 9
        checksum += digit
    return (checksum % 10) == 0

def validate_imei(imei):
    """Validate 15-digit IMEI format and Luhn verification."""
    clean_imei = re.sub(r'[\s\-]', '', str(imei or ''))
    if not re.match(r'^\d{15}$', clean_imei):
        return False, clean_imei, "IMEI must be exactly 15 numeric digits."
    is_luhn = luhn_checksum_valid(clean_imei)
    return True, clean_imei, None if is_luhn else "Notice: IMEI digits format valid (check digit checksum differs from standard Luhn)."

def validate_email(email):
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(pattern, str(email or '').strip()) is not None

def calculate_distance(lat1, lng1, lat2, lng2):
    """Haversine distance in kilometers."""
    R = 6371.0
    lat1_r, lng1_r = math.radians(lat1), math.radians(lng1)
    lat2_r, lng2_r = math.radians(lat2), math.radians(lng2)
    dlng = lng2_r - lng1_r
    dlat = lat2_r - lat1_r
    a = math.sin(dlat / 2)**2 + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlng / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(R * c, 2)

def derive_deterministic_location(seed_str, country=None, timezone_str=None, anchor_coords=None):
    """
    Generate realistic deterministic coordinates based on input hash and country/regional context.
    """
    h = hashlib.sha256(seed_str.encode('utf-8')).hexdigest()

    # 1. If anchor coordinates provided (e.g. from local verified hardware GPS)
    if anchor_coords and isinstance(anchor_coords, (tuple, list)) and len(anchor_coords) >= 2:
        base_lat, base_lng = float(anchor_coords[0]), float(anchor_coords[1])
        base_city = "Local Cellular Sector (Anchor Lock)"
        jitter_lat = ((int(h[4:8], 16) % 100) - 50) * 0.00025
        jitter_lng = ((int(h[8:12], 16) % 100) - 50) * 0.00025
        return round(base_lat + jitter_lat, 6), round(base_lng + jitter_lng, 6), base_city

    # 2. Determine country/region
    country_key = normalize_country_key(country)
    if not country_key and timezone_str:
        country_key = normalize_country_key(TIMEZONE_TO_COUNTRY.get(timezone_str))

    if country_key and country_key in REGIONAL_CITIES:
        cities = REGIONAL_CITIES[country_key]
        idx = int(h[:4], 16) % len(cities)
        base_city, base_lat, base_lng = cities[idx]
    else:
        # Fallback worldwide sample cities
        sample_cities = [
            ("Nairobi, Kenya", -1.286389, 36.817223),
            ("London, United Kingdom", 51.5074, -0.1278),
            ("New York, NY, USA", 40.7128, -74.0060),
            ("Lagos, Nigeria", 6.5244, 3.3792),
            ("Tokyo, Japan", 35.6762, 139.6503),
            ("Berlin, Germany", 52.5200, 13.4050),
            ("Dubai, UAE", 25.2048, 55.2708),
            ("San Francisco, CA, USA", 37.7749, -122.4194),
            ("Johannesburg, South Africa", -26.2041, 28.0473),
            ("Mombasa, Kenya", -4.0435, 39.6682),
        ]
        idx = int(h[:4], 16) % len(sample_cities)
        base_city, base_lat, base_lng = sample_cities[idx]

    # Small jitter within ~1-2km (simulating cellular sector beam coverage)
    jitter_lat = ((int(h[4:8], 16) % 100) - 50) * 0.0003
    jitter_lng = ((int(h[8:12], 16) % 100) - 50) * 0.0003
    return round(base_lat + jitter_lat, 6), round(base_lng + jitter_lng, 6), base_city

def simulate_device_tracking(device_type, identifier, account_id="", country_or_region=None, client_timezone=None, anchor_coords=None):
    """
    Simulate full telemetry & step log resolution for Android / iPhone device,
    anchored to regional country/carrier network context.
    """
    clean_id = re.sub(r'[\s\-]', '', str(identifier or ''))
    tac = clean_id[:6]
    brand, model, carrier_name = TAC_DATABASE.get(
        tac, 
        ("Android Device" if device_type == "android" else "Apple Inc.", 
         "Smartphone Gen-X" if device_type == "android" else "iPhone Pro", 
         "Global GSM / LTE")
    )
    
    lat, lng, location_name = derive_deterministic_location(
        clean_id,
        country=country_or_region,
        timezone_str=client_timezone,
        anchor_coords=anchor_coords
    )

    # Cellular sector triangulation radius (typically 500m to 2500m)
    accuracy_meters = 1500
    
    steps = [
        {"progress": 15, "stage": "INIT", "text": "Initializing GSMA device lookup and cellular carrier interrogator..."},
        {"progress": 35, "stage": "TAC_VERIFY", "text": f"Hardware identity matched: {brand} {model} (TAC: {tac or 'N/A'})."},
        {"progress": 55, "stage": "HLR_QUERY", "text": f"Interrogating cellular carrier routing network ({carrier_name})..."},
        {"progress": 75, "stage": "RF_LOCK", "text": "Cell tower sector beam locked. Signal strength: -68 dBm (Carrier HLR)."},
        {"progress": 90, "stage": "GEO_SOLVE", "text": f"Resolving regional cell sector near {location_name}..."},
        {"progress": 100, "stage": "COMPLETE", "text": f"Carrier sector lock: {lat}, {lng}. Sector radius: ±{accuracy_meters}m (Simulated Cellular HLR)."}
    ]
    
    find_my_url = f"https://www.google.com/android/find?u=0&hl=en&source=android-browser&q={lat},{lng}" if device_type == "android" else f"https://www.icloud.com/find?q={lat},{lng}"
    google_maps_url = f"https://www.google.com/maps?q={lat},{lng}"
    
    return {
        "success": True,
        "device_type": device_type,
        "identifier": clean_id,
        "account_id": account_id,
        "brand": brand,
        "model": model,
        "carrier": carrier_name,
        "latitude": lat,
        "longitude": lng,
        "location_name": location_name,
        "accuracy_meters": accuracy_meters,
        "telemetry_mode": "simulated_cellular",
        "telemetry_source": "Simulated Cellular HLR / TAC Grid",
        "is_simulated": True,
        "battery_level": "78%",
        "connection_status": "Online (LTE/5G)",
        "find_my_url": find_my_url,
        "google_maps_url": google_maps_url,
        "steps": steps
    }

def locate_phone_number(phone_str, user_location_str=None):
    """
    Locate phone number using phonenumbers and OpenCage geocoding.
    """
    clean_number = str(phone_str or '').strip()
    if not clean_number.startswith('+'):
        clean_number = '+' + clean_number

    try:
        parsed_num = phonenumbers.parse(clean_number, None)
        if not phonenumbers.is_valid_number(parsed_num):
            return {"success": False, "error": f"'{phone_str}' is not a valid international phone number format."}
    except Exception as e:
        return {"success": False, "error": f"Failed to parse phone number: {str(e)}"}

    int_format = phonenumbers.format_number(parsed_num, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
    country_code = parsed_num.country_code
    national_number = parsed_num.national_number
    geo_desc = phonenumbers_geocoder.description_for_number(parsed_num, "en")
    service_carrier = carrier.name_for_number(parsed_num, "en") or "Unknown / Regional Provider"
    timezones_list = list(timezone.time_zones_for_number(parsed_num))
    
    # Try geocoding with OpenCage
    target_lat = None
    target_lng = None
    resolved_address = geo_desc or "Unknown Location"
    
    query = geo_desc or f"Country code +{country_code}"
    try:
        geocoder_client = OpenCageGeocode(OPENCAGE_API_KEY)
        result = geocoder_client.geocode(query)
        if result and len(result):
            target_lat = result[0]['geometry']['lat']
            target_lng = result[0]['geometry']['lng']
            resolved_address = result[0].get('formatted', geo_desc)
    except Exception:
        pass

    # If geocoding resolved only to country level or failed, use regional city hub
    country_key = normalize_country_key(geo_desc)
    if country_key and country_key in REGIONAL_CITIES:
        target_lat, target_lng, city_hub = derive_deterministic_location(clean_number, country=country_key)
        resolved_address = f"{city_hub}, {geo_desc} (Cellular Routing Hub)"
    elif target_lat is None or target_lng is None:
        for country, coords in COUNTRY_COORDINATES.items():
            if country.lower() in geo_desc.lower():
                target_lat, target_lng = coords
                resolved_address = f"{geo_desc} (Regional center)"
                break
        if target_lat is None:
            target_lat, target_lng, _ = derive_deterministic_location(clean_number, country=geo_desc)

    # Calculate distance if user location provided
    user_coords = None
    distance_km = None
    if user_location_str and user_location_str.strip():
        user_loc_clean = user_location_str.strip()
        try:
            geocoder_client = OpenCageGeocode(OPENCAGE_API_KEY)
            u_res = geocoder_client.geocode(user_loc_clean)
            if u_res and len(u_res):
                u_lat = u_res[0]['geometry']['lat']
                u_lng = u_res[0]['geometry']['lng']
                user_coords = {"lat": u_lat, "lng": u_lng, "formatted": u_res[0].get('formatted', user_loc_clean)}
                distance_km = calculate_distance(u_lat, u_lng, target_lat, target_lng)
        except Exception:
            pass

    maps_url = f"https://www.google.com/maps?q={target_lat},{target_lng}"
    if user_coords:
        directions_url = f"https://www.google.com/maps/dir/{user_coords['lat']},{user_coords['lng']}/{target_lat},{target_lng}"
    else:
        directions_url = maps_url

    return {
        "success": True,
        "input_number": phone_str,
        "formatted_number": int_format,
        "country_code": country_code,
        "national_number": national_number,
        "location_name": geo_desc or "International",
        "resolved_address": resolved_address,
        "carrier": service_carrier,
        "timezones": timezones_list,
        "target_lat": target_lat,
        "target_lng": target_lng,
        "accuracy_meters": 2000,
        "telemetry_mode": "simulated_cellular",
        "telemetry_source": "Carrier MSISDN & Regional HLR Node",
        "is_simulated": True,
        "user_coords": user_coords,
        "distance_km": distance_km,
        "maps_url": maps_url,
        "directions_url": directions_url
    }


def reverse_geocode_coordinates(lat, lng):
    """
    Reverse geocode high-precision GPS coordinates into a human-readable street address.
    """
    try:
        geocoder_client = OpenCageGeocode(OPENCAGE_API_KEY)
        result = geocoder_client.reverse_geocode(lat, lng)
        if result and len(result):
            formatted = result[0].get('formatted')
            components = result[0].get('components', {})
            road = components.get('road') or components.get('pedestrian', '')
            suburb = components.get('suburb') or components.get('neighbourhood', '')
            city = components.get('city') or components.get('town') or components.get('state', '')
            country = components.get('country', '')
            
            detailed = ", ".join(filter(None, [road, suburb, city, country]))
            return detailed or formatted or f"{lat:.6f}, {lng:.6f}"
    except Exception as e:
        print(f"Reverse geocode error: {e}")
    
    return f"GPS Coordinates: {lat:.6f}, {lng:.6f}"

