# ==========================================================
# 🎨 CENTRALIZED UI & ASSETS ENGINE (GLASSMORPHISM THEME)
# ==========================================================

# ─────────────────────────────────────────────
# 1️⃣ GLOBAL CSS INJECTIONS
# ─────────────────────────────────────────────
GLOBAL_HEAD = """
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700;900&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdn.plyr.io/3.7.8/plyr.css" />
<style>
    :root {
        --bg: #0a0a0c;
        --bg-panel: rgba(20, 20, 31, 0.7);
        --text: #ffffff;
        --text-muted: #a0a0b0;
        --accent: #E50914;
        --accent-hover: #b30710;
        --border: rgba(255, 255, 255, 0.08);
    }
    body {
        font-family: 'DM Sans', sans-serif;
        background-color: var(--bg);
        color: var(--text);
        margin: 0;
        min-height: 100vh;
        background-image: radial-gradient(circle at 50% 50%, #1a1525 0%, #0a0a0c 80%);
    }
    .glass-panel {
        background: var(--bg-panel);
        backdrop-filter: blur(16px);
        border: 1px solid var(--border);
        border-radius: 16px;
        box-shadow: 0 20px 40px rgba(0,0,0,0.5);
    }
    .btn {
        background: var(--accent);
        color: #fff;
        border: none;
        padding: 10px 20px;
        border-radius: 8px;
        font-weight: bold;
        cursor: pointer;
        transition: 0.2s;
        text-decoration: none;
        display: inline-block;
    }
    .btn:hover { background: var(--accent-hover); }
    .nav-bar {
        padding: 20px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 1px solid var(--border);
    }
    .nav-links a {
        color: var(--text);
        text-decoration: none;
        margin-left: 20px;
        font-weight: 500;
    }
    .nav-links a:hover { color: var(--accent); }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; }
    .input-field {
        width: 100%; padding: 12px; margin-bottom: 15px; border-radius: 8px;
        border: 1px solid var(--border); background: rgba(0,0,0,0.5); color: #fff;
    }
</style>
"""

# ─────────────────────────────────────────────
# 2️⃣ AUTHENTICATION LAYOUT (LOGIN)
# ─────────────────────────────────────────────
def build_auth_layout(error_msg=""):
    err_html = f'<div style="color:var(--accent); margin-bottom:15px;">{error_msg}</div>' if error_msg else ""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <title>Admin Login - Actor Gallery</title>
    {GLOBAL_HEAD}
</head>
<body style="display:flex; align-items:center; justify-content:center;">
    <div class="glass-panel" style="padding:40px; width:100%; max-width:400px; text-align:center;">
        <h2>Actor Gallery Admin</h2>
        <p class="text-muted">Secure Console Access</p>
        {err_html}
        <form action="/api/login" method="post">
            <input type="text" name="username" class="input-field" placeholder="Admin Username" required>
            <input type="password" name="password" class="input-field" placeholder="Admin Password" required>
            <button type="submit" class="btn" style="width:100%;">Sign In to Console</button>
        </form>
    </div>
</body>
</html>"""

# ─────────────────────────────────────────────
# 3️⃣ MASTER DASHBOARD GRID
# ─────────────────────────────────────────────
def build_dashboard_grid(metrics, total_actors, total_posts):
    total_files = metrics.get('total', 0)
    primary = metrics.get('primary', 0)
    cloud = metrics.get('cloud', 0)
    archive = metrics.get('archive', 0)
    
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <title>Dashboard - Actor Gallery Admin</title>
    {GLOBAL_HEAD}
</head>
<body>
    <div class="nav-bar glass-panel" style="border-radius:0; border-top:none; border-left:none; border-right:none;">
        <h2 style="margin:0;">Actor Gallery CMS</h2>
        <div class="nav-links">
            <a href="/dashboard">Dashboard</a>
            <a href="/dashboard/actors">Actors</a>
            <a href="/dashboard/posts">Posts</a>
            <a href="/logout" class="btn" style="margin-left:20px;">Logout</a>
        </div>
    </div>
    
    <div style="padding:40px; max-width:1200px; margin:0 auto;">
        <h3 style="margin-bottom:30px;">System Telemetry</h3>
        <div class="grid">
            <div class="glass-panel" style="padding:20px; text-align:center;">
                <h4 class="text-muted">Total Files Cached</h4>
                <h1 style="font-size:48px; margin:10px 0; color:var(--accent);">{total_files:,}</h1>
            </div>
            <div class="glass-panel" style="padding:20px; text-align:center;">
                <h4 class="text-muted">Actor Profiles</h4>
                <h1 style="font-size:48px; margin:10px 0;">{total_actors:,}</h1>
            </div>
            <div class="glass-panel" style="padding:20px; text-align:center;">
                <h4 class="text-muted">Published Posts</h4>
                <h1 style="font-size:48px; margin:10px 0;">{total_posts:,}</h1>
            </div>
        </div>
        
        <h3 style="margin-top:50px; margin-bottom:20px;">Repository Breakdown</h3>
        <div class="grid">
            <div class="glass-panel" style="padding:20px;">
                <h4>🟢 Primary Node</h4><p>{primary:,} Documents</p>
            </div>
            <div class="glass-panel" style="padding:20px;">
                <h4>☁️ Cloud Node</h4><p>{cloud:,} Documents</p>
            </div>
            <div class="glass-panel" style="padding:20px;">
                <h4>📦 Archive Node</h4><p>{archive:,} Documents</p>
            </div>
        </div>
    </div>
</body>
</html>"""

