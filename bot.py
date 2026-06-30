import logging
import asyncio
import signal
import os
import time
import sys
import gc
from typing import Union, AsyncGenerator
from datetime import datetime
import pytz

# ==========================================================
# 🔥 UVLOOP (High Performance C-Based Event Loop Engine)
# ==========================================================
try:
    import uvloop
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
except ImportError:
    pass

# ==========================================================
# 📊 LOGGING CENTER
# ==========================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logging.getLogger('hydrogram').setLevel(logging.ERROR)
logging.getLogger('aiohttp.access').setLevel(logging.WARNING)
logging.getLogger('aiohttp.server').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# ==========================================================
# CORE IMPORTS
# ==========================================================
from aiohttp import web
from hydrogram import Client, types, StopPropagation, idle, enums
from hydrogram.errors import FloodWait 
from hydrogram.handlers import MessageHandler, CallbackQueryHandler
from web import web_app
from info import (
    API_ID, API_HASH, BOT_TOKEN, PORT, ADMINS, 
    LOG_CHANNEL, TIME_ZONE
)
from utils import temp
from database.users_chats_db import db
from database.ia_filterdb import ensure_indexes

# ==========================================================
# 🛠️ HEALTH CHECK ENDPOINT (Koyeb Dynamic Health Check OK)
# ==========================================================
routes = web.RouteTableDef()

@routes.get("/health")
async def health_check(request):
    uptime = time.time() - temp.START_TIME
    return web.json_response({"status": "healthy", "uptime": f"{uptime:.2f}s"})

# ==========================================================
# ⏳ SMART AUTO-DELETE BACKGROUND WORKER (RAM Protected)
# ==========================================================
async def auto_delete_worker(bot):
    """Restart-proof MongoDB based auto-delete engine with strict memory flush"""
    while True:
        try:
            cursor = await db.get_expired_delete_tasks()
            deleted_any = False
            
            async for task in cursor:
                chat_id = task["chat_id"]
                message_id = task["message_id"]
                
                try:
                    await bot.delete_messages(chat_id, message_id)
                    deleted_any = True
                except Exception as tg_err:
                    logger.debug(f"Message already deleted or unavailable in {chat_id}: {tg_err}")
                
                await db.remove_from_delete_queue(chat_id, message_id)
            
            if deleted_any:
                gc.collect()
                
        except Exception as e:
            logger.error(f"Error in auto_delete_worker loop: {e}")
            
        await asyncio.sleep(15)

# ==========================================================
# 🛡️ MASTER GATEKEEPER MIDDLEWARE (STRICT ADMIN ONLY LOCK)
# ==========================================================
async def master_message_gatekeeper(client, message):
    user_id = message.from_user.id if message.from_user else None
    if user_id not in ADMINS:
        if message.chat.type == enums.ChatType.PRIVATE:
            try:
                await message.reply_text("<b>❌ Access Denied! This is a strict Admin-Only authorized bot instance.</b>")
            except:
                pass
        raise StopPropagation

async def master_callback_gatekeeper(client, query):
    if query.from_user.id not in ADMINS:
        try:
            await query.answer("❌ Unauthorized Access! This bot is restricted to Admin only.", show_alert=True)
        except:
            pass
        raise StopPropagation

