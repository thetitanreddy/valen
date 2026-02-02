from flask import Flask, request, render_template_string
import firebase_admin
from firebase_admin import credentials, firestore
import secrets
import time
import io
import base64
from datetime import datetime, timedelta
from PIL import Image
import qrcode
import os
import json

app = Flask(__name__)

# --- 1. FIREBASE SETUP ---
if not firebase_admin._apps:
    if os.environ.get("FIREBASE_KEY_JSON"):
        cred_dict = json.loads(os.environ.get("FIREBASE_KEY_JSON"))
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
    else:
        try:
            cred = credentials.Certificate("firebase_key.json")
            firebase_admin.initialize_app(cred)
        except Exception as e:
            print(f"🔥 Firebase setup failed: {e}")

db = firestore.client()

# --- 2. PREMIUM CINEMA STYLES ---
STYLE = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Cinzel+Decorative:wght@700&family=Lato:wght@300;400;700&display=swap');

/* GLOBAL RESETS */
* { box-sizing: border-box; }

body {
    background-color: #0a0a0a;
    color: #e0e0e0;
    font-family: 'Lato', sans-serif;
    margin: 0;
    padding: 0;
    display: flex;
    justify-content: center;
    align-items: center;
    min-height: 100vh;
    overflow-x: hidden;
}

/* ANIMATIONS */
@keyframes fadeInUp {
    from { opacity: 0; transform: translateY(40px); }
    to { opacity: 1; transform: translateY(0); }
}

@keyframes popIn {
    0% { opacity: 0; transform: scale(0.8); }
    70% { transform: scale(1.02); }
    100% { opacity: 1; transform: scale(1); }
}

@keyframes heartbeat {
    0% { transform: scale(1); box-shadow: 0 0 0 rgba(255, 255, 255, 0); }
    50% { transform: scale(1.05); box-shadow: 0 0 20px rgba(255, 255, 255, 0.2); }
    100% { transform: scale(1); box-shadow: 0 0 0 rgba(255, 255, 255, 0); }
}

@keyframes shimmer {
    0% { background-position: -1000px 0; }
    100% { background-position: 1000px 0; }
}

.container {
    width: 90%;
    max-width: 450px;
    text-align: center;
    padding: 20px;
    perspective: 1000px;
}

h1 {
    font-family: 'Cinzel Decorative', cursive;
    color: #ffffff;
    font-size: 2.5rem;
    margin-bottom: 25px;
    text-shadow: 0px 0px 20px rgba(255,255,255,0.2);
    animation: fadeInUp 0.8s ease-out;
}

