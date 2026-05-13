from dotenv import load_dotenv
import os
import random
from openai import AsyncOpenAI

# Initialize OpenAI client (make sure OPENAI_API_KEY is set in your environment variables)
load_dotenv()
client = AsyncOpenAI()

PROVINCES = [
    "an-giang", "ba-ria-vung-tau", "bac-lieu", "bac-kan", "bac-giang", "bac-ninh", "ben-tre", 
    "binh-duong", "binh-dinh", "binh-phuoc", "binh-thuan", "ca-mau", "cao-bang", "can-tho", 
    "da-nang", "dak-lak", "dak-nong", "dien-bien", "dong-nai", "dong-thap", "gia-lai", 
    "ha-giang", "ha-nam", "ha-noi", "ha-tinh", "hai-duong", "hai-phong", "hau-giang", 
    "hoa-binh", "hung-yen", "khanh-hoa", "kien-giang", "kon-tum", "lai-chau", "lang-son", 
    "lao-cai", "lam-dong", "long-an", "mekong", "nam-dinh", "nghe-an", "ninh-binh", "ninh-thuan", 
    "phu-tho", "phu-yen", "quang-binh", "quang-nam", "quang-ngai", "quang-ninh", "quang-tri", 
    "soc-trang", "son-la", "tay-ninh", "thai-binh", "thai-nguyen", "thanh-hoa", "thua-thien-hue", 
    "tien-giang", "ho-chi-minh", "tra-vinh", "tuyen-quang", "vinh-long", "vinh-phuc", "yen-bai"
]

async def get_province_slug_for_location(location: str) -> str | None:
    """
    Sử dụng LLM (OpenAI) để ánh xạ một địa danh hoặc địa điểm bất kỳ sang slug của tỉnh thành tương ứng.
    Ví dụ: "Sapa" -> "lao-cai", "Hội An" -> "quang-nam", "Bến Ninh Kiều" -> "can-tho".
    """
    if not location:
        return None

    prompt = f"""
Bạn là một chuyên gia về địa lý du lịch Việt Nam. Nhiệm vụ của bạn là đọc đoạn văn bản cung cấp và tìm ra địa danh du lịch nổi bật nhất được nhắc đến. Sau đó, ánh xạ địa danh đó sang TÊN SLUG của 1 trong 63 tỉnh/thành phố của Việt Nam.

Đặc biệt nếu nhắc đến các tỉnh miền Tây (Mekong Delta), hãy ưu tiên trả về "mekong".
Nếu đoạn văn chứa nhiều địa điểm (ví dụ: Hà Nội, Sapa, Đà Nẵng), hãy TỰ ĐỘNG CHỌN NGẪU NHIÊN 1 địa điểm trong số đó để ánh xạ sang slug.

Danh sách các slug hợp lệ:
{', '.join(PROVINCES)}

Đoạn văn bản đầu vào: "{location}"

Hãy trả về CHỈ ĐÚNG 1 SLUG từ danh sách trên mà không kèm bất kỳ lời giải thích, dấu câu hay nội dung nào khác. Nếu hoàn toàn không có địa danh nào, hãy trả về "unknown".
    """
    
    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini", # Dùng model nhỏ để tốc độ phản hồi nhanh và rẻ
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=10,
        )
        slug = response.choices[0].message.content.strip().lower()
        
        if slug in PROVINCES:
            return slug
        else:
            return None
    except Exception as e:
        print(f"[Error] Mapping location failed: {e}")
        return None

async def extract_and_map_destinations(text: str, max_items: int = 4) -> list[dict[str, str]]:
    """
    Đọc toàn bộ văn bản (tour info), trích xuất ra danh sách các điểm đến cụ thể
    và ánh xạ chính xác mỗi điểm đến với slug của tỉnh tương ứng.
    Trả về list: [{"name": "Hà Nội", "slug": "ha-noi"}, ...]
    """
    prompt = f"""
Bạn là chuyên gia du lịch Việt Nam. Hãy đọc đoạn văn bản sau và trích xuất ra {max_items} địa điểm/tỉnh thành NỔI BẬT NHẤT xuất hiện trong văn bản.
Với mỗi địa điểm, hãy cung cấp tên hiển thị (name) và mã slug tương ứng thuộc danh sách 63 tỉnh/thành.

Danh sách slug hợp lệ:
{', '.join(PROVINCES)}

Lưu ý:
- Tên hiển thị (name) nên ngắn gọn, ví dụ "Hà Nội", "Vịnh Hạ Long", "Sapa", "Hội An".
- Slug (slug) PHẢI nằm trong danh sách slug trên. (Ví dụ Sapa -> lao-cai, Hạ Long -> quang-ninh).

Văn bản:
"{text}"

Hãy trả về ĐÚNG MỘT object JSON có chứa 1 key là "destinations". Key này trỏ tới một array, mỗi element là một object có 2 key "name" và "slug".
"""
    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            response_format={"type": "json_object"}
        )
        import json
        content = response.choices[0].message.content
        data = json.loads(content)
        return data.get("destinations", [])
    except Exception as e:
        print(f"[Error] Extract destinations failed: {e}")
        return []

def get_random_image_for_province(province_slug: str | None, assets_dir: str = "assets") -> str:
    """
    Nhận vào slug của tỉnh, tìm trong thư mục tương ứng và pick ra 1 ảnh ngẫu nhiên.
    Nếu không tìm thấy hoặc lỗi, sẽ fallback về ảnh mặc định.
    """
    default_image = "/assets/vietnam-safar-logo.png" # Có thể thay bằng một ảnh cover chung
    
    if not province_slug:
        return default_image
        
    folder_path = os.path.join(assets_dir, province_slug)
    
    if os.path.isdir(folder_path):
        valid_extensions = {".jpg", ".jpeg", ".png", ".webp"}
        files = [
            f for f in os.listdir(folder_path) 
            if os.path.isfile(os.path.join(folder_path, f)) and os.path.splitext(f)[1].lower() in valid_extensions
        ]
        
        if files:
            chosen_image = random.choice(files)
            return f"/{assets_dir}/{province_slug}/{chosen_image}"
            
    return default_image
    
async def select_landing_image(location: str) -> str:
    """
    Hàm tổng hợp: 
    1. Truyền vào location (vd: "Biển Cửa Lò")
    2. Gọi LLM để biết thuộc tỉnh nào (vd: "nghe-an")
    3. Chọn 1 ảnh ngẫu nhiên trong thư mục /assets/nghe-an
    4. Trả về path ảnh để gắn vào thẻ <img> hoặc background-image của landing page
    """
    province_slug = await get_province_slug_for_location(location)
    image_url = get_random_image_for_province(province_slug)
    return image_url
