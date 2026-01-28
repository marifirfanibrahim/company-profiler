"""
build selenium driver
fetch page html
wait css selector
scroll page
dismiss overlays
read cookies
"""

import time

from selenium import webdriver
from selenium.webdriver.common.by import By


# ==================== DRIVER ====================

def build_chrome_driver(
    headless: bool,
    window_width: int,
    window_height: int,
    extra_args: list,
    page_load_strategy: str,
    use_profile: bool,
    user_data_dir: str,
    profile_dir: str,
):
    # build chrome driver
    options = webdriver.ChromeOptions()

    # set page load strategy
    pls = str(page_load_strategy or "").strip().lower()
    if pls not in ["normal", "eager", "none"]:
        pls = "eager"
    options.set_capability("pageLoadStrategy", pls)

    # set headless mode
    if bool(headless):
        options.add_argument("--headless=new")

    # set window size
    options.add_argument(f"--window-size={int(window_width)},{int(window_height)}")

    # add stable args
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    # reduce automation flags
    options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
    options.add_experimental_option("useAutomationExtension", False)

    # attach persistent profile
    if bool(use_profile):
        udd = str(user_data_dir or "").strip()
        pdir = str(profile_dir or "").strip()

        if udd:
            options.add_argument(f"--user-data-dir={udd}")

            if pdir:
                options.add_argument(f"--profile-directory={pdir}")

    # add extra args
    for arg in list(extra_args or []):
        # normalize arg string
        s = str(arg or "").strip()
        if not s:
            continue
        options.add_argument(s)

    # build driver
    driver = webdriver.Chrome(options=options)

    return driver


# ==================== FETCH ====================

def fetch_page_source(driver, url: str, page_load_timeout: int):
    # load url and return html
    driver.set_page_load_timeout(int(page_load_timeout))
    driver.get(str(url))
    return str(driver.page_source or "")


# ==================== WAIT ====================

def wait_for_css(driver, css_selector: str, wait_seconds: int, poll_seconds: float):
    # wait for css selector without exceptions
    sel = str(css_selector or "").strip()
    if not sel:
        return False

    # normalize wait seconds
    wait = int(wait_seconds)
    if wait <= 0:
        return False

    # normalize poll seconds
    poll = float(poll_seconds)
    if poll <= 0.0:
        poll = 0.5

    start = time.time()
    while True:
        # check element presence
        found = driver.find_elements(By.CSS_SELECTOR, sel)
        if found:
            return True

        # check timeout
        elapsed = time.time() - start
        if elapsed >= float(wait):
            return False

        # sleep poll
        time.sleep(poll)


# ==================== SCROLL ====================

def scroll_to_bottom(driver, steps: int, sleep_seconds: float):
    # scroll page to trigger dynamic loads
    s = int(steps)
    if s <= 0:
        return

    # normalize sleep
    pause = float(sleep_seconds)
    if pause < 0.0:
        pause = 0.0

    for _ in range(s):
        # scroll to bottom
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

        # sleep between scrolls
        if pause > 0.0:
            time.sleep(pause)


# ==================== DISMISS ====================

def click_first_xpath(driver, xpath: str) -> bool:
    # click first matching xpath
    xp = str(xpath or "").strip()
    if not xp:
        return False

    # find matching elements
    matches = driver.find_elements(By.XPATH, xp)
    if not matches:
        return False

    # click first match
    el = matches[0]
    driver.execute_script("arguments[0].click();", el)
    return True


def dismiss_common_overlays(driver) -> bool:
    # attempt dismiss common cookie modals
    clicked = False

    # click accept button
    clicked = click_first_xpath(
        driver,
        "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'accept')]"
    ) or clicked

    # click agree button
    clicked = click_first_xpath(
        driver,
        "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'agree')]"
    ) or clicked

    # click ok button
    clicked = click_first_xpath(
        driver,
        "//button[normalize-space(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'))='ok']"
    ) or clicked

    return bool(clicked)


# ==================== COOKIES ====================

def has_cookie(driver, cookie_name: str) -> bool:
    # check cookie present
    name = str(cookie_name or "").strip()
    if not name:
        return False

    # read cookie list
    cookies = driver.get_cookies() or []
    for c in cookies:
        # validate cookie type
        if not isinstance(c, dict):
            continue

        # match cookie name
        if str(c.get("name") or "") == name and str(c.get("value") or ""):
            return True

    return False