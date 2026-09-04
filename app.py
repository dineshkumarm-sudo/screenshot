import asyncio
import io
import streamlit as st
from PIL import Image
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async

# Streamlit Page Setup
st.set_page_config(page_title="Full Page Screenshot Tool", page_icon="📸", layout="wide")

st.title("📸 Full-Page Web Screenshot Tool")
st.write("Enter any public URL below to generate a complete, full-page screenshot.")

# User Inputs
url_input = st.text_input("Enter Web URL:", placeholder="https://example.com")
width = st.number_input("Viewport Width (px):", min_value=800, max_value=3840, value=1920, step=100)

async def capture_full_page(url: str, viewport_width: int):
    async with async_playwright() as p:
        # Launch Chromium with anti-detection flags
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
            ]
        )
        
        # Create a realistic context mimicking a real Desktop browser
        context = await browser.new_context(
            viewport={"width": viewport_width, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            locale="en-US",
            timezone_id="America/New_York",
            device_scale_factor=1,
            has_touch=False,
            is_mobile=False,
        )

        page = await context.new_page()

        # Apply stealth patches to bypass automation/bot checks
        await stealth_async(page)

        try:
            # Navigate to URL
            await page.goto(url, wait_until="domcontentloaded", timeout=45000)
            
            # Wait briefly for dynamic JS to evaluate
            await page.wait_for_timeout(2000)

            # Auto-scroll down the page to trigger lazy-loaded images & infinite media
            await page.evaluate("""
                async () => {
                    await new Promise((resolve) => {
                        let totalHeight = 0;
                        const distance = 300;
                        const timer = setInterval(() => {
                            const scrollHeight = document.body.scrollHeight;
                            window.scrollBy(0, distance);
                            totalHeight += distance;

                            if(totalHeight >= scrollHeight - window.innerHeight){
                                clearInterval(timer);
                                // Scroll back to top after loading everything
                                window.scrollTo(0, 0);
                                resolve();
                            }
                        }, 100);
                    });
                }
            """)
            
            # Wait for images/styles to settle after scroll
            await page.wait_for_timeout(1500)

            # Hide fixed/sticky elements so they don't stretch over the full screenshot
            await page.evaluate("""
                () => {
                    const elements = document.querySelectorAll('*');
                    for (let el of elements) {
                        const position = window.getComputedStyle(el).position;
                        if (position === 'fixed') {
                            el.style.position = 'absolute';
                        }
                    }
                }
            """)

            # Capture full page screenshot buffer
            image_bytes = await page.screenshot(full_page=True, type="png")
            return image_bytes, None

        except Exception as e:
            return None, str(e)
        finally:
            await browser.close()

# Action Button
if st.button("Capture Screenshot", type="primary"):
    if not url_input:
        st.warning("Please enter a valid URL.")
    else:
        # Standardize URL string
        target_url = url_input.strip()
        if not target_url.startswith(("http://", "https://")):
            target_url = "https://" + target_url

        with st.spinner("Navigating, dodging bot checks, and capturing full page..."):
            img_bytes, error = asyncio.run(capture_full_page(target_url, width))

        if error:
            st.error(f"Failed to capture screenshot: {error}")
        elif img_bytes:
            st.success("Screenshot captured successfully!")
            
            # Convert bytes to PIL image for display
            image = Image.open(io.BytesIO(img_bytes))
            
            # Display image in Streamlit
            st.image(image, caption=f"Full Screenshot of {target_url}", use_column_width=True)

            # Download button
            st.download_button(
                label="📥 Download Screenshot (PNG)",
                data=img_bytes,
                file_name="full_screenshot.png",
                mime="image/png"
            )