import os
import json
import urllib.request

missing_tasks = [
    ("Peridot Grand Luxury Boutique Hotel exterior building", "hanoi/peridot-grand-luxury-boutique-hotel/exterior", "exterior"),
    ("Celina Of The Sea Cruise room interior", "halong/celina-of-the-sea-cruise/interior", "interior"),
    ("Anantara Hoi An Resort room interior", "quang-nam/anantara-hoi-an-resort/interior", "interior"),
    ("Anantara Hoi An Resort exterior building", "quang-nam/anantara-hoi-an-resort/exterior", "exterior"),
    ("Hyatt Regency Danang Resort and Spa exterior building", "danang/hyatt-regency-danang-resort-and-spa/exterior", "exterior")
]

base_path = "/Users/nam/Workspace/projects/running/travel.ai/quotation-landingpage-template/assets/hotels"

for query, folder, img_type in missing_tasks:
    full_folder = os.path.join(base_path, folder)
    imgs = []
    for i in range(1, 4):
        path = os.path.join(full_folder, f"image_{i}.jpg")
        # Use a seed based on query and index to get consistent random images
        seed = query.replace(' ', '') + str(i)
        url = f"https://picsum.photos/seed/{seed}/800/600"
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response, open(path, 'wb') as out_file:
                out_file.write(response.read())
            print(f"Downloaded picsum for {path}")
            imgs.append(path)
        except Exception as e:
            print(f"Failed {url}: {e}")
            
    # Update info.json
    hotel_dir = os.path.dirname(full_folder)
    info_path = os.path.join(hotel_dir, "info.json")
    if os.path.exists(info_path):
        with open(info_path, 'r') as f:
            info = json.load(f)
        
        if 'images' not in info:
            info['images'] = {'interior': [], 'exterior': []}
            
        def to_rel(p):
            return p.replace("/Users/nam/Workspace/projects/running/travel.ai/quotation-landingpage-template/", "")
            
        info['images'][img_type] = [to_rel(p) for p in imgs]
        with open(info_path, 'w') as f:
            json.dump(info, f, indent=2)
