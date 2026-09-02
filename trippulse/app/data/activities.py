from typing import List, Dict, Any, Optional
from app.models.trip_state import ActivityPlan

INDOOR_ALTERNATIVES_CATALOG = [
    {
        "name": "Mori Art Museum & Roppongi Hills Observation Deck",
        "category": "Cultural",
        "cost": 22.0,
        "location": "Roppongi, Tokyo",
        "is_outdoor": False,
        "description": "Panoramic indoor observatory and contemporary art gallery."
    },
    {
        "name": "TeamLab Planets Digital Art Exhibition",
        "category": "Cultural",
        "cost": 34.0,
        "location": "Toyosu, Tokyo",
        "is_outdoor": False,
        "description": "Immersive indoor digital art museum."
    },
    {
        "name": "Tsutaya Books & Daikanyama T-Site Lounge",
        "category": "Relaxation",
        "cost": 15.0,
        "location": "Daikanyama, Tokyo",
        "is_outdoor": False,
        "description": "Architectural bookstore lounge and indoor cafe."
    },
    {
        "name": "Edo-Tokyo Museum & Indoor Market",
        "category": "Cultural",
        "cost": 18.0,
        "location": "Ryogoku, Tokyo",
        "is_outdoor": False,
        "description": "Covered historical museum and traditional indoor market."
    }
]