# ==========================================================
# BOT CLIENT CLASS
# ==========================================================
class Bot(Client):
    def __init__(self):
        super().__init__(
            name="Auto_Filter_Bot",
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN,
            plugins={"root": "plugins"}
        )
        self._runner = None 
        self._delete_task = None  

    async def start(self):
        # 1. Start Pyrogram/Hydrogram Client Instance
        await super().start()
        temp.START_TIME = time.time()

        # 2. Database Indexes Sync (Makkhan DB Tuning)
        await ensure_indexes()
        await db._ensure_indexes() 
        logger.info("✅ Database Connections & Indexes Fully Synced")

        # 3. Register Explicit Master Gatekeepers at Top Group Priority (-1)
        self.add_handler(MessageHandler(master_message_gatekeeper), group=-1)
        self.add_handler(CallbackQueryHandler(master_callback_gatekeeper), group=-1)
        logger.info("🛡️ Master Admin-Only Security Guard Activated")

        # 4. Persistent Hard Restart Logic Sync
        if os.path.exists("restart.txt"):
            try:
                with open("restart.txt", "r") as f:
                    content = f.read().strip().split()
                    if len(content) == 2:
                        chat_id, msg_id = map(int, content)
                        await self.edit_message_text(chat_id=chat_id, message_id=msg_id, text="<b>✅ Admin Engine Session Rebuilt & Active!</b>")
            except Exception as e:
                logger.error(f"Restart message error: {e}")
            finally:
                try: os.remove("restart.txt")
                except: pass

        # 5. Set Centralized Context Registry Identity
        temp.BOT = self
        me = await self.get_me()
        temp.ME = me.id
        temp.U_NAME = me.username
        temp.B_NAME = me.first_name

        # 6. Start Web Server with Health Routes
        web_app.add_routes(routes)
        self._runner = web.AppRunner(web_app, access_log=None)
        await self._runner.setup()
        await web.TCPSite(self._runner, "0.0.0.0", PORT).start()
        logger.info(f"🌐 Web Server Control Panel Live on Port {PORT}")

        # 7. Start Background Automation Tasks
        self._delete_task = asyncio.create_task(auto_delete_worker(self)) 
        logger.info("⏳ Persistent Auto-Delete RAM Guard Activated")

        # 8. Send Startup Logs (Perfect info.py TIME_ZONE Sync)
        local_tz = pytz.timezone(TIME_ZONE)
        now = datetime.now(local_tz)
        startup_msg = (
            f"🤖 <b>Fast Finder Admin Engine Online!</b>\n\n"
            f"📅 <b>Date:</b> {now.strftime('%d %B %Y')}\n"
            f"🕐 <b>Time:</b> {now.strftime('%I:%M:%S %p')}\n"
            f"🌏 <b>Timezone:</b> {TIME_ZONE}\n"
            f"🛡️ <b>Security Mode:</b> 100% Strict Admin Lock\n"
            f"⚡ <b>Performance Engine:</b> uvloop + Motor Mode"
        )

        async def _safe_send(admin_id):
            try:
                await self.send_message(admin_id, startup_msg)
            except FloodWait as e:
                await asyncio.sleep(e.value)
                await self.send_message(admin_id, startup_msg)
            except Exception:
                pass

        await asyncio.gather(*[_safe_send(aid) for aid in ADMINS])

        if LOG_CHANNEL:
            try:
                await self.send_message(LOG_CHANNEL, f"<b>⚡ {me.mention} System Fully Synced & Restricted on {TIME_ZONE}! 🚀</b>")
            except Exception as e:
                logger.warning(f"Failed to send log to LOG_CHANNEL: {e}")

        logger.info(f"@{me.username} is Smoothly Operational!")

    # ✅ GRACEFUL SHUTDOWN (Protects Database Pools & Containers)
    async def stop(self, *args):
        logger.info("Initiating Graceful Shutdown Pipeline...")
        
        if getattr(self, '_runner', None):
            await self._runner.cleanup()
            logger.info("✅ Web App Runner Cleaned Up")

        if getattr(self, '_delete_task', None):
            self._delete_task.cancel()
            try: await self._delete_task
            except asyncio.CancelledError: pass
            logger.info("✅ Auto-Delete Engine Flushed & Stopped")

        await super().stop()
        logger.info("System Halted Gracefully. All Memory Freed ✅")

    async def iter_messages(self, chat_id: Union[int, str], limit: int, offset: int = 0) -> AsyncGenerator["types.Message", None]:
        current = offset
        while current < limit:
            diff = min(200, limit - current)
            try:
                messages = await self.get_messages(chat_id, list(range(current, current + diff)))
                for message in messages:
                    if message and not message.empty: 
                        yield message
                current += diff
            except Exception as e:
                logger.error(f"Error fetching messages: {e}")
                return

# ==========================================================
# KICKSTART LIFE-CYCLE LOOP
# ==========================================================
async def main():
    bot = Bot()
    
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, lambda: asyncio.create_task(bot.stop()))
        except NotImplementedError:
            pass 
            
    await bot.start()
    await idle()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Process Interrupted Externally.")
