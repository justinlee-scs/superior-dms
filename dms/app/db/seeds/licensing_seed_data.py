"""
Seed data for BC Business License Tracking.

Source: Official list of BC regional districts and municipalities
(BC Ministry of Municipal Affairs / Statistics Canada 2021 census boundaries).

This is intentionally exhaustive — every incorporated municipality in BC
(cities, district municipalities, towns, villages, and special designations)
is included, mapped to its regional district.

NOTE: This list reflects BC's municipal structure as of the 2021 census.
Boundaries/incorporations change occasionally (rare) - if a new municipality
incorporates or one dissolves, add/remove it via the admin UI rather than
editing this seed file, since the seed only runs once (or via --reset).
"""

# Official BC Regional Districts (27 standard + 2 special-status areas)
# Names match the legally defined administrative area names.
REGIONAL_DISTRICTS = [
    "Alberni-Clayoquot",
    "Bulkley-Nechako",
    "Capital",
    "Cariboo",
    "Central Coast",
    "Central Kootenay",
    "Central Okanagan",
    "Columbia Shuswap",
    "Comox Valley",
    "Cowichan Valley",
    "East Kootenay",
    "Fraser Valley",
    "Fraser-Fort George",
    "Kitimat-Stikine",
    "Kootenay Boundary",
    "Metro Vancouver",
    "Mount Waddington",
    "Nanaimo",
    "North Coast",
    "North Okanagan",
    "Okanagan-Similkameen",
    "Peace River",
    "qathet",
    "Squamish-Lillooet",
    "Strathcona",
    "Sunshine Coast",
    "Thompson-Nicola",
    # Special status areas (not standard regional districts, but function
    # similarly for administrative/licensing purposes):
    "Northern Rockies",   # Single-municipality regional municipality
    "Stikine Region",     # Unincorporated, no municipalities - included for completeness
]

