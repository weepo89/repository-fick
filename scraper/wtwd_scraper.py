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
        """Handle the login process"""
        # First get the login page to get any required tokens
        login_page = self.session.get(self.LOGIN_URL)
        soup = BeautifulSoup(login_page.text, 'html.parser')
        
        # Extract ASP.NET form fields safely
        def _val(name):
            el = soup.find('input', {'name': name})
            return el.get('value', '') if el else ''
        viewstate = _val('__VIEWSTATE')
        viewstategenerator = _val('__VIEWSTATEGENERATOR')
        eventvalidation = _val('__EVENTVALIDATION')
        req_token = _val('__RequestVerificationToken')
        
        # Prepare login data
        login_data = {
            '__VIEWSTATE': viewstate,
            '__VIEWSTATEGENERATOR': viewstategenerator,
            '__EVENTVALIDATION': eventvalidation,
            'dnn$ctr$Login$Login_ICGCustom$textUsername': self.username,
            'dnn$ctr$Login$Login_ICGCustom$textPassword': self.password,
            'dnn$ctr$Login$Login_ICGCustom$btnLogin': 'Login',
            '__EVENTTARGET': '',
            '__EVENTARGUMENT': '',
            'ScrollTop': '',
            '__dnnVariable': '',
            '__RequestVerificationToken': req_token
        }
        
        # Additional headers for DNN
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Referer': self.LOGIN_URL,
            'DNNVariables': ''
        })
        
        # Perform login
        response = self.session.post(self.LOGIN_URL, data=login_data)
        
        # Debug: Save the response (absolute path)
        login_dbg = os.path.abspath("wtwd_login_debug.html")
        with open(login_dbg, "w", encoding="utf-8") as f:
            f.write(response.text)
        logger.debug(f"Saved login debug HTML to {login_dbg}")
            
        # Check if login was successful (case-insensitive)
        resp_l = response.text.lower()
        if "logout" not in resp_l and self.username.lower() not in resp_l:
            raise RequestError("Login failed")
            
    @retry(times=3, backoff_factor=0.6, allowed_exceptions=(RequestError,))
    def fetch_tires(self, size: Optional[str] = None) -> List[Tire]:
        """Search for tires and extract the results.

        Uses a GET to Shop.aspx?Search=... (the site redirects client-side). Parses
        the result grid (Telerik/radgrid table) and extracts size, price and stock
        from each row using explicit td indices with robust fallbacks.
        """
        if not size:
            return []

        # Normalize size into the compact numeric form the site expects (e.g. 225/45R17 -> 2254517)
        compact_size = ''.join(ch for ch in size if ch.isdigit())
        params = {'TireSizeA': compact_size, 'Search': compact_size}
        response = self.session.get(self.SEARCH_URL, params=params)

        # Save debug HTML so you can inspect locally (absolute path)
        dbg_path = os.path.abspath("wtwd_search_debug.html")
        with open(dbg_path, "w", encoding="utf-8") as f:
            f.write(response.text)
        logger.debug(f"Saved search debug HTML to {dbg_path}")

        soup = BeautifulSoup(response.text, 'html.parser')
        tires: List[Tire] = []

        # Try to find the RadGrid / results table used on the page
        table = soup.find('table', id=lambda v: v and 'ItemGridView' in v) \
                or soup.find('table', class_='rgMasterTable') \
                or soup.find('table', class_=lambda v: v and 'radgrid' in v.lower())

        if not table:
            logger.debug('No results table found on search page')
            # Try a fallback: some searches on this site require submitting the DNN RadComboBox input
            try:
                logger.debug('Attempting fallback: perform form POST using DNN TireSearchView input')
                # GET the Shop page first to collect hidden fields
                shop_page = self.session.get(self.SEARCH_URL)
                shop_soup = BeautifulSoup(shop_page.text, 'html.parser')
                def _sval(name, s=shop_soup):
                    el = s.find('input', {'name': name})
                    return el.get('value', '') if el else ''
                viewstate = _sval('__VIEWSTATE')
                viewstategenerator = _sval('__VIEWSTATEGENERATOR')
                eventvalidation = _sval('__EVENTVALIDATION')
                token = _sval('__RequestVerificationToken')

                # The DNN/Telerik input name observed in the page
                tire_input_name = 'dnn$ctr3203$TireSearchView$TireSizeARadComboBox'
                form = {
                    '__VIEWSTATE': viewstate,
                    '__VIEWSTATEGENERATOR': viewstategenerator,
                    '__EVENTVALIDATION': eventvalidation,
                    '__RequestVerificationToken': token,
                    tire_input_name: compact_size,
                    'Search': compact_size,
                }
                post_resp = self.session.post(self.SEARCH_URL, data=form)
                fallback_dbg = os.path.abspath("wtwd_search_debug_fallback.html")
                with open(fallback_dbg, "w", encoding="utf-8") as f:
                    f.write(post_resp.text)
                logger.debug(f"Saved fallback search debug HTML to {fallback_dbg}")
                shop_soup = BeautifulSoup(post_resp.text, 'html.parser')
                table = shop_soup.find('table', id=lambda v: v and 'ItemGridView' in v) \
                        or shop_soup.find('table', class_='rgMasterTable') \
                        or shop_soup.find('table', class_=lambda v: v and 'radgrid' in v.lower())
                if not table:
                    logger.debug('Fallback POST did not return a results table')
                    return []
            except Exception as e:
                logger.debug(f'fallback POST search failed: {e}')
                return []

        # rows are typically in tbody with classes like rgRow / rgAltRow
        tbody = table.find('tbody') or table
        # prefer explicit Telerik data rows
        rows = list(tbody.find_all('tr', class_='rgRow')) + list(tbody.find_all('tr', class_='rgAltRow'))
        if not rows:
            # fallback: any tr that isn't a header or a "no records" placeholder
            rows = [r for r in tbody.find_all('tr') if not r.find('th') and 'no records' not in r.get_text().lower()]

        import re
        # Match sizes like: LT265/65R20, 265/65R20, 205/55/16, 225/45R17 and hyphen variants
        size_re = re.compile(r"\b(?:LT)?\d{2,3}[-/]?\d{2}(?:R[-]?\d{1,2}|[-/]\d{1,2})\b", re.IGNORECASE)
        # Match contiguous numeric sizes like 2756520 (-> 275/65R20)
        contiguous_size_re = re.compile(r"\b([A-Za-z]*)(\d{3})(\d{2})(\d{2})\b")
        price_re = re.compile(r"\$\s*[\d,]+(?:\.\d{2})?")

        parsed_count = 0
        logger.debug(f"Found {len(rows)} candidate result rows in table")
        for row in rows:
            try:
                cells = row.find_all('td')

                # If this is the Telerik ItemGridView, common layout is:
                # [0]=icon/center, [1]=Part#, [2]=Description, [3]=Size, [4]=Manufacturer, [5]=FET, [6]=Price, [7]=WTWD Avail
                def txt(i):
                    return ' '.join(cells[i].stripped_strings).strip() if i < len(cells) else ''

                part = txt(1)
                desc = txt(2)
                size_cell = txt(3)
                manuf = txt(4)
                price_cell = txt(6)
                avail = txt(7)

                # size normalization and fallbacks
                size_val = ''
                m = size_re.search(size_cell.replace('-', '/')) or size_re.search(desc)
                if m:
                    size_val = m.group(0)
                else:
                    cm = contiguous_size_re.search(size_cell) or contiguous_size_re.search(desc)
                    if cm:
                        pref = cm.group(1) or ''
                        a,b,c = cm.group(2), cm.group(3), cm.group(4)
                        size_val = f"{pref}{a}/{b}R{c}"
                    else:
                        size_val = size_cell

                # price
                p = price_re.search(price_cell) or price_re.search(desc)
                price_val = float(p.group(0).replace('$','').replace(',','').strip()) if p else 0.0

                # stock
                stock_val = 0
                if any(ch.isdigit() for ch in avail):
                    digits = ''.join(filter(str.isdigit, avail))
                    try:
                        stock_val = int(digits)
                    except:
                        stock_val = 0

                brand = manuf or (desc.split()[0] if desc else 'UNK')
                model = desc or part

                tires.append(Tire(brand=brand, model=model, size=size_val, price=price_val, stock=stock_val))
                parsed_count += 1
            except Exception as e:
                logger.debug(f"skip row parse: {e}")

        logger.debug(f"Parsed {parsed_count} tires from table")

        return tires
