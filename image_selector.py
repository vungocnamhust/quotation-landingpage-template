from dotenv import load_dotenv
import os
import random
from openai import AsyncOpenAI

# Initialize OpenAI client (make sure OPENAI_API_KEY is set in your environment variables)
load_dotenv()
client = AsyncOpenAI(timeout=10.0)

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

# ---------------------------------------------------------------------------
# Local keyword map — pure-Python, không cần gọi mạng.
# Key: lowercase string xuất hiện trong tên địa danh (có thể có dấu hoặc không dấu).
# Value: slug tỉnh tương ứng trong PROVINCES.
# ---------------------------------------------------------------------------
KEYWORD_MAP: dict[str, str] = {
    # Hà Nội
    "hà nội": "ha-noi", "ha noi": "ha-noi", "hanoi": "ha-noi", "hanoï": "ha-noi",
    # TP. Hồ Chí Minh
    "hồ chí minh": "ho-chi-minh", "ho chi minh": "ho-chi-minh",
    "hcm": "ho-chi-minh", "saigon": "ho-chi-minh", "sài gòn": "ho-chi-minh",
    "sai gon": "ho-chi-minh", "tphcm": "ho-chi-minh",
    # Đà Nẵng
    "đà nẵng": "da-nang", "da nang": "da-nang", "danang": "da-nang",
    # Quảng Nam / Hội An
    "quảng nam": "quang-nam", "quang nam": "quang-nam",
    "hội an": "quang-nam", "hoi an": "quang-nam", "hoian": "quang-nam",
    # Quảng Ninh / Hạ Long
    "quảng ninh": "quang-ninh", "quang ninh": "quang-ninh",
    "hạ long": "quang-ninh", "ha long": "quang-ninh", "halong": "quang-ninh",
    "vịnh hạ long": "quang-ninh", "vinh ha long": "quang-ninh",
    "cat ba": "quang-ninh", "cát bà": "quang-ninh",
    # Lào Cai / Sapa
    "lào cai": "lao-cai", "lao cai": "lao-cai", "laocai": "lao-cai",
    "sapa": "lao-cai", "sa pa": "lao-cai",
    "bắc hà": "lao-cai", "bac ha": "lao-cai",
    # Khánh Hoà / Nha Trang
    "khánh hoà": "khanh-hoa", "khanh hoa": "khanh-hoa",
    "nha trang": "khanh-hoa", "nhatrang": "khanh-hoa",
    # Lâm Đồng / Đà Lạt
    "lâm đồng": "lam-dong", "lam dong": "lam-dong",
    "đà lạt": "lam-dong", "da lat": "lam-dong", "dalat": "lam-dong",
    # Thừa Thiên Huế
    "thừa thiên huế": "thua-thien-hue", "thua thien hue": "thua-thien-hue",
    "huế": "thua-thien-hue", "hue": "thua-thien-hue",
    "lăng cô": "thua-thien-hue", "lang co": "thua-thien-hue",
    # Kiên Giang / Phú Quốc
    "kiên giang": "kien-giang", "kien giang": "kien-giang",
    "phú quốc": "kien-giang", "phu quoc": "kien-giang", "phuquoc": "kien-giang",
    # Bình Thuận / Mũi Né
    "bình thuận": "binh-thuan", "binh thuan": "binh-thuan",
    "mũi né": "binh-thuan", "mui ne": "binh-thuan",
    "phan thiết": "binh-thuan", "phan thiet": "binh-thuan",
    # Cần Thơ
    "cần thơ": "can-tho", "can tho": "can-tho", "cantho": "can-tho",
    "bến ninh kiều": "can-tho", "ben ninh kieu": "can-tho",
    # Mekong Delta
    "mekong": "mekong", "đồng bằng sông cửu long": "mekong",
    "dong bang song cuu long": "mekong", "miền tây": "mekong", "mien tay": "mekong",
    "tây nam bộ": "mekong", "tay nam bo": "mekong",
    # Hà Giang
    "hà giang": "ha-giang", "ha giang": "ha-giang",
    "đồng văn": "ha-giang", "dong van": "ha-giang",
    "mèo vạc": "ha-giang", "meo vac": "ha-giang",
    # Ninh Bình
    "ninh bình": "ninh-binh", "ninh binh": "ninh-binh",
    "tràng an": "ninh-binh", "trang an": "ninh-binh",
    "tam cốc": "ninh-binh", "tam coc": "ninh-binh",
    "bích động": "ninh-binh", "bich dong": "ninh-binh",
    # Nghệ An
    "nghệ an": "nghe-an", "nghe an": "nghe-an",
    "cửa lò": "nghe-an", "cua lo": "nghe-an",
    # Quảng Bình / Phong Nha
    "quảng bình": "quang-binh", "quang binh": "quang-binh",
    "phong nha": "quang-binh", "ke bang": "quang-binh",
    # Hải Phòng
    "hải phòng": "hai-phong", "hai phong": "hai-phong", "haiphong": "hai-phong",
    # Đắk Lắk / Buôn Ma Thuột
    "đắk lắk": "dak-lak", "dak lak": "dak-lak", "daklak": "dak-lak",
    "buôn ma thuột": "dak-lak", "buon ma thuot": "dak-lak", "bmt": "dak-lak",
    # Gia Lai / Pleiku
    "gia lai": "gia-lai", "pleiku": "gia-lai",
    # Kon Tum
    "kon tum": "kon-tum", "kontum": "kon-tum",
    # Bà Rịa - Vũng Tàu
    "bà rịa": "ba-ria-vung-tau", "ba ria": "ba-ria-vung-tau",
    "vũng tàu": "ba-ria-vung-tau", "vung tau": "ba-ria-vung-tau", "vungtau": "ba-ria-vung-tau",
    # Thanh Hoá
    "thanh hoá": "thanh-hoa", "thanh hoa": "thanh-hoa",
    "sầm sơn": "thanh-hoa", "sam son": "thanh-hoa",
    # Phú Yên
    "phú yên": "phu-yen", "phu yen": "phu-yen",
    "tuy hoà": "phu-yen", "tuy hoa": "phu-yen",
    # Bình Định / Quy Nhơn
    "bình định": "binh-dinh", "binh dinh": "binh-dinh",
    "quy nhơn": "binh-dinh", "quy nhon": "binh-dinh", "quynhon": "binh-dinh",
    # Điện Biên
    "điện biên": "dien-bien", "dien bien": "dien-bien", "điện biên phủ": "dien-bien",
    # Sơn La
    "sơn la": "son-la", "son la": "son-la", "mộc châu": "son-la", "moc chau": "son-la",
    # Lai Châu
    "lai châu": "lai-chau", "lai chau": "lai-chau",
    # Yên Bái / Mù Cang Chải
    "yên bái": "yen-bai", "yen bai": "yen-bai",
    "mù cang chải": "yen-bai", "mu cang chai": "yen-bai",
    # Hoà Bình
    "hoà bình": "hoa-binh", "hoa binh": "hoa-binh",
    # Lạng Sơn
    "lạng sơn": "lang-son", "lang son": "lang-son",
    # Đồng Nai
    "đồng nai": "dong-nai", "dong nai": "dong-nai",
    # Bình Dương
    "bình dương": "binh-duong", "binh duong": "binh-duong",
    # Tiền Giang
    "tiền giang": "tien-giang", "tien giang": "tien-giang",
    "mỹ tho": "tien-giang", "my tho": "tien-giang",
    # Đồng Tháp
    "đồng tháp": "dong-thap", "dong thap": "dong-thap",
    "sa đéc": "dong-thap", "sa dec": "dong-thap",
    # Vĩnh Long
    "vĩnh long": "vinh-long", "vinh long": "vinh-long",
    # An Giang
    "an giang": "an-giang", "châu đốc": "an-giang", "chau doc": "an-giang",
    "long xuyên": "an-giang", "long xuyen": "an-giang",
    # Cao Bằng
    "cao bằng": "cao-bang", "cao bang": "cao-bang", "bản giốc": "cao-bang", "ban gioc": "cao-bang",
}


