import json
import os
from jinja2 import Environment, FileSystemLoader

# =====================================================================
# PHẦN 3: MASTER DATABASE (PRE-GENERATED CONTENT)
# Lưu trữ tại CSDL, không dùng LLM tạo lại mỗi lần để tiết kiệm token
# =====================================================================

MASTER_TOUR_MODULES = {
    "Arrival in Hanoi & Welcome Dinner": {
        "title": "Arrival in Hanoi & Welcome Dinner",
        "description": [
            "Welcome to Vietnam's capital city. Upon arrival, you will be greeted by our VIP airport concierge and transferred to your luxury hotel in a private premium vehicle.",
            "In the evening, enjoy a curated welcome dinner at one of Hanoi's finest Michelin-starred or fine dining restaurants, setting the tone for your exquisite journey."
        ],
        "activities": ["VIP Airport Fast-track", "Private Premium Transfer", "Exclusive Welcome Dinner"],
        "notes": ["Please have your e-Visa ready for the fast-track service."]
    },
    "Hanoi City Full Day Tour": {
        "title": "Hanoi City Full Day Tour",
        "description": [
            "Experience the rich culture and history of Hanoi in our signature full-day tour. Navigate the bustling streets of the Old Quarter and explore historical landmarks with your private expert guide.",
            "Savor authentic local flavors during a curated culinary experience for lunch."
        ],
        "activities": ["Temple of Literature", "Hoan Kiem Lake", "Old Quarter Cyclo Ride", "Egg Coffee Tasting"],
        "notes": ["Dress modestly (cover shoulders and knees) for temple visits.", "Bring comfortable walking shoes."]
    },
    "Ninh Binh City Full Day Tour": {
        "title": "Ninh Binh: The Halong Bay on Land",
        "description": [
            "Escape the city to the breathtaking landscapes of Ninh Binh. Glide on a private hand-rowed sampan through the tranquil waterways and majestic limestone karsts of Trang An.",
            "Visit the ancient capital of Hoa Lu and discover its rich dynastic history."
        ],
        "activities": ["Private Trang An Boat Tour", "Hoa Lu Ancient Capital", "Bich Dong Pagoda"],
        "notes": ["Bring sun protection and a hat.", "A light jacket is recommended for the boat ride in the morning."]
    },
    "Transfer to Ha Long & Cruise": {
        "title": "Ha Long Bay Luxury Cruise",
        "description": [
            "Transfer to Ha Long Bay, a UNESCO World Heritage site. Board your ultra-luxury cruise and set sail through thousands of emerald limestone islands.",
            "Enjoy exclusive onboard activities, a magnificent sunset over the bay, and a special Birthday Dinner curated by the executive chef."
        ],
        "activities": ["Seaplane or Limousine Transfer", "Luxury Cruise Check-in", "Sunset Deck Party", "Birthday Gala Dinner"],
        "notes": ["Pack a small overnight bag for the cruise; large luggage can be stored.", "Bring swimwear for the cruise pool/jacuzzi."]
    },
    "Fly to Da Nang & Transfer to Hoi An": {
        "title": "Journey to Heritage: Hoi An",
        "description": [
            "Disembark your cruise and transfer to the airport for a short flight to Central Vietnam. Upon arrival in Da Nang, your chauffeur will whisk you away to the ancient town of Hoi An.",
            "Enjoy a private tailoring service in the afternoon to get bespoke silk garments made."
        ],
        "activities": ["Domestic Flight to Da Nang", "Private Transfer", "Bespoke Tailoring Experience"],
        "notes": []
    },
    "Hoi An City Full Day Tour": {
        "title": "Hoi An Ancient Town Discovery",
        "description": [
            "Step back in time as you explore the enchanting, lantern-lit streets of Hoi An Ancient Town. Discover well-preserved merchant houses, ancient assembly halls, and the iconic Japanese Covered Bridge.",
            "Enjoy a hands-on culinary workshop or a peaceful sunset boat ride on the Thu Bon River."
        ],
        "activities": ["Japanese Covered Bridge", "Phuc Kien Assembly Hall", "Private Lantern Making", "Thu Bon River Sunset"],
        "notes": []
    },
    "Hoi An Photo Half Day Tour": {
        "title": "Hoi An Photography & Leisure",
        "description": [
            "Join a professional photographer for a morning photo walk to capture the best lighting and hidden corners of Hoi An.",
            "The afternoon is yours at leisure to relax at your resort or do some final shopping."
        ],
        "activities": ["Guided Photography Tour", "Local Market Visit", "Free Afternoon"],
        "notes": ["Bring your camera or smartphone fully charged."]
    },
    "Transfer to Da Nang & Half Day Tour": {
        "title": "Da Nang Coastal City Tour",
        "description": [
            "Transfer along the scenic coastline to Da Nang. Discover the Marble Mountains with their stunning caves and pagodas, followed by a visit to the pristine Son Tra Peninsula.",
            "Check in to your luxurious beach front pool villa and unwind."
        ],
        "activities": ["Marble Mountains", "Linh Ung Pagoda", "Beachfront Relaxation"],
        "notes": ["Stairs are involved at Marble Mountains; comfortable shoes are essential."]
    },
    "Ba Na Hills French Village Full Day Experience": {
        "title": "Ba Na Hills & The Golden Bridge",
        "description": [
            "Ascend via one of the world's longest cable cars to Ba Na Hills. Walk across the spectacular Golden Bridge, held up by giant stone hands.",
            "Explore the French Village, lush gardens, and enjoy premium entertainment and dining."
        ],
        "activities": ["Record-breaking Cable Car", "Golden Bridge", "French Village", "Fantasy Park"],
        "notes": ["The temperature on the mountain can be cool; bring a light jacket."]
    },
    "Hue City Full Day": {
        "title": "Imperial Hue Exploration",
        "description": [
            "Journey over the spectacular Hai Van Pass to Hue, Vietnam's former imperial capital. Explore the vast Imperial Citadel and the opulent royal tombs along the Perfume River.",
            "Enjoy a refined royal-style lunch."
        ],
        "activities": ["Hai Van Pass Scenic Drive", "Imperial Citadel", "Tomb of Emperor Tu Duc", "Thien Mu Pagoda"],
        "notes": ["Modest dress required for visiting temples and tombs."]
    },
    "Free Day at the beach villa": {
        "title": "Villa Leisure & Birthday Celebration",
        "description": [
            "A full day completely at your leisure to enjoy the world-class amenities of your 3-Bedroom Beach Front Pool Villa.",
            "In the evening, celebrate with a spectacular, privately catered Birthday Dinner right on the beach or in your villa."
        ],
        "activities": ["Spa Treatments (Optional)", "Poolside Relaxation", "Private Birthday BBQ"],
        "notes": []
    },
    "Fly to Ho Chi Minh City & Cu Chi Tour": {
        "title": "Saigon Arrival & Cu Chi Tunnels",
        "description": [
            "Fly to the bustling metropolis of Ho Chi Minh City (Saigon). In the afternoon, venture out to the historic Cu Chi Tunnels to explore the intricate underground network.",
            "Check into your ultra-luxury hotel in the heart of District 1."
        ],
        "activities": ["Domestic Flight to SGN", "Cu Chi Tunnels Speedboat Tour", "Saigon City Orientation"],
        "notes": ["The tunnels can be narrow and humid."]
    },
    "Mekong Full Day Tour": {
        "title": "Mekong Delta Luxury Expedition",
        "description": [
            "Leave the city behind for the lush landscapes of the Mekong Delta. Board a private luxury sampan to cruise the winding canals, visiting local orchards and artisan villages.",
            "Enjoy a farm-to-table lunch at a beautiful riverside colonial-style restaurant."
        ],
        "activities": ["Private Sampan Cruise", "Coconut Candy Workshop", "Tropical Fruit Tasting", "Riverside Lunch"],
        "notes": ["Sunscreen and mosquito repellent are highly recommended."]
    },
    "Departure from Ho Chi Minh City": {
        "title": "Farewell Vietnam",
        "description": [
            "Enjoy a final gourmet breakfast at your hotel. At the designated time, your private chauffeur will transfer you to Tan Son Nhat International Airport for your departure flight.",
            "Safe travels, and we hope to welcome you back to Vietnam soon!"
        ],
        "activities": ["Luxury Airport Transfer", "Farewell"],
        "notes": ["Please check out by 12:00 PM unless late check-out is arranged."]
    }
}

