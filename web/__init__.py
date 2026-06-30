from aiohttp import web
from .stream_api import stream_routes
from .admin_panel import admin_panel_routes

# ─────────────────────────────────────────────────────────
# 🌐 INITIALIZE AIOHTTP WEB APPLICATION ENGINE
# ─────────────────────────────────────────────────────────
web_app = web.Application()

# 🔗 Bind all routing nodes to the central web application
web_app.add_routes(stream_routes)
web_app.add_routes(admin_panel_routes)
