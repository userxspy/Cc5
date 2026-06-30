import logging
import asyncio
import re
import time
import gc
import pytz
from datetime import datetime, timedelta
from hydrogram.errors import FloodWait
from hydrogram import enums

from info import ADMINS, TIME_ZONE
from database.users_chats_db import db

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# 🧠 TEMP RUNTIME STORAGE (Central Context Registry)
# ─────────────────────────────────────────────
class temp(object):
    START_TIME = 0
    ME, BOT, U_NAME, B_NAME = None, None, None, None
    CANCEL = False 
    SETTINGS_CACHE = {}  # Dynamic RAM Cache for Group Settings
    PM_FILES = {}        # Track messages for automated deletion queue

# ─────────────────────────────────────────────
# ⚙️ GROUP SETTINGS TTL CACHE (Koyeb Zero-COLLSCAN Guard)
# ─────────────────────────────────────────────
async def get_settings(chat_id):
    """Fetches group settings from RAM cache or MongoDB with 5-minute TTL"""
    now = time.time()
    if chat_id in temp.SETTINGS_CACHE:
        cache_data, expiry = temp.SETTINGS_CACHE[chat_id]
        if now < expiry:
            return cache_data

    # Cache miss - Fetch directly from MongoDB Settings Collection
    try:
        settings = await db.settings.find_one({'id': chat_id})
        if not settings:
            # Default production fallback settings
            settings = {
                'id': chat_id,
                'caption': "",
                'simple_mode': True,
                'auto_delete': True
            }
            await db.settings.insert_one(settings)
            
        # Lock into RAM Cache for exactly 5 minutes (300 seconds)
        temp.SETTINGS_CACHE[chat_id] = (settings, now + 300)
        return settings
    except Exception as e:
        logger.error(f"Error in get_settings pipeline: {e}")
        return {'id': chat_id, 'caption': "", 'simple_mode': True, 'auto_delete': True}

async def save_group_settings(chat_id, settings_dict):
    """Updates MongoDB and immediately syncs the local RAM cache"""
    try:
        await db.settings.update_one({'id': chat_id}, {'$set': settings_dict}, upsert=True)
        temp.SETTINGS_CACHE[chat_id] = (settings_dict, time.time() + 300)
        return True
    except Exception as e:
        logger.error(f"Error saving group settings: {e}")
        return False

# ─────────────────────────────────────────────
# 👮‍♂️ TECHNICAL ADMIN PERMISSION CHECKER
# ─────────────────────────────────────────────
async def is_check_admin(client, chat_id, user_id):
    """Validates if a user has core deletion/admin permissions in a group"""
    if user_id in ADMINS: 
        return True
    try:
        member = await client.get_chat_member(chat_id, user_id)
        return member.status in (enums.ChatMemberStatus.OWNER, enums.ChatMemberStatus.ADMINISTRATOR)
    except Exception:
        return False

# ─────────────────────────────────────────────
# 📊 DATA PARSERS & STRING CONVERTERS
# ─────────────────────────────────────────────
def get_size(size):
    """Converts raw bytes into human readable format (MB, GB)"""
    if not size: 
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    size = float(size)
    while size >= 1024 and i < 4:
        size, i = size / 1024, i + 1
    return f"{size:.2f} {units[i]}"

def get_readable_time(seconds):
    """Converts seconds into formatted string layout (e.g. 2d 5h 10m)"""
    res, periods = "", [('d', 86400), ('h', 3600), ('m', 60), ('s', 1)]
    for name, sec in periods:
        if seconds >= sec:
            val, seconds = divmod(seconds, sec)
            res += f"{int(val)}{name} "
    return res.strip() or "0s"

def get_wish():
    """Generates localized day greeting based on info.py TIME_ZONE settings"""
    tz = pytz.timezone(TIME_ZONE)
    h = datetime.now(tz).hour
    return "ɢᴏᴏᴅ ᴍᴏʀɴɪɴɢ 🌞" if h < 12 else "ɢᴏᴏᴅ ᴀꜰᴛᴇʀɴᴏᴏɴ 🌗" if h < 18 else "ɢᴏᴏᴅ ᴇᴠᴇɴɪɴɢ 🌘"

async def get_seconds(time_string):
    """Parses time strings like '5m' or '2h' into exact absolute seconds"""
    match = re.match(r"(\d+)(s|min|hour|day|month|year)", time_string.strip().lower())
    if not match: 
        return 0
    value = int(match.group(1))
    unit = match.group(2)
    
    return value * {
        "s": 1, 
        "min": 60, 
        "hour": 3600, 
        "day": 86400, 
        "month": 2592000, 
        "year": 31536000
    }.get(unit, 0)