MASTER_IMAGES = {
    "Hanoi": {"hero": "https://placehold.co/1200x800/17412e/FFF?text=Hanoi+Luxury", "carousel": ["https://placehold.co/1200x800?text=Hanoi+1", "https://placehold.co/1200x800?text=Hanoi+2"]},
    "Ninh Binh": {"hero": "https://placehold.co/1200x800/17412e/FFF?text=Ninh+Binh"},
    "Ha Long": {"hero": "https://placehold.co/1200x800/17412e/FFF?text=Halong+Bay"},
    "Hoi An": {"hero": "https://placehold.co/1200x800/17412e/FFF?text=Hoi+An+Ancient+Town"},
    "Da Nang": {"hero": "https://placehold.co/1200x800/17412e/FFF?text=Da+Nang+Coast"},
    "Ba Na Hills": {"hero": "https://placehold.co/1200x800/17412e/FFF?text=Golden+Bridge"},
    "Hue": {"hero": "https://placehold.co/1200x800/17412e/FFF?text=Imperial+Hue"},
    "Ho Chi Minh City": {"hero": "https://placehold.co/1200x800/17412e/FFF?text=Saigon+Vibes"},
    "Mekong Delta": {"hero": "https://placehold.co/1200x800/17412e/FFF?text=Mekong+Delta"}
}

