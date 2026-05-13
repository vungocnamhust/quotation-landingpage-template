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
Bạn là một chuyên gia về địa lý du lịch Việt Nam. Nhiệm vụ của bạn là ánh xạ một địa danh, địa điểm hoặc điểm du lịch được cung cấp sang tên của một trong 63 tỉnh/thành phố của Việt Nam tương ứng với địa điểm đó.

Đặc biệt nếu là miền tây thì hãy trả về mekong

Danh sách các tỉnh/thành (dạng slug):
{', '.join(PROVINCES)}

Địa điểm đầu vào: "{location}"

Hãy trả về CHỈ ĐÚNG 1 SLUG từ danh sách trên mà không kèm bất kỳ lời giải thích, dấu câu hay nội dung nào khác. Nếu không thể xác định, hãy trả về chữ "unknown".
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
