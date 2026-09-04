import subprocess
import sys

# Auto-install chromium binary on startup if missing
try:
    subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)
except Exception as e:
    print(f"Playwright browser installation warning: {e}")

import asyncio
import base64
import io
import streamlit as st
import streamlit.components.v1 as components
from PIL import Image
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

st.set_page_config(page_title="Full Page Screenshot Tool", page_icon="📸", layout="wide")

st.title("📸 Full-Page Web Screenshot Tool")
st.write("Enter any public URL below to generate a complete, full-page screenshot.")

# User Inputs
url_input = st.text_input("Enter Web URL:", placeholder="https://example.com")
width = st.number_input("Viewport Width (px):", min_value=800, max_value=3840, value=1920, step=100)

async def capture_full_page(url: str, viewport_width: int):
    # Use Stealth class context wrapper for Playwright
    async with Stealth().use_async(async_playwright()) as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
            ]
        )
        
        context = await browser.new_context(
            viewport={"width": viewport_width, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            locale="en-US",
            timezone_id="America/New_York",
        )

        page = await context.new_page()

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=45000)
            await page.wait_for_timeout(2000)

            # Auto-scroll down the page to trigger lazy-loaded images
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
                                window.scrollTo(0, 0);
                                resolve();
                            }
                        }, 100);
                    });
                }
            """)
            
            await page.wait_for_timeout(1500)

            # Convert fixed headers to absolute so they don't stretch down full screenshot
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

            image_bytes = await page.screenshot(full_page=True, type="png")
            return image_bytes, None

        except Exception as e:
            return None, str(e)
        finally:
            await browser.close()

# Function to trigger browser download automatically
def trigger_auto_download(img_bytes, filename="full_screenshot.png"):
    b64 = base64.b64encode(img_bytes).decode("utf-8")
    js_code = f"""
    <script>
        const link = document.createElement('a');
        link.href = 'data:image/png;base64,{b64}';
        link.download = '{filename}';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    </script>
    """
    components.html(js_code, height=0, width=0)

if st.button("Capture Screenshot", type="primary"):
    if not url_input:
        st.warning("Please enter a valid URL.")
    else:
        target_url = url_input.strip()
        if not target_url.startswith(("http://", "https://")):
            target_url = "https://" + target_url

        with st.spinner("Navigating, bypassing bot checks, and capturing..."):
            img_bytes, error = asyncio.run(capture_full_page(target_url, width))

        if error:
            st.error(f"Failed to capture screenshot: {error}")
        elif img_bytes:
            st.success("Screenshot captured! Downloading automatically...")
            
            # 1. Automatically start browser download
            trigger_auto_download(img_bytes, filename="full_screenshot.png")
            
            # 2. Display the preview image in Streamlit
            image = Image.open(io.BytesIO(img_bytes))
            st.image(image, caption=f"Full Screenshot of {target_url}", use_container_width=True)

            # 3. Fallback download button (in case browser blocks auto-downloads)
            st.download_button(
                label="📥 Re-download Screenshot (PNG)",
                data=img_bytes,
                file_name="full_screenshot.png",
                mime="image/png"
            )