MASTER_HOTELS = {
    "Peridot Grand Luxury Boutique Hotel": {
        "ext_img": "https://placehold.co/1200x800/17412e/FFF?text=Peridot+Grand+Exterior",
        "rooms": {
            "Grand Deluxe": {"room_img": "https://placehold.co/1200x800/17412e/FFF?text=Grand+Deluxe+Room"}
        }
    },
    "Celina Of The Sea Cruise": {
        "ext_img": "https://placehold.co/1200x800/17412e/FFF?text=Celina+Cruise+Exterior",
        "rooms": {
            "Executive Balcony": {"room_img": "https://placehold.co/1200x800/17412e/FFF?text=Executive+Balcony+Cabin"}
        }
    },
    "Anantara Hoi An Resort": {
        "ext_img": "https://placehold.co/1200x800/17412e/FFF?text=Anantara+Hoi+An+Exterior",
        "rooms": {
            "Deluxe Balcony": {"room_img": "https://placehold.co/1200x800/17412e/FFF?text=Deluxe+Balcony+Room"}
        }
    },
    "Hyatt Regency Danang Resort and Spa": {
        "ext_img": "https://placehold.co/1200x800/17412e/FFF?text=Hyatt+Regency+Danang",
        "rooms": {
            "3 Bedroom Beach Front Pool Villa": {"room_img": "https://placehold.co/1200x800/17412e/FFF?text=3+Bedroom+Beachfront+Villa"}
        }
    },
    "The Reverie Saigon Hotel": {
        "ext_img": "https://placehold.co/1200x800/17412e/FFF?text=Reverie+Saigon+Exterior",
        "rooms": {
            "Deluxe Room": {"room_img": "https://placehold.co/1200x800/17412e/FFF?text=Reverie+Deluxe+Room"}
        }
    }
}


# =====================================================================
# PHẦN 2: DYNAMIC DATA (LLM EXTRACTED)
# Đây là dữ liệu duy nhất mà LLM cần bóc tách từ ảnh/yêu cầu của khách.
# Cấu trúc cực kỳ nhẹ (skeleton), tiết kiệm token.
# =====================================================================

core_metadata = {
    "tour_title": "Vietnam Grand Luxury & Birthday Celebration",
    "quotation_id": "VN-2027-LUX",
    "lang": "en",
    "hero_img": "https://placehold.co/1920x1080/0e2f22/FFF?text=Vietnam+Grand+Luxury"
}