CITY_ACTIVITY_CATALOG = {
    "PARIS": [
        {"day": 1, "time_slot": "Morning", "name": "Eiffel Tower & Champ de Mars Walk", "category": "Sightseeing", "cost": 30.0, "location": "7th Arr., Paris", "is_outdoor": True, "rain_alternative": "Musée d'Orsay Indoor Gallery"},
        {"day": 1, "time_slot": "Afternoon", "name": "Louvre Museum Classical Tour", "category": "Cultural", "cost": 22.0, "location": "1st Arr., Paris", "is_outdoor": False, "rain_alternative": None},
        {"day": 1, "time_slot": "Evening", "name": "Seine River Dinner Cruise", "category": "Dining", "cost": 65.0, "location": "Pont Neuf, Paris", "is_outdoor": True, "rain_alternative": "Le Train Bleu Covered Station Dining"},
        {"day": 2, "time_slot": "Morning", "name": "Montmartre & Sacré-Cœur Exploration", "category": "Outdoor", "cost": 0.0, "location": "18th Arr., Paris", "is_outdoor": True, "rain_alternative": "Opéra Garnier Indoor Tour"},
        {"day": 2, "time_slot": "Afternoon", "name": "Le Marais Boutique & Cafe Hopping", "category": "Cultural", "cost": 35.0, "location": "4th Arr., Paris", "is_outdoor": True, "rain_alternative": "Centre Pompidou Modern Art Gallery"},
        {"day": 2, "time_slot": "Evening", "name": "Latin Quarter Bistro Dinner", "category": "Dining", "cost": 50.0, "location": "5th Arr., Paris", "is_outdoor": False, "rain_alternative": None},
        {"day": 3, "time_slot": "Morning", "name": "Sainte-Chapelle Stained Glass View", "category": "Cultural", "cost": 15.0, "location": "Île de la Cité, Paris", "is_outdoor": False, "rain_alternative": None},
        {"day": 3, "time_slot": "Afternoon", "name": "Jardin du Luxembourg Promenade", "category": "Outdoor", "cost": 0.0, "location": "6th Arr., Paris", "is_outdoor": True, "rain_alternative": "Panthéon Indoor Monument"}
    ],
    "LISBON": [
        {"day": 1, "time_slot": "Morning", "name": "Belém Tower & Jerónimos Monastery", "category": "Cultural", "cost": 15.0, "location": "Belém, Lisbon", "is_outdoor": True, "rain_alternative": "MAAT Art & Technology Museum"},
        {"day": 1, "time_slot": "Afternoon", "name": "Pastéis de Belém Tasting & Tram 28 Ride", "category": "Dining", "cost": 12.0, "location": "Belém, Lisbon", "is_outdoor": False, "rain_alternative": None},
        {"day": 1, "time_slot": "Evening", "name": "Fado Night & Dinner in Alfama", "category": "Dining", "cost": 45.0, "location": "Alfama, Lisbon", "is_outdoor": False, "rain_alternative": None},
        {"day": 2, "time_slot": "Morning", "name": "Castelo de São Jorge & Miradouro View", "category": "Outdoor", "cost": 15.0, "location": "Castelo, Lisbon", "is_outdoor": True, "rain_alternative": "Lisbon Oceanarium Indoor Complex"},
        {"day": 2, "time_slot": "Afternoon", "name": "Time Out Market Gourmet Tasting", "category": "Dining", "cost": 30.0, "location": "Cais do Sodré, Lisbon", "is_outdoor": False, "rain_alternative": None},
        {"day": 2, "time_slot": "Evening", "name": "LX Factory Evening Lounge & Art", "category": "Cultural", "cost": 25.0, "location": "Alcântara, Lisbon", "is_outdoor": True, "rain_alternative": "LX Factory Indoor Concept Stores"},
        {"day": 3, "time_slot": "Morning", "name": "Sintra Day Tour & Pena Palace", "category": "Outdoor", "cost": 35.0, "location": "Sintra, Lisbon", "is_outdoor": True, "rain_alternative": "National Tile Museum (Azulejo)"},
        {"day": 3, "time_slot": "Afternoon", "name": "Chiado & Baixa Shopping District", "category": "Sightseeing", "cost": 20.0, "location": "Chiado, Lisbon", "is_outdoor": True, "rain_alternative": "Bertrand Bookshop Lounge"}
    ],
    "NEW YORK": [
        {"day": 1, "time_slot": "Morning", "name": "Central Park & Bethesda Terrace Walk", "category": "Outdoor", "cost": 0.0, "location": "Manhattan, NYC", "is_outdoor": True, "rain_alternative": "Metropolitan Museum of Art (The Met)"},
        {"day": 1, "time_slot": "Afternoon", "name": "Summit One Vanderbilt Observatory", "category": "Sightseeing", "cost": 42.0, "location": "Midtown, NYC", "is_outdoor": False, "rain_alternative": None},
        {"day": 1, "time_slot": "Evening", "name": "Broadway Musical & Theater District", "category": "Cultural", "cost": 95.0, "location": "Times Square, NYC", "is_outdoor": False, "rain_alternative": None},
        {"day": 2, "time_slot": "Morning", "name": "High Line Elevated Park & Hudson Yards", "category": "Outdoor", "cost": 0.0, "location": "Chelsea, NYC", "is_outdoor": True, "rain_alternative": "Chelsea Market Food Hall"},
        {"day": 2, "time_slot": "Afternoon", "name": "Museum of Modern Art (MoMA)", "category": "Cultural", "cost": 25.0, "location": "Midtown, NYC", "is_outdoor": False, "rain_alternative": None},
        {"day": 2, "time_slot": "Evening", "name": "Greenwich Village Jazz Club & Dinner", "category": "Dining", "cost": 55.0, "location": "Greenwich Village, NYC", "is_outdoor": False, "rain_alternative": None},
        {"day": 3, "time_slot": "Morning", "name": "Brooklyn Bridge Walk & DUMBO", "category": "Outdoor", "cost": 0.0, "location": "Brooklyn, NYC", "is_outdoor": True, "rain_alternative": "New-York Historical Society"},
        {"day": 3, "time_slot": "Afternoon", "name": "SoHo Shopping & Rooftop Cafe", "category": "Dining", "cost": 30.0, "location": "SoHo, NYC", "is_outdoor": True, "rain_alternative": "Mercer Street Indoor Lounge"}
    ]
}

