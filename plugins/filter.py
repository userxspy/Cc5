import asyncio
import re
import math
import random
import aiohttp
import logging
import gc
from lru import LRU  
from hydrogram import Client, filters, enums
from hydrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from info import ADMINS, DELETE_TIME, MAX_BOT_RESULTS, PICS, SPELL_CHECK, URL
from utils import get_size, is_check_admin, temp, get_settings, save_group_settings
from database.ia_filterdb import get_search_results
from database.users_chats_db import db
from Script import script  

logger = logging.getLogger(__name__)

# 🧠 LRU RAM MEMOIZATION ENGINE
BUTTONS = LRU(300) 
SRC_TO_SHORT = {"primary": "pri", "cloud": "cld", "archive": "arc", "all": "all"}
SHORT_TO_SRC = {"pri": "primary", "cld": "cloud", "arc": "archive", "all": "all"}

# Active deletion task context map
ACTIVE_DELETE_TASKS = {}

def check_cache_limit():
    """Aggressive cache flushing to keep Koyeb free tier pod safe from memory overhead"""
    if hasattr(temp, "FILES") and len(temp.FILES) > 300:
        temp.FILES.clear()
    gc.collect()

# ─────────────────────────────────────────────────────────
# 🗑️ AUTOMATED GROUP DELETION TIMER RESET PIPELINE
# ─────────────────────────────────────────────────────────
async def start_auto_delete_timer(client, chat_id, message_id):
    """Handles deletion intervals and replaces existing tasks on new triggers"""
    if DELETE_TIME <= 0: 
        return

    # Cancel previous running task for this specific group chat
    if chat_id in ACTIVE_DELETE_TASKS:
        old_task = ACTIVE_DELETE_TASKS[chat_id]
        if old_task and not old_task.done():
            old_task.cancel()

    async def _delete_task():
        try:
            await asyncio.sleep(DELETE_TIME)
            await client.delete_messages(chat_id, message_id)
        except Exception:
            pass
        finally:
            ACTIVE_DELETE_TASKS.pop(chat_id, None)

    task = asyncio.create_task(_delete_task())
    ACTIVE_DELETE_TASKS[chat_id] = task

# ─────────────────────────────────────────────────────────
# 🎛️ UNIVERSAL UI GENERATOR (FILTER INTERFACE BUILDER)
# ─────────────────────────────────────────────────────────
def get_filter_ui(search, files, total, act_src, offset, chat_id, req, key, next_off, is_simple_mode):
    # Cap total pages size
    total_pages = math.ceil(total / MAX_BOT_RESULTS)
    current_page = int(offset / MAX_BOT_RESULTS) + 1

    cap = f"<b>🍿 Fast Finder Results For:</b> <code>{search}</code>\n"
    cap += f"📂 <b>Storage Hub:</b> <code>{act_src.upper()}</code>\n"
    cap += f"📊 <b>Total Files Found:</b> <code>{total:,} Matrix</code>\n\n"

    if is_simple_mode:
        cap += "<b>👇 Click buttons below to watch or download:</b>"
        btn = []
        for file in files:
            f_name = file.get("file_name", "File")
            f_size = get_size(file.get("file_size", 0))
            f_id   = file.get("file_id")
            
            # Button format: Name [Size] linking straight to PM extraction start parameters
            btn.append([InlineKeyboardButton(
                text=f"🎬 {f_name} [{f_size}]",
                url=f"https://t.me/{temp.U_NAME}?start=file_{chat_id}_{f_id}"
            )])
    else:
        # Text List layout mode
        btn = []
        for idx, file in enumerate(files, start=offset + 1):
            f_name = file.get("file_name", "File")
            f_size = get_size(file.get("file_size", 0))
            f_id   = file.get("file_id")
            
            cap += f"<b>{idx}.</b> <a href='https://t.me/{temp.U_NAME}?start=file_{chat_id}_{f_id}'><b>{f_name}</b></a> <code>[{f_size}]</code>\n"
        
        cap += "\n<i>⚠️ Click text links above to pull files from bot core.</i>"

    # Pagination navigation controls engine
    nav_btn = []
    curr_short = SRC_TO_SHORT.get(req, "all")

    if offset > 0:
        prev_off = offset - MAX_BOT_RESULTS
        nav_btn.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"nav#{key}#prev#{prev_off}#{curr_short}"))
    
    if total_pages > 1:
        nav_btn.append(InlineKeyboardButton(f"Page {current_page}/{total_pages}", callback_data="pages_alert"))

    if next_off:
        nav_btn.append(InlineKeyboardButton("Next ➡️", callback_data=f"nav#{key}#next#{next_off}#{curr_short}"))

    if nav_btn:
        btn.append(nav_btn)

    # Core collection filtering switch buttons
    switch_btn = [
        InlineKeyboardButton("📁 All", callback_data=f"nav#{key}#col#0#all"),
        InlineKeyboardButton("🟢 Primary", callback_data=f"nav#{key}#col#0#pri")
    ]
    btn.append(switch_btn)
    btn.append([InlineKeyboardButton("🗑️ Clean Layout Panel", callback_data=f"close_{chat_id}")])

    return cap, InlineKeyboardMarkup(btn)

