import urllib.request
import urllib.parse
import json
import os
import time
import subprocess

destinations = {
    "bangkok": "Bangkok",
    "chiang-mai": "Chiang Mai",
    "phuket": "Phuket",
    "phnom-penh": "Phnom Penh",
    "siem-reap": "Siem Reap",
    "luang-prabang": "Luang Prabang",
    "vientiane": "Vientiane",
    "da-nang": "Da Nang",
    "ha-giang": "Ha Giang",
    "ha-noi": "Hanoi",
    "ho-chi-minh": "Ho Chi Minh City",
    "khanh-hoa": "Nha Trang",
    "kien-giang": "Phu Quoc",
    "lam-dong": "Da Lat",
    "lao-cai": "Sapa Vietnam",
    "mekong": "Mekong Delta",
    "ninh-binh": "Ninh Binh",
    "quang-nam": "Hoi An",
    "quang-ninh": "Ha Long Bay",
    "thua-thien-hue": "Hue Vietnam"
}

def fetch_commons_images(query, limit=5):
    url = f"https://commons.wikimedia.org/w/api.php?action=query&generator=search&gsrsearch={urllib.parse.quote(query)}&gsrnamespace=6&gsrlimit={limit}&prop=imageinfo&iiprop=url&iiurlwidth=1200&format=json"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'})
    try:
        response = urllib.request.urlopen(req)
        data = json.loads(response.read().decode())
        pages = data.get('query', {}).get('pages', {})
        urls = []
        for page_id, page_data in pages.items():
            if 'imageinfo' in page_data:
                img_url = page_data['imageinfo'][0].get('thumburl') or page_data['imageinfo'][0].get('url')
                if img_url:
                    urls.append(img_url)
        return urls
    except Exception as e:
        print(f"Error fetching {query}: {e}")
        return []

for folder, query in destinations.items():
    print(f"\nProcessing {folder}...")
    time.sleep(1)
    urls = fetch_commons_images(f"{query} landmark OR {query} nature filetype:bitmap", 8)
    if not urls:
        urls = fetch_commons_images(f"{query} filetype:bitmap", 5)
    
    hero_dir = f"assets/{folder}/hero"
    os.makedirs(hero_dir, exist_ok=True)
    
    for idx, url in enumerate(urls[:5]):
        ext = url.split('.')[-1].split('?')[0]
        if ext.lower() not in ['jpg', 'jpeg', 'png', 'webp']:
            ext = "jpg"
        filepath = f"{hero_dir}/hero{idx+1}.{ext}"
        print(f"Downloading {url} to {filepath}")
        try:
            subprocess.run(["curl", "-sL", "-A", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36", url, "-o", filepath], check=True)
        except Exception as e:
            print(f"Failed to download {url}: {e}")