def _normalize(text: str) -> str:
    """Chuyển về lowercase và strip whitespace để so sánh."""
    return text.lower().strip()


def resolve_slug_locally(location: str) -> str | None:
    """
    Tra cứu slug của tỉnh thành hoàn toàn bằng Python — không cần gọi OpenAI.

    Chiến lược (theo thứ tự ưu tiên):
    1. Kiểm tra xem `location` đã là slug hợp lệ chưa (vd: "ha-noi").
    2. Exact match với KEYWORD_MAP.
    3. Substring match: kiểm tra xem bất kỳ keyword nào có xuất hiện trong location không.
    4. Trả về None nếu không tìm được.
    """
    if not location:
        return None

    normalized = _normalize(location)

    # 1. Kiểm tra xem input đã là slug hợp lệ
    if normalized in PROVINCES:
        return normalized

    # 2. Exact match trong KEYWORD_MAP
    if normalized in KEYWORD_MAP:
        return KEYWORD_MAP[normalized]

    # 3. Substring match — duyệt qua tất cả keyword, ưu tiên keyword dài nhất trước
    best_match: str | None = None
    best_len = 0
    for keyword, slug in KEYWORD_MAP.items():
        if keyword in normalized and len(keyword) > best_len:
            best_match = slug
            best_len = len(keyword)

    return best_match


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


async def get_province_slug_for_location(location: str) -> str | None:
    """
    Sử dụng LLM (OpenAI) để ánh xạ một địa danh hoặc địa điểm bất kỳ sang slug của tỉnh thành tương ứng.
    Ví dụ: "Sapa" -> "lao-cai", "Hội An" -> "quang-nam", "Bến Ninh Kiều" -> "can-tho".

    Chú ý: Ưu tiên dùng `resolve_slug_locally()` và `resolve_slug_from_known()` trước khi gọi hàm này
    để tránh tốn token không cần thiết.
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
        slug = response.choices[0].message.content.strip().lower()  # type: ignore
        
        if slug in PROVINCES:
            return slug
        else:
            return None
    except Exception as e:
        print(f"[Error] Mapping location failed: {e}")
        return None

async def extract_and_map_destinations(text: str, max_items: int | None = None) -> list[dict[str, str]]:
    """
    Đọc toàn bộ văn bản (tour info), trích xuất ra danh sách các điểm đến cụ thể
    và ánh xạ chính xác mỗi điểm đến với slug của tỉnh tương ứng.
    Trả về list: [{"name": "Hà Nội", "slug": "ha-noi"}, ...]
    """
    limit_text = f"trích xuất ra {max_items} địa điểm/tỉnh thành" if max_items else "trích xuất ra TẤT CẢ địa điểm/tỉnh thành"
    prompt = f"""
Bạn là chuyên gia du lịch Việt Nam. Hãy đọc đoạn văn bản sau và {limit_text} NỔI BẬT NHẤT xuất hiện trong văn bản.
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
        data = json.loads(content)  # type: ignore
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