dynamic_itinerary_input = [
    {"day": 1, "date": "3/27/2027", "city": "Hanoi", "module_key": "Arrival in Hanoi & Welcome Dinner", "overnight": "HAN", "meals": ["Dinner"]},
    {"day": 2, "date": "3/28/2027", "city": "Hanoi", "module_key": "Hanoi City Full Day Tour", "overnight": "HAN", "meals": ["Lunch", "Dinner (Full)"]},
    {"day": 3, "date": "3/29/2027", "city": "Ninh Binh", "module_key": "Ninh Binh City Full Day Tour", "overnight": "HAN", "meals": ["Lunch", "Dinner (Full)"]},
    {"day": 4, "date": "3/30/2027", "city": "Ha Long", "module_key": "Transfer to Ha Long & Cruise", "overnight": "HAL", "meals": []},
    {"day": 5, "date": "3/31/2027", "city": "Hoi An", "module_key": "Fly to Da Nang & Transfer to Hoi An", "overnight": "HOA", "meals": ["Lunch"]},
    {"day": 6, "date": "4/1/2027", "city": "Hoi An", "module_key": "Hoi An City Full Day Tour", "overnight": "HOA", "meals": ["Lunch", "Dinner (Full)"]},
    {"day": 7, "date": "4/2/2027", "city": "Hoi An", "module_key": "Hoi An Photo Half Day Tour", "overnight": "HOA", "meals": ["Lunch", "Dinner (1 Half)"]},
    {"day": 8, "date": "4/3/2027", "city": "Da Nang", "module_key": "Transfer to Da Nang & Half Day Tour", "overnight": "DAD", "meals": ["Lunch", "Dinner (Half)"]},
    {"day": 9, "date": "4/4/2027", "city": "Ba Na Hills", "module_key": "Ba Na Hills French Village Full Day Experience", "overnight": "DAD", "meals": ["Dinner (Full)"]},
    {"day": 10, "date": "4/5/2027", "city": "Hue", "module_key": "Hue City Full Day", "overnight": "DAD", "meals": ["Lunch", "Dinner (Full)"]},
    {"day": 11, "date": "4/6/2027", "city": "Da Nang", "module_key": "Free Day at the beach villa", "overnight": "DAD", "meals": ["Lunch", "Dinner"]},
    {"day": 12, "date": "4/7/2027", "city": "Ho Chi Minh City", "module_key": "Fly to Ho Chi Minh City & Cu Chi Tour", "overnight": "SGN", "meals": ["Lunch", "Dinner (Half)"]},
    {"day": 13, "date": "4/8/2027", "city": "Mekong Delta", "module_key": "Mekong Full Day Tour", "overnight": "SGN", "meals": ["Lunch", "Dinner (Full)"]},
    {"day": 14, "date": "4/9/2027", "city": "Ho Chi Minh City", "module_key": "Departure from Ho Chi Minh City", "overnight": "", "meals": []}
]

dynamic_hotels_input = [
    {"name": "Peridot Grand Luxury Boutique Hotel", "roomType": "Grand Deluxe", "dateStr": "3/27 - 3/29/2027", "location": "Hanoi"},
    {"name": "Celina Of The Sea Cruise", "roomType": "Executive Balcony", "dateStr": "3/30/2027", "location": "Ha Long"},
    {"name": "Anantara Hoi An Resort", "roomType": "Deluxe Balcony", "dateStr": "3/31 - 4/2/2027", "location": "Hoi An"},
    {"name": "Hyatt Regency Danang Resort and Spa", "roomType": "3 Bedroom Beach Front Pool Villa", "dateStr": "4/3 - 4/6/2027", "location": "Da Nang"},
    {"name": "The Reverie Saigon Hotel", "roomType": "Deluxe Room", "dateStr": "4/7 - 4/8/2027", "location": "Ho Chi Minh City"}
]

