import io
import time
import streamlit as st
from PIL import Image
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

st.set_page_config(page_title="Full Page Screenshot Tool", page_icon="📸", layout="wide")

st.title("📸 Full-Page Web Screenshot Tool")
st.write("Paste any public URL to capture a complete, full-length screenshot for data validation.")

# Session state initialization
if "img_bytes" not in st.session_state:
    st.session_state.img_bytes = None
if "target_url" not in st.session_state:
    st.session_state.target_url = ""

url_input = st.text_input("Enter Web URL:", placeholder="https://example.com")
width = st.number_input("Viewport Width (px):", min_value=800, max_value=3840, value=1920, step=100)

def get_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36")
    
    # Check if running in Streamlit Cloud Linux container
    try:
        service = Service("/usr/bin/chromedriver")
        driver = webdriver.Chrome(service=service, options=chrome_options)
    except Exception:
        # Fallback for local development
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
    return driver

def capture_full_page_selenium(url: str, viewport_width: int):
    driver = None
    try:
        driver = get_driver()
        driver.set_window_size(viewport_width, 1080)
        driver.get(url)
        time.sleep(2)

        # 1. Preset Age Cookies
        parsed_domain = url.split("//")[-1].split("/")[0]
        cookies = ["age_verified", "is_over_18", "adult_verified", "ageGatePassed", "over18"]
        for cookie_name in cookies:
            try:
                driver.add_cookie({"name": cookie_name, "value": "true", "domain": f".{parsed_domain}", "path": "/"})
            except Exception:
                pass

        # 2. Click Popups & Age Verification
        driver.execute_script("""
            const keywords = ['yes', 'i am 18', 'i am over 18', 'i am 21', 'i am over 21', 'enter', 'confirm', 'agree', 'verify', 'accept', 'allow', 'continue'];
            const elements = Array.from(document.querySelectorAll('button, a, input[type="button"], input[type="submit"], div[role="button"]'));
            for (const el of elements) {
                const text = (el.innerText || el.value || '').trim().toLowerCase();
                if (keywords.some(k => text === k || text.includes(k))) {
                    try { el.click(); } catch (e) {}
                }
            }
        """)
        time.sleep(1)

        # 3. Scroll to trigger lazy loading
        total_height = driver.execute_script("return document.body.scrollHeight")
        viewport_height = driver.execute_script("return window.innerHeight")
        for pos in range(0, total_height, 300):
            driver.execute_script(f"window.scrollTo(0, {pos});")
            time.sleep(0.05)
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(1)

        # 4. Hide Sticky Headers
        driver.execute_script("""
            const elements = document.querySelectorAll('*');
            for (let el of elements) {
                const style = window.getComputedStyle(el);
                if (style.position === 'fixed') {
                    el.style.position = 'absolute';
                }
            }
        """)

        # 5. Expand Window to Full Height & Capture
        full_height = driver.execute_script("return Math.max(document.body.scrollHeight, document.documentElement.scrollHeight);")
        driver.set_window_size(viewport_width, full_height)
        time.sleep(1)

        png_bytes = driver.get_screenshot_as_png()
        return png_bytes, None

    except Exception as e:
        return None, str(e)
    finally:
        if driver:
            driver.quit()

if st.button("Capture Screenshot", type="primary"):
    if not url_input:
        st.warning("Please enter a valid URL.")
    else:
        target_url = url_input.strip()
        if not target_url.startswith(("http://", "https://")):
            target_url = "https://" + target_url

        with st.spinner("Navigating, bypassing popups, and capturing..."):
            img_bytes, error = capture_full_page_selenium(target_url, width)

        if error:
            st.error(f"Failed to capture screenshot: {error}")
            st.session_state.img_bytes = None
        elif img_bytes:
            st.session_state.img_bytes = img_bytes
            st.session_state.target_url = target_url

# Render download and preview
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
