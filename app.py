import subprocess
import sys

# Auto-install chromium binary on startup if missing
try:
    subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)
except Exception as e:
    print(f"Playwright browser installation warning: {e}")

import asyncio
import io
import streamlit as st
from PIL import Image
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

st.set_page_config(page_title="Full Page Screenshot Tool", page_icon="📸", layout="wide")

st.title("📸 Full-Page Web Screenshot Tool")
st.write("Enter any public URL below to generate a complete, full-page screenshot.")

# Initialize session state
if "img_bytes" not in st.session_state:
    st.session_state.img_bytes = None
if "target_url" not in st.session_state:
    st.session_state.target_url = ""

# User Inputs
url_input = st.text_input("Enter Web URL:", placeholder="https://example.com")
width = st.number_input("Viewport Width (px):", min_value=800, max_value=3840, value=1920, step=100)

async def capture_full_page(url: str, viewport_width: int):
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

        # 1. PRE-SET COMMON AGE & COOKIE VERIFICATION COOKIES
        # Many sites check cookies like 'age_verified', 'is_over_18', or 'adult'
        parsed_domain = url.split("//")[-1].split("/")[0]
        common_cookies = [
            {"name": "age_verified", "value": "true", "domain": f".{parsed_domain}", "path": "/"},
            {"name": "is_over_18", "value": "1", "domain": f".{parsed_domain}", "path": "/"},
            {"name": "adult_verified", "value": "true", "domain": f".{parsed_domain}", "path": "/"},
            {"name": "ageGatePassed", "value": "true", "domain": f".{parsed_domain}", "path": "/"},
            {"name": "over18", "value": "1", "domain": f".{parsed_domain}", "path": "/"},
        ]
        try:
            await context.add_cookies(common_cookies)
        except Exception:
            pass # Ignore if domain formatting fails

        page = await context.new_page()

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=45000)
            await page.wait_for_timeout(2000)

            # 2. AUTO-CLICK AGE VERIFICATION & POPUP BUTTONS
            await page.evaluate("""
                () => {
                    // Common keywords on age gate buttons
                    const targetKeywords = [
                        'yes', 'i am 18', 'i am over 18', 'i am 21', 'i am over 21', 
                        'enter', 'confirm', 'agree', 'verify', 'accept', 'i agree',
                        'over 18', 'over 21', 'allow', 'continue'
                    ];

                    // Find all clickable elements
                    const elements = Array.from(document.querySelectorAll('button, a, input[type="button"], input[type="submit"], div[role="button"]'));

                    for (const el of elements) {
                        const text = (el.innerText || el.value || '').strip ? (el.innerText || el.value || '').trim().toLowerCase() : '';
                        
                        // Check if button text matches any age check keywords
                        if (targetKeywords.some(keyword => text === keyword || text.includes(keyword))) {
                            try {
                                el.click();
                            } catch (e) {}
                        }
                    }
                }
            """)

            # Wait briefly after clicking popups
            await page.wait_for_timeout(1500)

            # 3. AUTO-SCROLL TO TRIGGER LAZY-LOADED IMAGES
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

            # 4. REMOVE REMAINING OVERLAYS AND FIX STICKY HEADERS
            await page.evaluate("""
                () => {
                    // Hide modal backdrops & sticky headers
                    const elements = document.querySelectorAll('*');
                    for (let el of elements) {
                        const style = window.getComputedStyle(el);
                        if (style.position === 'fixed') {
                            el.style.position = 'absolute';
                        }
                        // Remove dark overlay screens if any are left
                        if (style.zIndex > 999 and (style.backgroundColor.includes('rgba') or style.position === 'fixed')) {
                            // Only remove if it covers high screen area
                            const rect = el.getBoundingClientRect();
                            if (rect.width >= window.innerWidth * 0.8 && rect.height >= window.innerHeight * 0.8) {
                                el.style.display = 'none';
                            }
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

if st.button("Capture Screenshot", type="primary"):
    if not url_input:
        st.warning("Please enter a valid URL.")
    else:
        target_url = url_input.strip()
        if not target_url.startswith(("http://", "https://")):
            target_url = "https://" + target_url

        with st.spinner("Navigating, bypassing age checks, and capturing..."):
            img_bytes, error = asyncio.run(capture_full_page(target_url, width))

        if error:
            st.error(f"Failed to capture screenshot: {error}")
            st.session_state.img_bytes = None
        elif img_bytes:
            st.session_state.img_bytes = img_bytes
            st.session_state.target_url = target_url

# Render download button and preview if screenshot exists in session state
if st.session_state.img_bytes:
    st.success("Screenshot captured successfully!")

    st.download_button(
        label="📥 CLICK HERE TO DOWNLOAD SCREENSHOT (PNG)",
        data=st.session_state.img_bytes,
        file_name="full_screenshot.png",
        mime="image/png",
        type="primary"
    )

    image = Image.open(io.BytesIO(st.session_state.img_bytes))
    st.image(image, caption=f"Full Screenshot Preview of {st.session_state.target_url}", use_container_width=True)