.card {
    background: linear-gradient(145deg, #161616, #0f0f0f);
    padding: 30px;
    border-radius: 20px;
    border: 1px solid #333;
    box-shadow: 0 20px 60px rgba(0,0,0,0.6);
    animation: fadeInUp 0.8s ease-out 0.2s backwards;
    transition: transform 0.3s ease;
    position: relative;
    overflow: hidden;
}

/* INPUTS & TEXTAREA */
textarea, select, input[type="number"], input[type="text"] {
    background-color: #1a1a1a;
    border: 1px solid #444;
    color: white;
    padding: 15px;
    border-radius: 12px;
    width: 100%;
    box-sizing: border-box;
    font-family: 'Lato', sans-serif;
    font-size: 1rem;
    transition: all 0.3s;
    outline: none;
    resize: none;
    margin-bottom: 15px;
    box-shadow: inset 0 2px 5px rgba(0,0,0,0.5);
}
textarea:focus, input:focus { 
    border-color: #888; 
    background-color: #222;
}

/* DROP ZONE */
.drop-zone {
    width: 100%;
    padding: 25px;
    border: 2px dashed #444;
    border-radius: 15px;
    background-color: #1a1a1a;
    color: #888;
    text-align: center;
    cursor: pointer;
    transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
    margin-bottom: 20px;
}
.drop-zone:hover { border-color: #fff; background-color: #222; transform: translateY(-3px); }
.drop-zone.active { border-color: #51cf66; background-color: #1a2a1a; }
.drop-zone p { margin: 0; pointer-events: none; font-size: 0.95rem; font-weight: bold;}

/* BUTTONS */
.btn {
    background: linear-gradient(135deg, #ffffff, #b0b0b0);
    color: #000;
    border: none;
    padding: 18px 30px;
    border-radius: 50px;
    cursor: pointer;
    font-weight: 800;
    font-size: 1.1rem;
    width: 100%;
    margin-top: 15px;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    transition: all 0.3s;
    box-shadow: 0 5px 20px rgba(255,255,255,0.15);
}
.btn:hover { transform: translateY(-3px) scale(1.02); background: #ffffff; box-shadow: 0 10px 30px rgba(255,255,255,0.3); }

/* SPECIAL BUTTONS */
.btn-pulse { animation: heartbeat 2s infinite; }
.btn.loading {
    background: #333; color: #fff; cursor: wait;
    animation: shimmer 2s infinite linear;
    background: linear-gradient(to right, #333 0%, #444 50%, #333 100%);
    background-size: 1000px 100%;
}

/* MESSAGE REVEAL STYLES */
.protected-text {
    font-family: 'Cinzel Decorative', cursive;
    font-size: 1.6rem;
    line-height: 1.6;
    margin: 30px 0;
    color: #fff;
    -webkit-user-select: none;
    user-select: none;
    cursor: default;
    animation: fadeInUp 1s ease-out 0.5s backwards; /* Staggered delay */
}

.secret-image {
    display: block; 
    width: 100%; 
    border-radius: 12px; 
    margin-bottom:15px;
    box-shadow: 0 0 30px rgba(255,255,255,0.1); /* Glow effect */
    animation: popIn 0.8s cubic-bezier(0.175, 0.885, 0.32, 1.275) 0.2s backwards; /* Pop in effect */
}

a { color: #888; text-decoration: none; font-size: 0.9rem; transition: 0.3s; }
a:hover { color: #fff; text-shadow: 0 0 10px white;}
.success { color: #51cf66; font-weight: bold; }
.error { color: #ff6b6b; font-weight: bold; }

</style>
"""

# --- 3. HTML PAGES ---

HTML_CREATE = f"""
<!DOCTYPE html>
<html>
<head><title>Cupid's Secret</title><meta name="viewport" content="width=device-width, initial-scale=1">{STYLE}</head>
<body>
    <div class="container">
        <h1>Cupid's Secret</h1>
        <div class="card">
            
            <form action="/create" method="POST" enctype="multipart/form-data" id="secretForm" onsubmit="startLoading()">
                
                <textarea name="message" rows="4" placeholder="Write your secret here..." maxlength="500"></textarea>
                
                <div class="drop-zone" id="dropZone">
                    <p>📸 Add Photo (Optional)</p>
                    <input type="file" name="file" id="fileInput" accept="image/*" hidden>
                </div>
                
                <div id="filePreview" style="color: #51cf66; font-weight:bold; margin-bottom: 20px; display: none; animation: fadeInUp 0.4s;"></div>
                
                <div style="display:flex; gap:12px; margin-bottom: 20px;">
                    <input type="number" name="duration_val" value="15" min="1" style="width:40%;">
                    <select name="duration_unit" style="width:60%;">
                        <option value="Minutes">Minutes</option>
                        <option value="Hours">Hours</option>
                        <option value="Days">Days</option>
                    </select>
                </div>

                <label style="display:flex; align-items:center; gap:12px; font-size:0.95rem; margin-bottom:25px; cursor:pointer; opacity:0.9;">
                    <input type="checkbox" name="one_time" checked style="width:20px; height:20px; accent-color:#fff;">
                    Vanish after 1 view?
                </label>

                <button type="submit" class="btn" id="submitBtn">Seal Secret 🔒</button>
            </form>
        </div>
    </div>

    <script>
        function startLoading() {{
            const btn = document.getElementById('submitBtn');
            btn.innerHTML = "⚡ PROCESSING...";
            btn.classList.add('loading');
        }}

        const dropZone = document.getElementById('dropZone');
        const fileInput = document.getElementById('fileInput');
        const filePreview = document.getElementById('filePreview');

        dropZone.addEventListener('click', () => fileInput.click());

        fileInput.addEventListener('change', () => {{
            if (fileInput.files.length) {{
                filePreview.innerHTML = "✅ Photo Attached: " + fileInput.files[0].name;
                filePreview.style.display = 'block';
                dropZone.classList.add('active');
                dropZone.innerHTML = '<p style="color:#fff;">🖼️ Photo Selected</p>';
            }}
        }});
        
        dropZone.addEventListener('dragover', (e) => {{ e.preventDefault(); dropZone.style.transform = 'scale(1.05)'; }});
        dropZone.addEventListener('dragleave', () => {{ dropZone.style.transform = 'scale(1)'; }});
        dropZone.addEventListener('drop', (e) => {{
            e.preventDefault();
            dropZone.style.transform = 'scale(1)';
            if (e.dataTransfer.files.length) {{
                fileInput.files = e.dataTransfer.files;
                const event = new Event('change');
                fileInput.dispatchEvent(event);
            }}
        }});
    </script>
</body>
</html>
"""

HTML_RESULT = f"""
<!DOCTYPE html>
<html>
<head><title>Sealed</title><meta name="viewport" content="width=device-width, initial-scale=1">{STYLE}</head>
<body>
    <div class="container">
        <h1>Sealed</h1>
        <div class="card">
            <h3 class="success" style="margin-top:0;">✨ Secret Secured</h3>
            <p style="font-size:0.9rem; color:#aaa; margin-bottom:10px;">Share this link:</p>
            
            <input type="text" value="{{{{ share_link }}}}" readonly onclick="this.select()" style="margin-bottom:20px; text-align:center; font-family:monospace;">
            
            <div style="background:white; padding:15px; border-radius:15px; display:inline-block; animation: heartbeat 2s infinite;">
                <img src="data:image/png;base64,{{{{ qr_b64 }}}}" style="width:180px; margin:0; display:block;">
            </div>
            <br><br>
            <a href="/">Create Another</a>
        </div>
    </div>
</body>
</html>
"""

HTML_REVEAL = f"""
<!DOCTYPE html>
<html>
<head><title>Secret Awaits</title><meta name="viewport" content="width=device-width, initial-scale=1">{STYLE}</head>
<body>
    <div class="container">
        <h1 style="font-size:4rem; margin-bottom:10px;">✉️</h1>
        <div class="card">
            <h2 style="margin-top:0;">A Secret Awaits</h2>
            <p style="font-size:1.1rem; line-height:1.5;">{{{{ warning_text }}}}</p>
            <br>
            <form action="/reveal/{{{{ link_id }}}}" method="POST">
                <button type="submit" class="btn btn-pulse">Break the Seal</button>
            </form>
        </div>
    </div>
</body>
</html>
"""

HTML_MESSAGE = f"""
<!DOCTYPE html>
<html>
<head><title>Revealed</title><meta name="viewport" content="width=device-width, initial-scale=1">{STYLE}</head>
<body>
    <div class="container">
        <h1 style="font-size:3rem; margin-bottom:10px; animation: popIn 0.5s;">💖</h1>
        <div class="card">
            {{% if image_data %}}
                <img src="data:image/jpeg;base64,{{{{ image_data }}}}" alt="Secret Image" class="secret-image">
            {{% endif %}}
            
            {{% if message %}}
                <div class="protected-text">“{{{{ message }}}}”</div>
            {{% endif %}}
            
            <p style="margin-top:20px; color:#888; font-size:0.9rem; font-style:italic; animation: fadeInUp 1s ease-out 0.8s backwards;">{{{{ footer_text }}}}</p>
            <br>
            <a href="/" class="btn" style="background:transparent; border:1px solid #555; color:#fff; display:inline-block; padding:10px 20px; width:auto; animation: fadeInUp 1s ease-out 1s backwards;">Reply</a>
        </div>
    </div>
</body>
</html>
"""

HTML_ERROR = f"""
<!DOCTYPE html>
<html>
<head><title>Error</title><meta name="viewport" content="width=device-width, initial-scale=1">{STYLE}</head>
<body>
    <div class="container">
        <h1 style="font-size:4rem;">{{{{ icon }}}}</h1>
        <div class="card">
            <h3 class="error">{{{{ title }}}}</h3>
            <p>{{{{ text }}}}</p>
            <br>
            <a href="/" class="btn">Create New</a>
        </div>
    </div>
</body>
</html>
"""

# --- 4. IMAGE PROCESSING ---
def process_image(file):
    try:
        img = Image.open(file)
        if img.mode in ("RGBA", "P"): img = img.convert("RGB")
        img.thumbnail((800, 800))
        buf = io.BytesIO()
        img.save(buf, format='JPEG', quality=65, optimize=True)
        b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
        if len(b64) > 950000: return None 
        return b64
    except: return None

# --- 5. ROUTES ---
@app.route("/", methods=["GET"])
def home():
    return render_template_string(HTML_CREATE)

@app.route("/create", methods=["POST"])
def create():
    msg = request.form.get("message", "")
    f = request.files.get("file")
    
    img_b64 = None
    if f and f.filename != '':
        img_b64 = process_image(f)
        if not img_b64 and len(msg) < 1:
             return render_template_string(HTML_ERROR, icon="⚠️", title="Too Big", text="Photo is too large. Try a smaller one.")
    
    if not img_b64 and len(msg.strip()) < 1:
        return render_template_string(HTML_ERROR, icon="⚠️", title="Empty", text="Please add a message or a photo.")

    try: val = int(request.form.get("duration_val", 15))
    except: val = 15
    unit = request.form.get("duration_unit", "Minutes")
    mult = 1
    if unit == "Hours": mult = 60
    elif unit == "Days": mult = 1440
    minutes = val * mult
    
    link_id = secrets.token_urlsafe(8)
    expiry = int((datetime.now() + timedelta(minutes=minutes)).timestamp())
    one_time = request.form.get("one_time") is not None
    
    doc = {
        "message": msg,
        "image_data": img_b64,
        "created_at": int(time.time()),
        "expiry": expiry,
        "opened": False,
        "one_time": one_time
    }
    db.collection("links").document(link_id).set(doc)
    
    base = request.host_url.rstrip("/")
    share_link = f"{base}/secret/{link_id}"
    
    qr = qrcode.make(share_link)
    buf = io.BytesIO()
    qr.save(buf, format="PNG")
    qr_b64 = base64.b64encode(buf.getvalue()).decode()
    
    return render_template_string(HTML_RESULT, share_link=share_link, qr_b64=qr_b64)

@app.route("/secret/<link_id>", methods=["GET"])
def view_secret(link_id):
    doc_ref = db.collection("links").document(link_id)
    doc = doc_ref.get()
    if not doc.exists: return render_template_string(HTML_ERROR, icon="💨", title="Invalid", text="Link not found.")
    data = doc.to_dict()
    if int(time.time()) > data['expiry']: return render_template_string(HTML_ERROR, icon="⏳", title="Expired", text="This secret has expired.")
    if data['one_time'] and data['opened']: return render_template_string(HTML_ERROR, icon="💔", title="Gone", text="This secret was already viewed.")
    warn = "⚠️ This message will vanish forever after you view it once." if data['one_time'] else "✨ Available until expiry."
    return render_template_string(HTML_REVEAL, warning_text=warn, link_id=link_id)

@app.route("/reveal/<link_id>", methods=["POST"])
def reveal(link_id):
    doc_ref = db.collection("links").document(link_id)
    doc = doc_ref.get()
    if not doc.exists: return render_template_string(HTML_ERROR, icon="❌", title="Error", text="Not found.")
    data = doc.to_dict()
    if int(time.time()) > data['expiry']: return render_template_string(HTML_ERROR, icon="⏳", title="Expired", text="Too late.")
    if data['one_time'] and data['opened']: return render_template_string(HTML_ERROR, icon="💔", title="Gone", text="Already seen.")
    doc_ref.update({"opened": True})
    footer = "Locked in the past." if data['one_time'] else "Viewable until expiry."
    return render_template_string(HTML_MESSAGE, message=data.get('message'), image_data=data.get('image_data'), footer_text=footer)

if __name__ == "__main__":
    app.run(debug=True)
