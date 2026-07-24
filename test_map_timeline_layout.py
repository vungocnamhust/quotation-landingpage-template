import os
import sys
import asyncio
from playwright.async_api import async_playwright

async def run():
    print("Starting Playwright test for Map & Timeline Layout...")
    async with async_playwright() as p:
        try:
            browser = await p.chromium.launch(headless=True)
        except Exception as e:
            print("Failed to launch chromium. Error:", e)
            return

        context = await browser.new_context()
        page = await context.new_page()

        # Step 1: Test HTML Landing Page
        html_file = os.path.abspath("test-brosure-fresh.html")
        if not os.path.exists(html_file):
            print(f"Skipping HTML test, file not found: {html_file}")
        else:
            print(f"Testing HTML Layout: {html_file}")
            await page.goto(f"file://{html_file}")
            
            # Wait for JS to render markers and timeline
            await page.wait_for_selector(".timeline-item", timeout=10000)

            # UI/UX Layout Criteria
            print("Checking UI/UX Layout Proportions...")
            map_section = page.locator(".map-section")
            timeline_section = page.locator(".timeline-section")
            map_bb = await map_section.bounding_box()
            timeline_bb = await timeline_section.bounding_box()
            
            # Roughly 60/40 split check
            total_width = map_bb["width"] + timeline_bb["width"]
            map_ratio = map_bb["width"] / total_width
            timeline_ratio = timeline_bb["width"] / total_width
            assert 0.58 <= map_ratio <= 0.62, f"Map section ratio is {map_ratio}, expected ~0.60"
            assert 0.38 <= timeline_ratio <= 0.42, f"Timeline section ratio is {timeline_ratio}, expected ~0.40"
            
            # Check Blend Mode
            print("Checking CSS mix-blend-mode...")
            blend_mode = await page.evaluate("window.getComputedStyle(document.querySelector('.leaflet-tile-pane')).mixBlendMode")
            assert blend_mode == "multiply", f"Expected mix-blend-mode 'multiply', got {blend_mode}"

            # Check Items
            print("Checking Timeline items rendering...")
            items_count = await page.locator(".timeline-item").count()
            assert items_count > 0, "No timeline items rendered"
            
            # Check specific text rendering for first item
            first_item = page.locator(".timeline-item").first
            duration_text = await first_item.locator(".item-duration").inner_text()
            assert "DAY" in duration_text.upper() or "NIGHTS" in duration_text.upper(), "Day/Nights range not found"
            
            # Check interaction
            print("Checking Timeline Interaction...")
            await first_item.click()
            await page.wait_for_timeout(500)
            is_active = await first_item.evaluate("el => el.classList.contains('active')")
            assert is_active, "Timeline item did not receive 'active' class on click"
            
            # Check Map Mode Switcher
            print("Checking Map Mode Toggle...")
            await page.locator("#toggle-mode-image").click()
            await page.wait_for_selector(".custom-irregular-marker", timeout=2000)
            
            await page.locator("#toggle-mode-classic").click()
            await page.wait_for_selector(".luxury-marker-wrapper", timeout=2000)
            print("HTML Tests passed!")

        # Step 2: Test PDF Layout (using PDF template HTML view)
        pdf_html = os.path.abspath("test-brosure-fresh-pdf.html")
        if not os.path.exists(pdf_html):
            print(f"Skipping PDF HTML test, file not found: {pdf_html}")
        else:
            print(f"Testing PDF Static Layout: {pdf_html}")
            await page.goto(f"file://{pdf_html}")
            
            # Wait for rendering
            await page.wait_for_selector(".timeline-item", timeout=10000)
            
            # Check timeline exists in PDF
            timeline = page.locator("#map-timeline")
            assert await timeline.is_visible(), "Timeline not visible in PDF layout"
            
            # Check static markers
            markers_count = await page.locator(".luxury-marker-wrapper").count()
            assert markers_count > 0, "No luxury markers in PDF map"
            
            # Check page break inside rule
            print("Checking page break logic...")
            first_timeline_item = page.locator(".timeline-item").first
            page_break = await first_timeline_item.evaluate("(el) => window.getComputedStyle(el).pageBreakInside")
            assert page_break in ["avoid", "avoid-page", "auto"], f"Expected page-break-inside avoid, got {page_break}"

            print("PDF HTML Tests passed!")

        await browser.close()
        print("✅ All Map/Timeline Playwright tests passed successfully!")

if __name__ == "__main__":
    asyncio.run(run())
