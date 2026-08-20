from dotenv import load_dotenv
import os
import random
from pydantic import BaseModel, Field
from pydantic_ai import Agent
import llm_client

load_dotenv()
model = llm_client.get_model()

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

from core.rules.destination_rules import (
    DESTINATION_KEYWORD_MAP as KEYWORD_MAP,
    match_destination_slug as resolve_slug_locally,
)



def resolve_slug_from_known(location: str, known_slugs: dict[str, str]) -> str | None:
    """
    Tìm slug trong bảng `known_slugs` đã được extract trước đó.
    `known_slugs` là dict {tên địa danh lowercase → slug}, ví dụ:
        {"hà nội": "ha-noi", "sapa": "lao-cai", ...}

    Chiến lược:
    1. Exact match.
    2. Substring match: địa danh trong known_slugs xuất hiện trong location,
       hoặc location xuất hiện trong tên địa danh.
    """
    if not location or not known_slugs:
        return None

    normalized = _normalize(location)

    # 1. Exact match
    if normalized in known_slugs:
        return known_slugs[normalized]

    # 2. Substring match (cả hai chiều), ưu tiên match dài nhất
    best_match: str | None = None
    best_len = 0
    for known_name, slug in known_slugs.items():
        if (known_name in normalized or normalized in known_name) and len(known_name) > best_len:
            best_match = slug
            best_len = len(known_name)

    return best_match


# PydanticAI Agents definition
slug_agent = Agent(
    model=model,
    output_type=str,
    system_prompt=(
        "Bạn là một chuyên gia về địa lý du lịch Việt Nam. Nhiệm vụ của bạn là đọc đoạn văn bản cung cấp và tìm ra địa danh du lịch nổi bật nhất được nhắc đến. "
        "Sau đó, ánh xạ địa danh đó sang TÊN SLUG của 1 trong 63 tỉnh/thành phố của Việt Nam.\n"
        "Đặc biệt nếu nhắc đến các tỉnh miền Tây (Mekong Delta), hãy ưu tiên trả về 'mekong'.\n"
        "Nếu đoạn văn chứa nhiều địa điểm (ví dụ: Hà Nội, Sapa, Đà Nẵng), hãy TỰ ĐỘNG CHỌN NGẪU NHIÊN 1 địa điểm trong số đó để ánh xạ sang slug.\n"
        f"Danh sách các slug hợp lệ: {', '.join(PROVINCES)}\n"
        "Hãy trả về CHỈ ĐÚNG 1 SLUG từ danh sách trên mà không kèm bất kỳ lời giải thích, dấu câu hay nội dung nào khác. Nếu hoàn toàn không có địa danh nào, hãy trả về 'unknown'."
    )
)

class Destination(BaseModel):
    name: str = Field(description="Tên hiển thị ngắn gọn, ví dụ: 'Hà Nội', 'Vịnh Hạ Long', 'Sapa', 'Hội An'")
    slug: str = Field(description="Mã slug tương ứng thuộc danh sách 63 tỉnh/thành")

class DestinationList(BaseModel):
    destinations: list[Destination] = Field(description="Danh sách các địa điểm/tỉnh thành trích xuất được")

destinations_agent = Agent(
    model=model,
    output_type=DestinationList,
    system_prompt=(
        "Bạn là chuyên gia du lịch Việt Nam. Hãy đọc đoạn văn bản sau và trích xuất ra các địa điểm/tỉnh thành nổi bật nhất xuất hiện trong văn bản.\n"
        "Với mỗi địa điểm, hãy cung cấp tên hiển thị (name) và mã slug tương ứng thuộc danh sách 63 tỉnh/thành.\n"
        f"Danh sách slug hợp lệ: {', '.join(PROVINCES)}\n"
        "Lưu ý:\n"
        "- Tên hiển thị (name) nên ngắn gọn, ví dụ 'Hà Nội', 'Vịnh Hạ Long', 'Sapa', 'Hội An'.\n"
        "- Slug (slug) PHẢI nằm trong danh sách slug trên (Ví dụ Sapa -> lao-cai, Hạ Long -> quang-ninh)."
    )
)

