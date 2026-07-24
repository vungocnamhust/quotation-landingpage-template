"""
test_responsive_brosure.py
──────────────────────────
Playwright responsive audit cho template vietnam_luxury_brosure.html

Luồng:
  1. Generate quotation qua FastAPI TestClient (dùng payload từ generate_8d7n_quotation.py)
  2. Lưu HTML ra file tạm
  3. Mở bằng file:// URI trong Playwright
  4. Chạy responsive checks trên 7 viewports theo 5-tier system

Chạy:
  python -m pytest test_responsive_brosure.py -v --tb=short

Nếu cần screenshot:
  python -m pytest test_responsive_brosure.py -v --tb=short -s
  # Ảnh lưu vào ./_responsive_screenshots/
"""

import os
import sys
import time
import pathlib
import tempfile
import pytest
from playwright.sync_api import Page

# ─── Setup path & mocks ────────────────────────────────────────────────────────
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

import image_selector

async def _mock_destinations(text, max_items=None):
    return [
        {"name": "Hà Nội",   "slug": "ha-noi"},
        {"name": "Hạ Long",  "slug": "quang-ninh"},
        {"name": "Hội An",   "slug": "quang-nam"},
        {"name": "Đà Nẵng", "slug": "da-nang"},
    ]

image_selector.extract_and_map_destinations = _mock_destinations

# ─── Paths ────────────────────────────────────────────────────────────────────
GENERATED_HTML_PATH = pathlib.Path(tempfile.gettempdir()) / "test_responsive_brosure.html"
SCREENSHOTS_DIR = pathlib.Path(__file__).parent / "_responsive_screenshots"


# ─── Generate HTML once per test session ──────────────────────────────────────
def _generate_quotation_html() -> str:
    """Generate fresh HTML using the 8D7N payload with vietnam_luxury_brosure template."""
    from generate_8d7n_quotation import payload
    from main import app
    from fastapi.testclient import TestClient

    test_payload = dict(payload)
    test_payload["template"] = "vietnam_luxury_brosure.html"
    test_payload["quotationNumber"] = f"QT-RESPONSIVE-TEST-{int(time.time())}"

    client = TestClient(app)
    resp = client.post("/quotations?lang=en", json=test_payload)
    assert resp.status_code == 200, f"Failed to create quotation: {resp.text[:300]}"

    q_id = resp.json()["quotationId"]
    html_resp = client.get(f"/quotations/{q_id}?lang=en")
    assert html_resp.status_code == 200, f"Failed to get quotation HTML: {html_resp.text[:300]}"
    return html_resp.text


@pytest.fixture(scope="session")
def html_file_uri() -> str:
    """Session-scoped: generate once, reuse across all tests."""
    print("\n⏳ Generating quotation with vietnam_luxury_brosure template…")
    html = _generate_quotation_html()
    GENERATED_HTML_PATH.write_text(html, encoding="utf-8")
    SCREENSHOTS_DIR.mkdir(exist_ok=True)
    print(f"✅ HTML saved → {GENERATED_HTML_PATH}")
    return GENERATED_HTML_PATH.as_uri()


# ─── Viewport definitions (5-tier, Desktop-first) ─────────────────────────────
#
# Tier    Breakpoint    Devices
# base    > 1600px      1920px monitors, 2K/4K
# T0      ≤ 1600px      MacBook Pro 16", Dell XPS 15
# T1      ≤ 1280px      MacBook Pro 14", MacBook Air 13"
# T2      ≤ 980px       iPad Landscape, small laptops
# T3      ≤ 768px       iPad Portrait, large phones
# T4      ≤ 480px       iPhone, small Android
#
VIEWPORTS = {
    "desktop_2k":   {"width": 1920, "height": 1080, "tier": "base"},
    "laptop_16in":  {"width": 1600, "height": 900,  "tier": "T0"},
    "laptop_14in":  {"width": 1280, "height": 800,  "tier": "T1"},
    "tablet_land":  {"width": 980,  "height": 768,  "tier": "T2"},
    "tablet_port":  {"width": 768,  "height": 1024, "tier": "T3"},
    "mobile_large": {"width": 480,  "height": 900,  "tier": "T4"},
    "mobile_small": {"width": 375,  "height": 812,  "tier": "T4"},
}


# ─── Helpers ──────────────────────────────────────────────────────────────────
def set_vp(page: Page, vp: dict):
    page.set_viewport_size({"width": vp["width"], "height": vp["height"]})
    page.wait_for_timeout(350)   # let CSS reflow