# ─────────────────────────────────────────────────────────
# 🤖 GROUP SEARCH INCOMING HOOKS
# ─────────────────────────────────────────────────────────
@Client.on_message(filters.group & filters.text & filters.incoming, group=1)
async def group_search(client, message):
    if message.text.startswith(("/", "!", "#")): 
        return
        
    search = message.text.strip()
    if len(search) < 2: 
        return

    # Auto routing collection parameters via group profile configs
    settings = await get_settings(message.chat.id)
    req = settings.get("collection_scope", "all")
    is_simple_mode = settings.get("simple_mode", True)

    files, next_off, total, act_src = await get_search_results(search, MAX_BOT_RESULTS, offset=0, collection_type=req)
    
    if not files:
        if SPELL_CHECK:
            asyncio.create_task(suggest_spellings(client, message, search))
        return

    # Generate a unique session key for LRU tracking map
    key = f"{message.chat.id}_{message.id}"
    BUTTONS[key] = search
    
    if not hasattr(temp, "FILES"): 
        temp.FILES = {}
    temp.FILES[key] = files

    cap, markup = get_filter_ui(search, files, total, act_src, 0, message.chat.id, req, key, next_off, is_simple_mode)
    
    res_msg = await message.reply_text(cap, reply_markup=markup, disable_web_page_preview=True)
    asyncio.create_task(start_auto_delete_timer(client, message.chat.id, res_msg.id))
    check_cache_limit()

# ─────────────────────────────────────────────────────────
# 🍿 PRIVATE PM SEARCH INCOMING HOOKS
# ─────────────────────────────────────────────────────────
@Client.on_message(filters.private & filters.text & filters.incoming)
async def pm_search(client, message):
    if message.text.startswith(("/", "!", "#")): 
        return
        
    search = message.text.strip()
    if len(search) < 2: 
        return

    files, next_off, total, act_src = await get_search_results(search, MAX_BOT_RESULTS, offset=0, collection_type="all")
    
    if not files:
        if SPELL_CHECK:
            asyncio.create_task(suggest_spellings(client, message, search))
        return

    key = f"{message.chat.id}_{message.id}"
    BUTTONS[key] = search
    
    if not hasattr(temp, "FILES"): 
        temp.FILES = {}
    temp.FILES[key] = files

    cap, markup = get_filter_ui(search, files, total, act_src, 0, message.chat.id, "all", key, next_off, is_simple_mode=True)
    await message.reply_text(cap, reply_markup=markup, disable_web_page_preview=True)
    check_cache_limit()

# ─────────────────────────────────────────────────────────
# 🗺️ PAGINATION & ROUTING CALLBACK QUERIES HANDLER
# ─────────────────────────────────────────────────────────
@Client.on_callback_query(filters.regex(r"^nav#"))
async def navigation_callback_handler(client, query):
    tokens = query.data.split("#")
    key     = tokens[1]
    action  = tokens[2]

    search = BUTTONS.get(key)
    if not search: 
        return await query.answer("❌ Search context has expired! Please perform a fresh query search.", show_alert=True)

    offset, coll_short = (int(tokens[3]), tokens[4]) if action in ("next", "prev") else (0, tokens[4])
    coll_type = SHORT_TO_SRC.get(coll_short, "all")

    files, next_off, total, act_src = await get_search_results(search, MAX_BOT_RESULTS, offset, collection_type=coll_type)
    
    if not files:
        err = "❌ No more pages available!" if action in ("next", "prev") else f"❌ No matching entries found inside repository scope: {coll_type.upper()}"
        return await query.answer(err, show_alert=True)

    if not hasattr(temp, "FILES"): 
        temp.FILES = {}
    temp.FILES[key] = files
    
    settings = await get_settings(query.message.chat.id)
    is_simple_mode = settings.get("simple_mode", True)
    
    cap, markup = get_filter_ui(search, files, total, act_src, offset, query.message.chat.id, coll_type, key, next_off, is_simple_mode)

    try: 
        await query.message.edit_text(cap, reply_markup=markup, disable_web_page_preview=True)
        if query.message.chat.type in (enums.ChatType.GROUP, enums.ChatType.SUPERGROUP):
            asyncio.create_task(start_auto_delete_timer(client, query.message.chat.id, query.message.id))
    except Exception:
        pass
    finally:
        await query.answer()

@Client.on_callback_query(filters.regex(r"^pages_alert$"))
async def pages_info_alert(client, query):
    await query.answer("ℹ️ Telemetry UI page status indicator.", show_alert=False)

# ─────────────────────────────────────────────────────────
# 🔎 GOOGLE SPELL COMPACTION ENGINE
# ─────────────────────────────────────────────────────────
async def suggest_spellings(client, message, query):
    """Hits Google Search Completion API to generate 'Did you mean' shortcuts"""
    g_url = f"http://google.com/complete/search?client=chrome&q={aiohttp.helpers.quote_with_fallback(query)}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(g_url, timeout=4) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data and len(data) > 1 and data[1]:
                        s_list = data[1]
                        btn = []
                        for s in s_list[:3]: # Limit top 3 results
                            if s.lower() == query.lower(): 
                                continue
                            btn.append([InlineKeyboardButton(f"🔎 Did you mean: {s}", callback_data=f"spell#{s}")])
                        if btn:
                            btn.append([InlineKeyboardButton("❌ Close", callback_data=f"close_{message.chat.id}")])
                            await message.reply_text(
                                "<b>❌ No assets match found!</b>\n<i>Please check Google alternative corrections below:</i>",
                                reply_markup=InlineKeyboardMarkup(btn)
                            )
    except Exception:
        pass

@Client.on_callback_query(filters.regex(r"^spell#"))
async def spell_query_callback(client, query):
    target_text = query.data.split("#")[1]
    await query.message.delete()
    
    # Fake original user text query behavior
    query.message.text = target_text
    query.message.from_user = query.from_user
    
    if query.message.chat.type == enums.ChatType.PRIVATE:
        await pm_search(client, query.message)
    else:
        await group_search(client, query.message)
