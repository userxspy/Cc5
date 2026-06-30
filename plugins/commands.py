import os
import random
import asyncio
import logging
import time
from hydrogram import Client, filters, enums
from hydrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

from Script import script
from database.ia_filterdb import db_count_documents, get_file_details, delete_files, actors
from database.users_chats_db import db

from info import URL, BIN_CHANNEL, PICS, IS_STREAM, REACTIONS, PM_FILE_DELETE_TIME
from utils import get_settings, get_size, temp, get_readable_time, get_wish

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# 🍿 MINI APP SECURE HTTPS CONVERTOR
# ─────────────────────────────────────────────
def _build_mini_app_url(base_url: str) -> str:
    url = base_url.strip() if base_url else ""
    if not url: 
        return ""
    if url.startswith("http://"):
        url = "https://" + url[len("http://"):]
    if not url.startswith("https://"):
        url = f"https://{url}"
    return f"{url.rstrip('/')}/miniapp"

MINI_APP_URL = _build_mini_app_url(URL)

# ─────────────────────────────────────────────
# 🚀 CORE /start COMMAND & PARAMETER EXTRACTOR
# ─────────────────────────────────────────────
@Client.on_message(filters.command("start") & filters.incoming)
async def start_command_handler(client, message):
    if message.chat.type in (enums.ChatType.GROUP, enums.ChatType.SUPERGROUP):
        return await message.reply(f"<b>Hey {message.from_user.mention}, <i>{get_wish()}</i>\nEngine is fully optimized for this chat group.</b>")

    if REACTIONS:
        try: await message.react(random.choice(REACTIONS), big=True)
        except: pass

    # Start parameter file extraction tunnel (Clicking links from group)
    if len(message.command) > 1:
        try:
            parts = message.command[1].split("_")
            if len(parts) >= 3:
                try: await message.delete()
                except: pass

                grp_id, file_id = int(parts[1]), "_".join(parts[2:])
                file = await get_file_details(file_id)
                if not file: 
                    return await message.reply("<b>❌ File Not Found inside database!</b>")

                settings = await get_settings(grp_id)
                cap_template = settings.get('caption', script.FILE_CAPTION)
                caption = cap_template.format(
                    file_name=str(file.get('file_name', 'File')),
                    file_size=get_size(file.get('file_size', 0))
                )

                btn = [[InlineKeyboardButton('❌ Close File', callback_data=f'close_{message.from_user.id}')]]
                if IS_STREAM:
                    btn.insert(0, [InlineKeyboardButton("▶️ Watch Online / Fast Download", callback_data=f"stream#{file_id}")])

                target_media = file.get('file_ref') or file_id
                msg = await client.send_cached_media(message.chat.id, target_media, caption=caption, reply_markup=InlineKeyboardMarkup(btn))

                # Auto PM deletion guard
                if PM_FILE_DELETE_TIME > 0:
                    del_msg = await msg.reply(f"⚠️ <code>This file will be automatically destroyed in {get_readable_time(PM_FILE_DELETE_TIME)}.</code>")
                    await db.add_to_delete_queue(message.chat.id, msg.id, PM_FILE_DELETE_TIME)
                    await db.add_to_delete_queue(message.chat.id, del_msg.id, PM_FILE_DELETE_TIME)
                return
        except Exception as e:
            logger.error(f"File extraction route failed: {e}")
            return

    # Master Admin main control dock interface
    btn = [
        [InlineKeyboardButton("🍿 Open Mini App (Web Mode)", web_app=WebAppInfo(url=MINI_APP_URL))],
        [InlineKeyboardButton("👮‍♂️ Master Guide", callback_data="admin_cmds"), InlineKeyboardButton("📊 Storage Stats", callback_data="stats")],
        [InlineKeyboardButton("❌ Close Panel", callback_data=f"close_{message.from_user.id}")]
    ]
    await message.reply_photo(
        random.choice(PICS),
        caption=script.START_TXT.format(message.from_user.mention, get_wish()),
        reply_markup=InlineKeyboardMarkup(btn)
    )

