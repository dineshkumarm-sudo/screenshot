import subprocess
import sys

# Auto-install Playwright Chromium & system libraries on startup
try:
    subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)
    subprocess.run([sys.executable, "-m", "playwright", "install-deps", "chromium"], check=True)
except Exception as e:
    print(f"Playwright installation warning: {e}")

import asyncio
import io
import streamlit as st
from PIL import Image
from playwright.async_api import async_playwright

st.set_page_config(page_title="Full Page Screenshot Tool", page_icon="📸", layout="wide")

st.title("📸 Full-Page Web Screenshot Tool")
st.write("Paste any public URL to capture a complete, full-length screenshot for data validation.")

# Initialize session state
if "img_bytes" not in st.session_state:
    st.session_state.img_bytes = None
if "target_url" not in st.session_state:
    st.session_state.target_url = ""

# User Inputs
url_input = st.text_input("Enter Web URL:", placeholder="https://example.com")
width = st.number_input("Viewport Width (px):", min_value=800, max_value=3840, value=1920, step=100)

async def capture_full_page(url: str, viewport_width: int):
    async with async_playwright() as p:
        # Launch standard Chromium with native anti-detection arguments
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
                "--window-size=1920,1080",
            ]
        )
        
        # Real Desktop context mimicking a normal Chrome user session
        context = await browser.new_context(
            viewport={"width": viewport_width, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            locale="en-US",
            timezone_id="America/New_York",
            extra_http_headers={
                "Accept-Language": "en-US,en;q=0.9",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
            }
        )

        # 1. PRE-SET COMMON COOKIES FOR AGE GATES
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
            pass

        page = await context.new_page()

        # Mask navigator.webdriver flag natively
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)

        try:
            response = await page.goto(url, wait_until="domcontentloaded", timeout=45000)
            
            if response and response.status >= 400:
                return None, f"Website returned HTTP error status {response.status}. Access might be restricted or blocked."

            await page.wait_for_timeout(2500)

            # 2. AUTO-CLICK AGE VERIFICATION & POPUP BUTTONS
            await page.evaluate("""
                () => {
                    const targetKeywords = [
                        'yes', 'i am 18', 'i am over 18', 'i am 21', 'i am over 21', 
                        'enter', 'confirm', 'agree', 'verify', 'accept', 'i agree',
                        'over 18', 'over 21', 'allow', 'continue'
                    ];

                    const elements = Array.from(document.querySelectorAll('button, a, input[type="button"], input[type="submit"], div[role="button"]'));

                    for (const el of elements) {
                        const text = (el.innerText || el.value || '').trim().toLowerCase();
                        if (targetKeywords.some(keyword => text === keyword || text.includes(keyword))) {
                            try {
                                el.click();
                            } catch (e) {}
                        }
                    }
                }
            """)

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

            # 4. REMOVE OVERLAYS & FIX STICKY HEADERS
            await page.evaluate("""
                () => {
                    const elements = document.querySelectorAll('*');
                    for (let el of elements) {
                        const style = window.getComputedStyle(el);
                        if (style.position === 'fixed') {
                            el.style.position = 'absolute';
                        }
                        const zIndex = parseInt(style.zIndex, 10);
                        if (!isNaN(zIndex) && zIndex > 999 && (style.backgroundColor.includes('rgba') || style.position === 'fixed')) {
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

# Render download button and preview
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
