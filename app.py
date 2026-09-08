import io
import urllib.parse
import requests
import streamlit as st
from PIL import Image

st.set_page_config(page_title="Full Page Screenshot Tool", page_icon="📸", layout="wide")

st.title("📸 Full-Page Web Screenshot Tool")
st.write("Paste any public URL to capture a complete screenshot (supports anti-bot protected sites).")

# Session state initialization
if "img_bytes" not in st.session_state:
    st.session_state.img_bytes = None
if "target_url" not in st.session_state:
    st.session_state.target_url = ""

url_input = st.text_input("Enter Web URL:", placeholder="https://www.ajmadison.com/cgi-bin/ajmadison/SHP53EM5N.html")
width = st.number_input("Viewport Width (px):", min_value=800, max_value=3840, value=1920, step=100)

def capture_screenshot(url: str, viewport_width: int):
    encoded_url = urllib.parse.quote(url, safe='')
    
    # 1. Try ScraperAPI Anti-Bot Bypass if secret key is present
    api_key = st.secrets.get("SCRAPERAPI_KEY", "")
    if api_key:
        try:
            # ScraperAPI with JavaScript rendering + Anti-Bot bypass
            scraper_url = f"http://api.scraperapi.com?api_key={api_key}&url={encoded_url}&render=true&device_type=desktop&premium=true"
            # Use screenshot parameter via Microlink with ScraperAPI proxy or direct render endpoint
            shot_endpoint = f"https://api.microlink.io/?url={urllib.parse.quote(scraper_url, safe='')}&screenshot=true&embed=screenshot.url"
            
            res = requests.get(shot_endpoint, timeout=45)
            if res.status_code == 200:
                img_res = requests.get(res.url, timeout=30)
                if img_res.status_code == 200 and len(img_res.content) > 5000:
                    return img_res.content, None
        except Exception:
            pass

    # 2. Fallback Engine: ScreenshotOne / Microlink Stealth Mode
    try:
        # Microlink with adblock & bot-bypass settings enabled
        microlink_url = (
            f"https://api.microlink.io/?"
            f"url={encoded_url}&"
            f"screenshot=true&"
            f"embed=screenshot.url&"
            f"adblock=true&"
            f"viewport.width={viewport_width}&"
            f"waitUntil=networkidle0"
        )
        
        response = requests.get(microlink_url, timeout=35)
        if response.status_code == 200:
            img_res = requests.get(response.url, timeout=30)
            if img_res.status_code == 200 and len(img_res.content) > 5000:
                return img_res.content, None

        # 3. Fallback Engine: Thum.io
        alt_endpoint = f"https://image.thum.io/get/width/{viewport_width}/fullpage/{url}"
        alt_res = requests.get(alt_endpoint, timeout=35)
        
        if alt_res.status_code == 200 and len(alt_res.content) > 5000:
            return alt_res.content, None

        return None, "Cloudflare/Anti-Bot protection blocked the capture. Add SCRAPERAPI_KEY in Streamlit Secrets to bypass."

    except Exception as e:
        return None, str(e)

if st.button("Capture Screenshot", type="primary"):
    if not url_input:
        st.warning("Please enter a valid URL.")
    else:
        target_url = url_input.strip()
        if not target_url.startswith(("http://", "https://")):
            target_url = "https://" + target_url

        with st.spinner("Bypassing anti-bot checks and rendering screenshot..."):
            img_bytes, error = capture_screenshot(target_url, width)

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

    try:
        image = Image.open(io.BytesIO(st.session_state.img_bytes))
        st.image(image, caption=f"Full Screenshot Preview of {st.session_state.target_url}", use_container_width=True)
    except Exception:
        st.info("Screenshot ready for download.")