async def get_province_slug_for_location(location: str) -> str | None:
    """
    Sử dụng LLM (DeepSeek-Flash qua PydanticAI) để ánh xạ một địa danh hoặc địa điểm bất kỳ sang slug của tỉnh thành tương ứng.
    Ví dụ: "Sapa" -> "lao-cai", "Hội An" -> "quang-nam", "Bến Ninh Kiều" -> "can-tho".
    """
    if not location:
        return None
    try:
        res = await slug_agent.run(f"Đoạn văn bản đầu vào: '{location}'")
        slug = res.data.strip().lower()
        if slug in PROVINCES:
            return slug
        return None
    except Exception as e:
        print(f"[Error] Mapping location failed: {e}")
        return None

async def extract_and_map_destinations(text: str, max_items: int | None = None) -> list[dict[str, str]]:
    """
    Đọc toàn bộ văn bản (tour info), trích xuất ra danh sách các điểm đến cụ thể
    và ánh xạ chính xác mỗi điểm đến với slug của tỉnh tương ứng bằng PydanticAI.
    """
    if not text:
        return []
    limit_text = f"trích xuất tối đa {max_items} địa điểm" if max_items else "trích xuất TẤT CẢ địa điểm"
    try:
        res = await destinations_agent.run(f"Đọc văn bản và {limit_text}:\n'{text}'")
        dest_list: DestinationList = res.data
        result = [{"name": d.name, "slug": d.slug} for d in dest_list.destinations if d.slug in PROVINCES]
        if max_items:
            result = result[:max_items]
        return result
    except Exception as e:
        print(f"[Error] Extract destinations failed: {e}")
        text_lower = text.lower()
        found = []
        seen_slugs = set()
        for kw, slug in KEYWORD_MAP.items():
            if kw in text_lower and slug not in seen_slugs:
                name_words = [w.capitalize() for w in kw.split()]
                found.append({"name": " ".join(name_words), "slug": slug})
                seen_slugs.add(slug)
        if max_items:
            found = found[:max_items]
        return found

def get_random_image_for_province(province_slug: str | None, assets_dir: str = "assets") -> str:
    """
    Nhận vào slug của tỉnh, tìm trong thư mục tương ứng và pick ra 1 ảnh ngẫu nhiên.
    Nếu không tìm thấy hoặc lỗi, sẽ fallback về ảnh mặc định.
    """
    imgs = get_all_images_for_province(province_slug, assets_dir)
    if imgs and imgs[0] != "/assets/vietnam-safar-logo.png":
        return random.choice(imgs)
    return "/assets/vietnam-safar-logo.png"

def get_all_images_for_province(province_slug: str | None, assets_dir: str = "assets") -> list[str]:
    """
    Nhận vào slug của tỉnh, tìm trong thư mục tương ứng (bao gồm cả thư mục con như hero/) 
    và trả về danh sách tất cả ảnh.
    """
    default_image = "/assets/vietnam-safar-logo.png"
    
    if not province_slug:
        return [default_image]
        
    folder_path = os.path.join(assets_dir, province_slug)
    
    if os.path.isdir(folder_path):
        valid_extensions = {".jpg", ".jpeg", ".png", ".webp"}
        all_imgs = []
        for root, _, files in os.walk(folder_path):
            for f in sorted(files):
                if os.path.splitext(f)[1].lower() in valid_extensions and not f.startswith("."):
                    rel = os.path.relpath(os.path.join(root, f), ".")
                    all_imgs.append(f"/{rel}")
        if all_imgs:
            return all_imgs
            
    return [default_image]

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
    """
    Nhận vào slug của tỉnh, tìm trong thư mục tương ứng và trả về danh sách tất cả ảnh.
    Nếu không tìm thấy hoặc lỗi, sẽ fallback về logo mặc định.
    """
    default_image = "/assets/vietnam-safar-logo.png"
    
    if not province_slug:
        return [default_image]
        
    folder_path = os.path.join(assets_dir, province_slug)
    
    if os.path.isdir(folder_path):
        valid_extensions = {".jpg", ".jpeg", ".png", ".webp"}
        files = sorted([
            f for f in os.listdir(folder_path) 
            if os.path.isfile(os.path.join(folder_path, f)) and os.path.splitext(f)[1].lower() in valid_extensions
        ])
        
        if files:
            return [f"/{assets_dir}/{province_slug}/{f}" for f in files]
            
    return [default_image]
