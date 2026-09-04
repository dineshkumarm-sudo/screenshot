import os
import subprocess
import sys

# Ensure Playwright Chromium browser binary is installed on Streamlit Cloud
try:
    from playwright.async_api import async_playwright
except ImportError:
    subprocess.run([sys.executable, "-m", "pip", "install", "playwright"])
    from playwright.async_api import async_playwright

# Install Chromium executable if missing
def ensure_playwright_installed():
    try:
        subprocess.run(["playwright", "install", "chromium"], check=True)
    except Exception as e:
        print(f"Error installing playwright chromium: {e}")

ensure_playwright_installed()

import asyncio
import io
import streamlit as st
from PIL import Image
from playwright_stealth import stealth_async

# --- REST OF YOUR APP CODE HERE ---
