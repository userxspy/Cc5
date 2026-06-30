import logging
from datetime import datetime, timedelta
import pytz
from motor.motor_asyncio import AsyncIOMotorClient
from info import DATABASE_URL, DATABASE_NAME, TIME_ZONE

logger = logging.getLogger(__name__)

# ==========================================================
# 🌍 TIMEZONE HELPER ENGINE
# ==========================================================
def get_local_now():
    """info.py के TIME_ZONE के अनुसार लाइव लोकल टाइम देता है"""
    tz = pytz.timezone(TIME_ZONE)
    return datetime.now(tz)


# ==========================================================
# 🤖 BOT CENTRAL DATABASE — 100% ADMIN ONLY & RAM OPTIMIZED
# ==========================================================
class Database:
    def __init__(self):
        # ✅ MOTOR ENGINE TUNING: कोएब आइडल थ्रॉटलिंग और मेमोरी लीक से 100% सुरक्षित
        self.client = AsyncIOMotorClient(
            DATABASE_URL, 
            minPoolSize=0,            # आइडल टाइम पर 0 कनेक्शन (RAM खपत न्यूनतम रखने के लिए)
            maxPoolSize=15,           # अधिकतम 15 कनेक्शंस पूल लिमिट
            maxIdleTimeMS=30000,      # 30 सेकंड बाद निष्क्रिय कनेक्शन ऑटो-कूलडाउन
            serverSelectionTimeoutMS=5000
        )
        self.db = self.client[DATABASE_NAME]
        
        # कलेक्शंस (सिर्फ एडमिन-ओनली फीचर्स के लिए आवश्यक)
        self.settings = self.db.Settings
        self.delete_queue = self.db.AutoDeleteQueue 

    async def _ensure_indexes(self):
        """डेटाबेस इंडेक्स सिंक - COLLSCAN लोड रोकने के लिए"""
        # अगर पुरानी 'id_1' अवैध इंडेक्स मौजूद है, तो उसे पूरी तरह से डिस्ट्रॉय करें
        try:
            await self.delete_queue.drop_index("id_1")
            logger.info("🗑️ Old unique index 'id_1' dropped from AutoDeleteQueue.")
        except Exception:
            pass 

        # ऑटो-डिलीट कतार के लिए इंडेक्स सिंक
        try:
            await self.delete_queue.create_index([("delete_at", 1)])
            logger.info("✅ AutoDeleteQueue index initialized successfully.")
        except Exception as e:
            logger.warning(f"Index sync warning: {e}")


    # ───────────────── ⏳ PERSISTENT AUTO-DELETE QUEUE ENGINE ─────────────────
    async def add_to_delete_queue(self, chat_id, message_id, delay_seconds):
        """रीस्टार्ट-प्रूफ ऑटो-डिलीट कतार में मैसेज जोड़ता है"""
        if not chat_id or not message_id:
            return False 
            
        delete_at = get_local_now() + timedelta(seconds=delay_seconds)
        
        # चैट आईडी और मैसेज आईडी का यूनिक कॉम्बो ताकि 'id: null' का लफड़ा कभी न आए
        task_id = f"{int(chat_id)}_{int(message_id)}"
        
        await self.delete_queue.update_one(
            {"_id": task_id},
            {
                "$set": {
                    "_id": task_id,
                    "chat_id": int(chat_id),
                    "message_id": int(message_id),
                    "delete_at": delete_at
                }
            },
            upsert=True
        )
        return True

    async def get_expired_delete_tasks(self):
        """समय सीमा समाप्त हो चुके डिलीट टास्क को खोजता है"""
        now = get_local_now()
        return self.delete_queue.find({"delete_at": {"$lte": now}})

    async def remove_from_delete_queue(self, chat_id, message_id):
        """सफलतापूर्वक डिलीट होने के बाद कतार से टास्क हटाता है"""
        task_id = f"{int(chat_id)}_{int(message_id)}"
        await self.delete_queue.delete_one({"_id": task_id})


    # ───────────────── 🎥 VIDEO STREAM ANALYTICS COUNTER ─────────────────
    async def track_video_play(self):
        """वेबसाइट / मिनी-ऐप पर स्ट्रीम प्ले होने की ग्लोबल काउंटिंग रिकॉर्ड करता है"""
        try:
            await self.settings.update_one(
                {"id": "global_stream_stats"},
                {"$inc": {"total_web_plays": 1}},
                upsert=True
            )
            return True
        except Exception as e:
            logger.error(f"Error in track_video_play pipeline: {e}")
            return False


# ==========================================================
# 🚀 INITIALIZE CENTRAL DATABASE INSTANCE
# ==========================================================
db = Database()
