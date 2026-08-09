import type { BrandThemeTokens } from '../display/types';

export type BrandKey = 'vietnam-safar' | 'capella-travel' | 'selvara';

export const DEFAULT_BRAND_KEY: BrandKey = 'vietnam-safar';
export const BRAND_PREFERENCE_KEY = 'travel_brand_tone';

export function isBrandKey(value: string | null | undefined): value is BrandKey {
  return value === 'vietnam-safar' || value === 'capella-travel' || value === 'selvara';
}

interface BrochureHeroSource {
  kicker: string;
  title: string;
  lede: string;
  metaPrimary: string;
  metaSecondary: string;
  footerMeta: string;
  backgroundImage: string;
}

interface BrochureLetterSource {
  chapterKicker: string;
  title: string;
  highlight: string;
  greeting: string;
  intro: string;
  body: string[];
  outro: string;
  signatureName: string;
  signatureRole: string;
  contactLine: string;
}

interface BrochureRouteSource {
  title: string;
  description: string;
  segments: Array<{
    sequence: string;
    title: string;
    description: string;
    sidebarLabel?: string;
    duration: string;
    hotelName: string;
    coordinates: [number, number];
    city: string;
    image: string;
  }>;
}

interface BrochureDaySource {
  dayLabel: string;
  title: string;
  city: string;
  description: string[];
  highlights: string;
  notes: string[];
  overnight: string;
  meals: string[];
  heroImage: string;
  secondaryImages: string[];
}

interface BrochureHotelSource {
  city: string;
  name: string;
  intro: string;
  dateRanges: string[];
  telephone: string;
  hotelImage: string;
  roomImage: string;
  roomType: string;
}

interface BrochurePricingSource {
  kicker: string;
  title: string;
  description: string;
  importantNote: string;
  options: Array<{
    category: string;
    optionName?: string;
    totalPrice?: string;
    perPersonPrice: string;
  }>;
}

interface BrochureDesignerSource {
  kicker: string;
  title: string;
  quote: string;
  name: string;
  subtitle: string;
  signatureLabel: string;
  experienceNote: string;
  avatar: string;
  finalRequirements: string[];
  confirmationItems: string[];
}

interface BrandBrochureSource {
  hero: BrochureHeroSource;
  letter: BrochureLetterSource;
  routeMap: BrochureRouteSource;
  itineraryDivider: {
    kicker: string;
    title: string;
    tagline: string;
    image: string;
  };
  itinerary: {
    kicker: string;
    title: string;
    description: string;
    days: BrochureDaySource[];
  };
  hotels: {
    title: string;
    description: string;
    roomNotes: string;
    cards: BrochureHotelSource[];
  };
  staysDivider: {
    image: string;
    kicker: string;
    title: string;
    tagline: string;
    closing: string;
  };
  pricing: BrochurePricingSource;
  inclusionsExclusions: {
    title: string;
    inclusionsLead: string;
    exclusionsLead: string;
    inclusions: string[];
    exclusions: string[];
  };
  paymentTerms: {
    kicker: string;
    title: string;
    description: string;
    cta: string;
    terms: Array<{
      label: string;
      bodyRichText: string;
    }>;
  };
  designer: BrochureDesignerSource;
  footer: {
    text: string;
    secondaryMeta: string;
  };
  states: {
    loadingTitle: string;
    loadingBody: string;
    errorTitle: string;
    errorBody: string;
    notFoundTitle: string;
    notFoundBody: string;
  };
}

export interface BrandInfo {
  id: BrandKey;
  name: string;
  logoGlyph: string;
  tagline: string;
  badge: string;
  description: string;
  mood: string;
  targetAudience: string;
  toneOfVoice: string;
  typography: {
    styleNote: string;
  };
  contact: {
    phone: string;
    email: string;
    website: string;
    whatsapp: string;
  };
  themeTokens: Omit<BrandThemeTokens, 'brandKey' | 'themeId'>;
  brochure: BrandBrochureSource;
}

function createThemeTokens(
  tokens: Omit<BrandThemeTokens, 'brandKey' | 'themeId'>
) {
  return tokens;
}