# municipality_name, type, regional_district
# type values: City, District Municipality, Town, Village, Island Municipality,
#              Mountain Resort Municipality, Resort Municipality,
#              Indian Government District
MUNICIPALITIES = [
    # --- Cities ---
    ("Abbotsford", "City", "Fraser Valley"),
    ("Armstrong", "City", "North Okanagan"),
    ("Burnaby", "City", "Metro Vancouver"),
    ("Campbell River", "City", "Strathcona"),
    ("Castlegar", "City", "Central Kootenay"),
    ("Chilliwack", "City", "Fraser Valley"),
    ("Colwood", "City", "Capital"),
    ("Coquitlam", "City", "Metro Vancouver"),
    ("Courtenay", "City", "Comox Valley"),
    ("Cranbrook", "City", "East Kootenay"),
    ("Dawson Creek", "City", "Peace River"),
    ("Delta", "City", "Metro Vancouver"),
    ("Duncan", "City", "Cowichan Valley"),
    ("Enderby", "City", "North Okanagan"),
    ("Fernie", "City", "East Kootenay"),
    ("Fort St. John", "City", "Peace River"),
    ("Grand Forks", "City", "Kootenay Boundary"),
    ("Greenwood", "City", "Kootenay Boundary"),
    ("Kamloops", "City", "Thompson-Nicola"),
    ("Kelowna", "City", "Central Okanagan"),
    ("Kimberley", "City", "East Kootenay"),
    ("Langford", "City", "Capital"),
    ("Langley", "City", "Metro Vancouver"),
    ("Maple Ridge", "City", "Metro Vancouver"),
    ("Merritt", "City", "Thompson-Nicola"),
    ("Mission", "City", "Fraser Valley"),
    ("Nanaimo", "City", "Nanaimo"),
    ("Nelson", "City", "Central Kootenay"),
    ("New Westminster", "City", "Metro Vancouver"),
    ("North Vancouver", "City", "Metro Vancouver"),
    ("Parksville", "City", "Nanaimo"),
    ("Penticton", "City", "Okanagan-Similkameen"),
    ("Pitt Meadows", "City", "Metro Vancouver"),
    ("Port Alberni", "City", "Alberni-Clayoquot"),
    ("Port Coquitlam", "City", "Metro Vancouver"),
    ("Port Moody", "City", "Metro Vancouver"),
    ("Powell River", "City", "qathet"),
    ("Prince George", "City", "Fraser-Fort George"),
    ("Prince Rupert", "City", "North Coast"),
    ("Quesnel", "City", "Cariboo"),
    ("Revelstoke", "City", "Columbia Shuswap"),
    ("Richmond", "City", "Metro Vancouver"),
    ("Rossland", "City", "Kootenay Boundary"),
    ("Salmon Arm", "City", "Columbia Shuswap"),
    ("Surrey", "City", "Metro Vancouver"),
    ("Terrace", "City", "Kitimat-Stikine"),
    ("Trail", "City", "Kootenay Boundary"),
    ("Vancouver", "City", "Metro Vancouver"),
    ("Vernon", "City", "North Okanagan"),
    ("Victoria", "City", "Capital"),
    ("West Kelowna", "City", "Central Okanagan"),
    ("White Rock", "City", "Metro Vancouver"),
    ("Williams Lake", "City", "Cariboo"),

    # --- District Municipalities ---
    ("100 Mile House", "District Municipality", "Cariboo"),
    ("Barriere", "District Municipality", "Thompson-Nicola"),
    ("Central Saanich", "District Municipality", "Capital"),
    ("Chetwynd", "District Municipality", "Peace River"),
    ("Clearwater", "District Municipality", "Thompson-Nicola"),
    ("Coldstream", "District Municipality", "North Okanagan"),
    ("Elkford", "District Municipality", "East Kootenay"),
    ("Esquimalt", "District Municipality", "Capital"),
    ("Fort St. James", "District Municipality", "Bulkley-Nechako"),
    ("Highlands", "District Municipality", "Capital"),
    ("Hope", "District Municipality", "Fraser Valley"),
    ("Houston", "District Municipality", "Bulkley-Nechako"),
    ("Hudson's Hope", "District Municipality", "Peace River"),
    ("Invermere", "District Municipality", "East Kootenay"),
    ("Kent", "District Municipality", "Fraser Valley"),
    ("Kitimat", "District Municipality", "Kitimat-Stikine"),
    ("Lake Country", "District Municipality", "Central Okanagan"),
    ("Langley", "District Municipality", "Metro Vancouver"),
    ("Lantzville", "District Municipality", "Nanaimo"),
    ("Lillooet", "District Municipality", "Squamish-Lillooet"),
    ("Logan Lake", "District Municipality", "Thompson-Nicola"),
    ("Mackenzie", "District Municipality", "Fraser-Fort George"),
    ("Metchosin", "District Municipality", "Capital"),
    ("New Hazelton", "District Municipality", "Kitimat-Stikine"),
    ("North Cowichan", "District Municipality", "Cowichan Valley"),
    ("North Saanich", "District Municipality", "Capital"),
    ("North Vancouver", "District Municipality", "Metro Vancouver"),
    ("Northern Rockies", "District Municipality", "Northern Rockies"),
    ("Oak Bay", "District Municipality", "Capital"),
    ("Peachland", "District Municipality", "Central Okanagan"),
    ("Port Edward", "District Municipality", "North Coast"),
    ("Port Hardy", "District Municipality", "Mount Waddington"),
    ("Saanich", "District Municipality", "Capital"),
    ("Sechelt", "District Municipality", "Sunshine Coast"),
    ("Sicamous", "District Municipality", "Columbia Shuswap"),
    ("Sooke", "District Municipality", "Capital"),
    ("Spallumcheen", "District Municipality", "North Okanagan"),
    ("Sparwood", "District Municipality", "East Kootenay"),
    ("Squamish", "District Municipality", "Squamish-Lillooet"),
    ("Stewart", "District Municipality", "Kitimat-Stikine"),
    ("Summerland", "District Municipality", "Okanagan-Similkameen"),
    ("Taylor", "District Municipality", "Peace River"),
    ("Tofino", "District Municipality", "Alberni-Clayoquot"),
    ("Tumbler Ridge", "District Municipality", "Peace River"),
    ("Ucluelet", "District Municipality", "Alberni-Clayoquot"),
    ("Vanderhoof", "District Municipality", "Bulkley-Nechako"),
    ("Wells", "District Municipality", "Cariboo"),
    ("West Vancouver", "District Municipality", "Metro Vancouver"),

    # --- Indian Government District ---
    ("shishalh Nation", "Indian Government District", "qathet"),

    # --- Island Municipality ---
    ("Bowen Island", "Island Municipality", "Metro Vancouver"),

    # --- Mountain Resort Municipality ---
    ("Sun Peaks Mountain", "Mountain Resort Municipality", "Thompson-Nicola"),

    # --- Resort Municipality ---
    ("Whistler", "Resort Municipality", "Squamish-Lillooet"),

    # --- Towns ---
    ("Comox", "Town", "Comox Valley"),
    ("Creston", "Town", "Central Kootenay"),
    ("Gibsons", "Town", "Sunshine Coast"),
    ("Golden", "Town", "Columbia Shuswap"),
    ("Ladysmith", "Town", "Cowichan Valley"),
    ("Lake Cowichan", "Town", "Cowichan Valley"),
    ("Oliver", "Town", "Okanagan-Similkameen"),
    ("Osoyoos", "Town", "Okanagan-Similkameen"),
    ("Port McNeill", "Town", "Mount Waddington"),
    ("Princeton", "Town", "Okanagan-Similkameen"),
    ("Qualicum Beach", "Town", "Nanaimo"),
    ("Sidney", "Town", "Capital"),
    ("Smithers", "Town", "Bulkley-Nechako"),
    ("View Royal", "Town", "Capital"),

    # --- Villages ---
    ("Alert Bay", "Village", "Mount Waddington"),
    ("Anmore", "Village", "Metro Vancouver"),
    ("Ashcroft", "Village", "Thompson-Nicola"),
    ("Belcarra", "Village", "Metro Vancouver"),
    ("Burns Lake", "Village", "Bulkley-Nechako"),
    ("Cache Creek", "Village", "Thompson-Nicola"),
    ("Canal Flats", "Village", "East Kootenay"),
    ("Chase", "Village", "Thompson-Nicola"),
    ("Clinton", "Village", "Thompson-Nicola"),
    ("Cumberland", "Village", "Comox Valley"),
    ("Daajing Giids", "Village", "North Coast"),
    ("Fraser Lake", "Village", "Bulkley-Nechako"),
    ("Fruitvale", "Village", "Kootenay Boundary"),
    ("Gold River", "Village", "Strathcona"),
    ("Granisle", "Village", "Bulkley-Nechako"),
    ("Harrison Hot Springs", "Village", "Fraser Valley"),
    ("Hazelton", "Village", "Kitimat-Stikine"),
    ("Kaslo", "Village", "Central Kootenay"),
    ("Keremeos", "Village", "Okanagan-Similkameen"),
    ("Lions Bay", "Village", "Metro Vancouver"),
    ("Lumby", "Village", "North Okanagan"),
    ("Lytton", "Village", "Thompson-Nicola"),
    ("Masset", "Village", "North Coast"),
    ("McBride", "Village", "Fraser-Fort George"),
    ("Midway", "Village", "Kootenay Boundary"),
    ("Montrose", "Village", "Kootenay Boundary"),
    ("Nakusp", "Village", "Central Kootenay"),
    ("New Denver", "Village", "Central Kootenay"),
    ("Pemberton", "Village", "Squamish-Lillooet"),
    ("Port Alice", "Village", "Mount Waddington"),
    ("Port Clements", "Village", "North Coast"),
    ("Pouce Coupe", "Village", "Peace River"),
    ("Radium Hot Springs", "Village", "East Kootenay"),
    ("Salmo", "Village", "Central Kootenay"),
    ("Sayward", "Village", "Strathcona"),
    ("Silverton", "Village", "Central Kootenay"),
    ("Slocan", "Village", "Central Kootenay"),
    ("Tahsis", "Village", "Strathcona"),
    ("Telkwa", "Village", "Bulkley-Nechako"),
    ("Valemount", "Village", "Fraser-Fort George"),
    ("Warfield", "Village", "Kootenay Boundary"),
    ("Zeballos", "Village", "Strathcona"),
]

# Sanity check helper (run as a script to validate before seeding)
if __name__ == "__main__":
    rd_set = set(REGIONAL_DISTRICTS)
    missing = set()
    for name, mtype, rd in MUNICIPALITIES:
        if rd not in rd_set:
            missing.add(rd)
    print(f"Regional districts defined: {len(REGIONAL_DISTRICTS)}")
    print(f"Municipalities defined: {len(MUNICIPALITIES)}")
    if missing:
        print(f"ERROR - municipalities reference undefined regional districts: {missing}")
    else:
        print("OK - all municipalities reference a defined regional district.")