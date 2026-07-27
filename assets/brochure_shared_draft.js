(function () {
  const draftEl = document.getElementById("brochure-draft");
  if (!draftEl) return;

  const body = document.body;
  const mode = body.dataset.brochureMode || "published";
  const isEditor = mode === "editor";
  const isPdf = mode === "pdf";
  const isPreview = body.dataset.brochurePreview === "1";
  const quotationId = body.dataset.quotationId || "";
  const currentLang = body.dataset.currentLang || "en";
  const targetOrigin = window.location.origin;
  const clientI18n = parseJsonScript("client-i18n") || {};

  let state = normalizeDraft(parseJsonScript("brochure-draft") || {});
  let saveTimer = null;
  let saveInFlight = false;
  let pendingSave = false;
  let previewReady = false;
  let previewIframe = null;
  let saveStatusEl = null;

  function parseJsonScript(id) {
    const el = document.getElementById(id);
    if (!el) return null;
    try {
      return JSON.parse(el.textContent || "{}");
    } catch (err) {
      console.error("[brochure-draft] Failed to parse", id, err);
      return null;
    }
  }

  function clone(value) {
    return JSON.parse(JSON.stringify(value));
  }

  function normalizeDraft(draft) {
    const next = clone(draft || {});
    next.meta = next.meta || {};
    next.meta.revision = Number(next.meta.revision || 1);
    next.brand = next.brand || {};
    next.brand.logo = normalizeAsset(next.brand.logo);
    next.brand.colors = next.brand.colors || {};
    next.brand.fonts = next.brand.fonts || {};
    next.assets = next.assets || {};
    next.assets.hero = normalizeAsset(next.assets.hero);
    next.assets.itineraryDivider = normalizeAsset(next.assets.itineraryDivider);
    next.assets.hotelDivider = normalizeAsset(next.assets.hotelDivider);
    next.traveler = next.traveler || {};
    next.trip = next.trip || {};
    next.narrative = next.narrative || {};
    next.route = next.route || {};
    next.route.staySegments = (next.route.staySegments || []).map((item, index) => ({
      id: item.id || `stay-${index + 1}`,
      displayName: item.displayName || "",
      daysLabel: item.daysLabel || "",
      nightsLabel: item.nightsLabel || "",
      hotelName: item.hotelName || "",
      hotelDateRange: item.hotelDateRange || "",
      hotelImage: normalizeAsset(item.hotelImage),
      mapSegmentDesc: item.mapSegmentDesc || "",
      mapSegmentDuration: item.mapSegmentDuration || "",
      coords: Array.isArray(item.coords) ? item.coords : [],
    }));
    next.itinerary = next.itinerary || {};
    next.itinerary.days = (next.itinerary.days || []).map((day, index) => {
      const images = day.images || {};
      return {
        id: day.id || `day-${day.dayNumber || index + 1}`,
        dayNumber: day.dayNumber || index + 1,
        segmentCity: day.segmentCity || "",
        title: day.title || "",
        description: Array.isArray(day.description) ? day.description : (day.description ? [String(day.description)] : []),
        overnight: day.overnight || "",
        meals: Array.isArray(day.meals) ? day.meals : splitLines(day.meals || ""),
        activities: Array.isArray(day.activities) ? day.activities : splitLines(day.activities || ""),
        notes: Array.isArray(day.notes) ? day.notes : splitLines(day.notes || ""),
        labelHighlights: day.labelHighlights || "Highlights:",
        labelNotes: day.labelNotes || "Notes:",
        layoutType: day.layoutType || "single",
        images: {
          hero: normalizeAsset(images.hero),
          small1: normalizeAsset(images.small1),
          small2: normalizeAsset(images.small2),
          carousel: (images.carousel || []).map(normalizeAsset),
        },
      };
    });
    next.stays = next.stays || {};
    next.stays.hotels = (next.stays.hotels || []).map((hotel, index) => ({
      id: hotel.id || `hotel-${index + 1}`,
      city: hotel.city || "",
      name: hotel.name || "",
      introduction: hotel.introduction || "",
      hotelDate: hotel.hotelDate || "",
      tel: hotel.tel || "",
      roomType: hotel.roomType || "",
      hotelImage: normalizeAsset(hotel.hotelImage),
      roomImage: normalizeAsset(hotel.roomImage),
    }));
    next.pricing = next.pricing || {};
    next.pricing.conditions = (next.pricing.conditions || []).map((item, index) => ({
      id: item.id || `price-cond-${index + 1}`,
      text: item.text || "",
    }));
    next.pricing.options = (next.pricing.options || []).map((opt, index) => ({
      id: opt.id || `price-${index + 1}`,
      category: opt.category || "",
      name: opt.name || "",
      perPersonText: opt.perPersonText || "",
      totalText: opt.totalText || "",
      isTotal: !!opt.isTotal,
      isConfirmedMainOption: !!opt.isConfirmedMainOption,
      isAlternativeOption: !!opt.isAlternativeOption,
    }));
    next.inclusions = (next.inclusions || []).map((item, index) => ({ id: item.id || `inc-${index + 1}`, text: item.text || "" }));
    next.exclusions = (next.exclusions || []).map((item, index) => ({ id: item.id || `exc-${index + 1}`, text: item.text || "" }));
    next.bookingTerms = next.bookingTerms || {};
    next.designer = next.designer || {};
    next.designer.image = normalizeAsset(next.designer.image);
    next.finalization = next.finalization || {};
    next.finalization.requiredItems = (next.finalization.requiredItems || []).map((item, index) => ({ id: item.id || `final-req-${index + 1}`, text: item.text || "" }));
    next.finalization.afterConfirmation = (next.finalization.afterConfirmation || []).map((item, index) => ({ id: item.id || `final-after-${index + 1}`, text: item.text || "" }));
    return next;
  }

  function normalizeAsset(asset) {
    if (!asset) return { assetId: "", url: "", status: "ready" };
    if (typeof asset === "string") return { assetId: "", url: asset, status: "ready" };
    return {
      assetId: asset.assetId || "",
      url: asset.url || "",
      status: asset.status || "ready",
    };
  }

  function splitLines(value) {
    return String(value || "")
      .split(/\n+/)
      .map((item) => item.trim())
      .filter(Boolean);
  }

  function getPath(target, path) {
    return path.split(".").reduce((acc, key) => {
      if (acc == null) return undefined;
      if (/^\d+$/.test(key)) return acc[Number(key)];
      return acc[key];
    }, target);
  }

  function setPath(target, path, value) {
    const parts = path.split(".");
    let cursor = target;
    for (let i = 0; i < parts.length - 1; i += 1) {
      const key = parts[i];
      const nextKey = parts[i + 1];
      if (/^\d+$/.test(key)) {
        cursor = cursor[Number(key)];
        continue;
      }
      if (!cursor[key] || typeof cursor[key] !== "object") {
        cursor[key] = /^\d+$/.test(nextKey) ? [] : {};
      }
      cursor = cursor[key];
    }
    const last = parts[parts.length - 1];
    if (/^\d+$/.test(last)) cursor[Number(last)] = value;
    else cursor[last] = value;
  }

  function textValue(value) {
    if (Array.isArray(value)) return value.join("\n");
    return value == null ? "" : String(value);
  }

  function setTextContent(selector, value) {
    document.querySelectorAll(selector).forEach((el) => {
      el.textContent = value || "";
    });
  }

  function setEditable(field, value, html) {
    document.querySelectorAll(`[data-editable="${field}"]`).forEach((el) => {
      if (html) el.innerHTML = value || "";
      else el.textContent = value || "";
    });
  }

  function setAssetImage(el, url) {
    if (!el || !url) return;
    if (el.tagName === "IMG") el.src = url;
    else {
      el.style.backgroundImage = `url('${url.replace(/'/g, "\\'")}')`;
      el.style.setProperty("--image", `url('${url.replace(/'/g, "\\'")}')`);
    }
  }

  function applyBrandTokens(draft) {
    const brand = draft.brand || {};
    const colors = brand.colors || {};
    const fonts = brand.fonts || {};
    const root = document.documentElement;
    const varMap = {
      "--primary": colors.primary,
      "--primary-dark": colors.primaryDark,
      "--accent": colors.accent,
      "--accent-light": colors.accentLight,
      "--bg-main": colors.bgMain,
      "--bg-alt": colors.bgAlt,
      "--text-main": colors.textMain,
      "--text-muted": colors.textMuted,
      "--text-light": colors.textLight,
      "--serif": fonts.serif ? `'${fonts.serif}', Georgia, serif` : "",
      "--sans": fonts.sans ? `'${fonts.sans}', Arial, sans-serif` : "",
      "--font-accent": fonts.accent ? `'${fonts.accent}', serif` : "",
    };
    Object.entries(varMap).forEach(([key, value]) => {
      if (value) root.style.setProperty(key, value);
    });
    document.querySelectorAll(".brand img").forEach((img) => {
      if (brand.logo && brand.logo.url) img.src = brand.logo.url;
    });
    document.querySelectorAll(".brand span, .brand").forEach((node) => {
      if (node.children.length === 0 && brand.name) node.textContent = brand.name;
    });
    const navBrandText = document.querySelector("a.brand span");
    if (navBrandText && brand.name) navBrandText.textContent = brand.name;
    const fav = document.querySelector('link[rel="apple-touch-icon"]');
    if (fav && brand.logo && brand.logo.url) fav.href = brand.logo.url;
  }

  function buildCarouselMarkup(urls) {
    return `
      <div class="carousel-inner" style="position: absolute; inset: 0; display: flex; transition: transform 0.5s cubic-bezier(0.16, 1, 0.3, 1);">
        ${urls.map((url) => `<div class="carousel-slide" style="flex: 0 0 100%; height: 100%; background: url('${escapeAttr(url)}') center/cover no-repeat;"></div>`).join("")}
      </div>
      <div class="carousel-dots no-print" style="position: absolute; bottom: 20px; left: 50%; transform: translateX(-50%); display: flex; gap: 6px; z-index: 3;">
        ${urls.map((_, index) => `<button class="carousel-dot ${index === 0 ? "active" : ""}" aria-label="Go to slide ${index + 1}" style="width: 6px; height: 6px; border-radius: 50%; border: none; background: rgba(255,255,255,0.4); cursor: pointer; padding: 0;"></button>`).join("")}
      </div>
    `;
  }

  function escapeAttr(value) {
    return String(value || "").replace(/"/g, "&quot;").replace(/'/g, "\\'");
  }

  function applyAssets(draft) {
    const assets = draft.assets || {};
    const heroUrl = assets.hero && assets.hero.url;
    if (heroUrl) {
      document.documentElement.style.setProperty("--hero-img", `url('${heroUrl.replace(/'/g, "\\'")}')`);
      const hero = document.querySelector(".hero");
      if (hero) hero.style.setProperty("--hero-img", `url('${heroUrl.replace(/'/g, "\\'")}')`);
      const cover = document.querySelector(".cover");
      if (cover) {
        cover.style.backgroundImage = `linear-gradient(160deg,rgba(17,19,15,.88),rgba(17,19,15,.55) 55%,rgba(17,19,15,.18)), url('${heroUrl.replace(/'/g, "\\'")}')`;
      }
    }
    const itineraryDividerUrl = assets.itineraryDivider && assets.itineraryDivider.url;
    const hotelDividerUrl = assets.hotelDivider && assets.hotelDivider.url;
    document.querySelectorAll('[data-editable="img_hotel_divider"]').forEach((img) => setAssetImage(img, hotelDividerUrl));
    document.querySelectorAll("#divider-itinerary, .itinerary-intro-panel").forEach((el) => {
      if (itineraryDividerUrl) el.style.backgroundImage = `url('${itineraryDividerUrl.replace(/'/g, "\\'")}')`;
    });
    const designerUrl = draft.designer && draft.designer.image && draft.designer.image.url;
    if (designerUrl) {
      document.documentElement.style.setProperty("--designer-img", `url('${designerUrl.replace(/'/g, "\\'")}')`);
      const avatar = document.getElementById("designer-avatar-container");
      if (avatar) avatar.style.backgroundImage = `url('${designerUrl.replace(/'/g, "\\'")}')`;
    }
  }

  function applyTopLevel(draft) {
    const trip = draft.trip || {};
    const narrative = draft.narrative || {};
    const route = draft.route || {};
    const pricing = draft.pricing || {};
    const bookingTerms = draft.bookingTerms || {};
    const designer = draft.designer || {};

    setEditable("tour_title", trip.title || "");
    setEditable("lede", trip.lede || "");
    setEditable("hero_meta_1", narrative.heroMeta1 || "");
    setEditable("hero_meta_2", narrative.heroMeta2 || "");
    setEditable("cover_kicker", narrative.coverKicker || "");
    setEditable("route_map_h2", route.title || "");
    setEditable("route_map_p", route.description || "");
    setEditable("itinerary_h2", (draft.itinerary || {}).title || "");
    setEditable("itinerary_p", (draft.itinerary || {}).description || "");
    setEditable("pricing_kicker", pricing.kicker || "");
    setEditable("pricing_h2", pricing.title || "");
    setEditable("pricing_p", pricing.description || "");
    setEditable("payment_kicker", bookingTerms.kicker || "");
    setEditable("payment_title", bookingTerms.title || "");
    setEditable("payment_desc", bookingTerms.description || "");
    setEditable("term_deposit", bookingTerms.deposit || "");
    setEditable("term_balance", bookingTerms.balance || "");
    setEditable("term_cancellation", bookingTerms.cancellation || "");
    setEditable("term_confirmation", bookingTerms.confirmation || "");
    setEditable("letter_greeting", narrative.letterGreeting || "");
    setEditable("letter_intro", narrative.letterIntro || "");
    setEditable("letter_body_p2", narrative.letterBody2 || "");
    setEditable("letter_outro", narrative.letterOutro || "");
    setEditable("letter_sign_off", narrative.letterSignOff || "");
    setEditable("letter_sender", narrative.letterSender || "");
    setEditable("footer_text", narrative.footerText || "");
    setEditable("contact_phone", designer.phone || "");
    setEditable("contact", designer.phone || "");
    setEditable("seller_email", designer.email || "");
    setEditable("seller_name2", designer.name || "");
    setEditable("designer_signature", designer.signature || "");
    setEditable("designer_experience", designer.experience || "");
    setEditable("designer_quote", designer.quote || "");
    setEditable("designer_title", designer.title || "");
  }

  function applyItinerary(draft) {
    (draft.itinerary.days || []).forEach((day, index) => {
      const dayNumber = day.dayNumber || index + 1;
      setEditable(`day_title_${dayNumber}`, day.title || "");
      (day.description || []).forEach((paragraph, paragraphIndex) => {
        setEditable(`day_desc_${dayNumber}_${paragraphIndex}`, paragraph || "");
      });
      setEditable(`day_overnight_${dayNumber}`, day.overnight || "");
      setEditable(`day_meals_${dayNumber}`, (day.meals || []).join(" · "));
      setEditable(`day_highlights_${dayNumber}`, (day.activities || []).join(" · "));
      setEditable(`day_label_highlights_${dayNumber}`, day.labelHighlights || "Highlights:");
      setEditable(`day_label_notes_${dayNumber}`, day.labelNotes || "Notes:");
      (day.notes || []).forEach((note, noteIndex) => {
        setEditable(`day_note_${dayNumber}_${noteIndex}`, note || "");
      });
      const images = day.images || {};
      const heroUrl = images.hero && images.hero.url;
      const carouselUrls = (images.carousel || []).map((item) => item.url).filter(Boolean);
      const heroTarget = document.querySelector(`[data-editable="day_img_hero_${dayNumber}"]`);
      if (heroTarget && heroUrl) setAssetImage(heroTarget, heroUrl);
      const small1Target = document.querySelector(`[data-editable="day_img_small1_${dayNumber}"]`);
      if (small1Target && images.small1 && images.small1.url) setAssetImage(small1Target, images.small1.url);
      const small2Target = document.querySelector(`[data-editable="day_img_small2_${dayNumber}"]`);
      if (small2Target && images.small2 && images.small2.url) setAssetImage(small2Target, images.small2.url);
      const carouselTarget = document.querySelector(`[data-editable="day_img_carousel_${dayNumber}"]`);
      if (carouselTarget) {
        const urls = carouselUrls.length ? carouselUrls : (heroUrl ? [heroUrl] : []);
        if (urls.length) carouselTarget.innerHTML = buildCarouselMarkup(urls);
      }
    });

    const itineraryDataEl = document.getElementById("itinerary-data");
    if (itineraryDataEl) {
      itineraryDataEl.textContent = JSON.stringify((draft.itinerary.days || []).map((day) => ({
        dayNumber: day.dayNumber,
        title: day.title,
        description: day.description,
        overnight: day.overnight,
        meals: day.meals,
        activities: day.activities,
        notes: day.notes,
      })));
    }
  }

  function applyHotels(draft) {
    (draft.stays.hotels || []).forEach((hotel, index) => {
      const idx = index + 1;
      setEditable(`hotel_city_${idx}`, hotel.city || "");
      setEditable(`hotel_name_${idx}`, hotel.name || "");
      setEditable(`hotel_intro_${idx}`, hotel.introduction || "");
      setEditable(`hotel_date_${idx}`, hotel.hotelDate || "");
      setEditable(`hotel_tel_${idx}`, hotel.tel ? `TEL: ${hotel.tel}` : "");
      setEditable(`hotel_room_type_${idx}`, hotel.roomType || "");
    });
    setEditable("room_notes", draft.stays.roomNotes || "");

    document.querySelectorAll(".hotel-editorial-grid").forEach((grid, index) => {
      const hotel = (draft.stays.hotels || [])[index];
      if (!hotel) return;
      const imgs = grid.querySelectorAll("img");
      if (imgs[0] && hotel.hotelImage && hotel.hotelImage.url) imgs[0].src = hotel.hotelImage.url;
      if (imgs[1] && hotel.roomImage && hotel.roomImage.url) imgs[1].src = hotel.roomImage.url;
    });
  }

  function applyPricing(draft) {
    (draft.pricing.options || []).forEach((option, index) => {
      const idx = index + 1;
      setEditable(`price_opt_cat_${idx}`, option.category || "");
      setEditable(`price_opt_name_${idx}`, option.name || "");
      setEditable(`price_pax_${idx}`, option.perPersonText || "");
      setEditable(`price_total_${idx}`, option.totalText || "");
    });
    (draft.pricing.conditions || []).forEach((item, index) => {
      if (index === 0) setEditable("price_cond_first", item.text || "");
    });
  }

  function applyCollection(fieldPrefix, items) {
    items.forEach((item, index) => {
      setEditable(`${fieldPrefix}_${index + 1}`, item.text || "");
    });
  }

  function applyFinalization(draft) {
    (draft.finalization.requiredItems || []).forEach((item, index) => {
      setEditable(`final_req_${index}`, item.text || "");
    });
    (draft.finalization.afterConfirmation || []).forEach((item, index) => {
      setEditable(`final_after_${index}`, item.text || "");
    });
  }

  function applyRouteSegments(draft) {
    const segments = draft.route.staySegments || [];
    segments.forEach((segment, index) => {
      setEditable(`map_segment_title_${index}`, segment.displayName || "");
      setEditable(`map_segment_duration_${index}`, [segment.daysLabel, segment.nightsLabel].filter(Boolean).join(" • "));
      setEditable(`map_segment_hotel_${index}`, segment.hotelName || "");
      setEditable(`map_segment_desc_${index}`, segment.mapSegmentDesc || "", true);
    });

    const staySegmentsEl = document.getElementById("stay-segments-data");
    if (staySegmentsEl) staySegmentsEl.textContent = JSON.stringify(segments);

    const timeline = document.getElementById("map-timeline");
    if (timeline) {
      timeline.innerHTML = "";
      segments.forEach((segment, index) => {
        const item = document.createElement("div");
        item.style.cssText = "display:flex; flex-direction:column; align-items:center; gap:8px; width: 85px; position:relative;";
        item.innerHTML = `
          <div style="width:26px;height:26px;border-radius:50%;background:var(--primary);color:#fff;display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:700;">${index + 1}</div>
          <div style="text-align:center;width:100%;">
            <span class="font-serif" style="font-size:13px;font-weight:500;color:var(--primary);display:block;line-height:1.2;">${escapeHtml(segment.displayName || "")}</span>
            <span style="font-size:9px;color:var(--text-muted);display:block;margin-top:4px;">${escapeHtml(segment.nightsLabel || segment.daysLabel || "")}</span>
            ${segment.hotelName ? `<div style="font-size:8px;color:var(--text-muted);margin-top:3px;">${escapeHtml(segment.hotelName)}</div>` : ""}
          </div>
        `;
        timeline.appendChild(item);
        if (index < segments.length - 1) {
          const line = document.createElement("div");
          line.style.cssText = "flex: 1; min-width: 15px; max-width: 40px; height: 1px; background: var(--accent); opacity: 0.5; margin-top: 13px;";
          timeline.appendChild(line);
        }
      });
    }

    document.querySelectorAll(".luxury-marker-label").forEach((el, index) => {
      if (segments[index]) el.textContent = segments[index].displayName || "";
    });
  }

  function escapeHtml(value) {
    return String(value || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function applyDraftToDom(draft) {
    applyBrandTokens(draft);
    applyAssets(draft);
    applyTopLevel(draft);
    applyItinerary(draft);
    applyHotels(draft);
    applyPricing(draft);
    applyCollection("inc", draft.inclusions || []);
    applyCollection("exc", draft.exclusions || []);
    applyFinalization(draft);
    applyRouteSegments(draft);
  }

  function updateSaveStatus(message, tone) {
    if (!saveStatusEl) return;
    saveStatusEl.textContent = message || "";
    saveStatusEl.dataset.tone = tone || "neutral";
  }

  function scheduleSave() {
    if (!isEditor) return;
    pendingSave = true;
    updateSaveStatus("Saving draft…", "pending");
    if (saveTimer) window.clearTimeout(saveTimer);
    saveTimer = window.setTimeout(() => {
      saveTimer = null;
      saveDraft();
    }, 500);
  }

  async function saveDraft() {
    if (!isEditor || saveInFlight || !pendingSave) return;
    pendingSave = false;
    saveInFlight = true;
    try {
      const res = await fetch(`/api/v1/quotations/${quotationId}/draft?lang=${encodeURIComponent(currentLang)}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ draft: state }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to save draft");
      state = normalizeDraft(data.draft || state);
      updateSaveStatus("Draft saved", "success");
      sendDraftToPreview();
    } catch (err) {
      console.error("[brochure-draft] Save failed", err);
      updateSaveStatus("Draft save failed", "error");
    } finally {
      saveInFlight = false;
      if (pendingSave) saveDraft();
    }
  }

  async function uploadAsset(file) {
    const form = new FormData();
    form.append("quotation_id", quotationId);
    form.append("file", file);
    const res = await fetch("/api/v1/assets", {
      method: "POST",
      body: form,
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Asset upload failed");
    return data;
  }

  async function handleAssetInput(path, file) {
    if (!file) return;
    const tempUrl = URL.createObjectURL(file);
    setPath(state, path, { assetId: "", url: tempUrl, status: "uploading" });
    applyDraftToDom(state);
    sendDraftToPreview();
    scheduleSave();
    try {
      const uploaded = await uploadAsset(file);
      setPath(state, path, {
        assetId: uploaded.assetId || "",
        url: uploaded.url || tempUrl,
        status: uploaded.status || "ready",
      });
      applyDraftToDom(state);
      sendDraftToPreview();
      scheduleSave();
    } catch (err) {
      console.error("[brochure-draft] Upload failed", err);
      setPath(state, path, { assetId: "", url: tempUrl, status: "error" });
      applyDraftToDom(state);
      sendDraftToPreview();
      updateSaveStatus("Asset upload failed", "error");
    }
  }

  function sendDraftToPreview() {
    if (!isEditor || !previewIframe || !previewIframe.contentWindow || !previewReady) return;
    previewIframe.contentWindow.postMessage({
      type: "BROCHURE_DRAFT_SYNC",
      revision: (state.meta && state.meta.revision) || 1,
      draft: state,
    }, targetOrigin);
  }

  function initPreviewMessaging() {
    window.addEventListener("message", (event) => {
      if (event.origin !== targetOrigin || !event.data || typeof event.data !== "object") return;
      if (event.data.type === "PDF_PREVIEW_READY") {
        previewReady = true;
        sendDraftToPreview();
      } else if (event.data.type === "PDF_PREVIEW_APPLIED") {
        updateSaveStatus("Preview updated", "success");
      } else if (event.data.type === "PDF_PREVIEW_ERROR") {
        updateSaveStatus("Preview sync failed", "error");
      }
    });
  }

  function initPdfPreviewRuntime() {
    window.addEventListener("message", (event) => {
      if (event.origin !== targetOrigin || !event.data || event.data.type !== "BROCHURE_DRAFT_SYNC") return;
      try {
        state = normalizeDraft(event.data.draft || {});
        applyDraftToDom(state);
        window.parent.postMessage({ type: "PDF_PREVIEW_APPLIED", revision: event.data.revision || 0 }, targetOrigin);
      } catch (err) {
        console.error("[brochure-draft] PDF preview sync failed", err);
        window.parent.postMessage({ type: "PDF_PREVIEW_ERROR", message: err.message || String(err) }, targetOrigin);
      }
    });
    window.parent.postMessage({ type: "PDF_PREVIEW_READY" }, targetOrigin);
  }

  function getFieldSections() {
    const trip = [
      field("trip.title", "Trip title"),
      field("trip.lede", "Trip lede", "textarea"),
      field("trip.routeText", "Route"),
      field("trip.travelDates", "Travel dates"),
      field("trip.quotationNumber", "Quotation number"),
    ];
    const narrative = [
      field("narrative.coverKicker", "Cover kicker"),
      field("narrative.heroMeta1", "Hero meta 1"),
      field("narrative.heroMeta2", "Hero meta 2"),
      field("narrative.letterGreeting", "Letter greeting"),
      field("narrative.letterIntro", "Letter intro", "textarea"),
      field("narrative.letterBody2", "Letter body", "textarea"),
      field("narrative.letterOutro", "Letter outro", "textarea"),
      field("narrative.letterSignOff", "Sign-off"),
      field("narrative.letterSender", "Sender label"),
      field("narrative.footerText", "Footer text", "textarea"),
    ];
    const brand = [
      field("brand.name", "Brand name"),
      field("brand.domain", "Brand domain"),
      field("brand.colors.primary", "Primary color", "color"),
      field("brand.colors.primaryDark", "Primary dark", "color"),
      field("brand.colors.accent", "Accent", "color"),
      field("brand.colors.accentLight", "Accent light", "color"),
      field("brand.fonts.serif", "Serif font"),
      field("brand.fonts.sans", "Sans font"),
      field("brand.fonts.accent", "Accent font"),
      field("brand.logo", "Brand logo", "asset"),
      field("assets.hero", "Hero image", "asset"),
      field("assets.itineraryDivider", "Itinerary divider", "asset"),
      field("assets.hotelDivider", "Hotel divider", "asset"),
    ];
    const designer = [
      field("designer.name", "Designer name"),
      field("designer.signature", "Designer signature"),
      field("designer.title", "Designer title"),
      field("designer.experience", "Designer experience", "textarea"),
      field("designer.quote", "Designer quote", "textarea"),
      field("designer.phone", "Phone"),
      field("designer.email", "Email"),
      field("designer.image", "Designer image", "asset"),
    ];
    const booking = [
      field("bookingTerms.kicker", "Terms kicker"),
      field("bookingTerms.title", "Terms title"),
      field("bookingTerms.description", "Terms description", "textarea"),
      field("bookingTerms.deposit", "Deposit", "textarea"),
      field("bookingTerms.balance", "Balance", "textarea"),
      field("bookingTerms.cancellation", "Cancellation", "textarea"),
      field("bookingTerms.confirmation", "Confirmation", "textarea"),
    ];
    return { trip, narrative, brand, designer, booking };
  }

  function field(path, label, type) {
    return { path, label, type: type || "text" };
  }

  function renderField(def) {
    const value = getPath(state, def.path);
    if (def.type === "textarea") {
      return `<label class="draft-field"><span>${escapeHtml(def.label)}</span><textarea data-path="${def.path}">${escapeHtml(textValue(value))}</textarea></label>`;
    }
    if (def.type === "color") {
      return `<label class="draft-field"><span>${escapeHtml(def.label)}</span><input type="color" data-path="${def.path}" value="${escapeHtml(textValue(value) || "#000000")}" /></label>`;
    }
    if (def.type === "asset") {
      const url = value && value.url ? value.url : "";
      return `<label class="draft-field"><span>${escapeHtml(def.label)}</span><input type="file" accept="image/*" data-asset-path="${def.path}" /><small class="draft-asset-url">${escapeHtml(url)}</small></label>`;
    }
    return `<label class="draft-field"><span>${escapeHtml(def.label)}</span><input type="text" data-path="${def.path}" value="${escapeHtml(textValue(value))}" /></label>`;
  }

  function renderDynamicSections() {
    const daysMarkup = (state.itinerary.days || []).map((day, index) => `
      <details class="draft-card">
        <summary>Day ${day.dayNumber}: ${escapeHtml(day.title || day.segmentCity || "")}</summary>
        ${renderField(field(`itinerary.days.${index}.title`, "Title"))}
        <label class="draft-field"><span>Description</span><textarea data-array-path="itinerary.days.${index}.description">${escapeHtml((day.description || []).join("\n\n"))}</textarea></label>
        ${renderField(field(`itinerary.days.${index}.overnight`, "Overnight"))}
        <label class="draft-field"><span>Meals</span><textarea data-array-path="itinerary.days.${index}.meals">${escapeHtml((day.meals || []).join("\n"))}</textarea></label>
        <label class="draft-field"><span>Highlights</span><textarea data-array-path="itinerary.days.${index}.activities">${escapeHtml((day.activities || []).join("\n"))}</textarea></label>
        <label class="draft-field"><span>Notes</span><textarea data-array-path="itinerary.days.${index}.notes">${escapeHtml((day.notes || []).join("\n"))}</textarea></label>
        <label class="draft-field"><span>Primary image</span><input type="file" accept="image/*" data-asset-path="itinerary.days.${index}.images.hero" /></label>
      </details>
    `).join("");

    const hotelsMarkup = (state.stays.hotels || []).map((hotel, index) => `
      <details class="draft-card">
        <summary>Hotel ${index + 1}: ${escapeHtml(hotel.name || hotel.city || "")}</summary>
        ${renderField(field(`stays.hotels.${index}.city`, "City"))}
        ${renderField(field(`stays.hotels.${index}.name`, "Name"))}
        <label class="draft-field"><span>Introduction</span><textarea data-path="stays.hotels.${index}.introduction">${escapeHtml(hotel.introduction || "")}</textarea></label>
        ${renderField(field(`stays.hotels.${index}.hotelDate`, "Date"))}
        ${renderField(field(`stays.hotels.${index}.tel`, "Telephone"))}
        ${renderField(field(`stays.hotels.${index}.roomType`, "Room type"))}
        <label class="draft-field"><span>Hotel image</span><input type="file" accept="image/*" data-asset-path="stays.hotels.${index}.hotelImage" /></label>
        <label class="draft-field"><span>Room image</span><input type="file" accept="image/*" data-asset-path="stays.hotels.${index}.roomImage" /></label>
      </details>
    `).join("");

    const pricingMarkup = (state.pricing.options || []).map((option, index) => `
      <details class="draft-card">
        <summary>Pricing option ${index + 1}</summary>
        ${renderField(field(`pricing.options.${index}.category`, "Category"))}
        ${renderField(field(`pricing.options.${index}.name`, "Name"))}
        ${renderField(field(`pricing.options.${index}.perPersonText`, "Per person"))}
        ${renderField(field(`pricing.options.${index}.totalText`, "Total"))}
      </details>
    `).join("");

    const routeMarkup = (state.route.staySegments || []).map((segment, index) => `
      <details class="draft-card">
        <summary>Route segment ${index + 1}: ${escapeHtml(segment.displayName || "")}</summary>
        ${renderField(field(`route.staySegments.${index}.displayName`, "Display name"))}
        ${renderField(field(`route.staySegments.${index}.daysLabel`, "Days label"))}
        ${renderField(field(`route.staySegments.${index}.nightsLabel`, "Nights label"))}
        ${renderField(field(`route.staySegments.${index}.hotelName`, "Hotel name"))}
        <label class="draft-field"><span>Description</span><textarea data-path="route.staySegments.${index}.mapSegmentDesc">${escapeHtml(segment.mapSegmentDesc || "")}</textarea></label>
      </details>
    `).join("");

    return { daysMarkup, hotelsMarkup, pricingMarkup, routeMarkup };
  }

  function renderEditor() {
    const sections = getFieldSections();
    const dynamic = renderDynamicSections();
    const panel = document.createElement("aside");
    panel.id = "brochure-draft-sidebar";
    panel.innerHTML = `
      <div class="draft-sidebar-inner">
        <div class="draft-sidebar-header">
          <div>
            <h3>Brochure Draft</h3>
            <p>${escapeHtml(quotationId)}</p>
          </div>
          <div id="draft-save-status">Ready</div>
        </div>
        <details open class="draft-section"><summary>Trip</summary>${sections.trip.map(renderField).join("")}</details>
        <details class="draft-section"><summary>Narrative</summary>${sections.narrative.map(renderField).join("")}</details>
        <details class="draft-section"><summary>Brand & Assets</summary>${sections.brand.map(renderField).join("")}</details>
        <details class="draft-section"><summary>Designer</summary>${sections.designer.map(renderField).join("")}</details>
        <details class="draft-section"><summary>Booking Terms</summary>${sections.booking.map(renderField).join("")}</details>
        <details class="draft-section"><summary>Route</summary>${dynamic.routeMarkup}</details>
        <details class="draft-section"><summary>Itinerary</summary>${dynamic.daysMarkup}</details>
        <details class="draft-section"><summary>Hotels</summary>${dynamic.hotelsMarkup}</details>
        <details class="draft-section"><summary>Pricing</summary>${dynamic.pricingMarkup}</details>
        <details class="draft-section"><summary>Lists</summary>
          <label class="draft-field"><span>Inclusions</span><textarea data-array-path="inclusions">${escapeHtml((state.inclusions || []).map((item) => item.text || "").join("\n"))}</textarea></label>
          <label class="draft-field"><span>Exclusions</span><textarea data-array-path="exclusions">${escapeHtml((state.exclusions || []).map((item) => item.text || "").join("\n"))}</textarea></label>
          <label class="draft-field"><span>Final details required</span><textarea data-array-path="finalization.requiredItems">${escapeHtml((state.finalization.requiredItems || []).map((item) => item.text || "").join("\n"))}</textarea></label>
          <label class="draft-field"><span>After confirmation</span><textarea data-array-path="finalization.afterConfirmation">${escapeHtml((state.finalization.afterConfirmation || []).map((item) => item.text || "").join("\n"))}</textarea></label>
        </details>
        <div class="draft-sidebar-actions">
          <button type="button" id="draft-save-btn">Save now</button>
          <button type="button" id="draft-publish-btn">Publish</button>
        </div>
        <div class="draft-sidebar-actions">
          <a id="draft-published-link" href="#" target="_blank" hidden>Open published page</a>
        </div>
      </div>
    `;
    document.body.appendChild(panel);
    saveStatusEl = panel.querySelector("#draft-save-status");
    updateSaveStatus("Ready", "neutral");

    const previewWrap = document.createElement("div");
    previewWrap.id = "brochure-pdf-preview";
    const currentUrl = new URL(window.location.href);
    const previewUrl = new URL(`/quotations/${quotationId}/pdf`, targetOrigin);
    previewUrl.searchParams.set("lang", currentLang);
    previewUrl.searchParams.set("preview", "1");
    if (currentUrl.searchParams.get("brand")) previewUrl.searchParams.set("brand", currentUrl.searchParams.get("brand"));
    previewWrap.innerHTML = `
      <div class="draft-preview-header">
        <strong>PDF Preview</strong>
        <span>Realtime sync</span>
      </div>
      <iframe title="PDF Preview" src="${previewUrl.toString()}"></iframe>
    `;
    document.body.appendChild(previewWrap);
    previewIframe = previewWrap.querySelector("iframe");

    panel.addEventListener("input", (event) => {
      const target = event.target;
      if (!(target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement)) return;
      const path = target.dataset.path;
      const arrayPath = target.dataset.arrayPath;
      if (path) {
        setPath(state, path, target.value);
      } else if (arrayPath) {
        const items = splitLines(target.value).map((text, index) => ({ id: `${arrayPath.split(".").pop()}-${index + 1}`, text }));
        setPath(state, arrayPath, items.some((item) => item.text === undefined) ? splitLines(target.value) : items);
        if (arrayPath.includes("itinerary.days")) {
          setPath(state, arrayPath, splitLines(target.value));
        }
        if (arrayPath === "inclusions" || arrayPath === "exclusions" || arrayPath.startsWith("finalization.")) {
          setPath(state, arrayPath, splitLines(target.value).map((text, index) => ({ id: `${arrayPath.split(".").pop()}-${index + 1}`, text })));
        }
      }
      state.meta.revision = Number(state.meta.revision || 1) + 1;
      applyDraftToDom(state);
      sendDraftToPreview();
      scheduleSave();
    });

    panel.addEventListener("change", (event) => {
      const target = event.target;
      if (!(target instanceof HTMLInputElement)) return;
      const assetPath = target.dataset.assetPath;
      if (assetPath && target.files && target.files[0]) {
        handleAssetInput(assetPath, target.files[0]);
      }
    });

    panel.querySelector("#draft-save-btn").addEventListener("click", () => {
      pendingSave = true;
      saveDraft();
    });
    panel.querySelector("#draft-publish-btn").addEventListener("click", async () => {
      updateSaveStatus("Publishing…", "pending");
      try {
        const res = await fetch(`/quotations/${quotationId}/publish?lang=${encodeURIComponent(currentLang)}`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ draft: state }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Publish failed");
        updateSaveStatus("Published", "success");
        const link = panel.querySelector("#draft-published-link");
        if (link && data.published_url) {
          link.hidden = false;
          link.href = data.published_url;
          link.textContent = data.published_url;
        }
      } catch (err) {
        console.error("[brochure-draft] Publish failed", err);
        updateSaveStatus("Publish failed", "error");
      }
    });
  }

  function injectEditorStyles() {
    const style = document.createElement("style");
    style.textContent = `
      body[data-brochure-mode="editor"] {
        padding-right: 360px;
      }
      #brochure-draft-sidebar {
        position: fixed;
        top: 0;
        right: 0;
        width: 360px;
        height: 100vh;
        background: rgba(255,255,255,0.98);
        border-left: 1px solid rgba(0,0,0,0.08);
        box-shadow: -10px 0 40px rgba(0,0,0,0.08);
        z-index: 1200;
        overflow: auto;
      }
      #brochure-draft-sidebar .draft-sidebar-inner {
        padding: 18px;
      }
      #brochure-draft-sidebar .draft-sidebar-header {
        display: flex;
        justify-content: space-between;
        gap: 12px;
        align-items: flex-start;
        margin-bottom: 16px;
      }
      #brochure-draft-sidebar h3 {
        margin: 0 0 4px;
        font-size: 18px;
      }
      #brochure-draft-sidebar p {
        margin: 0;
        color: #666;
        font-size: 12px;
      }
      #brochure-draft-sidebar details {
        border: 1px solid rgba(0,0,0,0.08);
        margin-bottom: 12px;
        background: #fff;
      }
      #brochure-draft-sidebar summary {
        cursor: pointer;
        font-weight: 700;
        padding: 10px 12px;
      }
      .draft-card {
        border-top: 1px solid rgba(0,0,0,0.06);
      }
      .draft-card summary {
        font-weight: 600;
        font-size: 13px;
      }
      .draft-field {
        display: block;
        padding: 0 12px 12px;
      }
      .draft-field span {
        display: block;
        font-size: 12px;
        margin-bottom: 6px;
        color: #555;
      }
      .draft-field input[type="text"],
      .draft-field input[type="email"],
      .draft-field textarea {
        width: 100%;
        border: 1px solid rgba(0,0,0,0.12);
        padding: 8px 10px;
        font: inherit;
        font-size: 13px;
        resize: vertical;
      }
      .draft-field textarea {
        min-height: 84px;
      }
      .draft-field input[type="color"] {
        width: 100%;
        height: 38px;
        border: 1px solid rgba(0,0,0,0.12);
        padding: 2px;
        background: white;
      }
      .draft-sidebar-actions {
        display: flex;
        gap: 10px;
        margin-top: 14px;
      }
      .draft-sidebar-actions button,
      .draft-sidebar-actions a {
        flex: 1;
        text-align: center;
        padding: 10px 12px;
        border: none;
        background: var(--primary, #17412e);
        color: white;
        text-decoration: none;
        cursor: pointer;
      }
      #draft-save-status[data-tone="success"] { color: #0a7f34; }
      #draft-save-status[data-tone="error"] { color: #c0392b; }
      #draft-save-status[data-tone="pending"] { color: #9a6700; }
      #brochure-pdf-preview {
        position: fixed;
        left: 18px;
        bottom: 18px;
        width: min(42vw, 520px);
        height: min(78vh, 760px);
        background: rgba(255,255,255,0.96);
        box-shadow: 0 18px 50px rgba(0,0,0,0.2);
        z-index: 1150;
        display: flex;
        flex-direction: column;
        border: 1px solid rgba(0,0,0,0.1);
      }
      #brochure-pdf-preview .draft-preview-header {
        display: flex;
        justify-content: space-between;
        padding: 10px 12px;
        font-size: 12px;
        border-bottom: 1px solid rgba(0,0,0,0.08);
      }
      #brochure-pdf-preview iframe {
        flex: 1;
        width: 100%;
        border: 0;
        background: #525659;
      }
      @media (max-width: 1100px) {
        body[data-brochure-mode="editor"] { padding-right: 0; }
        #brochure-draft-sidebar {
          width: min(420px, 100vw);
        }
        #brochure-pdf-preview {
          display: none;
        }
      }
    `;
    document.head.appendChild(style);
  }

  applyDraftToDom(state);

  if (isPdf && isPreview) {
    initPdfPreviewRuntime();
  } else if (isEditor) {
    injectEditorStyles();
    initPreviewMessaging();
    renderEditor();
    sendDraftToPreview();
  }
})();
