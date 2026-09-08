import io
import urllib.parse
import requests
import streamlit as st
from PIL import Image

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

def capture_full_page_api(url: str, viewport_width: int):
    try:
        # Use reliable free rendering API to bypass headless container limitations
        encoded_url = urllib.parse.quote(url, safe='')
        api_endpoint = f"https://render-tron.appspot.com/screenshot/{encoded_url}?width={viewport_width}"
        
        # Fallback multi-engine attempt
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/128.0.0.0 Safari/537.36"
        }
        
        response = requests.get(
            f"https://api.microlink.io/?url={encoded_url}&screenshot=true&meta=false&embed=screenshot.url",
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            # Microlink returns directly redirect or screenshot image
            img_res = requests.get(response.url, timeout=30)
            if img_res.status_code == 200:
                return img_res.content, None
                
        # Alternative secondary fallback engine
        alt_endpoint = f"https://image.thum.io/get/width/{viewport_width}/fullpage/{url}"
        alt_res = requests.get(alt_endpoint, timeout=30)
        
        if alt_res.status_code == 200 and len(alt_res.content) > 1000:
            return alt_res.content, None

        return None, "Unable to render page screenshot. The website may be blocking automated requests."

    except Exception as e:
        return None, str(e)

if st.button("Capture Screenshot", type="primary"):
    if not url_input:
        st.warning("Please enter a valid URL.")
    else:
        target_url = url_input.strip()
        if not target_url.startswith(("http://", "https://")):
            target_url = "https://" + target_url

        with st.spinner("Rendering full page screenshot..."):
            img_bytes, error = capture_full_page_api(target_url, width)

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