def save_screenshot(page: Page, vp_name: str, label: str):
    p = SCREENSHOTS_DIR / f"{vp_name}__{label}.png"
    page.screenshot(path=str(p), full_page=True)
    print(f"  📸 {p.name}")


def computed(page: Page, selector: str, prop: str) -> str:
    el = page.locator(selector).first
    if el.count() == 0:
        return ""
    return el.evaluate(f"el => window.getComputedStyle(el).{prop}")


def grid_col_count(page: Page, selector: str) -> int:
    """Return number of explicit column tracks in a CSS grid."""
    val = computed(page, selector, "gridTemplateColumns")
    if not val or val in ("none", ""):
        return 0
    return len([t for t in val.split(" ") if t.endswith("px") or t.endswith("fr")])


# ─── Page fixture ─────────────────────────────────────────────────────────────
@pytest.fixture()
def brosure_page(page: Page, html_file_uri: str) -> Page:
    page.goto(html_file_uri)
    page.wait_for_load_state("networkidle")
    return page


# ═══════════════════════════════════════════════════════════════════════════════
# 1. HORIZONTAL OVERFLOW — must pass on ALL viewports
# ═══════════════════════════════════════════════════════════════════════════════
class TestNoHorizontalOverflow:
    """No horizontal scroll on any viewport."""

    @pytest.mark.parametrize("vp_name,vp", VIEWPORTS.items())
    def test_no_overflow(self, brosure_page: Page, vp_name: str, vp: dict):
        set_vp(brosure_page, vp)
        scroll_w = brosure_page.evaluate("document.documentElement.scrollWidth")
        inner_w  = brosure_page.evaluate("window.innerWidth")
        if scroll_w > inner_w:
            save_screenshot(brosure_page, vp_name, "OVERFLOW")
            overflowing_elements = brosure_page.evaluate("""
                () => {
                    const docWidth = document.documentElement.clientWidth;
                    const els = [];
                    [].forEach.call(document.querySelectorAll('*'), function(el) {
                      if (el.scrollWidth > docWidth) {
                        els.push(el.tagName + (el.className ? '.' + el.className : '') + ' -> ' + el.scrollWidth);
                      }
                    });
                    return els;
                }
            """)
            print(f"\nOVERFLOWING ELEMENTS on {vp_name}:\n" + "\n".join(overflowing_elements))
        assert scroll_w <= inner_w, (
            f"[{vp_name} {vp['width']}px TIER={vp['tier']}] "
            f"Horizontal overflow! scrollWidth={scroll_w} > innerWidth={inner_w}"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# 2. NAVIGATION
# ═══════════════════════════════════════════════════════════════════════════════
class TestNavResponsive:

    def test_nav_links_visible_desktop(self, brosure_page: Page):
        """base/T0/T1: nav links must be visible."""
        for vp_name in ("desktop_2k", "laptop_16in", "laptop_14in"):
            set_vp(brosure_page, VIEWPORTS[vp_name])
            display = computed(brosure_page, ".nav-links", "display")
            assert display != "none", (
                f"Nav links should be visible at {VIEWPORTS[vp_name]['width']}px, got display={display}"
            )

    def test_nav_links_hidden_at_t2(self, brosure_page: Page):
        """T2 (≤980px): nav links hidden."""
        set_vp(brosure_page, VIEWPORTS["tablet_land"])
        display = computed(brosure_page, ".nav-links", "display")
        assert display == "none", f"Nav links should hide at 980px, got display={display}"

    def test_nav_actions_icon_only_at_t3(self, brosure_page: Page):
        """T3 (768px): nav-actions visible as icon-only (no pdf-btn-text)."""
        set_vp(brosure_page, VIEWPORTS["tablet_port"])
        actions_display = computed(brosure_page, ".nav-actions", "display")
        assert actions_display != "none", "nav-actions should show (icon-only) at 768px"

        # pdf-btn-text should be hidden
        pdf_text_display = computed(brosure_page, ".pdf-btn-text", "display")
        assert pdf_text_display == "none", (
            f"PDF button text should be hidden at 768px, got display={pdf_text_display}"
        )

    def test_nav_actions_hidden_at_t4(self, brosure_page: Page):
        """T4 (375px): nav-actions hidden entirely."""
        set_vp(brosure_page, VIEWPORTS["mobile_small"])
        display = computed(brosure_page, ".nav-actions", "display")
        assert display == "none", f"nav-actions should be hidden at 375px, got display={display}"


# ═══════════════════════════════════════════════════════════════════════════════
# 3. HERO SECTION
# ═══════════════════════════════════════════════════════════════════════════════
class TestHeroSection:

    def test_hero_h1_font_scales(self, brosure_page: Page):
        """h1 font-size must be smaller on mobile than desktop (clamp)."""
        set_vp(brosure_page, VIEWPORTS["desktop_2k"])
        fs_desk = float(computed(brosure_page, ".hero h1", "fontSize").replace("px", "") or 0)

        set_vp(brosure_page, VIEWPORTS["mobile_small"])
        fs_mob = float(computed(brosure_page, ".hero h1", "fontSize").replace("px", "") or 0)

        assert fs_mob > 0, "Could not read .hero h1 font-size"
        assert fs_mob < fs_desk, (
            f"Hero h1 not scaling down: desktop={fs_desk}px, mobile={fs_mob}px"
        )

    def test_hero_actions_stack_mobile(self, brosure_page: Page):
        """T4: hero-actions flex-direction must be column."""
        set_vp(brosure_page, VIEWPORTS["mobile_small"])
        flex_dir = computed(brosure_page, ".hero-actions", "flexDirection")
        if not flex_dir:
            pytest.skip("No .hero-actions found")
        assert flex_dir == "column", (
            f"hero-actions should stack (column) on mobile, got flexDirection={flex_dir}"
        )

    def test_hero_min_height_mobile(self, brosure_page: Page):
        """Hero min-height should fill viewport on mobile."""
        set_vp(brosure_page, VIEWPORTS["mobile_small"])
        min_h_str = computed(brosure_page, ".hero", "minHeight")
        min_h = float(min_h_str.replace("px", "") or 0)
        assert min_h >= 700, f"Hero min-height too small on mobile: {min_h_str}"


# ═══════════════════════════════════════════════════════════════════════════════
# 4. GALLERY LAYOUT
# ═══════════════════════════════════════════════════════════════════════════════
class TestGalleryLayout:

    def test_gallery_3col_desktop(self, brosure_page: Page):
        set_vp(brosure_page, VIEWPORTS["desktop_2k"])
        n = grid_col_count(brosure_page, ".gallery")
        if n == 0:
            pytest.skip("No .gallery found")
        assert n >= 3, f"Gallery should have ≥3 cols on desktop, got {n}"

    def test_gallery_2col_tablet_landscape(self, brosure_page: Page):
        """T2 (980px): 2-col with hierarchy preserved (large/wide spans still apply)."""
        set_vp(brosure_page, VIEWPORTS["tablet_land"])
        n = grid_col_count(brosure_page, ".gallery")
        if n == 0:
            pytest.skip("No .gallery found")
        assert n == 2, f"Gallery should be 2-col at ≤980px, got {n}"

    def test_gallery_large_tile_spans_at_t2(self, brosure_page: Page):
        """T2: .image-tile.large must still span 2 rows (hierarchy preserved)."""
        set_vp(brosure_page, VIEWPORTS["tablet_land"])
        large_tile = brosure_page.locator(".image-tile.large").first
        if large_tile.count() == 0:
            pytest.skip("No .image-tile.large found")
        grid_row = large_tile.evaluate("el => window.getComputedStyle(el).gridRow")
        assert "span 2" in grid_row or "2" in grid_row, (
            f".image-tile.large should span 2 rows at 980px, got gridRow='{grid_row}'"
        )

    def test_gallery_1col_small_mobile(self, brosure_page: Page):
        """T4 (375px): fully collapsed to 1-col, no spans."""
        set_vp(brosure_page, VIEWPORTS["mobile_small"])
        n = grid_col_count(brosure_page, ".gallery")
        if n == 0:
            pytest.skip("No .gallery found")
        assert n == 1, f"Gallery should be 1-col at 375px, got {n}"

        # spans should be reset
        large_tile = brosure_page.locator(".image-tile.large").first
        if large_tile.count() > 0:
            grid_row = large_tile.evaluate("el => window.getComputedStyle(el).gridRow")
            assert "span 2" not in grid_row, (
                f".image-tile.large should NOT span on small mobile, got gridRow='{grid_row}'"
            )


# ═══════════════════════════════════════════════════════════════════════════════
# 5. DAY CARD
# ═══════════════════════════════════════════════════════════════════════════════
class TestDayCard:

    def test_day_multicol_desktop(self, brosure_page: Page):
        set_vp(brosure_page, VIEWPORTS["desktop_2k"])
        n = grid_col_count(brosure_page, ".itinerary .day")
        if n == 0:
            pytest.skip("No .itinerary .day found")
        assert n >= 2, f"Day card should be multi-col on desktop, got {n}"

    def test_day_single_col_mobile(self, brosure_page: Page):
        set_vp(brosure_page, VIEWPORTS["mobile_small"])
        n = grid_col_count(brosure_page, ".itinerary .day")
        if n == 0:
            pytest.skip("No .itinerary .day found")
        assert n == 1, f"Day card should be 1-col on mobile, got {n}"


# ═══════════════════════════════════════════════════════════════════════════════
# 6. MAP LAYOUT
# ═══════════════════════════════════════════════════════════════════════════════
class TestMapLayout:

    def test_map_two_col_desktop(self, brosure_page: Page):
        set_vp(brosure_page, VIEWPORTS["desktop_2k"])
        n = grid_col_count(brosure_page, ".map-layout-new")
        if n == 0:
            pytest.skip("No .map-layout-new found")
        assert n == 2, f".map-layout-new should be 2-col on desktop, got {n}"

    def test_map_stacks_at_t3(self, brosure_page: Page):
        """T3 (768px): map stacks to 1-col (map above, timeline below)."""
        set_vp(brosure_page, VIEWPORTS["tablet_port"])
        n = grid_col_count(brosure_page, ".map-layout-new")
        if n == 0:
            pytest.skip("No .map-layout-new found")
        assert n == 1, f".map-layout-new should be 1-col at 768px, got {n}"


# ═══════════════════════════════════════════════════════════════════════════════
# 7. SECTION SPACING
# ═══════════════════════════════════════════════════════════════════════════════
class TestSectionSpacing:

    def test_section_padding_mobile_in_range(self, brosure_page: Page):
        """Padding should be between 28–56px on mobile (no oversized whitespace)."""
        set_vp(brosure_page, VIEWPORTS["mobile_small"])
        sections = brosure_page.locator("main > section")
        if sections.count() == 0:
            pytest.skip("No <section> in <main>")
        pt = float(sections.first.evaluate(
            "el => parseFloat(window.getComputedStyle(el).paddingTop)"
        ))
        assert pt <= 56, f"Section padding-top too large on mobile: {pt}px (max 56px)"
        assert pt >= 28, f"Section padding-top too small on mobile: {pt}px (min 28px)"

    def test_section_padding_larger_on_desktop(self, brosure_page: Page):
        """Section padding should be larger on desktop than mobile (fluid)."""
        set_vp(brosure_page, VIEWPORTS["mobile_small"])
        sections = brosure_page.locator("main > section")
        if sections.count() == 0:
            pytest.skip("No <section> in <main>")
        pt_mobile = float(sections.first.evaluate(
            "el => parseFloat(window.getComputedStyle(el).paddingTop)"
        ))
        set_vp(brosure_page, VIEWPORTS["desktop_2k"])
        pt_desktop = float(sections.first.evaluate(
            "el => parseFloat(window.getComputedStyle(el).paddingTop)"
        ))
        assert pt_desktop >= pt_mobile, (
            f"Section padding should be >= on desktop. desktop={pt_desktop}px, mobile={pt_mobile}px"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# 8. PUBLISH BAR
# ═══════════════════════════════════════════════════════════════════════════════
class TestPublishBar:

    @pytest.mark.parametrize("width", [400, 375, 360])
    def test_publish_bar_fits_narrow_screen(self, brosure_page: Page, width: int):
        brosure_page.set_viewport_size({"width": width, "height": 700})
        brosure_page.wait_for_timeout(300)
        bar = brosure_page.locator("#publish-bar")
        if bar.count() == 0:
            pytest.skip("No #publish-bar (hidden in read-only mode)")
        box = bar.bounding_box()
        if box is None:
            pytest.skip("publish-bar not visible")
        right_edge = box["x"] + box["width"]
        assert right_edge <= width + 2, (
            f"publish-bar overflows at {width}px: right_edge={right_edge:.0f}px"
        )
        assert box["x"] >= -2, f"publish-bar extends off left edge: x={box['x']}"


# ═══════════════════════════════════════════════════════════════════════════════
# 9. FULL-PAGE SCREENSHOTS (visual review)
# ═══════════════════════════════════════════════════════════════════════════════
class TestScreenshotAll:
    """Chụp full-page screenshots tất cả viewports để visual diff."""

    @pytest.mark.parametrize("vp_name,vp", VIEWPORTS.items())
    def test_screenshot(self, brosure_page: Page, vp_name: str, vp: dict):
        set_vp(brosure_page, vp)
        brosure_page.evaluate("window.scrollTo(0, 0)")
        out = SCREENSHOTS_DIR / f"{vp['tier']}__{vp_name}__{vp['width']}x{vp['height']}.png"
        brosure_page.screenshot(path=str(out), full_page=True)
        print(f"\n  📸 {out.name}")
        assert out.exists()
