"""
bursa config
html endpoints
params and limits
selenium settings
api settings
challenge settings
backfill settings
"""

from backend.configuration.paths import SELENIUM_PROFILE_PATH


# ==================== BASE URLS ====================

BURSA_BASE_URL = "https://www.bursamalaysia.com"                    # default bursa base url


# ==================== PATHS ====================

BURSA_COMPANY_ANNOUNCEMENTS_PATH = "/market_information/announcements/company_announcement"  # default listing path
BURSA_ANNOUNCEMENT_DETAILS_PATH = "/market_information/announcements/company_announcement/announcement_details"  # default detail path
BURSA_API_SEARCH_PATH = "/api/v1/announcements/search"              # default api search path


# ==================== PARAMS ====================

BURSA_COMPANY_PARAM = "company"                                     # default company code param
BURSA_ANN_ID_PARAM = "ann_id"                                       # default announcement id param


# ==================== LIMITS ====================

BURSA_MAX_ATTACHMENT_URLS = 20                                      # default 20
BURSA_MAX_RESULTS = 40                                              # default 12


# ==================== API ====================

BURSA_API_ANN_TYPE_PARAM = "ann_type"                               # default ann_type
BURSA_API_ANN_TYPE_VALUE = "company"                                # default company
BURSA_API_PER_PAGE_PARAM = "per_page"                               # default per_page
BURSA_API_PAGE_PARAM = "page"                                       # default page
BURSA_API_PER_PAGE = 20                                             # default 20
BURSA_API_MAX_PAGES = 2                                             # default 2


# ==================== BACKFILL ====================

BURSA_BACKFILL_ENABLED = True                                       # default true
BURSA_BACKFILL_PAGES_PER_RUN = 2                                    # default 2
BURSA_BACKFILL_AFTER_DONE_PAGES_PER_RUN = 1                         # default 1
BURSA_BACKFILL_RESET_OFFSET_ON_DONE = True                          # default true


# ==================== SELENIUM ====================

BURSA_SELENIUM_HEADLESS = False                                     # default false
BURSA_SELENIUM_PAGE_LOAD_TIMEOUT = 45                               # default 45
BURSA_SELENIUM_PAGE_LOAD_STRATEGY = "eager"                         # default eager
BURSA_SELENIUM_WAIT_SECONDS = 25                                    # default 25
BURSA_SELENIUM_WAIT_POLL_SECONDS = 0.5                              # default 0.5
BURSA_SELENIUM_LISTING_WAIT_CSS = "body"                            # default body
BURSA_SELENIUM_DETAIL_WAIT_CSS = "body"                             # default body
BURSA_SELENIUM_WINDOW_WIDTH = 1400                                  # default 1400
BURSA_SELENIUM_WINDOW_HEIGHT = 900                                  # default 900
BURSA_SELENIUM_SCROLL_ENABLED = True                                # default true
BURSA_SELENIUM_SCROLL_STEPS = 2                                     # default 2
BURSA_SELENIUM_SCROLL_SLEEP_SECONDS = 1.0                           # default 1.0
BURSA_SELENIUM_USE_PROFILE = True                                   # default true
BURSA_SELENIUM_USER_DATA_DIR = str(SELENIUM_PROFILE_PATH)           # default stores selenium_profile
BURSA_SELENIUM_PROFILE_DIR = "Default"                              # default Default
BURSA_SELENIUM_CHROME_ARGS = [                                      # default chrome args
    "--disable-blink-features=AutomationControlled",
    "--disable-background-networking",
    "--disable-default-apps",
    "--disable-extensions",
    "--disable-sync",
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-software-rasterizer",
    "--disable-features=VizDisplayCompositor",
    "--log-level=3",
]


# ==================== CHALLENGE ====================

BURSA_CHALLENGE_WAIT_SECONDS = 180                                  # default 180
BURSA_CHALLENGE_POLL_SECONDS = 1.0                                  # default 1.0
BURSA_CHALLENGE_SUCCESS_COOKIE = "cf_clearance"                     # default cf_clearance
BURSA_CHALLENGE_SUCCESS_SUBSTRING = "announcement_details"           # default announcement_details