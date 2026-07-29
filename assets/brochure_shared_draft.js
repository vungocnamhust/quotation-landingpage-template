(function () {
  const draftEl = document.getElementById("brochure-draft");
  if (!draftEl) return;

  const body = document.body;
  const mode = body.dataset.brochureMode || "published";
  const isEditor = mode === "editor";
  const quotationId = body.dataset.quotationId || "";
  const currentLang = body.dataset.currentLang || "en";
  const clientI18n = parseJsonScript("client-i18n") || {};
  let sectionRegistry = parseJsonScript("section-registry") || {};
  const parsedBrandPresets = parseJsonScript("brand-presets");
  const brandPresets = Array.isArray(parsedBrandPresets) ? parsedBrandPresets : [];
  const brandPresetMap = new Map(
    brandPresets
      .filter((preset) => preset && preset.brandId)
      .map((preset) => [preset.brandId, preset])
  );

  let state = normalizeDraft(parseJsonScript("brochure-draft") || {});
  let lastSavedRevision = Number((state.meta || {}).revision || 1);
  let saveTimer = null;
  let saveInFlight = false;
  let pendingSave = false;
  let saveStatusEl = null;
  let sidebarToggleEl = null;
  let mediaSearchTimer = null;
  const mediaPickerState = {
    open: false,
    path: "",
    label: "",
    items: [],
    search: "",
    loading: false,
    error: "",
    page: 1,
    pageSize: 18,
    hasMore: false,
    requestId: 0,
  };
  const DEFAULT_SECTION_TYPES = [
    "hero",
    "overview_letter",
    "route_map",
    "itinerary",
    "hotel_plan",
    "pricing",
    "inclusions_exclusions",
    "booking_terms",
    "designer",
    "finalization",
  ];
  const SIDEBAR_STORAGE_KEY = "brochureDraftCollapsed";

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

  function getSectionDefinitions() {
    const entries = Object.entries(sectionRegistry || {});
    if (entries.length) return entries.map(([type, def]) => ({ type, ...(def || {}) }));
    return DEFAULT_SECTION_TYPES.map((type) => ({ type, label: type.replace(/_/g, " ") }));
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
    next.bookingTerms = normalizeBookingTerms(next.bookingTerms || {});
    next.designer = next.designer || {};
    next.designer.image = normalizeAsset(next.designer.image);
    next.finalization = next.finalization || {};
    next.finalization.requiredTitle = next.finalization.requiredTitle || next.finalization.required_title || "Final Details Required";
    next.finalization.afterConfirmationTitle = next.finalization.afterConfirmationTitle || next.finalization.after_confirmation_title || "After Confirmation";
    next.finalization.requiredItems = (next.finalization.requiredItems || []).map((item, index) => ({ id: item.id || `final-req-${index + 1}`, text: item.text || "" }));
    next.finalization.afterConfirmation = (next.finalization.afterConfirmation || []).map((item, index) => ({ id: item.id || `final-after-${index + 1}`, text: item.text || "" }));
    next.layout = next.layout || {};
    next.layout.sections = normalizeLayoutSections(next.layout.sections || []);
    return next;
  }

  function normalizeBookingTerms(bookingTerms) {
    const next = { ...bookingTerms };
    const fallbackItems = [
      { id: "deposit", key: "deposit", label: next.depositLabel || "Deposit", body: next.deposit || "" },
      { id: "balance", key: "balance", label: next.balanceLabel || "Balance", body: next.balance || "" },
      { id: "cancellation", key: "cancellation", label: next.cancellationLabel || "Cancellation", body: next.cancellation || "" },
      { id: "confirmation", key: "confirmation", label: next.confirmationLabel || "Confirmation", body: next.confirmation || "" },
    ];
    next.items = (next.items || fallbackItems).map((item, index) => ({
      id: item.id || item.key || `term-${index + 1}`,
      key: item.key || item.id || `term_${index + 1}`,
      label: item.label || "",
      body: item.body || "",
    }));
    return next;
  }

  function normalizeLayoutSections(sections) {
    const source = Array.isArray(sections) && sections.length ? sections : DEFAULT_SECTION_TYPES.map((type, index) => ({
      id: type,
      type,
      enabled: true,
      order: index + 1,
      props: {},
    }));
    return source
      .map((section, index) => ({
        id: section.id || section.type || `section-${index + 1}`,
        type: section.type || DEFAULT_SECTION_TYPES[index] || "hero",
        enabled: section.enabled !== false,
        order: Number(section.order || index + 1),
        props: section.props && typeof section.props === "object" ? section.props : {},
      }))
      .sort((a, b) => a.order - b.order);
  }

  function bookingTermsMap(draft) {
    const items = ((draft.bookingTerms || {}).items || []).reduce((acc, item) => {
      acc[item.key || item.id] = item;
      return acc;
    }, {});
    return items;
  }

  function formatBookingItems(items) {
    return (items || []).map((item) => `${item.label || ""} || ${item.body || ""}`).join("\n");
  }

  function parseBookingItems(value) {
    return String(value || "")
      .split(/\n+/)
      .map((line, index) => {
        const [label, ...bodyParts] = line.split("||");
        const body = bodyParts.join("||").trim();
        return {
          id: `term-${index + 1}`,
          key: `term_${index + 1}`,
          label: (label || "").trim(),
          body,
        };
      })
      .filter((item) => item.label || item.body);
  }

  function formatLayoutSections(sections) {
    return (sections || []).map((section) => `${section.type} || ${section.enabled ? "on" : "off"} || ${section.order}`).join("\n");
  }

  function parseLayoutSections(value) {
    const parsed = String(value || "")
      .split(/\n+/)
      .map((line, index) => {
        const [typeRaw, enabledRaw, orderRaw] = line.split("||").map((item) => (item || "").trim());
        const type = typeRaw || DEFAULT_SECTION_TYPES[index] || "";
        if (!type) return null;
        return {
          id: type,
          type,
          enabled: enabledRaw !== "off",
          order: Number(orderRaw || index + 1),
          props: {},
        };
      })
      .filter(Boolean);
    return normalizeLayoutSections(parsed);
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

  function formatArrayField(path, value) {
    if (!Array.isArray(value)) return textValue(value);
    return value
      .map((item) => (item && typeof item === "object" ? item.text || "" : String(item || "")))
      .join(path.includes(".description") ? "\n\n" : "\n");
  }

  function describeErrors(detail) {
    const errors = detail && Array.isArray(detail.errors) ? detail.errors : [];
    if (!errors.length) return (detail && detail.message) || "Validation failed";
    return errors.map((item) => item.message || item.msg || item.path || "Validation error").join(" | ");
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

  function syncEditorFields(rootEl) {
    const root = rootEl || document;
    root.querySelectorAll("input[data-path], textarea[data-path]").forEach((el) => {
      const value = getPath(state, el.dataset.path || "");
      if (el instanceof HTMLInputElement && el.type === "file") return;
      if (el instanceof HTMLInputElement && el.type === "color") {
        el.value = textValue(value) || "#000000";
        return;
      }
      el.value = textValue(value);
    });
    root.querySelectorAll("textarea[data-array-path]").forEach((el) => {
      const path = el.dataset.arrayPath || "";
      el.value = formatArrayField(path, getPath(state, path));
    });
    root.querySelectorAll("textarea[data-booking-items]").forEach((el) => {
      el.value = formatBookingItems((state.bookingTerms || {}).items || []);
    });
    root.querySelectorAll("small[data-asset-url]").forEach((el) => {
      const value = getPath(state, el.dataset.assetUrl || "");
      el.textContent = value && value.url ? value.url : "";
    });
    root.querySelectorAll("img[data-asset-preview]").forEach((el) => {
      const value = getPath(state, el.dataset.assetPreview || "");
      const url = value && value.url ? value.url : "";
      el.src = url || "data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///ywAAAAAAQABAAACAUwAOw==";
      el.hidden = !url;
    });
    root.querySelectorAll("[data-asset-empty]").forEach((el) => {
      const value = getPath(state, el.dataset.assetEmpty || "");
      el.hidden = !!(value && value.url);
    });
    root.querySelectorAll("[data-brand-preset]").forEach((el) => {
      const active = el.dataset.brandPreset === (((state.meta || {}).brandId) || "");
      el.classList.toggle("is-active", active);
      el.setAttribute("aria-pressed", active ? "true" : "false");
    });
  }

  function setSidebarCollapsed(collapsed) {
    body.dataset.brochureSidebarCollapsed = collapsed ? "1" : "0";
    if (sidebarToggleEl) {
      sidebarToggleEl.textContent = collapsed
        ? (clientI18n.show_draft || "Show Draft")
        : (clientI18n.hide_draft || "Hide Draft");
      sidebarToggleEl.setAttribute("aria-expanded", collapsed ? "false" : "true");
    }
    try {
      window.localStorage.setItem(SIDEBAR_STORAGE_KEY, collapsed ? "1" : "0");
    } catch (err) {
      console.warn("[brochure-draft] Sidebar state was not persisted", err);
    }
  }

  function renderBrandPresetPicker() {
    if (!brandPresets.length) return "";
    return `
      <div class="draft-brand-presets">
        <span class="draft-brand-presets-label">${escapeHtml(clientI18n.brand_presets_label || "Brand Presets")}</span>
        <div class="draft-brand-presets-buttons">
          ${brandPresets.map((preset) => {
            const active = preset.brandId === (((state.meta || {}).brandId) || "");
            return `
              <button
                type="button"
                class="draft-brand-preset-btn ${active ? "is-active" : ""}"
                data-brand-preset="${escapeAttr(preset.brandId)}"
                aria-pressed="${active ? "true" : "false"}"
              >${escapeHtml(preset.label || preset.name || preset.brandId)}</button>
            `;
          }).join("")}
        </div>
      </div>
    `;
  }

  function applyBrandPreset(brandId, panel) {
    const preset = brandPresetMap.get(brandId);
    if (!preset) return;
    state.meta = state.meta || {};
    state.meta.brandId = preset.brandId;
    state.meta.revision = Number(state.meta.revision || 1) + 1;
    state.brand = state.brand || {};
    state.brand.name = preset.name || state.brand.name || "";
    state.brand.domain = preset.domain || state.brand.domain || "";
    state.brand.logo = normalizeAsset({ url: preset.logo || "", status: "ready" });
    state.brand.colors = { ...(preset.colors || {}) };
    state.brand.fonts = { ...(preset.fonts || {}) };
    applyDraftToDom(state);
    syncEditorFields(panel);
    updateSaveStatus(clientI18n.brand_preset_applied || "Brand preset applied", "neutral");
    scheduleSave();
  }

  function applyBrandTokens(draft) {
    const brand = draft.brand || {};
    const colors = brand.colors || {};
    const fonts = brand.fonts || {};
    const brandId = ((draft.meta || {}).brandId) || "";
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
    document.querySelectorAll(".domain-text").forEach((node) => {
      node.textContent = brand.name || "";
    });
    const fav = document.querySelector('link[rel="apple-touch-icon"]');
    if (fav && brand.logo && brand.logo.url) fav.href = brand.logo.url;
    const pdfBtn = document.getElementById("btn-pdf-view");
    if (pdfBtn) {
      const pdfUrl = new URL(pdfBtn.getAttribute("href") || `/quotations/${quotationId}/pdf`, window.location.origin);
      pdfUrl.searchParams.set("lang", currentLang);
      if (brandId) pdfUrl.searchParams.set("brand", brandId);
      else pdfUrl.searchParams.delete("brand");
      pdfBtn.href = `${pdfUrl.pathname}${pdfUrl.search}${pdfUrl.hash}`;
    }
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
    const bookingItems = bookingTermsMap(draft);

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
    setEditable("payment_label_deposit", (bookingItems.deposit || {}).label || "");
    setEditable("payment_label_balance", (bookingItems.balance || {}).label || "");
    setEditable("payment_label_cancellation", (bookingItems.cancellation || {}).label || "");
    setEditable("payment_label_confirmation", (bookingItems.confirmation || {}).label || "");
    setEditable("term_deposit", (bookingItems.deposit || {}).body || "", true);
    setEditable("term_balance", (bookingItems.balance || {}).body || "", true);
    setEditable("term_cancellation", (bookingItems.cancellation || {}).body || "", true);
    setEditable("term_confirmation", (bookingItems.confirmation || {}).body || "", true);
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

  function applyBookingTerms(draft) {
    const items = ((draft.bookingTerms || {}).items || []).filter((item) => item.label || item.body);
    document.querySelectorAll("[data-booking-terms-list]").forEach((container) => {
      container.innerHTML = items.map((item, index) => `
        <div class="term-row" data-booking-term-id="${escapeAttr(item.id || `term-${index + 1}`)}">
          <div data-editable="booking_term_label_${index}" style="font-family: var(--serif); font-size: inherit; color: inherit;">${escapeHtml(item.label || "")}</div>
          <div><div data-editable="booking_term_body_${index}" style="color: inherit; font-size: inherit; line-height: inherit;">${item.body || ""}</div></div>
        </div>
      `).join("");
    });
  }

  function applyFinalization(draft) {
    const finalization = draft.finalization || {};
    setEditable("final_req_title", finalization.requiredTitle || "");
    setEditable("final_after_title", finalization.afterConfirmationTitle || "");
    (draft.finalization.requiredItems || []).forEach((item, index) => {
      setEditable(`final_req_${index}`, item.text || "");
    });
    (draft.finalization.afterConfirmation || []).forEach((item, index) => {
      setEditable(`final_after_${index}`, item.text || "");
    });
    document.querySelectorAll("[data-finalization-required-list]").forEach((container) => {
      container.innerHTML = (finalization.requiredItems || []).map((item, index) => `<li data-editable="final_req_${index}">${escapeHtml(item.text || "")}</li>`).join("");
    });
    document.querySelectorAll("[data-finalization-after-list]").forEach((container) => {
      container.innerHTML = (finalization.afterConfirmation || []).map((item, index) => `<li data-editable="final_after_${index}">${escapeHtml(item.text || "")}</li>`).join("");
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
    applyLayout(draft);
    applyBrandTokens(draft);
    applyAssets(draft);
    applyTopLevel(draft);
    applyItinerary(draft);
    applyHotels(draft);
    applyPricing(draft);
    applyCollection("inc", draft.inclusions || []);
    applyCollection("exc", draft.exclusions || []);
    applyBookingTerms(draft);
    applyFinalization(draft);
    applyRouteSegments(draft);
  }

  function applyLayout(draft) {
    const sections = normalizeLayoutSections((((draft || {}).layout || {}).sections) || []);
    const main = document.getElementById("top");
    const pdfPagesRoot = document.querySelector(".pdf-pages") || document.body;
    const sectionGroups = new Map();
    document.querySelectorAll("[data-section-id]").forEach((node) => {
      const type = node.getAttribute("data-section-id");
      if (!type) return;
      if (!sectionGroups.has(type)) sectionGroups.set(type, []);
      sectionGroups.get(type).push(node);
    });

    sections.forEach((section, index) => {
      const nodes = sectionGroups.get(section.type) || [];
      nodes.forEach((node) => {
        node.style.display = section.enabled ? "" : "none";
        node.style.order = String(section.order || index + 1);
        const parent = node.closest(".pdf-page") ? pdfPagesRoot : main;
        if (parent && node.parentElement === parent) {
          parent.appendChild(node);
        }
      });
    });
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

  async function flushSave() {
    if (!isEditor) return;
    pendingSave = true;
    if (saveTimer) {
      window.clearTimeout(saveTimer);
      saveTimer = null;
    }
    while (saveInFlight) {
      await new Promise((resolve) => window.setTimeout(resolve, 25));
    }
    if (pendingSave) {
      await saveDraft();
    }
    while (saveInFlight) {
      await new Promise((resolve) => window.setTimeout(resolve, 25));
    }
  }

  async function saveDraft() {
    if (!isEditor || saveInFlight || !pendingSave) return;
    pendingSave = false;
    saveInFlight = true;
    try {
      const res = await fetch(`/api/v2/quotations/${quotationId}/document?lang=${encodeURIComponent(currentLang)}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ document: state, baseRevision: lastSavedRevision }),
      });
      const data = await res.json();
      if (!res.ok) {
        if (res.status === 409 && data.detail && data.detail.currentDocument) {
          state = normalizeDraft(data.detail.currentDocument);
          lastSavedRevision = Number(data.detail.currentRevision || ((state.meta || {}).revision || lastSavedRevision));
          applyDraftToDom(state);
          syncEditorFields(document.getElementById("brochure-draft-sidebar"));
          updateSaveStatus("Draft was updated elsewhere; latest version loaded", "error");
          return;
        }
        throw new Error(describeErrors(data.detail || data));
      }
      state = normalizeDraft(data.document || state);
      lastSavedRevision = Number(data.currentRevision || ((state.meta || {}).revision || lastSavedRevision));
      sectionRegistry = data.sectionRegistry || sectionRegistry;
      syncEditorFields(document.getElementById("brochure-draft-sidebar"));
      updateSaveStatus("Draft saved", "success");
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
    if (quotationId) form.append("quotationId", quotationId);
    form.append("file", file);
    const res = await fetch("/api/v2/media/upload", {
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
    syncEditorFields(document.getElementById("brochure-draft-sidebar"));
    try {
      const uploaded = await uploadAsset(file);
      await persistMediaSelection(uploaded.assetId || "", path);
      setPath(state, path, {
        assetId: uploaded.assetId || "",
        url: uploaded.originalUrl || uploaded.previewUrl || tempUrl,
        status: uploaded.status || "ready",
      });
      applyDraftToDom(state);
      syncEditorFields(document.getElementById("brochure-draft-sidebar"));
      scheduleSave();
    } catch (err) {
      console.error("[brochure-draft] Upload failed", err);
      setPath(state, path, { assetId: "", url: tempUrl, status: "error" });
      applyDraftToDom(state);
      syncEditorFields(document.getElementById("brochure-draft-sidebar"));
      updateSaveStatus("Asset upload failed", "error");
    }
  }

  function assetPathToSelection(path) {
    if (path === "assets.hero") return { sectionKey: "hero", slotKey: "cover_image", displayOrder: 0 };
    if (path === "brand.logo") return { sectionKey: "brand", slotKey: "logo", displayOrder: 0 };
    if (path === "assets.itineraryDivider") return { sectionKey: "itinerary", slotKey: "divider_image", displayOrder: 0 };
    if (path === "assets.hotelDivider") return { sectionKey: "hotel_plan", slotKey: "divider_image", displayOrder: 0 };
    if (path === "designer.image") return { sectionKey: "designer", slotKey: "portrait_image", displayOrder: 0 };

    let match = path.match(/^itinerary\.days\.(\d+)\.images\.hero$/);
    if (match) {
      const index = Number(match[1]);
      return { sectionKey: "itinerary", slotKey: `day_${index + 1}_hero_image`, displayOrder: index };
    }

    match = path.match(/^stays\.hotels\.(\d+)\.hotelImage$/);
    if (match) {
      const index = Number(match[1]);
      return { sectionKey: "hotel_plan", slotKey: `hotel_${index + 1}_image`, displayOrder: index };
    }

    match = path.match(/^stays\.hotels\.(\d+)\.roomImage$/);
    if (match) {
      const index = Number(match[1]);
      return { sectionKey: "hotel_plan", slotKey: `hotel_${index + 1}_room_image`, displayOrder: index };
    }

    return null;
  }

  async function persistMediaSelection(assetId, path) {
    const mapping = assetPathToSelection(path);
    if (!assetId || !mapping || !quotationId) return;
    const res = await fetch(`/api/v2/media/${encodeURIComponent(assetId)}/select`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        quotationId,
        lang: currentLang,
        sectionKey: mapping.sectionKey,
        slotKey: mapping.slotKey,
        displayOrder: mapping.displayOrder,
      }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(describeErrors(data.detail || data));
  }

  async function fetchMediaInventory(page, pageSize, search) {
    const params = new URLSearchParams({
      page: String(page),
      pageSize: String(pageSize),
      status: "ready",
    });
    if (quotationId) params.set("quotationId", quotationId);
    if (search) params.set("search", search);
    const res = await fetch(`/api/v2/media?${params.toString()}`);
    const data = await res.json();
    if (!res.ok) throw new Error(describeErrors(data.detail || data));
    return data;
  }

  function dedupeMediaItems(items) {
    const seen = new Set();
    return (items || []).filter((item) => {
      const key = item && item.id ? item.id : "";
      if (!key || seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  }

  function openMediaPicker(path, label, panel) {
    mediaPickerState.open = true;
    mediaPickerState.path = path || "";
    mediaPickerState.label = label || "Media library";
    mediaPickerState.items = [];
    mediaPickerState.search = "";
    mediaPickerState.error = "";
    mediaPickerState.page = 1;
    mediaPickerState.hasMore = false;
    renderEditorMediaPicker(panel);
    loadMediaLibrary(panel, { append: false });
  }

  function closeMediaPicker(panel) {
    mediaPickerState.open = false;
    mediaPickerState.loading = false;
    mediaPickerState.error = "";
    if (mediaSearchTimer) {
      window.clearTimeout(mediaSearchTimer);
      mediaSearchTimer = null;
    }
    renderEditorMediaPicker(panel);
  }

  async function loadMediaLibrary(panel, options) {
    if (!mediaPickerState.open) return;
    const append = !!(options && options.append);
    const nextPage = append ? mediaPickerState.page + 1 : 1;
    const requestId = mediaPickerState.requestId + 1;
    mediaPickerState.requestId = requestId;
    mediaPickerState.loading = true;
    mediaPickerState.error = "";
    renderEditorMediaPicker(panel);
    try {
      const payload = await fetchMediaInventory(nextPage, mediaPickerState.pageSize, (mediaPickerState.search || "").trim());
      if (requestId !== mediaPickerState.requestId) return;
      const incoming = Array.isArray(payload.items) ? payload.items : [];
      mediaPickerState.items = append
        ? dedupeMediaItems([].concat(mediaPickerState.items || [], incoming))
        : incoming;
      mediaPickerState.page = nextPage;
      mediaPickerState.hasMore = Number(payload.total || 0) > nextPage * mediaPickerState.pageSize;
      mediaPickerState.loading = false;
      renderEditorMediaPicker(panel);
    } catch (err) {
      if (requestId !== mediaPickerState.requestId) return;
      console.error("[brochure-draft] Media library failed", err);
      mediaPickerState.loading = false;
      mediaPickerState.error = err && err.message ? err.message : "Media library failed";
      renderEditorMediaPicker(panel);
    }
  }

  async function chooseMediaAsset(assetId, panel) {
    const asset = (mediaPickerState.items || []).find((item) => item && item.id === assetId);
    if (!asset || !mediaPickerState.path) return;
    try {
      await persistMediaSelection(asset.id, mediaPickerState.path);
      setPath(state, mediaPickerState.path, {
        assetId: asset.id,
        url: asset.originalUrl || asset.previewUrl || "",
        status: "ready",
      });
      state.meta.revision = Number(state.meta.revision || 1) + 1;
      applyDraftToDom(state);
      syncEditorFields(panel);
      updateSaveStatus("Library image selected", "success");
      closeMediaPicker(panel);
      scheduleSave();
    } catch (err) {
      console.error("[brochure-draft] Media select failed", err);
      mediaPickerState.error = err && err.message ? err.message : "Could not select this image";
      renderEditorMediaPicker(panel);
    }
  }

  function renderEditorMediaPicker(panel) {
    const picker = panel.querySelector(".draft-media-picker");
    if (!picker) return;
    if (!mediaPickerState.open) {
      picker.hidden = true;
      picker.classList.remove("is-open");
      return;
    }
    picker.hidden = false;
    picker.classList.add("is-open");
    const currentAssetId = (((getPath(state, mediaPickerState.path) || {}).assetId) || "");
    picker.innerHTML = `
      <button type="button" class="draft-media-picker-backdrop" data-close-media-picker aria-label="Close media library"></button>
      <div class="draft-media-picker-dialog" role="dialog" aria-modal="true" aria-label="Media library">
        <div class="draft-media-picker-header">
          <div>
            <strong>${escapeHtml(mediaPickerState.label || "Media library")}</strong>
            <p>Choose an existing image for this slot.</p>
          </div>
          <button type="button" class="draft-media-picker-close" data-close-media-picker>Close</button>
        </div>
        <div class="draft-media-picker-toolbar">
          <input
            type="search"
            id="draft-media-search"
            value="${escapeAttr(mediaPickerState.search)}"
            placeholder="Search images by filename or path"
            autocomplete="off"
          />
          <button type="button" data-refresh-media-picker>Refresh</button>
        </div>
        <div class="draft-media-picker-status" data-tone="${mediaPickerState.error ? "error" : (mediaPickerState.loading ? "pending" : "neutral")}">
          ${escapeHtml(mediaPickerState.error || (mediaPickerState.loading ? "Loading media library..." : `${mediaPickerState.items.length} image(s) available`))}
        </div>
        <div class="draft-media-grid">
          ${mediaPickerState.items.map((item) => {
            const active = currentAssetId === item.id;
            return `
              <article class="draft-media-card ${active ? "is-active" : ""}">
                <img
                  class="draft-media-card-image"
                  src="${escapeAttr(item.previewUrl || item.originalUrl || "")}"
                  alt="${escapeAttr(item.originalFilename || item.id)}"
                />
                <div class="draft-media-card-body">
                  <strong>${escapeHtml(item.originalFilename || item.id)}</strong>
                  <small>${escapeHtml([item.width && item.height ? `${item.width}x${item.height}` : "", item.sourceType || "", item.quotationId ? "Quotation" : "Shared"].filter(Boolean).join(" • "))}</small>
                  <button type="button" data-select-media-asset="${escapeAttr(item.id)}" ${active ? "disabled" : ""}>
                    ${active ? "Selected" : "Use image"}
                  </button>
                </div>
              </article>
            `;
          }).join("") || `<div class="draft-media-empty">${escapeHtml(mediaPickerState.loading ? "Loading..." : "No images found for this search.")}</div>`}
        </div>
        <div class="draft-media-picker-footer">
          <span>Results refresh automatically when you search.</span>
          ${mediaPickerState.hasMore ? `<button type="button" data-load-more-media>Load more</button>` : ""}
        </div>
      </div>
    `;
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
      field("bookingTerms.items", "Items", "bookingItems"),
    ];
    const layout = [
      field("layout.sections", "Sections", "layoutItems"),
      field("finalization.requiredTitle", "Final details title"),
      field("finalization.afterConfirmationTitle", "After confirmation title"),
    ];
    return { trip, narrative, brand, designer, booking, layout };
  }

  function field(path, label, type) {
    return { path, label, type: type || "text" };
  }

  function renderAssetField(path, label) {
    const value = normalizeAsset(getPath(state, path));
    const url = value && value.url ? value.url : "";
    return `
      <label class="draft-field draft-field-asset">
        <span>${escapeHtml(label)}</span>
        <div class="draft-asset-shell">
          <div class="draft-asset-preview-frame">
            <img
              class="draft-asset-preview-image"
              data-asset-preview="${escapeAttr(path)}"
              src="${escapeAttr(url || "data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///ywAAAAAAQABAAACAUwAOw==")}"
              alt="${escapeAttr(label)}"
              ${url ? "" : "hidden"}
            />
            <div class="draft-asset-preview-empty" data-asset-empty="${escapeAttr(path)}" ${url ? "hidden" : ""}>
              No image selected
            </div>
          </div>
          <div class="draft-asset-actions">
            <input type="file" accept="image/*" data-asset-path="${escapeAttr(path)}" />
            <button type="button" class="draft-asset-library-btn" data-open-gallery-for="${escapeAttr(path)}" data-asset-label="${escapeAttr(label)}">
              Choose from library
            </button>
          </div>
          <small class="draft-asset-url" data-asset-url="${escapeAttr(path)}">${escapeHtml(url)}</small>
        </div>
      </label>
    `;
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
      return renderAssetField(def.path, def.label);
    }
    if (def.type === "bookingItems") {
      return `<label class="draft-field"><span>${escapeHtml(def.label)}</span><textarea data-booking-items="bookingTerms.items" placeholder="Label || Body, one line per item">${escapeHtml(formatBookingItems((state.bookingTerms || {}).items || []))}</textarea></label>`;
    }
    if (def.type === "layoutItems") {
      return `<div class="draft-field"><span>${escapeHtml(def.label)}</span>${renderLayoutEditor()}</div>`;
    }
    return `<label class="draft-field"><span>${escapeHtml(def.label)}</span><input type="text" data-path="${def.path}" value="${escapeHtml(textValue(value))}" /></label>`;
  }

  function renderLayoutEditor() {
    const sections = normalizeLayoutSections((((state || {}).layout || {}).sections) || []);
    const current = new Map(sections.map((section) => [section.type, section]));
    return `
      <div class="draft-layout-list">
        ${getSectionDefinitions().map((definition, index) => {
          const section = current.get(definition.type) || {
            id: definition.type,
            type: definition.type,
            enabled: true,
            order: index + 1,
            props: {},
          };
          return `
            <div class="draft-layout-row" data-layout-type="${escapeAttr(definition.type)}">
              <label><input type="checkbox" data-layout-enabled="${escapeAttr(definition.type)}" ${section.enabled ? "checked" : ""} /> ${escapeHtml(definition.label || definition.type)}</label>
              <input type="number" min="1" data-layout-order="${escapeAttr(definition.type)}" value="${Number(section.order || index + 1)}" />
            </div>
          `;
        }).join("")}
      </div>
    `;
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
        ${renderAssetField(`itinerary.days.${index}.images.hero`, "Primary image")}
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
        ${renderAssetField(`stays.hotels.${index}.hotelImage`, "Hotel image")}
        ${renderAssetField(`stays.hotels.${index}.roomImage`, "Room image")}
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
        <details class="draft-section"><summary>Brand & Assets</summary>${renderBrandPresetPicker()}${sections.brand.map(renderField).join("")}</details>
        <details class="draft-section"><summary>Designer</summary>${sections.designer.map(renderField).join("")}</details>
        <details class="draft-section"><summary>Booking Terms</summary>${sections.booking.map(renderField).join("")}</details>
        <details class="draft-section"><summary>Layout & Finalization</summary>${sections.layout.map(renderField).join("")}</details>
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
          <button type="button" id="draft-regenerate-btn">Regenerate Narrative</button>
        </div>
        <div class="draft-sidebar-actions">
          <a id="draft-published-link" href="#" target="_blank" hidden>Open published page</a>
        </div>
        <div class="draft-media-picker" hidden></div>
      </div>
    `;
    document.body.appendChild(panel);
    saveStatusEl = panel.querySelector("#draft-save-status");
    updateSaveStatus("Ready", "neutral");

    const toggle = document.createElement("button");
    toggle.type = "button";
    toggle.id = "brochure-draft-toggle";
    document.body.appendChild(toggle);
    sidebarToggleEl = toggle;
    sidebarToggleEl.addEventListener("click", () => {
      setSidebarCollapsed(body.dataset.brochureSidebarCollapsed !== "1");
    });
    let storedCollapsed = false;
    try {
      storedCollapsed = window.localStorage.getItem(SIDEBAR_STORAGE_KEY) === "1";
    } catch (err) {
      storedCollapsed = false;
    }
    setSidebarCollapsed(storedCollapsed);

    panel.addEventListener("input", (event) => {
      const target = event.target;
      if (!(target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement)) return;
      if (target.id === "draft-media-search") {
        mediaPickerState.search = target.value || "";
        if (mediaSearchTimer) window.clearTimeout(mediaSearchTimer);
        mediaSearchTimer = window.setTimeout(() => {
          loadMediaLibrary(panel, { append: false });
        }, 250);
        return;
      }
      const path = target.dataset.path;
      const arrayPath = target.dataset.arrayPath;
      const bookingItemsPath = target.dataset.bookingItems;
      const layoutSectionsPath = target.dataset.layoutSections;
      let didUpdate = false;
      if (path) {
        setPath(state, path, target.value);
        didUpdate = true;
      } else if (arrayPath) {
        const items = splitLines(target.value).map((text, index) => ({ id: `${arrayPath.split(".").pop()}-${index + 1}`, text }));
        setPath(state, arrayPath, items.some((item) => item.text === undefined) ? splitLines(target.value) : items);
        if (arrayPath.includes("itinerary.days")) {
          setPath(state, arrayPath, splitLines(target.value));
        }
        if (arrayPath === "inclusions" || arrayPath === "exclusions" || arrayPath.startsWith("finalization.")) {
          setPath(state, arrayPath, splitLines(target.value).map((text, index) => ({ id: `${arrayPath.split(".").pop()}-${index + 1}`, text })));
        }
        didUpdate = true;
      } else if (bookingItemsPath) {
        setPath(state, bookingItemsPath, parseBookingItems(target.value));
        didUpdate = true;
      } else if (layoutSectionsPath) {
        setPath(state, layoutSectionsPath, parseLayoutSections(target.value));
        didUpdate = true;
      } else if (target.dataset.layoutEnabled || target.dataset.layoutOrder) {
        const sections = normalizeLayoutSections((((state || {}).layout || {}).sections) || []);
        const current = new Map(sections.map((section) => [section.type, { ...section }]));
        if (target.dataset.layoutEnabled) {
          const section = current.get(target.dataset.layoutEnabled);
          if (section) section.enabled = !!target.checked;
        }
        if (target.dataset.layoutOrder) {
          const section = current.get(target.dataset.layoutOrder);
          if (section) section.order = Number(target.value || section.order || 1);
        }
        setPath(state, "layout.sections", normalizeLayoutSections(Array.from(current.values())));
        didUpdate = true;
      }
      if (!didUpdate) return;
      state.meta.revision = Number(state.meta.revision || 1) + 1;
      applyDraftToDom(state);
      syncEditorFields(panel);
      scheduleSave();
    });

    panel.addEventListener("click", async (event) => {
      if (!(event.target instanceof Element)) return;
      const presetBtn = event.target.closest("[data-brand-preset]");
      if (presetBtn) {
        applyBrandPreset(presetBtn.dataset.brandPreset || "", panel);
        return;
      }
      const openGalleryBtn = event.target.closest("[data-open-gallery-for]");
      if (openGalleryBtn) {
        openMediaPicker(
          openGalleryBtn.getAttribute("data-open-gallery-for") || "",
          openGalleryBtn.getAttribute("data-asset-label") || "Media library",
          panel,
        );
        return;
      }
      if (event.target.closest("[data-close-media-picker]")) {
        closeMediaPicker(panel);
        return;
      }
      if (event.target.closest("[data-refresh-media-picker]")) {
        await loadMediaLibrary(panel, { append: false });
        return;
      }
      if (event.target.closest("[data-load-more-media]")) {
        await loadMediaLibrary(panel, { append: true });
        return;
      }
      const selectMediaBtn = event.target.closest("[data-select-media-asset]");
      if (selectMediaBtn) {
        await chooseMediaAsset(selectMediaBtn.getAttribute("data-select-media-asset") || "", panel);
      }
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
        await flushSave();
        const res = await fetch(`/api/v2/quotations/${quotationId}/publish?lang=${encodeURIComponent(currentLang)}`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ baseRevision: lastSavedRevision }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(describeErrors(data.detail || data));
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
    panel.querySelector("#draft-regenerate-btn").addEventListener("click", async () => {
      updateSaveStatus("Regenerating…", "pending");
      try {
        await flushSave();
        const res = await fetch(`/api/v2/quotations/${quotationId}/regenerate-narrative?lang=${encodeURIComponent(currentLang)}`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ scopes: ["hero", "overview", "itinerary", "booking_terms", "finalization"] }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(describeErrors(data.detail || data));
        state = normalizeDraft(data.document || state);
        lastSavedRevision = Number(data.currentRevision || ((state.meta || {}).revision || lastSavedRevision));
        applyDraftToDom(state);
        syncEditorFields(panel);
        updateSaveStatus("Narrative regenerated", "success");
      } catch (err) {
        console.error("[brochure-draft] Regenerate failed", err);
        updateSaveStatus("Regenerate failed", "error");
      }
    });

    syncEditorFields(panel);
  }

  function injectEditorStyles() {
    const style = document.createElement("style");
    style.textContent = `
      body[data-brochure-mode="editor"] {
        padding-right: 360px;
        transition: padding-right 0.24s ease;
      }
      body[data-brochure-mode="editor"][data-brochure-sidebar-collapsed="1"] {
        padding-right: 0;
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
        transition: transform 0.24s ease, box-shadow 0.24s ease;
      }
      body[data-brochure-mode="editor"][data-brochure-sidebar-collapsed="1"] #brochure-draft-sidebar {
        transform: translateX(calc(100% + 24px));
        box-shadow: none;
      }
      #brochure-draft-toggle {
        position: fixed;
        top: 88px;
        right: 376px;
        z-index: 1210;
        border: none;
        background: var(--primary, #17412e);
        color: white;
        padding: 10px 14px;
        cursor: pointer;
        box-shadow: 0 12px 30px rgba(0,0,0,0.16);
        transition: right 0.24s ease, transform 0.24s ease;
      }
      body[data-brochure-mode="editor"][data-brochure-sidebar-collapsed="1"] #brochure-draft-toggle {
        right: 16px;
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
      .draft-field-asset {
        display: grid;
        gap: 0.5rem;
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
      .draft-field input[type="search"],
      .draft-media-picker-toolbar input[type="search"] {
        width: 100%;
        border: 1px solid rgba(0,0,0,0.12);
        padding: 0.75rem 0.875rem;
        font: inherit;
        font-size: 0.875rem;
      }
      .draft-field input[type="color"] {
        width: 100%;
        height: 38px;
        border: 1px solid rgba(0,0,0,0.12);
        padding: 2px;
        background: white;
      }
      .draft-asset-shell {
        display: grid;
        gap: 0.625rem;
      }
      .draft-asset-preview-frame {
        width: 100%;
        min-height: 8rem;
        border: 1px solid rgba(0,0,0,0.08);
        background: linear-gradient(135deg, rgba(14,36,28,0.04), rgba(14,36,28,0.08));
        display: grid;
        place-items: center;
        overflow: hidden;
      }
      .draft-asset-preview-image {
        display: block;
        width: 100%;
        max-height: 12rem;
        object-fit: cover;
      }
      .draft-asset-preview-empty {
        color: #666;
        font-size: 0.8125rem;
        padding: 1rem;
        text-align: center;
      }
      .draft-asset-actions {
        display: grid;
        gap: 0.5rem;
      }
      .draft-asset-actions input[type="file"],
      .draft-asset-actions button,
      .draft-media-picker-close,
      .draft-media-picker-toolbar button,
      .draft-media-card button,
      .draft-media-picker-footer button {
        min-height: 2.75rem;
      }
      .draft-asset-library-btn,
      .draft-media-picker-close,
      .draft-media-picker-toolbar button,
      .draft-media-card button,
      .draft-media-picker-footer button {
        border: 1px solid rgba(0,0,0,0.12);
        background: white;
        color: #17382d;
        padding: 0.75rem 0.875rem;
        cursor: pointer;
        font: inherit;
        font-size: 0.875rem;
      }
      .draft-asset-library-btn:hover,
      .draft-media-picker-close:hover,
      .draft-media-picker-toolbar button:hover,
      .draft-media-card button:hover,
      .draft-media-picker-footer button:hover {
        border-color: var(--primary, #17412e);
      }
      .draft-asset-url {
        display: block;
        margin-top: 6px;
        color: #666;
        font-size: 11px;
        word-break: break-all;
      }
      .draft-brand-presets {
        padding: 12px;
        border-bottom: 1px solid rgba(0,0,0,0.06);
        display: grid;
        gap: 10px;
      }
      .draft-brand-presets-label {
        display: block;
        font-size: 12px;
        font-weight: 700;
        color: #555;
        text-transform: uppercase;
        letter-spacing: 0.06em;
      }
      .draft-brand-presets-buttons {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
      }
      .draft-brand-preset-btn {
        border: 1px solid rgba(0,0,0,0.12);
        background: white;
        color: #222;
        padding: 8px 10px;
        cursor: pointer;
        font: inherit;
        font-size: 12px;
      }
      .draft-brand-preset-btn.is-active {
        background: var(--primary, #17412e);
        color: white;
        border-color: var(--primary, #17412e);
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
      .draft-media-picker {
        position: fixed;
        inset: 0;
        z-index: 1001;
      }
      .draft-media-picker-backdrop {
        position: absolute;
        inset: 0;
        border: none;
        background: rgba(14, 20, 18, 0.55);
        cursor: pointer;
      }
      .draft-media-picker-dialog {
        position: relative;
        z-index: 1;
        width: min(100vw - 1.5rem, 42rem);
        max-height: calc(100vh - 1.5rem);
        margin: 0.75rem auto;
        background: #f8f7f2;
        border: 1px solid rgba(0,0,0,0.08);
        box-shadow: 0 1.25rem 3rem rgba(9, 20, 17, 0.18);
        display: grid;
        grid-template-rows: auto auto auto minmax(0, 1fr) auto;
      }
      .draft-media-picker-header,
      .draft-media-picker-toolbar,
      .draft-media-picker-footer {
        padding: 0.875rem 1rem;
      }
      .draft-media-picker-header {
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        gap: 0.75rem;
        border-bottom: 1px solid rgba(0,0,0,0.06);
      }
      .draft-media-picker-header strong {
        display: block;
        font-size: 1rem;
        margin-bottom: 0.25rem;
      }
      .draft-media-picker-header p,
      .draft-media-picker-footer span {
        margin: 0;
        font-size: 0.8125rem;
        color: #5f6864;
      }
      .draft-media-picker-toolbar {
        display: grid;
        gap: 0.625rem;
        border-bottom: 1px solid rgba(0,0,0,0.06);
      }
      .draft-media-picker-status {
        padding: 0.75rem 1rem;
        font-size: 0.8125rem;
        color: #4f5954;
        border-bottom: 1px solid rgba(0,0,0,0.06);
      }
      .draft-media-picker-status[data-tone="error"] {
        color: #b43a2d;
      }
      .draft-media-grid {
        overflow: auto;
        padding: 1rem;
        display: grid;
        grid-template-columns: 1fr;
        gap: 0.875rem;
      }
      .draft-media-card {
        border: 1px solid rgba(0,0,0,0.08);
        background: white;
        overflow: hidden;
      }
      .draft-media-card.is-active {
        border-color: var(--primary, #17412e);
        box-shadow: 0 0 0 1px rgba(23, 65, 46, 0.15);
      }
      .draft-media-card-image {
        display: block;
        width: 100%;
        aspect-ratio: 16 / 10;
        object-fit: cover;
        background: rgba(0,0,0,0.04);
      }
      .draft-media-card-body {
        padding: 0.875rem;
        display: grid;
        gap: 0.5rem;
      }
      .draft-media-card-body strong {
        font-size: 0.9375rem;
        line-height: 1.3;
      }
      .draft-media-card-body small {
        color: #5f6864;
        font-size: 0.75rem;
      }
      .draft-media-card button[disabled] {
        background: rgba(23, 65, 46, 0.1);
        color: #17382d;
        cursor: default;
      }
      .draft-media-empty {
        padding: 1.5rem 1rem;
        text-align: center;
        border: 1px dashed rgba(0,0,0,0.12);
        background: rgba(255,255,255,0.75);
        color: #5f6864;
        font-size: 0.875rem;
      }
      .draft-media-picker-footer {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 0.75rem;
        border-top: 1px solid rgba(0,0,0,0.06);
      }
      #draft-save-status[data-tone="success"] { color: #0a7f34; }
      #draft-save-status[data-tone="error"] { color: #c0392b; }
      #draft-save-status[data-tone="pending"] { color: #9a6700; }
      @media (min-width: 768px) {
        .draft-asset-actions {
          grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
        }
        .draft-media-picker-toolbar {
          grid-template-columns: minmax(0, 1fr) auto;
          align-items: center;
        }
        .draft-media-grid {
          grid-template-columns: repeat(2, minmax(0, 1fr));
        }
      }
      @media (max-width: 1100px) {
        body[data-brochure-mode="editor"] { padding-right: 0; }
        #brochure-draft-sidebar {
          width: min(420px, 100vw);
        }
        #brochure-draft-toggle {
          right: 16px;
          top: 78px;
        }
      }
      @media (min-width: 1024px) {
        .draft-media-grid {
          grid-template-columns: repeat(3, minmax(0, 1fr));
        }
      }
    `;
    document.head.appendChild(style);
  }

  applyDraftToDom(state);

  if (isEditor) {
    injectEditorStyles();
    renderEditor();
  }
})();
