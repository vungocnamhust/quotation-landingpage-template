import os
import requests
import json
import time
from duckduckgo_search import DDGS

missing_tasks = [
    ("Peridot Grand Luxury Boutique Hotel exterior building", "hanoi/peridot-grand-luxury-boutique-hotel/exterior", "exterior"),
    ("Celina Of The Sea Cruise room interior", "halong/celina-of-the-sea-cruise/interior", "interior"),
    ("Anantara Hoi An Resort room interior", "quang-nam/anantara-hoi-an-resort/interior", "interior"),
    ("Anantara Hoi An Resort exterior building", "quang-nam/anantara-hoi-an-resort/exterior", "exterior"),
    ("Hyatt Regency Danang Resort and Spa exterior building", "danang/hyatt-regency-danang-resort-and-spa/exterior", "exterior")
]

def download_images(query, folder, max_images=3):
    print(f"Searching for {query}")
    try:
        with DDGS() as ddgs:
            results = ddgs.images(query, max_results=max_images*2)
            if not results:
                print("No results")
                return []
            
            downloaded = []
            count = 0
            for res in results:
                if count >= max_images:
                    break
                url = res['image']
                ext = url.split('?')[0].split('.')[-1]
                if ext.lower() not in ['jpg', 'jpeg', 'png', 'webp']:
                    ext = 'jpg'
                path = os.path.join(folder, f"image_{count+1}.{ext}")
                try:
                    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
                    img_data = requests.get(url, timeout=10, headers=headers).content
                    with open(path, 'wb') as handler:
                        handler.write(img_data)
                    print(f"Downloaded {path}")
                    downloaded.append(path)
                    count += 1
                except Exception as e:
                    print(f"Failed to download {url}: {e}")
            return downloaded
    except Exception as e:
        print(f"DDGS error: {e}")
        return []

base_path = "/Users/nam/Workspace/projects/running/travel.ai/quotation-landingpage-template/assets/hotels"
for query, folder, img_type in missing_tasks:
    full_folder = os.path.join(base_path, folder)
    print(f"Processing {query}...")
    imgs = download_images(query, full_folder)
    
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
            
    time.sleep(3)  # Avoid rate limit
