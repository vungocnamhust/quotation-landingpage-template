import asyncio
import os
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Load the latest generated HTML file
        file_path = "file://" + os.path.abspath("vietnam-rails-mountains-shores-sara-2pax-quotation.html")
        print(f"Loading {file_path}...")
        await page.goto(file_path)
        
        # Wait for the images to load and the layout to settle
        await page.wait_for_selector(".hotel-images-group")
        
        # Find all hotel images groups
        hotel_groups = await page.locator(".hotel-images-group").all()
        print(f"Found {len(hotel_groups)} hotel image groups.")
        
        if len(hotel_groups) == 0:
            print("No hotel images found.")
            await browser.close()
            return

        # Take a screenshot of the first hotel group
        first_group = hotel_groups[0]
        await first_group.screenshot(path="hotel_group_screenshot.png")
        print("Screenshot saved to hotel_group_screenshot.png")
        
        # Get bounding boxes for main and sub images in the first group
        main_img = first_group.locator(".img-wrapper-main")
        sub_img = first_group.locator(".img-wrapper-sub")
        
        main_box = await main_img.bounding_box()
        sub_box = await sub_img.bounding_box()
        
        print("\n--- DIMENSIONS ---")
        if main_box:
            print(f"Main Image (Lớn):  Width = {main_box['width']:.2f}px, Height = {main_box['height']:.2f}px")
        if sub_box:
            print(f"Sub Image (Bé):    Width = {sub_box['width']:.2f}px, Height = {sub_box['height']:.2f}px")
            
        if main_box and sub_box:
            width_ratio = main_box['width'] / sub_box['width']
            height_ratio = main_box['height'] / sub_box['height']
            print(f"\nTỷ lệ Chiều rộng (Main / Sub): {width_ratio:.2f}x")
            print(f"Tỷ lệ Chiều cao (Main / Sub): {height_ratio:.2f}x")
            
            if width_ratio > 1.2 and height_ratio > 1.2:
                print("\n✅ KIỂM THỬ THÀNH CÔNG: Ảnh Main đã lớn hơn rõ rệt so với ảnh Sub ở cả 2 chiều, tạo hiệu ứng collage như design!")
            else:
                print("\n❌ KIỂM THỬ THẤT BẠI: Kích thước chưa có sự chênh lệch rõ ràng. Vui lòng kiểm tra lại CSS Grid và Aspect Ratio.")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