# ─────────────────────────────────────────────
# 📊 TELEMETRY DIAGNOSTICS GENERATOR (/stats)
# ─────────────────────────────────────────────
@Client.on_message(filters.command("stats") & filters.incoming)
async def technical_stats_command(client, message):
    msg = await message.reply("🔄 <code>Querying MongoDB Pool... Extracting Core Metadata...</code>")
    await generate_and_render_telemetry(msg, message.from_user.id)

async def generate_and_render_telemetry(msg, user_id):
    try:
        files = await db_count_documents()
        f = files if isinstance(files, dict) else {}

        try:
            tot_dir = await actors.count_documents({})
            app_dir = await actors.count_documents({"category": "app"})
            web_dir = await actors.count_documents({"category": "website"})
            act_dir = tot_dir - app_dir - web_dir
        except Exception:
            tot_dir = app_dir = web_dir = act_dir = 0

        stats_text = script.STATUS_TXT.format(
            get_readable_time(time.time() - temp.START_TIME),
            f.get('total', 0),
            f.get('primary', 0), f.get('primary_thumb', 0),
            f.get('cloud', 0), f.get('cloud_thumb', 0),
            f.get('archive', 0), f.get('archive_thumb', 0),
            tot_dir, act_dir, app_dir, web_dir,
            f.get('total_thumb', 0)
        )

        buttons = [
            [InlineKeyboardButton("🔄 WARMUP SYSTEM POSTERS", callback_data="warmup_trigger_all")],
            [InlineKeyboardButton("⬅️ Return Menu", callback_data="back_start")]
        ]
        await msg.edit(stats_text, reply_markup=InlineKeyboardMarkup(buttons))
    except Exception as ex:
        await msg.edit(f"❌ <b>Database Diagnostics Failed:</b>\n<code>{ex}</code>")

# ─────────────────────────────────────────────
# 🗑️ REPOSITORY PURGE SYSTEM (/delete & /delete_all)
# ─────────────────────────────────────────────
@Client.on_message(filters.command("delete") & filters.incoming)
async def single_delete_command(client, message):
    if len(message.command) < 3:
        return await message.reply("<b>Usage Layout:</b> `/delete primary Avengers.mkv`")
        
    storage = message.command[1].lower()
    if storage not in ["primary", "cloud", "archive"]:
        return await message.reply("❌ <code>Invalid scope! Choose primary, cloud or archive.</code>")

    msg = await message.reply("🗑️ <code>Processing structural data deletion...</code>")
    count = await delete_files(" ".join(message.command[2:]), storage)
    await msg.edit(f"✅ <b>Wiped <code>{count}</code> document nodes successfully from {storage.upper()} collection!</b>")

@Client.on_message(filters.command("delete_all") & filters.incoming)
async def full_wipeout_command(client, message):
    if len(message.command) < 2: 
        return await message.reply("<b>Usage Layout:</b> `/delete_all primary`")
        
    storage = message.command[1].lower()
    if storage not in ["primary", "cloud", "archive"]:
        return await message.reply("❌ <code>Invalid target scope block!</code>")

    await message.reply(
        f"⚠️ <b>CRITICAL WARNING: NUCLEAR WIPEOUT ALERT!</b>\n\nYou are triggering a permanent removal script for ALL documents cached inside <b>{storage.upper()}</b> collection.",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("💥 DESTROY AND PURGE ALL", callback_data=f"confirm_wipeout#{storage}"),
            InlineKeyboardButton("❌ ABORT ACTION", callback_data=f"close_{message.from_user.id}")
        ]])
    )

