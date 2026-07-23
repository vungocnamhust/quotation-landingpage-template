# API Schema — journeys.vietnamsafar.vn

## POST /api/v1/quotations

Tạo quotation landing page từ backend system.

### Request Headers

```json
{
  "Content-Type": "application/json",
  "Authorization": "Bearer <access_token>"
}
```

### Request Body

Dưới đây là cấu trúc dữ liệu JSON đầy đủ dùng để gửi lên API. Cấu trúc này tương thích với Pydantic schema `TourQuotationPayload` trong hệ thống.

```json
{
  "quotationNarrative": "A premium and slow-paced journey designed for luxury family travelers from Qatar, showcasing the cultural depth of Hanoi, the cinematic landscapes of Ha Long Bay, and the dramatic scenery of Sapa.",
  "programOverview": {
    "heading": "VỀ HÀNH TRÌNH CỦA QUÝ KHÁCH",
    "paragraphs": [
      "Hành trình di sản 8 ngày 7 đêm được may đo riêng mang đến sự cân bằng hoàn hảo giữa chiều sâu văn hóa của Hà Nội và vẻ đẹp ngoạn mục của miền Bắc Việt Nam.",
      "Thiết kế chậm rãi đảm bảo sự thoải mái cho gia đình, kết hợp ẩm thực thân thiện với người Hồi giáo (Halal-friendly) và xe du lịch riêng tư cao cấp."
    ]
  },
  "landingpageContent": {
    "heroSection": {
      "headline": "Hành Trình Di Sản Miền Bắc Việt Nam",
      "subtitle": "Trải nghiệm văn hóa thanh lịch & thiên nhiên kỳ vĩ được may đo riêng cho gia đình"
    },
    "visualDescription": "Một bức ảnh flycam chụp vịnh Hạ Long lúc hoàng hôn với những đảo đá vôi nhô lên mặt nước xanh lục bảo, phản chiếu ánh nắng vàng rực rỡ."
  },
  "journeyGlance": {
    "market": "GCC",
    "guestProfile": "Gia đình Qatari (4 Người lớn, 4 Trẻ em)",
    "hotelStandard": "5★ Luxury / Boutique",
    "mealPreference": "Thực đơn thân thiện Halal (Hải sản & Ăn chay chọn lọc)",
    "priceType": "Indicative",
    "tourCode": "VS-2026-N12",
    "domesticFlights": "Không bao gồm (Quý khách tự túc hoặc báo giá riêng)",
    "priceBasis": "Cơ sở phòng đôi / gia đình (Twin/Double/Family Sharing)",
    "partnerNote": "Báo giá tham khảo dành cho chuyến đi",
    "validity": "Giá trị tham khảo cho đến khi dịch vụ được xác nhận chính thức"
  },
  "whyWorks": {
    "privateFlexible": "Phương tiện di chuyển và hướng dẫn viên riêng đảm bảo gia đình có thể tự do điều chỉnh thời gian và tốc độ tham quan.",
    "comfort": "Lộ trình di chuyển hợp lý với các chặng nghỉ chất lượng cao, hạn chế tối đa việc di chuyển vội vàng gây mệt mỏi.",
    "muslimFriendly": "Các nhà hàng và điểm dừng chân được tuyển chọn kỹ lưỡng, cung cấp thực đơn không thịt lợn, ưu tiên hải sản và rau quả tươi ngon.",
    "balancedHighlights": "Kết hợp hài hòa giữa khám phá lịch sử thủ đô Hà Nội, ngủ đêm trên du thuyền Hạ Long đẳng cấp và thư giãn."
  },
  "itinerary": [
    {
      "dayNumber": 1,
      "destination": "Hà Nội",
      "summary": "Chào đón nồng hậu tại sân bay Nội Bài. Xe riêng đưa gia đình về nhận phòng khách sạn sang trọng tại trung tâm thành phố. Buổi tối tự do thư giãn.",
      "mainInclusions": "Xe riêng đưa đón sân bay, hướng dẫn viên tiếng Anh, nước uống chào mừng.",
      "senseOfPace": "Chậm rãi & thư giãn sau chuyến bay dài.",
      "dining": "Không bao gồm bữa tối (Gợi ý nhà hàng Halal gần khách sạn)"
    },
    {
      "dayNumber": 2,
      "destination": "Hà Nội - Vịnh Hạ Long",
      "summary": "Khởi hành đi Vịnh Hạ Long bằng xe Limousine cao cấp. Check-in du thuyền 5 sao, thưởng thức bữa trưa hải sản tươi ngon và du ngoạn qua các đảo đá vôi kỳ vĩ.",
      "mainInclusions": "Xe limousine khứ hồi, vé du thuyền 2 ngày 1 đêm, các hoạt động chèo thuyền kayak/thăm hang.",
      "senseOfPace": "Trôi chảy, nhẹ nhàng hòa mình vào thiên nhiên.",
      "dining": "Ăn sáng tại khách sạn, Ăn trưa & tối hải sản sang trọng trên du thuyền"
    }
  ],
  "hotelPlan": {
    "hotels": [
      {
        "destination": "Hà Nội",
        "checkInDate": "2026-09-26",
        "checkOutDate": "2026-09-27",
        "hotelArrangement": "Sofitel Legend Metropole Hanoi - 1 Đêm - Premium Room (Twin/Double)"
      },
      {
        "destination": "Vịnh Hạ Long",
        "checkInDate": "2026-09-27",
        "checkOutDate": "2026-09-28",
        "hotelArrangement": "Du Thuyền Orchid Classic - 1 Đêm - Suite Cabin rộng rãi"
      }
    ],
    "roomNotes": "Yêu cầu phòng thông nhau (connecting rooms) hoặc liền kề cho gia đình có trẻ em."
  },
  "optionalEnhancements": [
    {
      "title": "Hướng dẫn viên nói tiếng Ả Rập suốt tuyến",
      "status": "On request"
    },
    {
      "title": "Nâng hạng lên Cabin Suite Hoàng Gia trên du thuyền",
      "status": "Subject to availability"
    }
  ],
  "bookingTerms": {
    "deposit": "Đặt cọc trước 30% tổng chi phí dịch vụ ngay sau khi hai bên ký kết xác nhận.",
    "balance": "Thanh toán 70% còn lại tối thiểu 30 ngày trước ngày khởi hành chính thức.",
    "cancellation": "Hủy dịch vụ trước 45 ngày: miễn phí. Từ 30-44 ngày: phạt 50%. Dưới 30 ngày: phạt 100%.",
    "confirmation": "Tất cả dịch vụ chỉ được giữ chỗ chính thức sau khi nhận được tiền đặt cọc."
  },
  "finalization": {
    "finalDetailsRequired": "Danh sách họ tên đầy đủ, ngày tháng năm sinh, số hộ chiếu của tất cả các thành viên trong gia đình.",
    "afterConfirmation": "Vietnam Safar sẽ gửi toàn bộ phiếu xác nhận dịch vụ (Voucher), thông tin liên hệ khẩn cấp 24/7 và cẩm nang du lịch trước 10 ngày khởi hành."
  },
  "pricing": {
    "currency": "USD",
    "pricingTitle": "BÁO GIÁ LANDING PAGE CHI TIẾT",
    "basis": "Báo giá net mang tính chất tham khảo dựa trên nhóm 8 khách (4 người lớn & 4 trẻ em)",
    "priceOptions": [
      {
        "label": "Tùy chọn Standard (Khách sạn 4★ Premium & Du thuyền cao cấp)",
        "notes": "Bao gồm toàn bộ xe đưa đón riêng, vé tham quan và hướng dẫn viên.",
        "amount": 1250.0
      },
      {
        "label": "Tùy chọn Luxury (Khách sạn 5★ Ultra-Luxury & Du thuyền Orchid Classic)",
        "notes": "Trải nghiệm đẳng cấp nhất với dịch vụ VIP tại điểm đến.",
        "amount": 1850.0
      }
    ],
    "subtotal": 14800.0,
    "discountTotal": 800.0,
    "taxTotal": 0.0,
    "grandTotal": 14000.0
  },
  "retrievalStatus": {
    "hotel": "pending",
    "activity": "pending",
    "guide": "not_required",
    "transfer": "pending",
    "flight": "not_required"
  },
  "candidateBlocks": [
    {
      "block_id": "blk_hotel_hanoi",
      "service_type": "hotel",
      "destination": "Hanoi",
      "source_day_numbers": [1]
    },
    {
      "block_id": "blk_cruise_halong",
      "service_type": "hotel",
      "destination": "Halong Bay",
      "source_day_numbers": [2]
    }
  ],
  "quotationNumber": "QT-2026-0001"
}
```

### Response (201 Created)

```json
{
  "quotationId": "quo_effb6b1d7c83",
  "status": "published",
  "version": 1,
  "message": "Landing page published. Open quotationUrl to preview and edit inline.",
  "quotationUrl": "https://journeys.vietnamsafar.vn/quotations/quo_effb6b1d7c83",
  "pdfUrl": "https://journeys.vietnamsafar.vn/quotations/quo_effb6b1d7c83/pdf"
}
```

### Response (400/422 — Validation Error)

```json
{
  "detail": [
    {
      "type": "missing",
      "loc": [
        "body",
        "landingpageContent"
      ],
      "msg": "Field required",
      "input": {}
    }
  ],
  "hint": "Field path is in 'loc'. Check which required field is missing."
}
```

> **Note:** API endpoint và schema trên là phiên bản đề xuất dựa trên workflow. Cần xác nhận với dev team về endpoint thực tế, authentication method, và field mapping chính xác.
