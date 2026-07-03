"""
centralize source configuration
define source settings and feeds
"""

from backend.configuration.paths import COMMONCRAWL_INDICES_PATH
from backend.helpers.persist.json_utils import load_json


# ==================== SOURCE SETTINGS ====================

# centralized user agent for all http requests
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"  # default browser ua

# user agent with app identification for apis
USER_AGENT_BOT = "company_profiler/1.3.1 (Business Intelligence Research; https://github.com/marifirfanibrahim/company_profiler)"  # default bot ua


# ==================== RSS FEED CONFIGURATIONS ====================

RSS_SOURCES = {
    'news_feeds': {
        'name': 'News Feeds',
        'feeds': [
            # general
            'https://www.thestar.com.my/rss/news/nation',
            'https://www.malaymail.com/feed/rss/malaysia',
            'https://www.nst.com.my/rss/news',
            'https://themalaysianreserve.com/feed/',
            'https://theedgemalaysia.com/rss/latest',
            'https://theedgemalaysia.com/rss/malaysia',
            'https://www.freemalaysiatoday.com/category/nation/feed/',
            'https://www.malaysiakini.com/rss/en/news',
            'https://www.bernama.com/en/rss.php',
            'https://www.therakyatpost.com/feed/',
            'https://www.sinarharian.com.my/rss',

            # additional malaysia sites
            'https://www.bharian.com.my/rss.xml',
            'https://www.hmetro.com.my/feed',
            'https://www.utusan.com.my/feed/',
            'https://www.kosmo.com.my/feed/',
            'https://www.astroawani.com/rss/latest/public.xml',

            # business & economy
            'https://www.thestar.com.my/rss/business',
            'https://theedgemalaysia.com/rss/business',
            'https://www.bernama.com/en/rss.php?cat=business',
            'https://www.freemalaysiatoday.com/category/business/feed/',

            # politics & opinion
            'https://www.sinarharian.com.my/rss/politik',
            'https://www.malaymail.com/feed/rss/opinion',
            'https://www.malaysiakini.com/rss/en/columns',

            # sports & lifestyle
            'https://www.nst.com.my/rss/sports',

            # regional / international
            'https://www.thestar.com.my/rss/news/world',
            'https://www.channelnewsasia.com/rssfeeds/8395986',
            'https://www.scmp.com/rss/91/feed'
        ]
    },
    'google_news': {
        'name': 'Google News',
        'feeds': [
            # general
            'https://news.google.com/rss/search?q=malaysia&hl=en-MY&gl=MY&ceid=MY:en',

            # politics & governance
            'https://news.google.com/rss/search?q=malaysia+politics&hl=en-MY&gl=MY&ceid=MY:en',

            # economy & business
            'https://news.google.com/rss/search?q=malaysia+economy&hl=en-MY&gl=MY&ceid=MY:en&ceid=MY:en',
            'https://news.google.com/rss/search?q=malaysia+business&hl=en-MY&gl=MY&ceid=MY:en',

            # sports & entertainment
            'https://news.google.com/rss/search?q=malaysia+sports&hl=en-MY&gl=MY&ceid=MY:en',

            # technology & innovation
            'https://news.google.com/rss/search?q=malaysia+technology&hl=en-MY&gl=MY&ceid=MY:en',

            # health & education
            'https://news.google.com/rss/search?q=malaysia+health&hl=en-MY&gl=MY&ceid=MY:en',
            'https://news.google.com/rss/search?q=malaysia+education&hl=en-MY&gl=MY&ceid=MY:en',

            # environment & society
            'https://news.google.com/rss/search?q=malaysia+environment&hl=en-MY&gl=MY&ceid=MY:en',
            'https://news.google.com/rss/search?q=malaysia+environment&hl=en-MY&gl=MY&ceid=MY:en',
            'https://news.google.com/rss/search?q=malaysia+crime&hl=en-MY&gl=MY&ceid=MY:en',
            'https://news.google.com/rss/search?q=malaysia+travel&hl=en-MY&gl=MY&ceid=MY:en',
            'https://news.google.com/rss/search?q=malaysia+culture&hl=en-MY&gl=MY&ceid=MY:en'
        ]
    }
}


# ==================== OFFICIAL CASE DOMAINS ====================

OFFICIAL_CASE_DOMAINS = [
    # police and anti corruption
    "rmp.gov.my",
    "pdrm.gov.my",
    "sprm.gov.my",

    # financial and capital markets regulators
    "bnm.gov.my",
    "sc.com.my",
    "bursamalaysia.com",

    # legal and courts
    "agc.gov.my",
    "judiciary.gov.my",
    "kehakiman.gov.my"
]