# ─────────────────────────────────────────────
# 🔗 HIGH-SPEED STREAM PIPELINE TUNNEL (/link)
# ─────────────────────────────────────────────
@Client.on_message(filters.command("link") & filters.incoming)
async def link_stream_generator(client, message):
    media = getattr(message.reply_to_message, 'document', None) or getattr(message.reply_to_message, 'video', None) or getattr(message.reply_to_message, 'audio', None)
    if not media: 
        return await message.reply("❌ <b>Error: Reply to a valid streamable media asset node!</b>", quote=True)

    msg = await message.reply("⏳ <code>Injecting asset into routing streaming tunnel...</code>", quote=True)
    try:
        copied = await message.reply_to_message.copy(BIN_CHANNEL)
        btn = [
            [InlineKeyboardButton("🍿 WATCH ONLINE PLAYER", url=f"{URL}watch/{copied.id}"),
             InlineKeyboardButton("📥 LIGHTNING DOWNLOAD", url=f"{URL}download/{copied.id}")],
            [InlineKeyboardButton("❌ Close Stream", callback_data=f"close_{message.from_user.id}")]
        ]
        await msg.edit_text("<b>⚡ Direct Pipeline Link Matrix Injected Successfully!</b>", reply_markup=InlineKeyboardMarkup(btn))
    except Exception as e:
        await msg.edit_text(f"❌ <b>Tunnel Binding Error:</b> <code>{e}</code>")

# ─────────────────────────────────────────────
# 🎛️ DOCK CALLBACKS INTERFACES
# ─────────────────────────────────────────────
@Client.on_callback_query(filters.regex(r"^(admin_cmds|stats|back_start)$"))
async def docking_callback_router(client, query):
    data = query.data
    text, buttons_markup = "", None

    if data == "back_start":
        text = script.START_TXT.format(query.from_user.mention, get_wish())
        btn = [
            [InlineKeyboardButton("🍿 Open Mini App (Web Mode)", web_app=WebAppInfo(url=MINI_APP_URL))],
            [InlineKeyboardButton("👮‍♂️ Master Guide", callback_data="admin_cmds"), InlineKeyboardButton("📊 Storage Stats", callback_data="stats")],
            [InlineKeyboardButton("❌ Close Panel", callback_data=f"close_{query.from_user.id}")]
        ]
        buttons_markup = InlineKeyboardMarkup(btn)
    elif data == "admin_cmds":
        text = script.ADMIN_COMMAND_TXT
        buttons_markup = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back Menu", callback_data="back_start")]])
    elif data == "stats":
        return await generate_and_render_telemetry(query.message, query.from_user.id)

    try: 
        await query.message.edit_caption(caption=text, reply_markup=buttons_markup)
    except Exception:
        try: await query.message.edit_text(text=text, reply_markup=buttons_markup)
        except Exception: pass

@Client.on_callback_query(filters.regex(r"^confirm_wipeout#"))
async def collection_purge_callback_executor(client, query):
    storage = query.data.split("#")[1]
    await query.message.edit(f"🗑️ <code>Executing data collection wipeout on {storage.upper()}... Stand by.</code>")
    count = await delete_files("*", storage)
    await query.message.edit(f"✅ <b>Collection Purged! Flushed `{count}` entries from `{storage.upper()}` repository.</b>")

@Client.on_callback_query(filters.regex(r"^stream#"))
async def streaming_tunnel_callback_handler(client, query):
    file_id = query.data.split("#")[1]
    await query.answer("🔗 Connecting stream tunnel nodes...", show_alert=False)
    try:
        file = await get_file_details(file_id)
        if not file: 
            return await query.answer("❌ Asset metadata node broken inside database!", show_alert=True)
            
        target_media = file.get('file_ref') or file_id
        msg = await client.send_cached_media(BIN_CHANNEL, target_media)
        btn = [
            [InlineKeyboardButton("🎬 Stream Online Player", url=f"{URL}watch/{msg.id}"),
             InlineKeyboardButton("⚡ Download Asset File", url=f"{URL}download/{msg.id}")],
            [InlineKeyboardButton("❌ Close Panel", callback_data=f"close_{query.from_user.id}")]
        ]
        await query.message.edit_reply_markup(InlineKeyboardMarkup(btn))
    except Exception as e:
        await query.answer(f"Error: {e}", show_alert=True)