export const BRANDS_DATA: Record<BrandKey, BrandInfo> = {
  'vietnam-safar': {
    id: 'vietnam-safar',
    name: 'Vietnam Safar',
    logoGlyph: '🌿',
    tagline: 'Wild Vietnam & Tropical Expeditions',
    badge: 'Tropical Nature Expedition',
    description:
      'Những hành trình thiên nhiên được thiết kế với nhịp điệu mạnh mẽ, giàu khám phá và mang cảm giác chạm rất gần vào bản địa.',
    mood: 'Rực rỡ, hoang dã, nhiều chuyển động, giàu cảm giác khám phá',
    targetAudience:
      'Nhóm bạn yêu trekking, nhà thám hiểm hiện đại, khách quốc tế muốn thấy Việt Nam nguyên bản theo nhịp nhanh và giàu hình ảnh.',
    toneOfVoice:
      'Tràn năng lượng, chắc nhịp, gợi cảm giác khám phá nhưng vẫn tinh chỉnh như một hành trình cao cấp.',
    typography: {
      styleNote:
        'Cormorant cho heading, Montserrat cho body, bảng màu lấy cảm hứng từ rừng nhiệt đới và giấy ngà.',
    },
    contact: {
      phone: '+84 901 234 567',
      email: 'concierge@vietnamsafar.com',
      website: 'www.vietnamsafar.com',
      whatsapp: 'https://wa.me/84901234567',
    },
    themeTokens: createThemeTokens({
      palette: {
        canvas: '#f9f6f0',
        paper: '#f9f6f0',
        ink: '#11130f',
        mutedInk: '#2c2a29',
        accent: '#095f43',
        accentAlt: '#b7894b',
        contrast: '#0d3f32',
        onContrast: '#ffffff',
        focus: '#095f43',
        storyContrast: '#0d3f32',
        investmentSurface: '#0d3f32',
        investmentText: '#ffffff',
      },
      radii: {
        card: '0.5rem',
        button: '0.375rem',
        frame: '0.625rem',
        pill: '999px',
      },
    }),
    brochure: {
      hero: {
        kicker: 'A Privately Arranged Journey',
        title: 'Chạm Vào Trái Tim Hoang Dã Của Đông Dương',
        lede:
          'Một brochure theme giàu hình ảnh cho hành trình băng rừng, vượt đèo và sống sát hơn với thiên nhiên bản địa.',
        metaPrimary: 'Hà Nội • Hà Giang • Phong Nha • Mekong',
        metaSecondary: '10 days / 9 nights • Editorial route storytelling',
        footerMeta:
          '“Bản sắc thương hiệu nằm ở nhịp khám phá: vừa mạnh, vừa giàu xúc cảm, vừa đủ tinh tế để trở thành một hành trình đáng nhớ.”',
        backgroundImage:
          'https://images.unsplash.com/photo-1528127269322-539801943592?q=80&w=2070&auto=format&fit=crop',
      },
      letter: {
        chapterKicker: 'Chapter 01 · Journey Overview',
        title: 'Một hành trình thiên nhiên được dàn dựng như một câu chuyện nhiều lớp',
        highlight:
          'Từ cao nguyên đá đến sông nước miền Tây, nhịp điệu luôn được đẩy về phía trải nghiệm thật, khí hậu thật và những khoảnh khắc không thể thay bằng ảnh stock.',
        greeting: 'Dear Explorer,',
        intro:
          'Brochure này được xây như một hành trình thị giác trước khi trở thành hành trình thực tế.',
        body: [
          'Phần mở đầu tạo cảm giác “giấy + địa hình + ánh sáng nhiệt đới”, rồi chuyển dần sang layout editorial để làm rõ chiều sâu trải nghiệm ở từng chặng.',
          'Route map và itinerary không chỉ kể điểm đến mà còn cho thấy sắc thái di chuyển: từ đèo núi, hang động, đến đồng bằng phù sa và đời sống bản địa.',
        ],
        outro:
          'Toàn bộ cụm public section được tổ chức để người xem vừa hiểu tuyến hành trình vừa cảm được tinh thần khám phá của thương hiệu.',
        signatureName: 'Nguyen Hoang Nam',
        signatureRole: 'Travel Designer',
        contactLine: 'concierge@vietnamsafar.com · +84 901 234 567',
      },
      routeMap: {
        title: 'Your route through the wild heart of Vietnam',
        description:
          'Tuyến hành trình ưu tiên địa hình, cảm giác di chuyển và những đoạn chuyển mood rõ rệt để brochure giữ được nhịp kể chuyện.',
        segments: [
          {
            sequence: '01',
            title: 'Hanoi arrival & northern briefing',
            description: 'Đón khách, làm mềm nhịp trước khi tăng dần độ phiêu lưu bằng một đêm nghỉ giàu chất địa phương.',
            duration: '1 night',
            hotelName: 'La Siesta Classic',
            coordinates: [21.0278, 105.8342],
            city: 'Hà Nội',
            image:
              'https://images.unsplash.com/photo-1508061253366-f7da158b6d46?q=80&w=900&auto=format&fit=crop',
          },
          {
            sequence: '02',
            title: 'Ha Giang loop & Tu San canyon',
            description: 'Ngày địa hình mạnh nhất, nơi texture núi đá và đường đèo trở thành phần chính của câu chuyện.',
            duration: '3 nights',
            hotelName: 'Auberge de Meo Vac',
            coordinates: [23.2243, 105.2865],
            city: 'Hà Giang',
            image:
              'https://images.unsplash.com/photo-1540611025311-01df3cef54b5?q=80&w=900&auto=format&fit=crop',
          },
          {
            sequence: '03',
            title: 'Phong Nha cave expedition',
            description: 'Chuyển từ đá sắc sang bóng tối và độ sâu, với nhịp trải nghiệm chậm nhưng giàu căng thẳng thị giác.',
            duration: '2 nights',
            hotelName: 'Chay Lap Farmstay',
            coordinates: [17.5451, 106.2870],
            city: 'Phong Nha',
            image:
              'https://images.unsplash.com/photo-1518509562904-e7ef99cdcc86?q=80&w=900&auto=format&fit=crop',
          },
          {
            sequence: '04',
            title: 'Mekong wetlands finale',
            description: 'Hạ nhịp bằng ánh sáng nước và đời sống miền sông, kết thúc bằng cảm giác phóng khoáng thay vì đóng khung.',
            duration: '3 nights',
            hotelName: 'Victoria Can Tho',
            coordinates: [10.0452, 105.7469],
            city: 'Mekong',
            image:
              'https://images.unsplash.com/photo-1569154941061-e231b4725ef1?q=80&w=900&auto=format&fit=crop',
          },
        ],
      },
      itineraryDivider: {
        kicker: 'Chapter 02 · Day-by-Day',
        title: 'Every day tuned for movement, texture, and breath',
        tagline:
          'Desktop giữ asymmetry như prototype. Mobile ưu tiên flow đọc top-down. PDF gom ngày theo cụm để tránh vỡ nhịp.',
        image:
          'https://images.unsplash.com/photo-1510312305653-8ed496efae75?q=80&w=1600&auto=format&fit=crop',
      },
      itinerary: {
        kicker: 'CHAPTER 02 · DAY-BY-DAY ITINERARY',
        title: 'Day-by-Day Journey Program',
        description:
          'Your journey, carefully crafted.',
        days: [
          {
            dayLabel: 'Day 01',
            title: 'Arrival in Hanoi and quiet briefing dinner',
            city: 'Hanoi',
            description: [
              'Đón khách tại sân bay, chuyển về khu phố cũ và làm quen nhịp hành trình bằng một bữa tối tinh giản.',
              'Tối ưu cho brochure opening arc: ít thông tin nhưng đủ tạo cảm giác chuẩn bị cho một chặng lớn hơn.',
            ],
            highlights: 'Arrival support · welcome dinner · route orientation',
            notes: ['Private airport meet-and-greet', 'Flexible early check-in when possible'],
            overnight: 'Hanoi',
            meals: ['Dinner'],
            heroImage:
              'https://images.unsplash.com/photo-1508061253366-f7da158b6d46?q=80&w=1200&auto=format&fit=crop',
            secondaryImages: [
              'https://images.unsplash.com/photo-1555921015-5532091f6026?q=80&w=800&auto=format&fit=crop',
              'https://images.unsplash.com/photo-1512453979798-5ea266f8880c?q=80&w=800&auto=format&fit=crop',
            ],
          },
          {
            dayLabel: 'Day 02',
            title: 'Ha Giang ridge roads and Ma Pi Leng pass',
            city: 'Ha Giang',
            description: [
              'Rời Hà Nội sớm để vào cao nguyên đá, nơi con đường và mặt địa hình là nhân vật chính của toàn bộ ngày.',
              'Section này dùng day-story-grid để ảnh và copy luôn có nhịp thở riêng, không biến itinerary thành bảng text dài.',
            ],
            highlights: 'Scenic mountain drive · village stops · high-pass viewpoints',
            notes: ['Private 4x4 support vehicle', 'Photo stops adjusted to weather'],
            overnight: 'Meo Vac',
            meals: ['Breakfast', 'Lunch'],
            heroImage:
              'https://images.unsplash.com/photo-1540611025311-01df3cef54b5?q=80&w=1200&auto=format&fit=crop',
            secondaryImages: [
              'https://images.unsplash.com/photo-1513415756790-2ac1c7d4bcfe?q=80&w=800&auto=format&fit=crop',
              'https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?q=80&w=800&auto=format&fit=crop',
            ],
          },
          {
            dayLabel: 'Day 03',
            title: 'River canyon descent and cave-country transfer',
            city: 'Phong Nha',
            description: [
              'Buổi sáng xuống hẻm vực, buổi chiều chuyển sang miền hang động với mood tối hơn và đậm chất expedition.',
              'Ngày chuyển vùng này giúp layout của brochure đổi nhịp nhưng vẫn giữ một tuyến kể thống nhất.',
            ],
            highlights: 'River descent · cave arrival · evening lodge reset',
            notes: ['Suitable for editorial quote pull-outs', 'Secondary imagery reserved for cave textures'],
            overnight: 'Phong Nha',
            meals: ['Breakfast', 'Dinner'],
            heroImage:
              'https://images.unsplash.com/photo-1518509562904-e7ef99cdcc86?q=80&w=1200&auto=format&fit=crop',
            secondaryImages: [
              'https://images.unsplash.com/photo-1493246507139-91e8fad9978e?q=80&w=800&auto=format&fit=crop',
              'https://images.unsplash.com/photo-1500534314209-a25ddb2bd429?q=80&w=800&auto=format&fit=crop',
            ],
          },
        ],
      },
      hotels: {
        title: 'Selected Hotel Plan',
        description:
          'Hotel section đi theo alternating editorial card để mỗi stay vừa là nơi nghỉ vừa là một lớp mood khác nhau trong hành trình.',
        roomNotes:
          'Ưu tiên phòng có tầm nhìn, ánh sáng tự nhiên tốt và trải nghiệm gắn với địa phương hơn là luxury rập khuôn.',
        cards: [
          {
            city: 'Hanoi, Vietnam',
            name: 'La Siesta Classic Hang Thung',
            intro:
              'Một điểm nghỉ chuyển tiếp rất phù hợp cho ngày đầu: ấm, có chiều sâu chất liệu và không lấn át tinh thần hoang dã của phần sau.',
            dateRanges: ['01 Oct – 02 Oct'],
            telephone: '+84 24 3926 3641',
            hotelImage:
              'https://images.unsplash.com/photo-1505693416388-ac5ce068fe85?q=80&w=1000&auto=format&fit=crop',
            roomImage:
              'https://images.unsplash.com/photo-1505693416388-ac5ce068fe85?q=80&w=1000&auto=format&fit=crop',
            roomType: 'Junior Suite',
          },
          {
            city: 'Meo Vac, Vietnam',
            name: 'Auberge de Meo Vac',
            intro:
              'Lodge miền núi phù hợp cho editorial alternation, với ánh sáng gỗ và mặt đứng đủ chân thật để không phá tuyến visual của brochure.',
            dateRanges: ['02 Oct – 05 Oct'],
            telephone: '+84 219 377 1789',
            hotelImage:
              'https://images.unsplash.com/photo-1505693416388-ac5ce068fe85?q=80&w=1000&auto=format&fit=crop',
            roomImage:
              'https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?q=80&w=1000&auto=format&fit=crop',
            roomType: 'Panorama Ridge Room',
          },
        ],
      },
      staysDivider: {
        image:
          'https://images.unsplash.com/photo-1519046904884-53103b34b206?q=80&w=1600&auto=format&fit=crop',
        kicker: 'Chapter 03 · THE JOURNEY, BROUGHT TOGETHER',
        title: 'A softer landing without losing the wild',
        tagline:
          'Divider section giữ không khí editorial full-bleed trên desktop, nhưng sẽ co về stacked composition khi cần tối ưu readability.',
        closing: 'The stay story should support the route story, never compete with it.',
      },
      pricing: {
        kicker: 'PACKAGE PRICING',
        title: 'Journey Investment:',
        description: 'Currency: USD. Final rates subject to reconfirmation.',
        importantNote:
          'Rates are indicative and subject to reconfirmation at the time of booking.',
        options: [
          {
            category: 'Package 14D13N (14 Days 13 Nights)',
            optionName: 'Single occupancy supplement: $1,170',
            totalPrice: '',
            perPersonPrice: 'USD 4,416/ person',
          },
          {
            category: 'Package 8D7N (8 Days 7 Nights)',
            optionName: 'Single occupancy supplement: $1,200',
            totalPrice: '',
            perPersonPrice: 'USD 2,346/ person',
          },
        ],
      },
      inclusionsExclusions: {
        title: 'What Your Journey Includes',
        inclusionsLead:
          'Your journey has been thoughtfully arranged to ensure a seamless and comfortable experience throughout.',
        exclusionsLead:
          'To keep your journey transparent and clearly defined, the following are not included unless specifically stated otherwise:',
        inclusions: [
          'Private airport transfer, international arrival fast-track assistance and Vietnam visa services.',
          'All private transfer with english-speaking guides mentioned in the itinerary.',
          'Experiences, admission fee, and exclusive arrangements throughout the journey mentioned in the itinerary.',
          'All meals mentioned in the itinerary.',
          'Domestic flights.',
        ],
        exclusions: [
          'International flights.',
          'Travel insurance and visa services.',
          'Personal expenses.',
          'Optional experiences not specified in the itinerary.',
          'Tips and gratuities.',
          'Any services not expressly listed as included.',
        ],
      },
      paymentTerms: {
        kicker: 'IMPORTANT NOTES',
        title: 'Booking Payment Terms',
        description:
          'Commercial conditions, deposits, and cancellation policy for this booking.',
        cta: 'Approve & Book This Journey',
        terms: [
          {
            label: 'Deposit',
            bodyRichText:
              '<ul><li>A deposit of 30% of the total tour cost is required upon confirmation of the booking. This deposit is non-refundable.</li><li>For bookings confirmed within 60 days of arrival, full payment of 100% of the total tour cost is required at the time of confirmation.</li></ul>',
          },
          {
            label: 'Balance',
            bodyRichText:
              '<p>The remaining 70% balance must be paid no later than 45 days prior to the scheduled arrival date.</p>',
          },
          {
            label: 'Cancellation',
            bodyRichText:
              '<ul><li>45+ days prior: Deposit forfeited (30%).</li><li>45–31 days prior: 50% of total cost forfeited.</li><li>30–20 days prior: 75% of total cost forfeited.</li><li>Under 20 days prior: 100% of total cost forfeited.</li></ul>',
          },
        ],
      },
      designer: {
        kicker: 'Your Journey Designer',
        title: 'Let us shape the final details together',
        quote:
          'Tôi tin rằng ham muốn dịch chuyển là thứ có thể lây lan. Việc của chúng tôi là biến cảm hứng đó thành một hành trình có cấu trúc, cảm xúc và độ chân thật đủ sâu.',
        name: 'Nguyen Hoang Nam',
        subtitle: 'Lead Expedition Designer',
        signatureLabel: 'Travel Designer',
        experienceNote:
          'Đồng hành từ giai đoạn chốt route, chọn stay, tối ưu khung giờ chụp ảnh cho đến các xử lý mềm về pacing.',
        avatar: 'https://images.unsplash.com/photo-1500648767791-00dcc994a43e?q=80&w=800&auto=format&fit=crop',
        finalRequirements: [
          'Passport copy valid for at least 6 months',
          'Domestic flight names exactly as in passport',
          'Fitness and dietary notes before confirmation',
        ],
        confirmationItems: [
          'Dedicated local concierge support throughout the trip',
          'Supplier vouchers and final timing sheet',
          'Weather-aware route adjustments when needed',
        ],
      },
      footer: {
        text:
          'Vietnam Safar crafts editorial-style expedition journeys across Vietnam with a focus on movement, landscape, and local texture.',
        secondaryMeta: 'Brochure theme preview · desktop / mobile / pdf parity',
      },
      states: {
        loadingTitle: 'Đang tải hành trình thiên nhiên',
        loadingBody: 'Hệ brochure đang dựng lại layout và section data cho Vietnam Safar.',
        errorTitle: 'Không thể dựng brochure theme',
        errorBody: 'Đã có lỗi khi tải dữ liệu hiển thị. Hãy thử tải lại để dựng lại các public section.',
        notFoundTitle: 'Không tìm thấy hành trình này',
        notFoundBody: 'Liên kết bạn mở không còn brochure public tương ứng hoặc đã được thay bằng bản khác.',
      },
    },
  },
  'capella-travel': {
    id: 'capella-travel',
    name: 'Capella Travel',
    logoGlyph: '👑',
    tagline: 'Bespoke Ultra-Luxury & Elite Journeys',
    badge: 'Ultra Luxury Heritage',
    description:
      'Brochure được điều chỉnh về phía quý phái, trang trọng và giàu cảm giác curated, nhưng vẫn giữ cùng contract layout và section API.',
    mood: 'Kiêu sa, nghi thức, yên tĩnh, chính xác, giàu cảm giác bespoke',
    targetAudience:
      'Gia đình thượng lưu, doanh nhân cao cấp, khách cần itinerary riêng tư với dịch vụ hoàn toàn được điều phối.',
    toneOfVoice:
      'Trang trọng, mềm nhưng chắc, tập trung vào sự hiếm có, chiều sâu dịch vụ và độ chỉn chu.',
    typography: {
      styleNote:
        'Cormorant dùng cho heading và cả accent để tăng chất heritage; scale rộng hơn cho hero và section title.',
    },
    contact: {
      phone: '+84 888 100 100',
      email: 'concierge@capellatravel.com',
      website: 'www.capellatravel.com',
      whatsapp: 'https://wa.me/84888100100',
    },
    themeTokens: createThemeTokens({
      palette: {
        canvas: '#f9f6f0',
        paper: '#f9f6f0',
        ink: '#171511',
        mutedInk: '#2c2a29',
        accent: '#d4af37',
        accentAlt: '#a98338',
        contrast: '#a98338',
        onContrast: '#ffffff',
        focus: '#a98338',
        storyContrast: '#333333',
        investmentSurface: '#a98338',
        investmentText: '#171511',
      },
      radii: {
        card: '0.5rem',
        button: '0.375rem',
        frame: '0.625rem',
        pill: '999px',
      },
    }),
    brochure: {
      hero: {
        kicker: 'A Privately Arranged Heritage Escape',
        title: 'Đỉnh Cao Nghệ Thuật Thưởng Lãm Thượng Lưu',
        lede:
          'Cùng một brochure system, nhưng được dàn lại thành nhịp kể tao nhã hơn: nhiều khoảng lặng, nhiều cảm giác curated, và giàu nghi thức dịch vụ.',
        metaPrimary: 'Ha Long • Ninh Thuan • Hue • Hoi An',
        metaSecondary: '8 days / 7 nights • heritage + private service arc',
        footerMeta:
          '“Luxury trong brochure này không đến từ việc xếp thêm lớp trang trí, mà từ cách nội dung được chắt lọc, giãn nhịp và trình bày với sự tự tin.”',
        backgroundImage:
          'https://images.unsplash.com/photo-1566073771259-6a8506099945?q=80&w=2070&auto=format&fit=crop',
      },
      letter: {
        chapterKicker: 'Chapter 01 · Bespoke Overview',
        title: 'Một brochure luxury bắt đầu bằng sự yên tĩnh có chủ đích',
        highlight:
          'Theme vẫn là brochure, nhưng mọi khoảng trắng, shell frame và scale typography đều được chỉnh để người xem cảm nhận được độ hiếm có trước cả khi đọc đến service details.',
        greeting: 'Dear Guest,',
        intro:
          'Capella Travel dùng cùng section architecture nhưng đẩy cảm xúc về phía heritage, riêng tư và điều phối tinh tế.',
        body: [
          'Hero không cần nhiều dòng; route map được giữ gọn; pricing và terms được trình bày như tài liệu thương mại cao cấp thay vì landing page thuần marketing.',
          'Điểm mạnh của hệ mới là brand vẫn có thể khác font role, shell ratio, responsive behavior và display variants mà không làm vỡ API của section component.',
        ],
        outro:
          'Đó là lý do theme được định nghĩa như “một tập hợp layout được sắp xếp với nhau”, chứ không chỉ là bộ màu và font.',
        signatureName: 'Victoria Le',
        signatureRole: 'Private Journey Director',
        contactLine: 'concierge@capellatravel.com · +84 888 100 100',
      },
      routeMap: {
        title: 'An itinerary of private access and refined pacing',
        description:
          'Tuyến route được viết theo logic service choreography: arrival, immersion, transfer, and a quiet closing gesture.',
        segments: [
          {
            sequence: '01',
            title: 'Hanoi arrival and butler reception',
            description: 'Bắt đầu bằng nhịp đón riêng và một đêm nghỉ đóng vai trò prelude cho trải nghiệm lớn hơn.',
            duration: '1 night',
            hotelName: 'Capella Hanoi',
            coordinates: [21.0245, 105.8573],
            city: 'Hanoi',
            image:
              'https://images.unsplash.com/photo-1578683010236-d716f9a3f461?q=80&w=900&auto=format&fit=crop',
          },
          {
            sequence: '02',
            title: 'Private yacht on Ha Long Bay',
            description: 'Một ngày nước, ánh sáng và dịch vụ, với rhythm chậm và không gian nhìn dài hơn.',
            duration: '2 nights',
            hotelName: 'Heritage Private Yacht',
            coordinates: [20.9101, 107.1839],
            city: 'Ha Long',
            image:
              'https://images.unsplash.com/photo-1544551763-46a013bb70d5?q=80&w=900&auto=format&fit=crop',
          },
          {
            sequence: '03',
            title: 'Amanoi coastal reset',
            description: 'Phần nghỉ riêng tư đóng vai trò làm mềm nhịp itinerary trước khi đi vào heritage finale.',
            duration: '2 nights',
            hotelName: 'Amanoi',
            coordinates: [11.6435, 109.0078],
            city: 'Ninh Thuan',
            image:
              'https://images.unsplash.com/photo-1582719508461-905c673771fd?q=80&w=900&auto=format&fit=crop',
          },
          {
            sequence: '04',
            title: 'Imperial culture closing in Hue',
            description: 'Kết bằng một chương văn hóa được dàn như closing chapter của toàn brochure.',
            duration: '2 nights',
            hotelName: 'Azerai La Residence',
            coordinates: [16.4637, 107.5909],
            city: 'Hue',
            image:
              'https://images.unsplash.com/photo-1535827841776-24afc1e255ac?q=80&w=900&auto=format&fit=crop',
          },
        ],
      },
      itineraryDivider: {
        kicker: 'Chapter 02 · Service Program',
        title: 'Every movement polished, every pause intentional',
        tagline:
          'Typography scale, shell frame và layout compaction của Capella được giữ riêng nhưng tất cả vẫn đi qua cùng registry.',
        image:
          'https://images.unsplash.com/photo-1506744038136-46273834b3fb?q=80&w=1600&auto=format&fit=crop',
      },
      itinerary: {
        kicker: 'Curated Sequence',
        title: 'A high-touch day-by-day arrangement',
        description:
          'Cùng contract day-story-grid nhưng nội dung được viết theo cadence mềm hơn, nhấn vào private service và sensory details.',
        days: [
          {
            dayLabel: 'Day 01',
            title: 'VIP arrival, suite check-in, and private supper',
            city: 'Hanoi',
            description: [
              'Khởi đầu bằng lối tiếp cận rất yên: đón riêng, lounge riêng và thời gian căn chỉnh cơ thể sau chuyến bay.',
              'Brochure version ưu tiên cảm giác ritual hơn là density thông tin.',
            ],
            highlights: 'VIP reception · suite arrival · private dining',
            notes: ['Fast-track airport handling', 'Personalized welcome amenities'],
            overnight: 'Hanoi',
            meals: ['Dinner'],
            heroImage:
              'https://images.unsplash.com/photo-1578683010236-d716f9a3f461?q=80&w=1200&auto=format&fit=crop',
            secondaryImages: [
              'https://images.unsplash.com/photo-1551882547-ff40c63fe5fa?q=80&w=800&auto=format&fit=crop',
              'https://images.unsplash.com/photo-1505693416388-ac5ce068fe85?q=80&w=800&auto=format&fit=crop',
            ],
          },
          {
            dayLabel: 'Day 02',
            title: 'Private yacht and bay-light choreography',
            city: 'Ha Long',
            description: [
              'Một ngày di chuyển rất ít nhưng cảm giác “được điều phối” hiện lên ở mọi điểm chạm.',
              'Các layout gallery phụ giúp phần này giữ đúng tinh thần editorial luxury thay vì catalogue dịch vụ.',
            ],
            highlights: 'Private cruise · Michelin-style lunch · sunset deck ritual',
            notes: ['Flexible tender landing based on weather', 'Butler-managed timing'],
            overnight: 'Ha Long Bay',
            meals: ['Breakfast', 'Lunch', 'Dinner'],
            heroImage:
              'https://images.unsplash.com/photo-1544551763-46a013bb70d5?q=80&w=1200&auto=format&fit=crop',
            secondaryImages: [
              'https://images.unsplash.com/photo-1499793983690-e29da59ef1c2?q=80&w=800&auto=format&fit=crop',
              'https://images.unsplash.com/photo-1473116763249-2faaef81ccda?q=80&w=800&auto=format&fit=crop',
            ],
          },
          {
            dayLabel: 'Day 03',
            title: 'Coastal sanctuary and tailored leisure',
            city: 'Ninh Thuan',
            description: [
              'Amanoi section chuyển brochure sang nhịp nghỉ, mở ra nhiều khoảng trắng hơn và ít câu hơn.',
              'PDF compaction sẽ gom các khối này lại nhưng vẫn giữ thứ tự ưu tiên về hình ảnh và title block.',
            ],
            highlights: 'Spa ritual · coastal villa time · sommelier-led dinner',
            notes: ['Private wellness curation', 'Flexible dining placement'],
            overnight: 'Ninh Thuan',
            meals: ['Breakfast', 'Dinner'],
            heroImage:
              'https://images.unsplash.com/photo-1582719508461-905c673771fd?q=80&w=1200&auto=format&fit=crop',
            secondaryImages: [
              'https://images.unsplash.com/photo-1519046904884-53103b34b206?q=80&w=800&auto=format&fit=crop',
              'https://images.unsplash.com/photo-1496417263034-38ec4f0b665a?q=80&w=800&auto=format&fit=crop',
            ],
          },
        ],
      },
      hotels: {
        title: 'Residences selected for grace, not noise',
        description:
          'Khác biệt nằm ở cách stay section dùng ít card hơn, nhiều breathing room hơn và weight nặng hơn cho title/meta.',
        roomNotes:
          'Tất cả lựa chọn phòng ưu tiên privacy, arrival experience và service consistency hơn là chỉ số diện tích đơn thuần.',
        cards: [
          {
            city: 'Hanoi, Vietnam',
            name: 'Capella Hanoi',
            intro:
              'Một property giàu sense of occasion, phù hợp để mở đầu brochure bằng confidence thay vì phô trương.',
            dateRanges: ['10 Nov – 11 Nov'],
            telephone: '+84 24 3987 8888',
            hotelImage:
              'https://images.unsplash.com/photo-1551882547-ff40c63fe5fa?q=80&w=1000&auto=format&fit=crop',
            roomImage:
              'https://images.unsplash.com/photo-1505693416388-ac5ce068fe85?q=80&w=1000&auto=format&fit=crop',
            roomType: 'Premier Suite',
          },
          {
            city: 'Ninh Thuan, Vietnam',
            name: 'Amanoi',
            intro:
              'Phần stay được dựng như một khoảng thở lớn, giúp brochure chuyển từ heritage richness sang luxury stillness.',
            dateRanges: ['12 Nov – 14 Nov'],
            telephone: '+84 259 377 0777',
            hotelImage:
              'https://images.unsplash.com/photo-1582719508461-905c673771fd?q=80&w=1000&auto=format&fit=crop',
            roomImage:
              'https://images.unsplash.com/photo-1496417263034-38ec4f0b665a?q=80&w=1000&auto=format&fit=crop',
            roomType: 'Ocean Pool Pavilion',
          },
        ],
      },
      staysDivider: {
        image:
          'https://images.unsplash.com/photo-1506744038136-46273834b3fb?q=80&w=1600&auto=format&fit=crop',
        kicker: 'Chapter 03 · Signature Stays',
        title: 'Private stays as part of the service narrative',
        tagline:
          'View mode rules giữ nguyên: desktop duy trì editorial split, mobile gom về reading order, pdf group theo page shell.',
        closing: 'Luxury needs silence between the details.',
      },
      pricing: {
        kicker: 'Package Pricing',
        title: 'Commercial presentation with restraint',
        description:
          'Pricing rows được tổ chức để nhìn giống tài liệu tư vấn hơn là bảng giá đại trà.',
        importantNote:
          'Bao gồm dịch vụ butler-selected, transfer riêng, và điều phối itinerary theo nhịp cá nhân hóa.',
        options: [
          {
            category: 'Heritage Signature',
            optionName: 'Capella Hanoi + private bay cruise',
            totalPrice: 'USD 11,800',
            perPersonPrice: 'USD 5,900 / person',
          },
          {
            category: 'Coastal Retreat',
            optionName: 'Amanoi villa + tailored leisure',
            totalPrice: 'USD 15,600',
            perPersonPrice: 'USD 7,800 / person',
          },
          {
            category: 'Grand Bespoke',
            optionName: 'Private air, yacht, and heritage finale',
            totalPrice: 'USD 24,400',
            perPersonPrice: 'USD 12,200 / person',
          },
        ],
      },
      inclusionsExclusions: {
        title: 'What your arrangement includes',
        inclusionsLead: 'Giữ wording gọn nhưng sang, đúng tinh thần commercial brochure cho phân khúc cao cấp.',
        exclusionsLead: 'Tách rõ những phần ngoài scope để tránh hứa quá mức.',
        inclusions: [
          'Private transfers, curated stays, and concierge coordination',
          'Selected fine-dining and experience meals',
          'Priority handling where available',
          'Tailored itinerary pacing and on-call support',
        ],
        exclusions: [
          'International business or first-class flights',
          'Visa, insurance, and external premium shopping services',
          'Expenses beyond the agreed itinerary scope',
          'Extra supplier charges caused by late changes',
        ],
      },
      paymentTerms: {
        kicker: 'Commercial Conditions',
        title: 'Booking & payment terms',
        description:
          'Desktop hiển thị dạng two-column detail panel, pdf group các term block để không bị gãy mạch đọc.',
        cta: 'Confirm This Bespoke Program',
        terms: [
          {
            label: 'Deposit',
            bodyRichText:
              '<p>30% to confirm planning and space hold. Peak-period and private-charter services may require a higher initial commitment.</p>',
          },
          {
            label: 'Balance',
            bodyRichText:
              '<p>Final balance is due 45 days before arrival unless earlier settlement is required by exclusive suppliers.</p>',
          },
          {
            label: 'Cancellation',
            bodyRichText:
              '<p>Refundability depends on supplier class, charter status, and cancellation timing. Exact conditions will be confirmed before deposit.</p>',
          },
          {
            label: 'Confirmation',
            bodyRichText:
              '<p>Confirmation is complete once payment clears and all premium suppliers have acknowledged the reservation.</p>',
          },
        ],
      },
      designer: {
        kicker: 'Your Journey Director',
        title: 'Let us finalize the experience privately',
        quote:
          'Luxury travel becomes memorable when every visible detail is supported by invisible preparation. That is where our role begins.',
        name: 'Victoria Le',
        subtitle: 'Private Journey Director',
        signatureLabel: 'Capella Travel',
        experienceNote:
          'Phụ trách điều phối dịch vụ cao cấp, supplier hold, private access logistics và tone consistency trong toàn bộ guest journey.',
        avatar: 'https://images.unsplash.com/photo-1544005313-94ddf0286df2?q=80&w=800&auto=format&fit=crop',
        finalRequirements: [
          'Passport details exactly as issued',
          'Preferred suite, bedding, and dietary notes',
          'Any celebration or privacy protocol requests',
        ],
        confirmationItems: [
          'Butler-ready arrival notes and supplier contacts',
          'Final itinerary booklet and service timing',
          'Dedicated support before and during the journey',
        ],
      },
      footer: {
        text:
          'Capella Travel arranges private luxury journeys across Vietnam with a focus on heritage, privacy, and meticulous service composition.',
        secondaryMeta: 'Brochure theme preview · structured for desktop, mobile, and pdf',
      },
      states: {
        loadingTitle: 'Đang tải brochure luxury',
        loadingBody: 'Các section đang được dàn lại theo theme brochure của Capella Travel.',
        errorTitle: 'Không thể tải brochure Capella',
        errorBody: 'Có lỗi xảy ra khi dựng layout hoặc data cho public display. Hãy thử lại trong giây lát.',
        notFoundTitle: 'Không tìm thấy brochure này',
        notFoundBody: 'Liên kết bạn mở không có brochure public tương ứng cho Capella Travel.',
      },
    },
  },
  selvara: {
    id: 'selvara',
    name: 'Selvara Journeys',
    logoGlyph: '🧘',
    tagline: 'Eco-Luxury & Mindful Sanctuary Retreats',
    badge: 'Mindful Eco-Retreat',
    description:
      'Theme brochure được chuyển sang nhịp dịu hơn, nhiều breathing room hơn và dùng typography/body scale mềm hơn cho các đoạn đọc dài.',
    mood: 'Tĩnh, sáng, chữa lành, ít áp lực thị giác, ưu tiên cảm giác thở',
    targetAudience:
      'Khách tìm retreat sinh thái, wellness traveller, cặp đôi hoặc gia đình cần một hành trình chữa lành có cấu trúc rõ.',
    toneOfVoice:
      'Mềm, có khoảng lặng, nhẹ nhưng không mơ hồ; luôn gợi cảm giác cân bằng và chăm sóc.',
    typography: {
      styleNote:
        'Body dùng Jost để tăng softness và readability, accent quay lại serif để giữ cảm giác hữu cơ nhưng đủ nghiêm.',
    },
    contact: {
      phone: '+84 933 222 111',
      email: 'hello@selvarajourneys.com',
      website: 'www.selvarajourneys.com',
      whatsapp: 'https://wa.me/84933222111',
    },
    themeTokens: createThemeTokens({
      palette: {
        canvas: '#f9f6f0',
        paper: '#f9f6f0',
        ink: '#11130f',
        mutedInk: '#2c2a29',
        accent: '#a98338',
        accentAlt: '#a98338',
        contrast: '#a98338',
        onContrast: '#ffffff',
        focus: '#a98338',
        storyContrast: '#0d3f32',
        investmentSurface: '#a98338',
        investmentText: '#11130f',
      },
      radii: {
        card: '0.5rem',
        button: '0.375rem',
        frame: '0.625rem',
        pill: '999px',
      },
    }),
    brochure: {
      hero: {
        kicker: 'A Mindfully Arranged Retreat',
        title: 'Trạm Dừng Chữa Lành Giữa Lòng Sinh Thái Nguyên Bản',
        lede:
          'Cùng brochure system nhưng tone được kéo về phía nhẹ hơn: nhiều nền giấy sáng, layout thoáng, typography dịu và hình ảnh có nhịp thở dài hơn.',
        metaPrimary: 'Yen Tu • Ninh Binh • Da Lat',
        metaSecondary: '7 days / 6 nights • mindful sanctuary flow',
        footerMeta:
          '“Một theme tốt không làm mọi brand trông giống nhau; nó tạo cùng chất lượng hệ thống nhưng cho mỗi brand một cách cất giọng riêng.”',
        backgroundImage:
          'https://images.unsplash.com/photo-1540555700478-4be289fbecef?q=80&w=2070&auto=format&fit=crop',
      },
      letter: {
        chapterKicker: 'Chapter 01 · Sanctuary Overview',
        title: 'Một hành trình chữa lành cần bố cục biết thở',
        highlight:
          'Selvara tận dụng cùng hệ atom, molecule và layout registry, nhưng typography/body scale và shell softness được nới ra để người xem không cảm thấy bị đẩy nhịp quá nhanh.',
        greeting: 'Dear Guest,',
        intro:
          'Trong brochure này, sự bình yên không đến từ việc thêm thật nhiều màu be, mà từ thứ tự thông tin và nhịp đọc được chăm sóc kỹ.',
        body: [
          'Hero mở mềm, route map gọn, itinerary kể chậm hơn và section designer kết thúc bằng cảm giác đồng hành thay vì thúc đẩy chốt sale.',
          'Điều đó chỉ làm được khi theme, typography, layout và section data cùng đi qua một contract thống nhất.',
        ],
        outro:
          'Khi mọi thứ được tổ chức đúng lớp, mỗi brand có thể dịu hay mạnh tùy ý mà không mất tính hệ thống.',
        signatureName: 'Linh Dao',
        signatureRole: 'Wellness Journey Designer',
        contactLine: 'hello@selvarajourneys.com · +84 933 222 111',
      },
      routeMap: {
        title: 'A route designed for softness and reset',
        description:
          'Tuyến route ưu tiên những điểm đến có khoảng lặng, chuyển cảnh nhẹ và đủ không gian để mood của brochure được giữ nhất quán.',
        segments: [
          {
            sequence: '01',
            title: 'Yen Tu arrival and forest stillness',
            description: 'Mở đầu trong vùng núi thiền định để điều chỉnh nhịp tâm trí trước mọi phần trải nghiệm sâu hơn.',
            duration: '2 nights',
            hotelName: 'Legacy Yen Tu',
            coordinates: [21.1498, 106.7196],
            city: 'Yen Tu',
            image:
              'https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?q=80&w=900&auto=format&fit=crop',
          },
          {
            sequence: '02',
            title: 'Ninh Binh river landscape',
            description: 'Một chương nhiều nước, đá và sương, rất hợp cho route timeline dạng stacked mềm.',
            duration: '2 nights',
            hotelName: 'Tam Coc Garden',
            coordinates: [20.2154, 105.92299],
            city: 'Ninh Binh',
            image:
              'https://images.unsplash.com/photo-1500534314209-a25ddb2bd429?q=80&w=900&auto=format&fit=crop',
          },
          {
            sequence: '03',
            title: 'Da Lat sanctuary closing',
            description: 'Kết thúc bằng khí hậu lạnh, mùi thông và nhịp nghỉ nhiều hơn hoạt động.',
            duration: '2 nights',
            hotelName: 'Ana Mandara Villas',
            coordinates: [11.9404, 108.4583],
            city: 'Da Lat',
            image:
              'https://images.unsplash.com/photo-1441974231531-c6227db76b6e?q=80&w=900&auto=format&fit=crop',
          },
        ],
      },
      itineraryDivider: {
        kicker: 'Chapter 02 · Gentle Flow',
        title: 'Slow structure, clear sequence',
        tagline:
          'Mobile layout vẫn đọc top-down, nhưng spacing và image treatment của Selvara được giữ mềm hơn để tránh tạo áp lực thị giác.',
        image:
          'https://images.unsplash.com/photo-1441974231531-c6227db76b6e?q=80&w=1600&auto=format&fit=crop',
      },
      itinerary: {
        kicker: 'Retreat Program',
        title: 'A day-by-day designed for ease',
        description:
          'Cấu trúc data không đổi, nhưng copy được viết ít nén hơn để atom typography có không gian thể hiện rõ tone healing.',
        days: [
          {
            dayLabel: 'Day 01',
            title: 'Arrival, grounding tea, and a quiet evening',
            city: 'Yen Tu',
            description: [
              'Ngày đầu giảm toàn bộ áp lực quyết định: đón, đưa về sanctuary, và một buổi tối để cơ thể nhận lại nhịp riêng.',
              'Desktop layout vẫn dùng day-story-grid, nhưng khoảng cách và phần body copy đều thoáng hơn hai brand còn lại.',
            ],
            highlights: 'Private arrival · tea ritual · rest-first pacing',
            notes: ['Optional early room readiness', 'Gentle meal suggestions on arrival'],
            overnight: 'Yen Tu',
            meals: ['Dinner'],
            heroImage:
              'https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?q=80&w=1200&auto=format&fit=crop',
            secondaryImages: [
              'https://images.unsplash.com/photo-1470770841072-f978cf4d019e?q=80&w=800&auto=format&fit=crop',
              'https://images.unsplash.com/photo-1448375240586-882707db888b?q=80&w=800&auto=format&fit=crop',
            ],
          },
          {
            dayLabel: 'Day 02',
            title: 'Forest walk and mindful movement',
            city: 'Yen Tu',
            description: [
              'Phần trải nghiệm chính nghiêng về chuyển động nhẹ và cảm nhận không gian thay vì activity-driven itinerary.',
              'Điều này giúp section có thể tái dùng cùng molecule nhưng không làm người xem cảm giác lặp.',
            ],
            highlights: 'Guided walk · breathwork · slow afternoon',
            notes: ['Movement level can be adapted', 'Quiet reading hour can replace an activity block'],
            overnight: 'Yen Tu',
            meals: ['Breakfast', 'Lunch'],
            heroImage:
              'https://images.unsplash.com/photo-1470770841072-f978cf4d019e?q=80&w=1200&auto=format&fit=crop',
            secondaryImages: [
              'https://images.unsplash.com/photo-1448375240586-882707db888b?q=80&w=800&auto=format&fit=crop',
              'https://images.unsplash.com/photo-1506744038136-46273834b3fb?q=80&w=800&auto=format&fit=crop',
            ],
          },
          {
            dayLabel: 'Day 03',
            title: 'River landscape and floating quiet',
            city: 'Ninh Binh',
            description: [
              'Chuyển sang Ninh Bình như một chapter mở rộng tầm nhìn, giữ tiết tấu êm và thuận cho bố cục editorial split.',
              'PDF mode sẽ gom phần này theo cụm để không gãy một ngày thành nhiều trang nhỏ.',
            ],
            highlights: 'Boat passage · limestone landscape · evening reset',
            notes: ['Ideal section for compact pull quote', 'Low-noise pacing across the day'],
            overnight: 'Ninh Binh',
            meals: ['Breakfast', 'Dinner'],
            heroImage:
              'https://images.unsplash.com/photo-1500534314209-a25ddb2bd429?q=80&w=1200&auto=format&fit=crop',
            secondaryImages: [
              'https://images.unsplash.com/photo-1510798831971-661eb04b3739?q=80&w=800&auto=format&fit=crop',
              'https://images.unsplash.com/photo-1441974231531-c6227db76b6e?q=80&w=800&auto=format&fit=crop',
            ],
          },
        ],
      },
      hotels: {
        title: 'Sanctuaries chosen for quiet confidence',
        description:
          'Stay cards vẫn alternating như brochure registry nhưng imagery và tone copy luôn ưu tiên calmness hơn contrast mạnh.',
        roomNotes:
          'Phòng ưu tiên ánh sáng dịu, tiếng ồn thấp, vật liệu tự nhiên và cảm giác “nghỉ thật” hơn là tiện nghi phô diễn.',
        cards: [
          {
            city: 'Yen Tu, Vietnam',
            name: 'Legacy Yen Tu',
            intro:
              'Một property nhiều gỗ, ánh sáng ấm và nhịp đi chậm, rất hợp cho brand muốn người xem thư giãn ngay từ section stay đầu tiên.',
            dateRanges: ['07 Sep – 09 Sep'],
            telephone: '+84 203 625 9888',
            hotelImage:
              'https://images.unsplash.com/photo-1470770841072-f978cf4d019e?q=80&w=1000&auto=format&fit=crop',
            roomImage:
              'https://images.unsplash.com/photo-1505693416388-ac5ce068fe85?q=80&w=1000&auto=format&fit=crop',
            roomType: 'Zen Terrace Suite',
          },
          {
            city: 'Ninh Binh, Vietnam',
            name: 'Tam Coc Garden',
            intro:
              'Từ chất liệu đến cảnh quan đều giúp section giữ đúng cảm giác eco-luxury mà không cần thêm nhiều trang trí thị giác.',
            dateRanges: ['09 Sep – 11 Sep'],
            telephone: '+84 229 361 8866',
            hotelImage:
              'https://images.unsplash.com/photo-1510798831971-661eb04b3739?q=80&w=1000&auto=format&fit=crop',
            roomImage:
              'https://images.unsplash.com/photo-1496417263034-38ec4f0b665a?q=80&w=1000&auto=format&fit=crop',
            roomType: 'Garden Retreat Room',
          },
        ],
      },
      staysDivider: {
        image:
          'https://images.unsplash.com/photo-1448375240586-882707db888b?q=80&w=1600&auto=format&fit=crop',
        kicker: 'Chapter 03 · Where You Rest',
        title: 'Stays designed to extend the calm',
        tagline:
          'Cùng layout registry nhưng shell của Selvara mềm hơn, border dịu hơn và footer tone ít tương phản hơn.',
        closing: 'Rest is not a gap between activities. It is part of the experience itself.',
      },
      pricing: {
        kicker: 'Retreat Pricing',
        title: 'Clear pricing, gentle presentation',
        description:
          'Pricing được giữ rõ cấu trúc nhưng copy bớt tính “sales” để hợp với tinh thần retreat.',
        importantNote:
          'Bao gồm sanctuary stays, private transfers, selected wellness experiences và hỗ trợ điều chỉnh lịch trình theo nhu cầu nghỉ ngơi.',
        options: [
          {
            category: 'Sanctuary',
            optionName: 'Retreat stays + private transfers',
            totalPrice: 'USD 3,960',
            perPersonPrice: 'USD 1,980 / person',
          },
          {
            category: 'Wellness Plus',
            optionName: 'Expanded therapy and guided movement',
            totalPrice: 'USD 4,820',
            perPersonPrice: 'USD 2,410 / person',
          },
          {
            category: 'Private Reset',
            optionName: 'Higher privacy and flexible pace',
            totalPrice: 'USD 5,640',
            perPersonPrice: 'USD 2,820 / person',
          },
        ],
      },
      inclusionsExclusions: {
        title: 'What your retreat includes',
        inclusionsLead: 'Cấu trúc giống các brand khác nhưng giọng văn giữ nhẹ và dễ thở hơn.',
        exclusionsLead: 'Những phần ngoài scope được nêu rõ để trải nghiệm tư vấn vẫn minh bạch.',
        inclusions: [
          'Private land arrangements and selected sanctuary stays',
          'Wellness-informed itinerary pacing',
          'Daily breakfast and selected mindful meals',
          'On-trip support and pre-arrival planning',
        ],
        exclusions: [
          'International flights and travel insurance',
          'Optional private treatments outside the agreed program',
          'Personal expenses and third-party purchases',
          'Force majeure changes and related supplier surcharges',
        ],
      },
      paymentTerms: {
        kicker: 'Important Notes',
        title: 'Booking & payment terms',
        description:
          'Term rows vẫn giống hệ brochure chung, nhưng copy đơn giản hơn và ít tính pháp lý nặng nề hơn trên bề mặt hiển thị.',
        cta: 'Confirm This Retreat',
        terms: [
          {
            label: 'Deposit',
            bodyRichText:
              '<p>30% deposit confirms planning, room hold, and key wellness services.</p>',
          },
          {
            label: 'Balance',
            bodyRichText:
              '<p>Final balance is due 45 days before arrival unless supplier terms require otherwise.</p>',
          },
          {
            label: 'Cancellation',
            bodyRichText:
              '<p>Cancellation terms depend on timing and supplier conditions. A detailed breakdown is shared before deposit.</p>',
          },
          {
            label: 'Confirmation',
            bodyRichText:
              '<p>Final confirmation follows payment receipt and supplier availability lock-in.</p>',
          },
        ],
      },
      designer: {
        kicker: 'Your Wellness Designer',
        title: 'Let us shape the final rhythm with you',
        quote:
          'Một hành trình chữa lành tốt không cần quá nhiều thứ. Nó chỉ cần đúng người, đúng nhịp, đúng khoảng lặng và một cấu trúc đủ an toàn để bạn thật sự thả lỏng.',
        name: 'Linh Dao',
        subtitle: 'Wellness Journey Designer',
        signatureLabel: 'Selvara Journeys',
        experienceNote:
          'Phụ trách sequencing cho retreat, chọn stay phù hợp tính khí khách và cân bằng giữa nghỉ, di chuyển và trải nghiệm có hướng dẫn.',
        avatar: 'https://images.unsplash.com/photo-1544005313-94ddf0286df2?q=80&w=800&auto=format&fit=crop',
        finalRequirements: [
          'Arrival details and wellness goals',
          'Dietary notes or health considerations',
          'Preferred room mood and activity intensity',
        ],
        confirmationItems: [
          'Pre-arrival briefing and timing summary',
          'Supplier confirmations and support contacts',
          'Quiet contingency planning if travel shifts',
        ],
      },
      footer: {
        text:
          'Selvara Journeys designs eco-luxury retreats in Vietnam with a focus on calm pacing, restorative stays, and meaningful stillness.',
        secondaryMeta: 'Brochure theme preview · one section API across brands',
      },
      states: {
        loadingTitle: 'Đang dựng retreat brochure',
        loadingBody: 'Selvara brochure đang map lại layout, typography và section data theo view mode hiện tại.',
        errorTitle: 'Không thể tải brochure Selvara',
        errorBody: 'Có lỗi khi dựng public display cho hành trình retreat này. Hãy thử tải lại trang.',
        notFoundTitle: 'Không tìm thấy retreat này',
        notFoundBody: 'Brochure public bạn mở hiện không tồn tại hoặc đã được thay bằng phiên bản khác.',
      },
    },
  },
};