# ==================== OFFICIAL CASE SOURCES ====================

OFFICIAL_CASE_SOURCES = [
    "Bank Negara Malaysia",
    "Securities Commission Malaysia",
    "Bursa Malaysia",
    "Bursa Disclosure",
    "Malaysian Anti Corruption Commission",
    "Royal Malaysia Police",
    "Attorney General Chambers",
    "Malaysian Judiciary",
    "Laws of Malaysia (AGC LOM)"
]


# ==================== RAM ====================

RAM_RATINGS_BASE_URL = "https://www.ram.com.my"                      # default ram base url
RAM_RATINGS_SEARCH_URL_TEMPLATE = "https://www.ram.com.my/search?key={query}"  # default ram search
RAM_RATINGS_MAX_RESULTS = 10                                         # default 10

RAM_RATINGS_SCRIPT_PATH = "/script/"                                 # default /script/
RAM_RATINGS_SCRIPT_HTML_PARAM = "html"                               # default html
RAM_RATINGS_SCRIPT_OSP = 221                                         # default 221
RAM_RATINGS_SCRIPT_TYPE = "osp"                                      # default osp
RAM_RATINGS_SCRIPT_CATID = 161                                       # default 161
RAM_RATINGS_SCRIPT_PAGE_PARAM = "page"                               # default page
RAM_RATINGS_SCRIPT_SEARCH_PARAM = "search"                           # default search
RAM_RATINGS_SCRIPT_OSPTYPE_PARAM = "osptype"                         # default osptype
RAM_RATINGS_SCRIPT_MAX_PAGES = 3                                     # default 3

RAM_RATINGS_SCRIPT_OSPTYPES = [                                      # default list
    "list-ratingannouncement",
    "list-publicationpr",
    "list-sustainabilitypr",
    "list-publication",
    "list-training",
    "list-webcontent",
]


# ==================== MARC ====================

MARC_RATINGS_BASE_URL = "https://www.marc.com.my"                    # default marc base url
MARC_RATINGS_SEARCH_URL_TEMPLATE = "https://www.marc.com.my/?s={query}"        # default marc search
MARC_RATINGS_MAX_RESULTS = 10                                        # default 10

MARC_RATINGS_QUERY_TOKEN_MIN_LENGTH = 3                              # default 3
MARC_RATINGS_MIN_QUERY_MATCHES = 1                                   # default 1
MARC_RATINGS_ALLOW_PREFIX_MATCH = True                               # default true
MARC_RATINGS_DROP_QUERY_TOKENS = [                                   # default token drops
    "berhad",
    "bhd",
    "sdn",
    "malaysia",
]


# ==================== COMMON CRAWL CONFIGURATIONS ====================

_loaded_indices = load_json(COMMONCRAWL_INDICES_PATH, default=[])     # load indices list

if isinstance(_loaded_indices, list):
    COMMONCRAWL_INDICES = [str(x).strip() for x in _loaded_indices if isinstance(x, str) and str(x).strip()]  # normalized indices
else:
    COMMONCRAWL_INDICES = []                                          # empty indices

COMMONCRAWL_INDEX_URL = "http://index.commoncrawl.org/{crawl_id}-index"  # index api url
COMMONCRAWL_S3_BASE = "https://data.commoncrawl.org"                  # s3 base url

COMMONCRAWL_TARGET_DOMAINS = [
    # malaysian news
    "thestar.com.my",
    "malaymail.com",
    "nst.com.my",
    "bernama.com",
    "theedgemalaysia.com",
    "freemalaysiatoday.com",
    "malaysiakini.com",
    "themalaysianreserve.com",
    "sinarharian.com.my",
    "theedgemarkets.com",
    "focusmalaysia.my",
    "therakyatpost.com",

    # additional malaysia sites
    "bharian.com.my",
    "hmetro.com.my",
    "utusan.com.my",
    "kosmo.com.my",
    "astroawani.com",

    # companies and regulators
    "bnm.gov.my",
    "sc.com.my",
    "bursamalaysia.com",
    "disclosure.bursamalaysia.com",
    "mof.gov.my",
    "miti.gov.my",
    "malaysia.gov.my",
    "treasury.gov.my",
    "dosm.gov.my",

    # rating and research sites
    "ram.com.my",
    "marc.com.my",

    # official case and enforcement sites
    "rmp.gov.my",
    "pdrm.gov.my",
    "sprm.gov.my",
    "agc.gov.my",
    "judiciary.gov.my",
    "kehakiman.gov.my",

    # international with malaysia coverage
    "reuters.com",
    "bloomberg.com",
    "scmp.com",
    "channelnewsasia.com",
    "ft.com",
    "wsj.com",
    "nikkei.com"
]