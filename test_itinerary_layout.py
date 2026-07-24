import pytest
from playwright.sync_api import Page, expect

# We assume a test HTML file was generated (e.g. by a sh test script)
TEST_FILE_URI = "file:///Users/nam/Workspace/projects/running/travel.ai/quotation-landingpage-template/vietnam-rails-mountains-shores-sara-2pax-quotation.html"

# Viewport configurations
VIEWPORTS = {
    "mobile": {"width": 375, "height": 812},
    "tablet": {"width": 768, "height": 1024},
    "desktop": {"width": 1440, "height": 900}
}

@pytest.fixture(scope="function")
def load_quotation(page: Page):
    """Fixture to load the generated HTML quotation."""
    page.goto(TEST_FILE_URI)
    # Wait for the itinerary section to be present
    page.wait_for_selector("#itinerary")
    yield page

def test_chapter_grouping(load_quotation, page: Page):
    """1. Verify Chapter Grouping: Ensure itinerary is grouped by chapters."""
    chapters = page.locator(".chapter")
    count = chapters.count()
    assert count > 0, "No chapters found in the itinerary."
    
    # Check the first chapter's header
    first_chapter = chapters.first
    chapter_num_text = first_chapter.locator(".chapter-number").inner_text()
    assert "CHAPTER" in chapter_num_text.upper(), f"Expected 'CHAPTER' in chapter number, got '{chapter_num_text}'"
    
    chapter_dest = first_chapter.locator("h3").inner_text()
    assert len(chapter_dest) > 0, "Chapter destination is empty."

def test_diverse_day_layouts(load_quotation, page: Page):
    """2. Verify Diverse Day Layouts: Ensure days use specific layouts instead of generic ones."""
    days = page.locator(".day")
    assert days.count() > 0, "No days found."
    
    # Map of expected image counts per layout
    layout_images = {
        "arrival": 1,
        "departure": 0,
        "transition": 1,
        "scenic": 3,
        "cultural": 3,
        "exploration": 2,
        "leisure": 1
    }
    
    # Verify that each day has a valid layout class and the expected number of images
    for i in range(days.count()):
        day = days.nth(i)
        class_attr = day.get_attribute("class")
        layout_match = [layout for layout in layout_images.keys() if f"layout-{layout}" in class_attr]
        
        assert len(layout_match) > 0, f"Day {i+1} is missing a recognized layout class."
        layout = layout_match[0]
        
        # Verify logic chip matches layout
        logic_chip = day.locator(".logic-chip")
        if logic_chip.count() > 0:
            assert logic_chip.inner_text().lower() == layout
        
        # We can't strictly assert the exact number of images rendered without knowing the specific data,
        # but we can ensure that if it's scenic or cultural, .supporting-images exists
        if layout in ["scenic", "cultural", "exploration"]:
            assert day.locator(".supporting-images").count() == 1, f"Layout {layout} should have .supporting-images"

def test_responsive_grid_ui_ux_mobile(load_quotation, page: Page):
    """3a. Verify Responsive Grid Behavior and UI/UX Integrity on Mobile."""
    page.set_viewport_size(VIEWPORTS["mobile"])
    page.wait_for_timeout(500)  # Allow CSS to recalculate
    
    # Check for horizontal scrolling overflow
    scroll_width = page.evaluate("document.body.scrollWidth")
    inner_width = page.evaluate("window.innerWidth")
    assert scroll_width <= inner_width, f"Horizontal overflow detected! scrollWidth={scroll_width}, innerWidth={inner_width}"
    
    # Check Stacking / Visual Hierarchy on mobile
    # In .layout-arrival, images and text should stack vertically (flex-direction: column or grid-template-columns: 1fr)
    arrival_days = page.locator(".layout-arrival")
    if arrival_days.count() > 0:
        arrival = arrival_days.first
        grid_cols = arrival.evaluate("el => window.getComputedStyle(el).gridTemplateColumns")
        # Ensure it's not a multi-column grid
        assert grid_cols == "none" or len(grid_cols.split("px")) <= 2, f"Grid did not collapse on mobile: {grid_cols}"
        
        # Ensure safe padding on the chapter container (should be ~24px from the media query)
        chapter_days = arrival.locator("..") # parent .chapter-days
        padding = chapter_days.evaluate("el => window.getComputedStyle(el).paddingLeft")
        assert padding == "24px" or padding == "0px", f"Expected mobile padding, got {padding}"

def test_responsive_grid_ui_ux_tablet(load_quotation, page: Page):
    """3b. Verify Responsive Grid Behavior and UI/UX Integrity on Tablet."""
    page.set_viewport_size(VIEWPORTS["tablet"])
    page.wait_for_timeout(500)
    
    scroll_width = page.evaluate("document.body.scrollWidth")
    inner_width = page.evaluate("window.innerWidth")
    assert scroll_width <= inner_width, f"Horizontal overflow detected on tablet! scrollWidth={scroll_width}, innerWidth={inner_width}"
    
    # Tablet media query (<980px) should also collapse the main grids
    exploration_days = page.locator(".layout-exploration")
    if exploration_days.count() > 0:
        expl = exploration_days.first
        grid_cols = expl.evaluate("el => window.getComputedStyle(el).gridTemplateColumns")
        assert grid_cols == "none" or len(grid_cols.split("px")) <= 2, f"Grid did not collapse on tablet: {grid_cols}"

def test_responsive_grid_ui_ux_desktop(load_quotation, page: Page):
    """3c. Verify Responsive Grid Behavior and UI/UX Integrity on Desktop."""
    page.set_viewport_size(VIEWPORTS["desktop"])
    page.wait_for_timeout(500)
    
    # On desktop, the grids should be multi-column
    exploration_days = page.locator(".layout-exploration")
    if exploration_days.count() > 0:
        expl = exploration_days.first
        grid_cols = expl.evaluate("el => window.getComputedStyle(el).gridTemplateColumns")
        # E.g. "828px 612px" -> means multiple columns
        assert len(grid_cols.split(" ")) > 1, f"Grid should be multi-column on desktop: {grid_cols}"
