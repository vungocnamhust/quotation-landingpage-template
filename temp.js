
    document.addEventListener("DOMContentLoaded", function () {
      const DEST_COORDS = {
        "hanoi": [21.0285, 105.8542],
        "ha noi": [21.0285, 105.8542],
        "ninh binh": [20.2539, 105.9750],
        "ninhbinh": [20.2539, 105.9750],
        "ha long": [20.9599, 107.0436],
        "halong": [20.9599, 107.0436],
        "ha long bay": [20.9599, 107.0436],
        "halong bay": [20.9599, 107.0436],
        "ho chi minh": [10.8231, 106.6297],
        "hcmc": [10.8231, 106.6297],
        "ho chi minh city": [10.8231, 106.6297],
        "saigon": [10.8231, 106.6297],
        "sai gon": [10.8231, 106.6297],
        "mekong": [10.2435, 106.3756],
        "mekong delta": [10.2435, 106.3756],
        "ben tre": [10.2401, 106.3768],
        "bentre": [10.2401, 106.3768],
        "my tho": [10.3592, 106.3653],
        "mytho": [10.3592, 106.3653],
        "hue": [16.4637, 107.5909],
        "da nang": [16.0544, 108.2022],
        "danang": [16.0544, 108.2022],
        "hoi an": [15.8801, 108.3380],
        "hoian": [15.8801, 108.3380],
        "sapa": [22.3364, 103.8438],
        "phu quoc": [10.2899, 103.9840],
        "nha trang": [12.2388, 109.1967],
        "da lat": [11.9404, 108.4583]
      };

      function findCoordinates(destText) {
        if (!destText) return null;
        const norm = destText.toLowerCase()
          .normalize("NFD").replace(/[\u0300-\u036f]/g, "");
        for (const [key, coords] of Object.entries(DEST_COORDS)) {
          if (norm.includes(key)) return coords;
        }
        return null;
      }

      function getDistance(c1, c2) {
        const R = 6371;
        const dLat = (c2[0] - c1[0]) * Math.PI / 180;
        const dLon = (c2[1] - c1[1]) * Math.PI / 180;
        const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
          Math.cos(c1[0] * Math.PI / 180) * Math.cos(c2[0] * Math.PI / 180) *
          Math.sin(dLon / 2) * Math.sin(dLon / 2);
        const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
        return R * c;
      }

      function getBezierPoints(p1, p2, count = 30) {
        const midLat = (p1[0] + p2[0]) / 2;
        const midLng = (p1[1] + p2[1]) / 2;
        const dx = p2[1] - p1[1];
        const dy = p2[0] - p1[0];
        const len = Math.sqrt(dx * dx + dy * dy);
        const scale = len * 0.15;
        const ctrlLat = midLat - (dx / len) * scale;
        const ctrlLng = midLng + (dy / len) * scale;
        const points = [];
        for (let i = 0; i <= count; i++) {
          const t = i / count;
          const lat = (1 - t) * (1 - t) * p1[0] + 2 * (1 - t) * t * ctrlLat + t * t * p2[0];
          const lng = (1 - t) * (1 - t) * p1[1] + 2 * (1 - t) * t * ctrlLng + t * t * p2[1];
          points.push([lat, lng]);
        }
        return points;
      }

      const dataEl = document.getElementById('itinerary-data');
      if (!dataEl) return;
      const rawDays = JSON.parse(dataEl.textContent);

      const destImagesEl = document.getElementById('destination-images');
      const destImages = destImagesEl ? JSON.parse(destImagesEl.textContent) : {};

      function resolveSlugLocally(location) {
        if (!location) return null;
        const normalized = location.toLowerCase().trim();
        const keywordMap = {
          "hà nội": "ha-noi", "ha noi": "ha-noi", "hanoi": "ha-noi", "hanoï": "ha-noi", "هانوي": "ha-noi",
          "hồ chí minh": "ho-chi-minh", "ho chi minh": "ho-chi-minh", "hcm": "ho-chi-minh", "saigon": "ho-chi-minh", "sài gòn": "ho-chi-minh", "sai gon": "ho-chi-minh", "tphcm": "ho-chi-minh", "مدينة هو تشي منه": "ho-chi-minh", "هو تشي منه": "ho-chi-minh", "سايغون": "ho-chi-minh",
          "đà nẵng": "da-nang", "da nang": "da-nang", "danang": "da-nang", "دانانغ": "da-nang", "دا نانغ": "da-nang",
          "quảng nam": "quang-nam", "quang nam": "quang-nam", "hội an": "quang-nam", "hoi an": "quang-nam", "hoian": "quang-nam", "هوي آن": "quang-nam", "هوي ان": "quang-nam",
          "quảng ninh": "quang-ninh", "quang ninh": "quang-ninh", "hạ long": "quang-ninh", "ha long": "quang-ninh", "halong": "quang-ninh", "vịnh hạ long": "quang-ninh", "vinh ha long": "quang-ninh", "cat ba": "quang-ninh", "cát bà": "quang-ninh", "خليج هاليغ": "quang-ninh", "هالونغ": "quang-ninh", "خليج هالونج": "quang-ninh",
          "lào cai": "lao-cai", "lao cai": "lao-cai", "laocai": "lao-cai", "sapa": "lao-cai", "sa pa": "lao-cai", "bắc hà": "lao-cai", "bac ha": "lao-cai", "سابا": "lao-cai",
          "khánh hoà": "khanh-hoa", "khanh hoa": "khanh-hoa", "nha trang": "khanh-hoa", "nhatrang": "khanh-hoa", "نها ترانغ": "khanh-hoa", "نها ترانج": "khanh-hoa",
          "lâm đồng": "lam-dong", "lam dong": "lam-dong", "đà lạt": "lam-dong", "da lat": "lam-dong", "dalat": "lam-dong", "دالات": "lam-dong",
          "thừa thiên huế": "thua-thien-hue", "thua thien hue": "thua-thien-hue", "huế": "thua-thien-hue", "hue": "thua-thien-hue", "lăng cô": "thua-thien-hue", "lang co": "thua-thien-hue",
          "kiên giang": "kien-giang", "kien giang": "kien-giang", "phú quốc": "kien-giang", "phu quoc": "kien-giang", "phuquoc": "kien-giang",
          "bình thuận": "binh-thuan", "binh thuan": "binh-thuan", "mũi né": "binh-thuan", "mui ne": "binh-thuan", "phan thiết": "binh-thuan", "phan thiet": "binh-thuan",
          "cần thơ": "can-tho", "can tho": "can-tho", "cantho": "can-tho", "bến ninh kiều": "can-tho", "ben ninh kieu": "can-tho",
          "mekong": "mekong", "đồng bằng sông cửu long": "mekong", "dong bang song cuu long": "mekong", "miền tây": "mekong", "mien tay": "mekong", "tây nam bộ": "mekong", "tay nam bo": "mekong",
          "hà giang": "ha-giang", "ha giang": "ha-giang", "đồng văn": "ha-giang", "dong van": "ha-giang", "mèo vạc": "ha-giang", "meo vac": "ha-giang",
          "ninh bình": "ninh-binh", "ninh binh": "ninh-binh", "tràng an": "ninh-binh", "trang an": "ninh-binh", "tam cốc": "ninh-binh", "tam coc": "ninh-binh", "bích động": "ninh-binh", "bich dong": "ninh-binh",
          "nghệ an": "nghe-an", "nghe an": "nghe-an", "cửa lò": "nghe-an", "cua lo": "nghe-an",
          "quảng bình": "quang-binh", "quang binh": "quang-binh", "phong nha": "quang-binh", "ke bang": "quang-binh",
          "hải phòng": "hai-phong", "hai phong": "hai-phong", "haiphong": "hai-phong",
          "đắk lắk": "dak-lak", "dak lak": "dak-lak", "daklak": "dak-lak", "buôn ma thuột": "dak-lak", "buon ma thuot": "dak-lak", "bmt": "dak-lak",
          "gia lai": "gia-lai", "pleiku": "gia-lai",
          "kon tum": "kon-tum", "kontum": "kon-tum",
          "bà rịa": "ba-ria-vung-tau", "ba ria": "ba-ria-vung-tau", "vũng tàu": "ba-ria-vung-tau", "vung tau": "ba-ria-vung-tau", "vungtau": "ba-ria-vung-tau",
          "thanh hoá": "thanh-hoa", "thanh hoa": "thanh-hoa", "sầm sơn": "thanh-hoa", "sam son": "thanh-hoa",
          "phú yên": "phu-yen", "phu yen": "phu-yen", "tuy hoà": "phu-yen", "tuy hoa": "phu-yen",
          "bình định": "binh-dinh", "binh dinh": "binh-dinh", "quy nhơn": "binh-dinh", "quy nhon": "binh-dinh", "quynhon": "binh-dinh",
          "điện biên": "dien-bien", "dien bien": "dien-bien", "điện biên phủ": "dien-bien",
          "sơn la": "son-la", "son la": "son-la", "mộc châu": "son-la", "moc chau": "son-la",
          "lai châu": "lai-chau", "lai java": "lai-chau",
          "yên bái": "yen-bai", "yen bai": "yen-bai", "mù cang chải": "yen-bai", "mu cang chai": "yen-bai",
          "hoà bình": "hoa-binh", "hoa binh": "hoa-binh",
          "lạng sơn": "lang-son", "lang son": "lang-son",
          "đồng nai": "dong-nai", "dong nai": "dong-nai",
          "bình dương": "binh-duong", "binh duong": "binh-duong",
          "tiền giang": "tien-giang", "tien giang": "tien-giang", "mỹ tho": "tien-giang", "my tho": "tien-giang",
          "đồng tháp": "dong-thap", "dong thap": "dong-thap", "sa đéc": "dong-thap", "sa dec": "dong-thap",
          "vĩnh long": "vinh-long", "vinh long": "vinh-long",
          "an giang": "an-giang", "châu đốc": "an-giang", "chau doc": "an-giang", "long xuyên": "an-giang", "long xuyen": "an-giang",
          "cao bằng": "cao-bang", "cao bang": "cao-bang", "bản giốc": "cao-bang", "ban gioc": "cao-bang"
        };
        if (keywordMap[normalized]) return keywordMap[normalized];
        let bestMatch = null;
        let bestLen = 0;
        for (const [keyword, slug] of Object.entries(keywordMap)) {
          if (normalized.includes(keyword) && keyword.length > bestLen) {
            bestMatch = slug;
            bestLen = keyword.length;
          }
        }
        return bestMatch;
      }

      
      function formatDate(dateStr) {
        if (!dateStr) return "";
        const d = new Date(dateStr);
        if (isNaN(d.getTime())) return dateStr;
        const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
        return d.getDate() + " " + months[d.getMonth()] + " " + d.getFullYear();
      }

      const daysData = rawDays.map(day => {
        let dest = "";
        if (Array.isArray(day.destinations) && day.destinations.length > 0) {
          dest = day.destinations[0];
        } else if (typeof day.destination === 'string') {
          dest = day.destination;
        } else if (typeof day.overnight === 'string') {
          dest = day.overnight;
        }

        let desc = "";
        if (Array.isArray(day.description)) {
          desc = day.description.join(' ');
        } else if (typeof day.description === 'string') {
          desc = day.description;
        } else if (typeof day.summary === 'string') {
          desc = day.summary;
        }

        const formattedDate = day.date ? ' · ' + formatDate(day.date) : '';
        const t = day.title || `Day ${day.dayNumber}`;

        return {
          dayNumber: day.dayNumber,
          destination: dest,
          title: t.includes('·') ? t : `${t}${formattedDate}`,
          description: desc,
          overnight: day.overnight || "",
          formattedDate: formattedDate
        };
      });

      const mapDestinations = [];
      const coordPoints = [];

      daysData.forEach(day => {
        const coords = findCoordinates(day.destination);
        if (!coords) return;

        const last = mapDestinations[mapDestinations.length - 1];
        if (!last || last.coords[0] !== coords[0] || last.coords[1] !== coords[1]) {
          const destName = day.destination.split(/->|-|\|/)[0].trim();
          const slug = resolveSlugLocally(destName);
          const imgUrl = (slug && destImages[slug]) ? destImages[slug] : '/assets/vietnam-safar-logo.png';

          mapDestinations.push({
            id: `dest-${mapDestinations.length}`,
            name: destName,
            coords: coords,
            img: imgUrl,
            days: [day.dayNumber],
            titles: [day.title]
          });
          coordPoints.push(coords);
        } else {
          last.days.push(day.dayNumber);
          last.titles.push(day.title);
        }
      });

      if (mapDestinations.length === 0) {
        document.getElementById('route-map').style.display = 'none';
        return;
      }

      const map = L.map('map', {
        zoomControl: true,
        scrollWheelZoom: false
      });

      // Thay thế bằng Tile của Google Maps (có hỗ trợ tiếng Việt & hiển thị Hoàng Sa, Trường Sa) 
      // vì URL eKMap cần có API Key thương mại mới hoạt động được.
      const vietmanMapUrl = 'https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}&hl=vi'; 
      L.tileLayer(vietmanMapUrl, {
        maxZoom: 18,
        attribution: '&copy; Bản đồ chủ quyền Việt Nam | Dữ liệu bản đồ &copy; Google'
      }).addTo(map);

      const sidebarContainer = document.getElementById('map-sidebar');
      sidebarContainer.innerHTML = '';

      const markers = [];
      const polylines = [];

      const shapePath = "M30,22 L70,22 C84,22 93,32 91,50 C89,68 82,78 68,78 L32,78 C18,78 9,68 9,50 C9,32 16,22 30,22 Z";
      let mapMode = 'classic'; // Default mode is classic

      function drawMarkers() {
        // Clear existing markers
        markers.forEach(m => map.removeLayer(m));
        markers.length = 0;

        mapDestinations.forEach((dest, idx) => {
          const dayRangeStr = dest.days.length > 1
            ? `Days ${dest.days[0]}-${dest.days[dest.days.length - 1]}`
            : `Day ${dest.days[0]}`;

          let html = '';
          let iconSize = [];
          let iconAnchor = [];
          let popupOffset = [];

          if (mapMode === 'image') {
            const patternId = `img-pattern-${dest.id}-${idx}`;
            html = `
              <div class="custom-irregular-marker" id="marker-wrapper-${idx}">
                <svg viewBox="0 0 100 100" class="marker-svg-container" xmlns="http://www.w3.org/2000/svg">
                  <defs>
                    <pattern id="${patternId}" x="0" y="0" width="1" height="1" patternContentUnits="objectBoundingBox">
                      <image href="${dest.img}" x="0" y="0" width="1" height="1" preserveAspectRatio="xMidYMid slice" />
                    </pattern>
                  </defs>
                  <path d="${shapePath}" class="marker-path-radar" />
                  <path d="${shapePath}" fill="url(#${patternId})" class="marker-path" />
                </svg>
              </div>
            `;
            iconSize = [80, 80];
            iconAnchor = [40, 40];
            popupOffset = [0, -25];
          } else {
            html = `
              <div class="custom-marker" id="marker-wrapper-${idx}">
                <div class="marker-pulse"></div>
                <div class="marker-core">${idx + 1}</div>
              </div>
            `;
            iconSize = [28, 28];
            iconAnchor = [14, 14];
            popupOffset = [0, -10];
          }

          const customIcon = L.divIcon({
            html: html,
            className: '',
            iconSize: iconSize,
            iconAnchor: iconAnchor
          });

          const popupContent = `
            <div class="map-popup">
              <h4>${dest.name}</h4>
              <strong style="color:var(--gold); font-size: 11px;">${dayRangeStr.toUpperCase()}</strong>
              <p style="margin: 6px 0 0; font-size:12px; color:var(--muted);">${dest.titles[0]}</p>
            </div>
          `;

          const marker = L.marker(dest.coords, { icon: customIcon })
            .addTo(map)
            .bindPopup(popupContent, { offset: popupOffset });

          markers.push(marker);

          // Setup card reference if not built yet
          if (!dest.cardEl) {
            const card = document.createElement('div');
            card.className = `sidebar-card ${idx === 0 ? 'active' : ''}`;
            card.innerHTML = `
              <span class="days-badge">${dayRangeStr}</span>
              <h4>${dest.name}</h4>
              <p>${dest.titles[0]}</p>
            `;

            card.addEventListener('click', () => {
              selectDestination(idx);
            });

            sidebarContainer.appendChild(card);
            dest.cardEl = card;
          }
        });
      }

      // Expose switchMapMode globally
      window.switchMapMode = function(mode) {
        if (mode === mapMode) return;
        mapMode = mode;

        document.querySelectorAll('.map-mode-toggle .mode-btn').forEach(btn => btn.classList.remove('active'));
        if (mode === 'classic') {
          document.getElementById('toggle-mode-classic').classList.add('active');
        } else {
          document.getElementById('toggle-mode-image').classList.add('active');
        }

        drawMarkers();
      };

      // Initial draw
      drawMarkers();

      for (let i = 0; i < coordPoints.length - 1; i++) {
        const p1 = coordPoints[i];
        const p2 = coordPoints[i + 1];
        const dist = getDistance(p1, p2);

        let pathPoints;
        let isFlight = dist > 300;

        if (isFlight) {
          pathPoints = getBezierPoints(p1, p2);
        } else {
          pathPoints = [p1, p2];
        }

        const lineOptions = {
          color: isFlight ? 'var(--gold)' : 'var(--emerald)',
          weight: 3,
          opacity: 0.8,
          dashArray: isFlight ? '6, 8' : 'none'
        };

        const polyline = L.polyline(pathPoints, lineOptions).addTo(map);
        polylines.push(polyline);
      }

      map.fitBounds(L.latLngBounds(coordPoints), {
        padding: [50, 50],
        maxZoom: 12
      });

      function selectDestination(index) {
        const dest = mapDestinations[index];
        map.setView(dest.coords, Math.max(map.getZoom(), 8), { animate: true });
        markers[index].openPopup();

        document.querySelectorAll('.sidebar-card').forEach(c => c.classList.remove('active'));
        dest.cardEl.classList.add('active');
        dest.cardEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

        document.querySelectorAll('.custom-marker, .custom-irregular-marker').forEach(m => m.classList.remove('active'));
        const activeMarkerEl = document.getElementById(`marker-wrapper-${index}`);
        if (activeMarkerEl) {
          activeMarkerEl.classList.add('active');
        }
      }

      markers.forEach((marker, idx) => {
        marker.on('click', () => {
          selectDestination(idx);
        });
      });
    });
  