# ─────────────────────────────────────────────
# 4️⃣ ACTORS DIRECTORY CMS (ACTOR GALLERY)
# ─────────────────────────────────────────────
def build_actors_template(actors_list):
    list_html = ""
    for actor in actors_list:
        name = actor.get('name', 'Unknown')
        cat = actor.get('category', 'website')
        img = actor.get('image_url', '')
        a_id = str(actor.get('_id', ''))
        
        list_html += f"""
        <div class="glass-panel" style="padding:15px; display:flex; align-items:center; gap:15px;">
            <img src="{img}" style="width:60px; height:60px; border-radius:50%; object-fit:cover;">
            <div style="flex-grow:1;">
                <h4 style="margin:0;">{name}</h4>
                <span class="text-muted" style="font-size:12px; text-transform:uppercase;">{cat}</span>
            </div>
            <a href="/dashboard/actors/delete/{a_id}" class="btn" style="background:#555;">Delete</a>
        </div>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <title>Actors - Actor Gallery</title>
    {GLOBAL_HEAD}
</head>
<body>
    <div class="nav-bar glass-panel" style="border-radius:0;"><h2 style="margin:0;">Actor Gallery CMS</h2>
        <div class="nav-links"><a href="/dashboard">Dashboard</a><a href="/dashboard/actors">Actors</a><a href="/logout" class="btn">Logout</a></div>
    </div>
    
    <div style="padding:40px; max-width:1200px; margin:0 auto; display:flex; gap:30px;">
        <div style="flex:1;">
            <h3>Add New Actor Profile</h3>
            <div class="glass-panel" style="padding:30px;">
                <form action="/dashboard/actors/add" method="post">
                    <input type="text" name="name" class="input-field" placeholder="Actor Name" required>
                    <select name="category" class="input-field" required>
                        <option value="website">Website Category</option>
                        <option value="app">App Category</option>
                    </select>
                    <input type="text" name="image_url" class="input-field" placeholder="Thumbnail Image URL" required>
                    <button type="submit" class="btn" style="width:100%;">Create Profile</button>
                </form>
            </div>
        </div>
        
        <div style="flex:2;">
            <h3>Directory Database</h3>
            <div style="display:flex; flex-direction:column; gap:15px;">
                {list_html if list_html else "<p>No actors found.</p>"}
            </div>
        </div>
    </div>
</body>
</html>"""

# ─────────────────────────────────────────────
# 5️⃣ PLYR VIDEO STREAMING ENGINE (MINI-APP / WEB)
# ─────────────────────────────────────────────
def render_player_page(file_title, stream_url):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <title>Watch: {file_title}</title>
    {GLOBAL_HEAD}
    <style>
        .player-wrapper {{ max-width: 1000px; margin: 40px auto; border-radius: 16px; overflow: hidden; box-shadow: 0 30px 60px rgba(0,0,0,0.8); border: 1px solid var(--border); }}
        .plyr {{ --plyr-color-main: #E50914; }}
    </style>
</head>
<body>
    <div class="player-wrapper glass-panel">
        <video id="player" playsinline controls data-poster="https://telegra.ph/file/0cbb9b9409849202bdc17.jpg">
            <source src="{stream_url}" type="video/mp4" />
        </video>
    </div>
    <div style="text-align:center; padding:20px;">
        <h2 style="margin:0 0 20px 0;">{file_title}</h2>
        <a href="{stream_url}" class="btn" download>📥 Download Asset Directly</a>
    </div>

    <script src="https://cdn.plyr.io/3.7.8/plyr.polyfilled.js"></script>
    <script>
        const player = new Plyr('#player', {{
            controls: ['play-large', 'play', 'progress', 'current-time', 'duration', 'mute', 'volume', 'settings', 'fullscreen'],
            settings: ['quality', 'speed']
        }});
        // Force Landscape mode when user clicks fullscreen on mobile devices
        player.on('enterfullscreen', () => {{
            if (screen.orientation && screen.orientation.lock) {{
                screen.orientation.lock('landscape').catch(() => {{}});
            }}
        }});
    </script>
</body>
</html>"""