price_options = [
    {
        "hotelCategory": "14D13N",
        "optionName": "14 Days 13 Nights Package",
        "is_total": True,
        "isConfirmedMainOption": True,
        "totalPrice": {"amount": 4450, "currency": "USD", "displayText": "$4,450"},
        "pricePerPerson": {"amount": 4450, "currency": "USD", "displayText": "$4,450"},
        "singleSupplement": {"amount": 1570, "currency": "USD", "displayText": "$1,570"}
    },
    {
        "hotelCategory": "8D7N",
        "optionName": "8 Days 7 Nights Package",
        "is_total": True,
        "isConfirmedMainOption": False,
        "totalPrice": {"amount": 2350, "currency": "USD", "displayText": "$2,350"},
        "pricePerPerson": {"amount": 2350, "currency": "USD", "displayText": "$2,350"},
        "singleSupplement": {"amount": 1300, "currency": "USD", "displayText": "$1,300"}
    }
]


# =====================================================================
# MERGE LOGIC (Kết hợp Dynamic Data + Master Database)
# =====================================================================

def build_itinerary(dynamic_input, modules_db, images_db):
    itinerary = []
    for day_in in dynamic_input:
        module = modules_db.get(day_in["module_key"], {})
        images = images_db.get(day_in["city"], images_db.get("Hanoi")) # Fallback to Hanoi if missing
        
        day_obj = {
            "dayNumber": day_in["day"],
            "date": day_in["date"],
            "segment_city": day_in["city"],
            "overnight": day_in["overnight"],
            "meals": day_in["meals"],
            "layout_type": "single",
            
            # Merged from Master DB
            "title": module.get("title", day_in["module_key"]),
            "description": module.get("description", ["Description not found."]),
            "activities": module.get("activities", []),
            "notes": module.get("notes", []),
            "layout_images": images
        }
        itinerary.append(day_obj)
    return itinerary

def build_hotels(dynamic_input, hotels_db):
    hotels = []
    for h_in in dynamic_input:
        master_h = hotels_db.get(h_in["name"], {})
        room_data = master_h.get("rooms", {}).get(h_in["roomType"], {})
        
        hotel_obj = {
            "name": h_in["name"],
            "roomType": h_in["roomType"],
            "dateStr": h_in["dateStr"],
            "location": h_in["location"],
            
            # Merged from Master DB
            "ext_img": master_h.get("ext_img", "https://placehold.co/1200x800?text=Hotel"),
            "room_img": room_data.get("room_img", "https://placehold.co/1200x800?text=Room")
        }
        hotels.append(hotel_obj)
    return hotels

# =====================================================================
# SYSTEM GENERATION (JINJA2 RENDER)
# =====================================================================

def translate_filter(val, lang): return val
def rtl_mixed_filter(val, lang): return val

def main():
    # 1. Thực hiện Merge Data
    final_itinerary = build_itinerary(dynamic_itinerary_input, MASTER_TOUR_MODULES, MASTER_IMAGES)
    final_hotels = build_hotels(dynamic_hotels_input, MASTER_HOTELS)
    
    # 2. Chuẩn bị Template Variables
    template_vars = {
        "lang": core_metadata["lang"],
        "tour_title": core_metadata["tour_title"],
        "quotation_id": core_metadata["quotation_id"],
        "img_0": core_metadata["hero_img"],
        "brand": {}, # Có thể load từ file config riêng của Agent
        "itinerary_days": final_itinerary,
        "hotels": final_hotels,
        "price_options": price_options,
        "pricing_h2": "Investment details",
        "pricing_p": "Please review the pricing options below.",
        "client_i18n": {
            "language_names": {
                "en": "English",
                "vi": "Tiếng Việt"
            }
        },
        "translation_status": {},
        "itinerary": final_itinerary,
        "route_stops": [],
        "stay_segments": []
    }

    # 3. Render HTML
    template_dir = os.path.join(os.path.dirname(__file__), 'templates')
    env = FileSystemLoader(template_dir)
    jinja_env = Environment(loader=env)
    jinja_env.filters['translate'] = translate_filter
    jinja_env.filters['rtl_mixed'] = rtl_mixed_filter
    
    template = jinja_env.get_template('vietnam_luxury_brosure.html')
    output_html = template.render(**template_vars)
    
    output_path = os.path.join(os.path.dirname(__file__), 'output_quotation.html')
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(output_html)
    print(f"Successfully generated quotation at {output_path}")

if __name__ == "__main__":
    main()
