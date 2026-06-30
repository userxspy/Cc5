import re
import os
import logging
from os import environ

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# 🧠 HELPERS & BOOLEAN PARSERS (RAM Safe)
# ─────────────────────────────────────────────
def is_enabled(key, default=False):
    val = environ.get(key, str(default)).lower()
    if val in ("true", "1", "yes", "y", "enable"): return True
    if val in ("false", "0", "no", "n", "disable"): return False
    logger.error(f"❌ {key} has invalid boolean value")
    exit(1)

def is_valid_ip(ip):
    ip_pattern = (
        r'\b(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.'
        r'(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.'
        r'(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.'
        r'\b(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b'
    )
    return re.match(ip_pattern, ip) is not None

def get_channels(env_var):
    val = environ.get(env_var, "").replace(",", " ").strip()
    if not val: return []
    channels = []
    for token in val.split():
        if token.isnumeric(): channels.append(int(token))
        elif token.startswith("-100") and token[4:].isnumeric(): channels.append(int(token))
        elif token.startswith("-") and token[1:].isnumeric(): channels.append(int(token))
        else: channels.append(token)
    return channels

# ─────────────────────────────────────────────
# ⚙️ CORE TELEGRAM BOT CREDENTIALS
# ─────────────────────────────────────────────
API_ID    = int(environ.get("API_ID", 0))
API_HASH  = environ.get("API_HASH", "").strip()
BOT_TOKEN = environ.get("BOT_TOKEN", "").strip()

if not API_ID or not API_HASH or not BOT_TOKEN:
    logger.error("❌ Critical Bot Credentials (API_ID, API_HASH, BOT_TOKEN) are missing!")
    exit(1)

# ─────────────────────────────────────────────
# 👮‍♂️ ADMINS & LOGGING SETTINGS
# ─────────────────────────────────────────────
ADMINS = [int(x) for x in environ.get("ADMINS", "").replace(",", " ").split() if x.isnumeric()]
if not ADMINS:
    logger.error("❌ ADMINS environment variable is mandatory for Admin-Only mode!")
    exit(1)

LOG_CHANNEL = int(environ.get("LOG_CHANNEL", 0))
BIN_CHANNEL = int(environ.get("BIN_CHANNEL", 0))
if not BIN_CHANNEL:
    logger.error("❌ BIN_CHANNEL variable is required for streaming routing tunnel!")
    exit(1)

# ─────────────────────────────────────────────
# 🗂️ MONGO DATABASE & EXTRA PARAMETERS
# ─────────────────────────────────────────────
DATABASE_URL  = environ.get("DATABASE_URL", "").strip()
DATABASE_NAME = environ.get("DATABASE_NAME", "AutoFilter_Admin_DB").strip()
if not DATABASE_URL:
    logger.error("❌ MongoDB DATABASE_URL missing!")
    exit(1)

TIME_ZONE = environ.get("TIME_ZONE", "Asia/Kolkata").strip()
PICS      = environ.get("PICS", "https://telegra.ph/file/0cbb9b9409849202bdc17.jpg").split()

# ─────────────────────────────────────────────
# 🍿 STREAM & FILE FILTERS CONFIGURATION
# ─────────────────────────────────────────────
PORT                = int(environ.get("PORT", 8000))
IS_STREAM           = is_enabled("IS_STREAM", True)
USE_CAPTION_FILTER  = is_enabled("USE_CAPTION_FILTER", False)
SPELL_CHECK         = is_enabled("SPELL_CHECK", True)

MAX_BOT_RESULTS     = int(environ.get("MAX_BOT_RESULTS", 10))
MAX_WEB_RESULTS     = int(environ.get("MAX_WEB_RESULTS", 20))
MAX_THUMB_CACHE     = int(environ.get("MAX_THUMB_CACHE", 500))

DELETE_TIME         = int(environ.get("DELETE_TIME", 300))       # ग्रुप्स के मैसेजेस के लिए
PM_FILE_DELETE_TIME = int(environ.get("PM_FILE_DELETE_TIME", 0)) # प्राइवेट मैसेज के लिए

THUMBNAIL_STORAGE_CHANNEL = int(environ.get("THUMBNAIL_STORAGE_CHANNEL", BIN_CHANNEL))
ACTOR_STORAGE_CHANNEL     = int(environ.get("ACTOR_STORAGE_CHANNEL", BIN_CHANNEL))

# ─────────────────────────────────────────────
# 🌐 WEB DOMAIN CONTEXT PARSER
# ─────────────────────────────────────────────
URL = environ.get("URL", "").strip()
if not URL:
    logger.error("❌ Web URL environment variable missing")
    exit(1)

if URL.startswith("http://"):
    URL = "https://" + URL[len("http://"):]

if URL.startswith("https://"):
    if not URL.endswith("/"): URL += "/"
elif is_valid_ip(URL):
    URL = f"https://{URL}/"
else:
    if not URL.startswith("https://") and "." in URL:
        URL = "https://" + URL.rstrip("/") + "/"

# ─────────────────────────────────────────────
# 🔐 WEB PANEL CREDENTIALS (INFO.PY SYNC ENGINE)
# ─────────────────────────────────────────────
WEB_USERNAME = environ.get("WEB_USERNAME", "admin").strip()
WEB_PASSWORD = environ.get("WEB_PASSWORD", "admin123").strip()

REACTIONS = environ.get("REACTIONS", "👍 ❤️ 🔥 😍 🤝").split()