def search_activities(destination: str, num_days: int = 3) -> List[ActivityPlan]:
    """Generates an itinerary of activities customized for the destination."""
    dest_key = destination.upper().strip()
    catalog = CITY_ACTIVITY_CATALOG.get(dest_key)
    
    activities = []
    
    if catalog:
        for idx, item in enumerate(catalog):
            if item["day"] > num_days:
                continue
            activities.append(ActivityPlan(
                activity_id=f"ACT-{item['day']}0{idx+1}",
                day=item["day"],
                time_slot=item["time_slot"],
                name=item["name"],
                category=item["category"],
                cost=item["cost"],
                location=item["location"],
                is_outdoor=item["is_outdoor"],
                rain_alternative=item.get("rain_alternative"),
                status="Confirmed"
            ))
    else:
        # Dynamic fallback for Tokyo or any other custom city
        city_title = destination.title().strip()
        is_tokyo = "TOKYO" in dest_key
        
        # Day 1
        activities.append(ActivityPlan(
            activity_id="ACT-101",
            day=1,
            time_slot="Morning",
            name=f"Historic District & Cultural Shrine Walk" if not is_tokyo else "Senso-ji Temple & Nakamise Shopping Street",
            category="Cultural",
            cost=0.0,
            location=f"Old Town, {city_title}",
            is_outdoor=True,
            rain_alternative=f"National History Museum & Covered Arcade",
            status="Confirmed"
        ))
        activities.append(ActivityPlan(
            activity_id="ACT-102",
            day=1,
            time_slot="Afternoon",
            name=f"{city_title} Panoramic Tower & Indoor Deck",
            category="Sightseeing",
            cost=28.0,
            location=f"Downtown, {city_title}",
            is_outdoor=False,
            rain_alternative=None,
            status="Confirmed"
        ))
        activities.append(ActivityPlan(
            activity_id="ACT-103",
            day=1,
            time_slot="Evening",
            name=f"Local Gourmet Food Tour & Night Market",
            category="Dining",
            cost=45.0,
            location=f"Gourmet Alley, {city_title}",
            is_outdoor=True,
            rain_alternative=f"Covered Food Hall & Bistro Lounge",
            status="Confirmed"
        ))

        # Day 2
        activities.append(ActivityPlan(
            activity_id="ACT-201",
            day=2,
            time_slot="Morning",
            name=f"{city_title} Botanical Gardens & Promenade Walk",
            category="Outdoor",
            cost=0.0,
            location=f"Central Park, {city_title}",
            is_outdoor=True,
            rain_alternative=f"Art Gallery & Indoor Japanese Gardens View",
            status="Confirmed"
        ))
        activities.append(ActivityPlan(
            activity_id="ACT-202",
            day=2,
            time_slot="Afternoon",
            name=f"{city_title} Landmark Plaza & Shopping District",
            category="Cultural",
            cost=30.0,
            location=f"Commercial Hub, {city_title}",
            is_outdoor=True,
            rain_alternative=f"Digital Art Exhibition & Indoor Experience",
            status="Confirmed"
        ))
        activities.append(ActivityPlan(
            activity_id="ACT-203",
            day=2,
            time_slot="Evening",
            name=f"Skyline Night View & Fine Dining",
            category="Dining",
            cost=60.0,
            location=f"Waterfront, {city_title}",
            is_outdoor=False,
            rain_alternative=None,
            status="Confirmed"
        ))

        # Day 3
        if num_days >= 3:
            activities.append(ActivityPlan(
                activity_id="ACT-301",
                day=3,
                time_slot="Morning",
                name=f"{city_title} Waterfront Market Food Tasting",
                category="Dining",
                cost=35.0,
                location=f"Harbor, {city_title}",
                is_outdoor=True,
                rain_alternative=f"Indoor Gourmet Market & Cafe",
                status="Confirmed"
            ))
            activities.append(ActivityPlan(
                activity_id="ACT-302",
                day=3,
                time_slot="Afternoon",
                name=f"{city_title} Royal Palace & Grounds Tour",
                category="Outdoor",
                cost=0.0,
                location=f"Heritage Quarter, {city_title}",
                is_outdoor=True,
                rain_alternative=f"Modern Art Museum & Covered Gallery",
                status="Confirmed"
            ))

    return activities

def get_indoor_alternatives(location: str, date: str, preference_tags: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """Returns suitable indoor alternative activities when bad weather hits."""
    city_title = location.title().strip()
    return [
        {
            "name": f"Grand Museum of Fine Arts ({city_title})",
            "category": "Cultural",
            "cost": 22.0,
            "location": f"Art District, {city_title}",
            "is_outdoor": False,
            "description": "Panoramic indoor observatory and art gallery."
        },
        {
            "name": f"Digital Immersive Light & Sound Exhibition ({city_title})",
            "category": "Cultural",
            "cost": 32.0,
            "location": f"Innovation Center, {city_title}",
            "is_outdoor": False,
            "description": "Interactive indoor digital exhibition."
        },
        {
            "name": f"Historical Covered Market & Food Lounge ({city_title})",
            "category": "Dining",
            "cost": 18.0,
            "location": f"Old Town, {city_title}",
            "is_outdoor": False,
            "description": "Covered historical market and food hall."
        }
    ]
