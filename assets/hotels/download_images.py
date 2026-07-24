import os
import requests
import json
from duckduckgo_search import DDGS

hotels = [
    ("Peridot Grand Luxury Boutique Hotel", "hanoi/peridot-grand-luxury-boutique-hotel"),
    ("Celina Of The Sea Cruise", "halong/celina-of-the-sea-cruise"),
    ("Anantara Hoi An Resort", "quang-nam/anantara-hoi-an-resort"),
    ("Hyatt Regency Danang Resort and Spa", "danang/hyatt-regency-danang-resort-and-spa"),
    ("The Reverie Saigon Hotel", "saigon/the-reverie-saigon-hotel")
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
                    # Fake user agent
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

for hotel, folder in hotels:
    base_dir = f"/Users/nam/Workspace/projects/running/travel.ai/quotation-landingpage-template/assets/hotels/{folder}"
    print(f"Processing {hotel}...")
    interior_imgs = download_images(f"{hotel} room interior", f"{base_dir}/interior")
    exterior_imgs = download_images(f"{hotel} exterior building", f"{base_dir}/exterior")
    
    # Update info.json
    info_path = f"{base_dir}/info.json"
    if os.path.exists(info_path):
        with open(info_path, 'r') as f:
            info = json.load(f)
        
        # Keep relative paths
        def to_rel(p):
            return p.replace("/Users/nam/Workspace/projects/running/travel.ai/quotation-landingpage-template/", "")
            
        info['images'] = {
            'interior': [to_rel(p) for p in interior_imgs],
            'exterior': [to_rel(p) for p in exterior_imgs]
        }
        with open(info_path, 'w') as f:
            json.dump(info, f, indent=2)
