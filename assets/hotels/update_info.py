import json
import os

hotels = {
    "hanoi/peridot-grand-luxury-boutique-hotel": {
        "name": "Peridot Grand Luxury Boutique Hotel",
        "website": "https://peridotgrandhotel.com/",
        "introduction": "Peridot Grand Luxury Boutique Hotel offers an oasis of tranquility in the heart of Hanoi's Old Quarter, blending chic design with Vietnamese hospitality."
    },
    "halong/celina-of-the-sea-cruise": {
        "name": "Celina Of The Sea Cruise",
        "website": "https://celinacruises.com/",
        "introduction": "Celina Of The Sea Cruise provides a luxurious and unforgettable journey through the majestic limestone karsts and emerald waters of Ha Long Bay."
    },
    "quang-nam/anantara-hoi-an-resort": {
        "name": "Anantara Hoi An Resort",
        "website": "https://www.anantara.com/en/hoi-an",
        "introduction": "Anantara Hoi An Resort is a boutique retreat on the banks of the Thu Bon River, offering elegant French colonial architecture and seamless access to the historic old town."
    },
    "danang/hyatt-regency-danang-resort-and-spa": {
        "name": "Hyatt Regency Danang Resort and Spa",
        "website": "https://www.hyatt.com/en-US/hotel/vietnam/hyatt-regency-danang-resort-and-spa/danhr",
        "introduction": "Hyatt Regency Danang Resort and Spa is a luxury beachfront resort offering stunning ocean views, expansive pools, and world-class dining on the pristine Non Nuoc Beach."
    },
    "saigon/the-reverie-saigon-hotel": {
        "name": "The Reverie Saigon Hotel",
        "website": "https://www.thereveriesaigon.com/",
        "introduction": "The Reverie Saigon is an ultra-luxury hotel in Ho Chi Minh City, showcasing spectacular Italian design, opulent interiors, and unparalleled views of the Saigon River."
    }
}

base_path = "/Users/nam/Workspace/projects/running/travel.ai/quotation-landingpage-template/assets/hotels"

for path_suffix, data in hotels.items():
    info_path = os.path.join(base_path, path_suffix, "info.json")
    if os.path.exists(info_path):
        with open(info_path, "r") as f:
            try:
                info = json.load(f)
            except:
                info = {}
                
        # Update fields
        info['name'] = data['name']
        info['website'] = data['website']
        info['introduction'] = data['introduction']
        
        # Ensure images block exists just in case
        if 'images' not in info:
            info['images'] = {"interior": [], "exterior": []}
            
        with open(info_path, "w") as f:
            json.dump(info, f, indent=2, ensure_ascii=False)
        print(f"Updated {info_path}")
    else:
        print(f"File not found: {info_path}")
