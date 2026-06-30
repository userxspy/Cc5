import math
import logging
import mimetypes
from urllib.parse import quote
from aiohttp import web
from hydrogram.errors import FloodWait

from info import BIN_CHANNEL, URL
from utils import temp, get_size
from database.users_chats_db import db

logger = logging.getLogger(__name__)
stream_routes = web.RouteTableDef()

# ⚡ GLOBAL CHUNK VELOCITY PARAMETERS
INITIAL_CHUNK_SIZE = 1024 * 1024 * 2  # 2MB Aggressive buffering chunk
NORMAL_CHUNK_SIZE  = 1024 * 512       # 512KB Stable stream chunk

# ─────────────────────────────────────────────────────────
# 🏠 CENTRAL LANDING HOME ROUTE (NETFLIX GLASSMORPHISM)
# ─────────────────────────────────────────────────────────
@stream_routes.get("/", allow_head=True)
async def homepage_root_handler(request):
    bot_username = getattr(temp, 'U_NAME', 'AutoFilterBot')

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Fast Finder — Control Room</title>
    <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700;900&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg: #0a0a0c;
            --text: #fff;
            --box: rgba(20, 20, 31, 0.7);
            --border: rgba(255, 255, 255, 0.08);
            --red: #E50914;
            --red-hover: #b30710;
        }}
        body {{
            font-family: 'DM Sans', sans-serif;
            background-color: var(--bg);
            color: var(--text);
            margin: 0;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            background-image: radial-gradient(circle at 50% 50%, #1a1525 0%, #0a0a0c 80%);
        }}
        .top-nav {{
            position: absolute;
            top: 0;
            right: 0;
            padding: 20px;
            z-index: 10;
        }}
        .login-nav-btn {{
            background: var(--red);
            color: #fff;
            text-decoration: none;
            padding: 10px 24px;
            border-radius: 8px;
            font-weight: 700;
            font-size: 14px;
            transition: 0.2s;
            box-shadow: 0 4px 15px rgba(229, 9, 20, 0.3);
        }}
        .login-nav-btn:hover {{
            background: var(--red-hover);
            transform: translateY(-1px);
        }}
        .container {{
            text-align: center;
            background: var(--box);
            padding: 50px 40px;
            border-radius: 24px;
            border: 1px solid var(--border);
            backdrop-filter: blur(16px);
            max-width: 450px;
            width: 90%;
            box-shadow: 0 20px 40px rgba(0,0,0,0.5);
        }}
        h1 {{
            font-size: 36px;
            font-weight: 900;
            margin: 0 0 10px;
            letter-spacing: -1px;
        }}
        p {{
            color: #a0a0b0;
            font-size: 15px;
            line-height: 1.6;
            margin: 0 0 30px;
        }}
        .btn {{
            background: #fff;
            color: #000;
            text-decoration: none;
            padding: 14px 32px;
            border-radius: 12px;
            font-weight: 700;
            font-size: 15px;
            display: inline-block;
            transition: 0.2s;
        }}
        .btn:hover {{
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(255,255,255,0.2);
        }}
    </style>
</head>
<body>
    <div class="top-nav">
        <a href="/login" class="login-nav-btn">🔐 Admin Login</a>
    </div>
    <div class="container">
        <h1>Fast Finder</h1>
        <p>Welcome to your advanced Admin-Only media repository and streaming control room system.</p>
        <a href="https://t.me/{bot_username}" class="btn">Open Telegram Bot</a>
    </div>
</body>
</html>"""
    return web.Response(text=html_content, content_type="text/html")

# ─────────────────────────────────────────────────────────
# 📥 DOWNLOAD & WATCH TUNNEL INTERCEPTORS
# ─────────────────────────────────────────────────────────
@stream_routes.get("/download/{msg_id}")
@stream_routes.get("/watch/{msg_id}")
async def stream_gateway_handler(request):
    msg_id = int(request.match_info['msg_id'])
    is_download = "download" in request.path

    bot = temp.BOT
    if not bot:
        return web.Response(text="<b>❌ Bot runtime is offline!</b>", content_type="text/html", status=503)

    try:
        msg = await bot.get_messages(BIN_CHANNEL, msg_id)
        if not msg or msg.empty:
            return web.Response(text="<b>❌ Media file node not found or expired!</b>", content_type="text/html", status=404)
            
        media = getattr(msg, msg.media.value, None)
        if not media:
            return web.Response(text="<b>❌ Invalid media format!</b>", content_type="text/html", status=400)
    except Exception as e:
        return web.Response(text=f"<b>❌ Access Error:</b> {e}", content_type="text/html", status=500)

    # Automatically track play metrics inside database analytics
    if not is_download and request.method == "GET":
        await db.track_video_play()

    file_name = getattr(media, 'file_name', 'video.mp4') or 'video.mp4'
    file_size = media.file_size

    # Parse Range Header (HTTP 206 Multi-part Chunking Engine)
    range_header = request.headers.get('Range')
    start, end = 0, file_size - 1

    if range_header:
        match = re.match(r'bytes=(\d+)-(\d*)', range_header)
        if match:
            start = int(match.group(1))
            if match.group(2):
                end = int(match.group(2))

    if start > end or start >= file_size or end >= file_size:
        return web.Response(status=416, headers={'Content-Range': f'bytes */{file_size}'})

    resp_size = (end - start) + 1
    
    # Extract Safe Content-Type
    mime_type, _ = mimetypes.guess_type(file_name)
    if not mime_type:
        mime_type = "video/mp4" if file_name.endswith(('.mp4', '.mkv')) else "application/octet-stream"

    headers = {
        'Accept-Ranges': 'bytes',
        'Content-Type': mime_type,
        'Content-Length': str(resp_size),
        'Content-Range': f'bytes {start}-{end}/{file_size}'
    }

    if is_download:
        # Force browser to run direct attachment savings download
        headers['Content-Disposition'] = f'attachment; filename="{quote(file_name)}"'

    # Render plyr HTML layout wrapper if user chooses /watch route instead of direct download binary bytes
    if not is_download and "range" not in request.headers.get('Connection', '').lower() and not range_header:
        from web.web_assets import render_player_page
        return web.Response(text=render_player_page(file_name, f"{URL}download/{msg_id}"), content_type="text/html")

    # Initialize dynamic high speed custom yielding pipeline
    stream_response = web.StreamResponse(status=206 if range_header else 200, headers=headers)
    await stream_response.prepare(request)

    # 🌊 RAM SAFE STREAM GENERATOR
    try:
        current_offset = start
        while current_offset <= end:
            # First 4MB gets aggressive push to avoid plyr buffering delay
            chunk_limit = INITIAL_CHUNK_SIZE if (current_offset - start) < (1024 * 1024 * 4) else NORMAL_CHUNK_SIZE
            chunk_to_read = min(chunk_limit, (end - current_offset) + 1)
            
            # Request telegram cloud server chunk bytes array directly
            try:
                async for chunk in bot.stream_media(media, offset=current_offset, limit=chunk_to_read):
                    await stream_response.write(chunk)
                    current_offset += len(chunk)
            except FloodWait as f_wait:
                await asyncio.sleep(f_wait.value)
                continue
                
    except (ClientResetError, ConnectionResetError, AssertionError):
        # Gracefully handle media playback close/seek events on frontend side
        pass
    except Exception as stream_err:
        logger.debug(f"Streaming pipeline tracking closing trigger: {stream_err}")
    finally:
        await stream_response.write_eof()

    return stream_response
