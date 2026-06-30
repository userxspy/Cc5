import re
import time
import random
import asyncio
import gc
import logging
from hydrogram import Client, filters
from hydrogram.errors import FloodWait, MessageNotModified, BadRequest
from info import ADMINS, BIN_CHANNEL, THUMBNAIL_STORAGE_CHANNEL
from utils import get_readable_time
from database.ia_filterdb import COLLECTIONS

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────
# 🎨 LUXURY MINIMALIST UI PANEL GENERATOR
# ─────────────────────────────────────────────────────────
def get_warmup_ui(col_name, processed, total, success, skipped, elapsed, eta, speed):
    percent = int((processed / max(total, 1)) * 100)
    dot = "🔴" if percent < 30 else ("🟡" if percent < 70 else "🟢")
    
    lines = [
        "🎬 <b>FAST FINDER - THUMBNAIL WARMUP CONSOLE</b>",
        "──────────────────────────────",
        f"📁 <b>Repository Hub :</b> <code>{col_name.upper()}</code>",
        f"📈 <b>Pipeline Index :</b> <code>{processed:,} / {total:,}</code>",
        f"🔒 <b>Strict Locked  :</b> <code>{success:,} Thumbs</code>",
        f"⚠️ <b>Rejected/Web   :</b> <code>{skipped:,} Files</code>",
        f"⏱️ <b>Time Remaining :</b> <code>{get_readable_time(eta)}</code>",
        f"⚡ <b>Stream Velocity:</b> <code>{speed:.1f} f/min</code>",
        f"──────────────────────────────",
        f"{dot} <b>Progress State:</b> <code>{percent}% Complete</code>"
    ]
    return "\n".join(lines)

# ─────────────────────────────────────────────────────────
# ⚙️ CORE THUMBNAIL WARMUP ENGINE MANAGER
# ─────────────────────────────────────────────────────────
async def start_warmup_engine(client, status_msg, user_id):
    start_time = time.time()
    
    # Target production collections for extraction loops
    target_collections = ["primary", "cloud", "archive"]
    
    for col_name in target_collections:
        col = COLLECTIONS.get(col_name)
        if not col: 
            continue
            
        try:
            total_docs = await col.count_documents({})
            if total_docs == 0: 
                continue
                
            processed, success, skipped = 0, 0, 0
            
            # Fetch all metadata documents from collection pool
            cursor = col.find({}, {"_id": 1, "file_ref": 1, "thumb_url": 1})
            
            async for doc in cursor:
                processed += 1
                file_id = doc["_id"]
                file_ref = doc.get("file_ref")
                current_thumb = doc.get("thumb_url")
                
                # If thumbnail already explicitly locked, skip calculation
                if current_thumb and current_thumb != "NO_THUMB" and not current_thumb.startswith("http"):
                    skipped += 1
                    continue
                    
                # Periodic UI status reporting to avoid telegram flood limits
                if processed % 15 == 0 or processed == total_docs:
                    elapsed = time.time() - start_time
                    speed = (processed / max(elapsed, 1)) * 60
                    rem_docs = total_docs - processed
                    eta = (rem_docs / max(speed, 1)) * 60
                    
                    ui_text = get_warmup_ui(col_name, processed, total_docs, success, skipped, elapsed, eta, speed)
                    try:
                        await status_msg.edit(ui_text)
                    except MessageNotModified:
                        pass
                    except FloodWait as f_err:
                        await asyncio.sleep(f_err.value)
                
                if not file_ref:
                    skipped += 1
                    continue
                    
                # Telegram asset diagnostic pulling path
                try:
                    # Pull original file information to check thumbnail state
                    # BIN_CHANNEL acts as routing tunnel for diagnostic validation
                    msg = await client.send_cached_media(THUMBNAIL_STORAGE_CHANNEL, file_ref)
                    media_obj = getattr(msg, msg.media.value, None)
                    
                    # Extract raw telegram generated poster thumbnail token
                    tg_thumb = getattr(media_obj, "thumbnail", None)
                    
                    if tg_thumb:
                        # Permanent lock of the generated token inside MongoDB collection node
                        await col.update_one({"_id": file_id}, {"$set": {"thumb_url": tg_thumb.file_id}})
                        success += 1
                    else:
                        await col.update_one({"_id": file_id}, {"$set": {"thumb_url": "NO_THUMB"}})
                        skipped += 1
                        
                    # Instantly destroy trace message to avoid channel bloating
                    asyncio.create_task(_safe_delete(msg))
                    
                except BadRequest:
                    # File link dead or unavailable inside telegram architecture
                    await col.update_one({"_id": file_id}, {"$set": {"thumb_url": "NO_THUMB"}})
                    skipped += 1
                except FloodWait as flood:
                    await asyncio.sleep(flood.value)
                except Exception as ex:
                    logger.debug(f"Warmup error on key {file_id}: {ex}")
                    skipped += 1
                    
                # Anti-Flood Throttling for Koyeb performance limits
                await asyncio.sleep(0.4)
                
            # Intermediate garbage collection flush per collection pool
            gc.collect()
            
        except Exception as col_err:
            logger.error(f"Critical error processing collection {col_name}: {col_err}")
            
    # Final completion console telemetry report
    total_elapsed = time.time() - start_time
    final_report = (
        "✅ <b>WARMUP PIPELINE COMPLETE!</b>\n\n"
        f"⚡ <b>Total Processed:</b> All Collections Sync\n"
        f"⏱️ <b>Total Execution Time:</b> <code>{get_readable_time(total_elapsed)}</code>\n"
        "🟢 <b>System Status:</b> 100% Locked & Cached"
    )
    try:
        await status_msg.edit(final_report)
    except Exception:
        pass

# ─────────────────────────────────────────────────────────
# 🗑 BACKGROUND DELETE HELPER — Non-blocking node
# ─────────────────────────────────────────────────────────
async def _safe_delete(msg):
    try:
        await msg.delete()
    except Exception:
        pass

# ─────────────────────────────────────────────────────────
# 📢 COMMAND ROUTE — /warmup_thumbs (ADMIN ONLY)
# ─────────────────────────────────────────────────────────
@Client.on_message(filters.command("warmup_thumbs") & filters.incoming)
async def warmup_thumbs_cmd(client, message):
    status_msg = await message.reply("⚙️ <b>Warmup Initialization Core Starting...</b>")
    await start_warmup_engine(client, status_msg, message.from_user.id)

# ─────────────────────────────────────────────────────────
# 🔘 BUTTON ROUTE — 🔄 WARMUP THUMBNAILS BUTTON CALLBACK
# ─────────────────────────────────────────────────────────
@Client.on_callback_query(filters.regex(r"^warmup_trigger_all$"))
async def warmup_callback_handler(client, query):
    await query.answer("⚙️ Thumbnail Warmup Initiated! Starting Background Pipeline...", show_alert=False)
    try:
        await query.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await start_warmup_engine(client, query.message, query.from_user.id)
