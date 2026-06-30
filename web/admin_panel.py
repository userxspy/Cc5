import uuid
import time
import logging
from aiohttp import web
from bson.objectid import ObjectId

from info import WEB_USERNAME, WEB_PASSWORD, ADMINS
from utils import temp
from database.ia_filterdb import actors, posts, db_count_documents

logger = logging.getLogger(__name__)
admin_panel_routes = web.RouteTableDef()

# ─────────────────────────────────────────────────────────
# 🛡️ SECURITY MIDDLEWARE — SESSION VALIDATOR GUARD
# ─────────────────────────────────────────────────────────
def is_admin_session_valid(request):
    """Checks inside temp class if cookie session exists and is not expired"""
    session_cookie = request.cookies.get('user_session')
    if not session_cookie or not hasattr(temp, 'USER_SESSIONS'):
        return False
        
    session_data = temp.USER_SESSIONS.get(session_cookie)
    if not session_data:
        return False
        
    if time.time() > session_data.get('expiry', 0):
        temp.USER_SESSIONS.pop(session_cookie, None) # Clear expired node
        return False
        
    return True

# ─────────────────────────────────────────────────────────
# 🔐 LOGIN ROUTES (INFO.PY SYNC ENGINE)
# ─────────────────────────────────────────────────────────
@admin_panel_routes.get('/login')
async def login_page_renderer(request):
    if is_admin_session_valid(request):
        return web.HTTPFound('/dashboard')
        
    from web.web_assets import build_auth_layout
    error_msg = request.query.get('err', '')
    return web.Response(text=build_auth_layout(error_msg), content_type='text/html')

@admin_panel_routes.post('/api/login')
async def api_login_authenticator(request):
    data = await request.post()
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()

    # Match strictly with environment configs in info.py
    if username == WEB_USERNAME and password == WEB_PASSWORD:
        session_id = str(uuid.uuid4())
        if not hasattr(temp, 'USER_SESSIONS'):
            temp.USER_SESSIONS = {}
            
        # Bind with primary designated admin ID
        default_tg_id = ADMINS[0] if ADMINS else 0
        
        # Lock session into localized RAM dict for exactly 7 days
        temp.USER_SESSIONS[session_id] = {
            'tg_id': default_tg_id,
            'expiry': time.time() + (86400 * 7)
        }
        
        response = web.HTTPFound('/dashboard')
        response.set_cookie('user_session', session_id, max_age=86400 * 7, httponly=True)
        return response

    return web.HTTPFound('/login?err=Invalid Admin Credentials')

@admin_panel_routes.get('/logout')
async def logout_handler(request):
    session_cookie = request.cookies.get('user_session')
    if session_cookie and hasattr(temp, 'USER_SESSIONS'):
        temp.USER_SESSIONS.pop(session_cookie, None)
        
    response = web.HTTPFound('/login')
    response.del_cookie('user_session')
    return response

# ─────────────────────────────────────────────────────────
# 📊 CENTRAL ADMIN DASHBOARD SYSTEM
# ─────────────────────────────────────────────────────────
@admin_panel_routes.get('/dashboard')
async def main_dashboard_renderer(request):
    if not is_admin_session_valid(request):
        return web.HTTPFound('/login')

    # Fetch fresh telemetry database configurations asynchronously
    db_metrics = await db_count_documents()
    total_actors = await actors.count_documents({})
    total_posts = await posts.count_documents({})

    from web.web_assets import build_dashboard_grid
    return web.Response(
        text=build_dashboard_grid(db_metrics, total_actors, total_posts),
        content_type='text/html'
    )

# ─────────────────────────────────────────────────────────
# 🎭 CELEBRITY ACTORS DIRECTORY CMS ROUTES
# ─────────────────────────────────────────────────────────
@admin_panel_routes.get('/dashboard/actors')
async def list_actors_panel(request):
    if not is_admin_session_valid(request):
        return web.HTTPFound('/login')

    # Query all celebrity profiles sorted descending
    actors_list = await actors.find({}).sort('_id', -1).to_list(length=200)
    
    from web.web_assets import build_actors_template
    return web.Response(text=build_actors_template(actors_list), content_type='text/html')

@admin_panel_routes.post('/dashboard/actors/add')
async def api_add_actor_profile(request):
    if not is_admin_session_valid(request):
        return web.HTTPFound('/login')

    data = await request.post()
    name = data.get('name', '').strip()
    category = data.get('category', 'website').strip()
    image_url = data.get('image_url', '').strip()

    if name:
        await actors.insert_one({
            "name": name,
            "category": category,
            "image_url": image_url or "https://telegra.ph/file/0cbb9b9409849202bdc17.jpg",
            "gallery": []
        })
    return web.HTTPFound('/dashboard/actors')

@admin_panel_routes.get('/dashboard/actors/delete/{actor_id}')
async def api_delete_actor(request):
    if not is_admin_session_valid(request):
        return web.HTTPFound('/login')

    actor_id = request.match_info['actor_id']
    try:
        await actors.delete_one({"_id": ObjectId(actor_id)})
    except Exception as e:
        logger.error(f"Actor deletion failed: {e}")
        
    return web.HTTPFound('/dashboard/actors')

# ─────────────────────────────────────────────────────────
# 🎬 POSTS CMS ENGINE ROUTES
# ─────────────────────────────────────────────────────────
@admin_panel_routes.get('/dashboard/posts')
async def list_posts_panel(request):
    if not is_admin_session_valid(request):
        return web.HTTPFound('/login')

    posts_list = await posts.find({}).sort('_id', -1).to_list(length=100)
    
    from web.web_assets import build_posts_template
    return web.Response(text=build_posts_template(posts_list), content_type='text/html')

@admin_panel_routes.post('/dashboard/posts/add')
async def api_publish_new_post(request):
    if not is_admin_session_valid(request):
        return web.HTTPFound('/login')

    data = await request.post()
    title = data.get('title', '').strip()
    tags = data.get('tags', '').strip()
    download_url = data.get('download_url', '').strip()

    if title:
        tags_array = [t.strip().lower() for t in tags.split(',') if t.strip()]
        await posts.insert_one({
            "title": title,
            "tags": tags_array,
            "download_url": download_url,
            "timestamp": time.time()
        })
    return web.HTTPFound('/dashboard/posts')

@admin_panel_routes.get('/dashboard/posts/delete/{post_id}')
async def api_delete_post(request):
    if not is_admin_session_valid(request):
        return web.HTTPFound('/login')

    post_id = request.match_info['post_id']
    try:
        await posts.delete_one({"_id": ObjectId(post_id)})
    except Exception as e:
        logger.error(f"Post deletion wizard failed: {e}")
        
    return web.HTTPFound('/dashboard/posts')

# ─────────────────────────────────────────────────────────
# 📴 DISABLED PUBLIC REGISTRATION FALLBACKS
# ─────────────────────────────────────────────────────────
@admin_panel_routes.get('/register')
@admin_panel_routes.get('/forgot_password')
async def registration_disabled_handler(request):
    return web.Response(
        text="<b>❌ Access Denied: Public registration architecture is deactivated on this admin instance.</b>", 
        content_type="text/html", 
        status=403
    )
