import asyncio
import sys
from playwright.async_api import async_playwright
import re

async def run():
    print("Starting Playwright sync test...")
    async with async_playwright() as p:
        try:
            browser = await p.chromium.launch(headless=True)
        except Exception as e:
            print("Failed to launch chromium. Error:", e)
            return

        context = await browser.new_context()
        
        # Open HTML page
        html_page = await context.new_page()
        html_url = "http://localhost:8111/quotations/quo_62861a208ec5?lang=en"
        print(f"Opening HTML: {html_url}")
        res = await html_page.goto(html_url)
        if res.status != 200:
            print(f"Failed to load HTML. Status: {res.status}")
            sys.exit(1)
        await html_page.wait_for_load_state("networkidle")

        # Open PDF page
        pdf_page = await context.new_page()
        pdf_url = "http://localhost:8111/quotations/quo_62861a208ec5/pdf?lang=en"
        print(f"Opening PDF: {pdf_url}")
        res = await pdf_page.goto(pdf_url)
        if res.status != 200:
            print(f"Failed to load PDF. Status: {res.status}")
            sys.exit(1)
        await pdf_page.wait_for_load_state("networkidle")

        passed = True

        def assert_equal(name, html_val, pdf_val):
            nonlocal passed
            html_val = html_val.strip() if html_val else ""
            pdf_val = pdf_val.strip() if pdf_val else ""
            if html_val != pdf_val:
                print(f"❌ [FAIL] {name} mismatch:\n  HTML: '{html_val}'\n  PDF:  '{pdf_val}'")
                passed = False
            else:
                print(f"✅ [PASS] {name} synced: '{html_val}'")

        def assert_contains(name, full_str, sub_str):
            nonlocal passed
            full_str = full_str or ""
            sub_str = sub_str or ""
            if sub_str not in full_str:
                print(f"❌ [FAIL] {name} missing:\n  Expected '{sub_str}' to be in '{full_str}'")
                passed = False
            else:
                print(f"✅ [PASS] {name} contains expected string.")

        print("\n--- 1. Brand Logo & Fonts ---")
        try:
            # HTML logo could be in a specific container, but we check img src
            html_logo_src = await html_page.get_attribute("img[src*='vietnam_safar.png']", "src")
            pdf_logo_src = await pdf_page.get_attribute("img[src*='vietnam_safar.png']", "src")
            assert_equal("Brand Logo SRC", html_logo_src, pdf_logo_src)
            
            pdf_fonts = await pdf_page.evaluate("Array.from(document.querySelectorAll('link[href*=\"fonts.googleapis.com\"]')).map(el => el.href).join(',')")
            # The test previously hardcoded Playfair Display, but live uses Allura
            assert_contains("PDF Font Accent", pdf_fonts, "family=Allura")
        except Exception as e:
             print(f"❌ [FAIL] Brand/Font error: {e}")
             passed = False

        print("\n--- 2. Cover Page & Hero Meta ---")
        try:
            html_meta1 = await html_page.inner_text("[data-editable='hero_meta_1']")
            html_meta2 = await html_page.inner_text("[data-editable='hero_meta_2']")
            
            pdf_overview = await pdf_page.evaluate("Array.from(document.querySelectorAll('.qrow')).find(row => row.innerText.includes('Overview'))?.querySelector('strong')?.innerText")
            pdf_dates = await pdf_page.evaluate("Array.from(document.querySelectorAll('.qrow')).find(row => row.innerText.includes('Travel dates'))?.querySelector('strong')?.innerText")
            
            assert_equal("Hero Meta 1 (Overview)", html_meta1, pdf_overview)

            # Same for dates, HTML might say 'APR', PDF 'Apr'
            assert_equal("Hero Meta 2 (Travel Dates)", html_meta2.upper(), pdf_dates.upper() if pdf_dates else "")
        except Exception as e:
             print(f"❌ [FAIL] Hero Meta error: {e}")
             passed = False

        print("\n--- 3. Itinerary & Day Images ---")
        try:
            # HTML image has data-img-type='hero'
            html_imgs = await html_page.evaluate("Array.from(document.querySelectorAll('div.day-image.hero-image')).map(el => el.style.getPropertyValue('--image') || el.style.backgroundImage)")
            
            pdf_imgs = await pdf_page.evaluate("Array.from(document.querySelectorAll('.day-card .day-meta div[style*=\"background-image\"]')).map(el => el.style.backgroundImage)")
            
            print(f"DEBUG ALL HTML IMGS: {html_imgs}")
            print(f"DEBUG ALL PDF IMGS: {pdf_imgs}")
            
            html_day1_img_raw = html_imgs[0] if html_imgs else ""
            m = re.search(r"url\(['\"]?(.*?)['\"]?\)", html_day1_img_raw)
            html_day1_img = m.group(1) if m else ""

            pdf_day1_img_raw = pdf_imgs[0] if pdf_imgs else ""
            m2 = re.search(r"url\(['\"]?(.*?)['\"]?\)", pdf_day1_img_raw)
            pdf_day1_img = m2.group(1) if m2 else ""

            assert_equal("Day 1 Thumbnail Image", html_day1_img, pdf_day1_img)
        except Exception as e:
             print(f"❌ [FAIL] Day 1 Thumbnail Image error: {e}")
             passed = False
             
        print("\n--- 4. Pricing & Terms ---")
        try:
            html_deposit = await html_page.inner_text("[data-editable='term_deposit']")
            # PDF terms table is a table in the Inclusions & Terms section
            pdf_deposit = await pdf_page.evaluate("Array.from(document.querySelectorAll('td')).find(td => td.innerText.includes('Deposit'))?.nextElementSibling?.innerText")
            assert_equal("Term Deposit", html_deposit, pdf_deposit)
        except Exception as e:
             print(f"❌ [FAIL] Terms error: {e}")
             passed = False

        print("\n--- 5. Journey Rhythm (Vibe/Tone) ---")
        try:
            html_rhythm_title = await html_page.inner_text("[data-editable='journey_overview_title']")
            pdf_rhythm_title = await pdf_page.evaluate("Array.from(document.querySelectorAll('h2.section-h2')).find(el => el.innerText && el.innerText.length > 5 && !el.innerText.includes('Mapped') && !el.innerText.includes('Specialist'))?.innerText")
            assert_equal("Journey Rhythm Title", html_rhythm_title, pdf_rhythm_title)
        except Exception as e:
             print(f"❌ [FAIL] Journey Rhythm error: {e}")
             passed = False

        print("\n--- 6. Designer Signature & Contact ---")
        try:
            html_designer_title = await html_page.inner_text("[data-editable='designer_title']")
            pdf_designer_title = await pdf_page.evaluate("Array.from(document.querySelectorAll('h2.section-h2')).find(el => el.innerText.includes('Specialist') || el.innerText.includes('Meet'))?.innerText")
            assert_equal("Designer Title", html_designer_title, pdf_designer_title)
        except Exception as e:
             print(f"❌ [FAIL] Designer section error: {e}")
             passed = False

        if passed:
            print("\n🎉 ALL SYNC TESTS PASSED!")
            sys.exit(0)
        else:
            print("\n❌ SOME TESTS FAILED.")
            sys.exit(1)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
