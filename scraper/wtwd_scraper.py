import os
import logging
from typing import List, Optional
import requests
from bs4 import BeautifulSoup
from .utils import Tire, safe_request, default_session, retry, RequestError
logger = logging.getLogger("thermite.scraper.wtwd")

class WTWD:
    BASE_URL = os.getenv("WTWD_BASE_URL", "http://www.shopwtwd.com")
    LOGIN_URL = f"{BASE_URL}/Login.aspx"
    SEARCH_URL = f"{BASE_URL}/Shop.aspx"
    
    def __init__(self, username: str, password: str, session=None):
        self.session = session or requests.Session()
        self.username = username
        self.password = password
        self._login()
    
    def _login(self):
        """Debug WTWD login step-by-step."""
        import time

        login_url = f"{self.BASE_URL}/login.aspx?ReturnUrl=%2fHome.aspx"
        print(f"\n🌐 Fetching WTWD login page: {login_url}")

        try:
            resp = self.session.get(login_url, headers={"User-Agent": "Mozilla/5.0"}, allow_redirects=True, timeout=10)
            print(f"🛰️ Login page status code: {resp.status_code}")
        except Exception as e:
            raise Exception(f"❌ Could not fetch WTWD login page — {e}")

        with open("wtwd_login_page_debug.html", "w", encoding="utf-8") as f:
            f.write(resp.text)

        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.text, "html.parser")

        # Try to extract ASP.NET hidden fields
        viewstate = soup.find("input", {"name": "__VIEWSTATE"})
        viewstategenerator = soup.find("input", {"name": "__VIEWSTATEGENERATOR"})
        eventvalidation = soup.find("input", {"name": "__EVENTVALIDATION"})
        token = soup.find("input", {"name": "__RequestVerificationToken"})

        print("🔍 Hidden fields detected:")
        print(f"   __VIEWSTATE: {'✅' if viewstate else '❌'}")
        print(f"   __VIEWSTATEGENERATOR: {'✅' if viewstategenerator else '❌'}")
        print(f"   __EVENTVALIDATION: {'✅' if eventvalidation else '❌'}")
        print(f"   __RequestVerificationToken: {'✅' if token else '❌'}")

        # Find username and password input names
        user_field, pass_field = None, None
        for inp in soup.select("input"):
            name = inp.get("name", "")
            t = inp.get("type", "")
            if "user" in name.lower():
                user_field = name
            if "pass" in name.lower():
                pass_field = name

        print(f"🧩 Username field: {user_field}")
        print(f"🧩 Password field: {pass_field}")

        # Build payload
        payload = {}
        if viewstate:
            payload["__VIEWSTATE"] = viewstate.get("value", "")
        if viewstategenerator:
            payload["__VIEWSTATEGENERATOR"] = viewstategenerator.get("value", "")
        if eventvalidation:
            payload["__EVENTVALIDATION"] = eventvalidation.get("value", "")
        if token:
            payload["__RequestVerificationToken"] = token.get("value", "")

        if user_field and pass_field:
            payload[user_field] = self.username
            payload[pass_field] = self.password
        else:
            print("⚠️ Username/password fields not detected — might be JS-rendered form")

        # Add a best-guess login button
        payload["ctl00$ContentPlaceHolder1$Login1$LoginButton"] = "Log In"

        print("🚀 Submitting login POST request...")
        post_resp = self.session.post(login_url, data=payload, headers={"User-Agent": "Mozilla/5.0"}, allow_redirects=True)
        print(f"📡 POST response code: {post_resp.status_code}")

        with open("wtwd_login_response_debug.html", "w", encoding="utf-8") as f:
            f.write(post_resp.text)

        time.sleep(1)

        # Check for successful login
        if "Logout" in post_resp.text or "Sign Out" in post_resp.text or "Welcome" in post_resp.text:
            print("✅ WTWD login successful!")
        else:
            print("❌ WTWD login failed — check wtwd_login_page_debug.html and wtwd_login_response_debug.html for clues.")
            raise Exception("WTWD login failed — check debug HTMLs.")
