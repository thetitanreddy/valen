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

# --- 2. PREMIUM ANIMATED STYLES ---
STYLE = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Cinzel+Decorative:wght@700&family=Lato:wght@300;400;700&display=swap');

* { box-sizing: border-box; }
body {
    background-color: #0a0a0a;
    color: #e0e0e0;
    font-family: 'Lato', sans-serif;
    margin: 0; padding: 0;
    display: flex; justify-content: center; align-items: center;
    min-height: 100vh; overflow-x: hidden;
}

/* ANIMATIONS */
@keyframes fadeInUp { from { opacity: 0; transform: translateY(40px); } to { opacity: 1; transform: translateY(0); } }
@keyframes popIn { 0% { opacity: 0; transform: scale(0.8); } 50% { transform: scale(1.02); } 100% { opacity: 1; transform: scale(1); } }
@keyframes heartbeat { 0% { transform: scale(1); } 50% { transform: scale(1.1); } 100% { transform: scale(1); } }
@keyframes blurReveal { from { filter: blur(10px); opacity: 0; } to { filter: blur(0); opacity: 1; } }

.container { width: 90%; max-width: 450px; text-align: center; padding: 20px; perspective: 1000px; }

h1 {
    font-family: 'Cinzel Decorative', cursive; color: #ffffff; font-size: 2.5rem;
    margin-bottom: 25px; text-shadow: 0px 0px 15px rgba(255,255,255,0.3);
    animation: fadeInUp 0.8s ease-out;
}

.card {
    background: linear-gradient(145deg, #161616, #0f0f0f);
    padding: 30px; border-radius: 20px; border: 1px solid #333;
    box-shadow: 0 20px 50px rgba(0,0,0,0.6);
    animation: fadeInUp 0.8s ease-out 0.2s backwards;
    transition: transform 0.3s ease;
}

textarea, select, input {
    background-color: #252525; border: 1px solid #444; color: white;
    padding: 15px; border-radius: 10px; width: 100%;
    font-family: 'Lato', sans-serif; font-size: 1rem;
    outline: none; resize: none; margin-bottom: 15px;
}
textarea:focus, input:focus { border-color: #888; }

.drop-zone {
    width: 100%; padding: 20px; border: 2px dashed #444; border-radius: 12px;
    background-color: #1a1a1a; color: #888; cursor: pointer; margin-bottom: 20px;
}
.drop-zone.active { border-color: #51cf66; background-color: #1a2a1a; }
.drop-zone p { margin: 0; pointer-events: none; }

.btn {
    background: linear-gradient(135deg, #ffffff, #b0b0b0);
    color: #000; border: none; padding: 18px 30px; border-radius: 50px;
    cursor: pointer; font-weight: 700; font-size: 1.1rem; width: 100%;
    margin-top: 15px; text-transform: uppercase; letter-spacing: 1px;
    box-shadow: 0 5px 15px rgba(255,255,255,0.1);
}
.btn:hover { transform: translateY(-3px) scale(1.02); background: #ffffff; }

/* REVEAL SPECIFIC */
.envelope-icon { font-size: 4rem; margin-bottom: 10px; display: inline-block; animation: heartbeat 2s infinite ease-in-out; }
.reveal-image { width: 100%; border-radius: 12px; margin-bottom: 20px; animation: popIn 0.8s cubic-bezier(0.34, 1.56, 0.64, 1); }
.protected-text {
    font-family: 'Cinzel Decorative', cursive; font-size: 1.6rem; line-height: 1.5;
    margin: 30px 0; color: #fff; user-select: none; -webkit-user-select: none;
    animation: blurReveal 1s ease 0.3s backwards;
}

/* REPLY SECTION */
.reply-section {
    margin-top: 30px; border-top: 1px solid #333; padding-top: 20px;
    display: none; /* Hidden by default */
    animation: fadeInUp 0.5s ease;
}

img { display: block; width: 100%; border-radius: 8px; margin-bottom:15px; }
a { color: #888; text-decoration: none; font-size: 0.9rem; }
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
                <div id="filePreview" style="color: #51cf66; font-weight:bold; margin-bottom: 20px; display: none;"></div>
                
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
        function startLoading() {{ document.getElementById('submitBtn').innerHTML = "⚡ PROCESSING..."; }}
        const dropZone = document.getElementById('dropZone');
        const fileInput = document.getElementById('fileInput');
        const filePreview = document.getElementById('filePreview');
        dropZone.addEventListener('click', () => fileInput.click());
        fileInput.addEventListener('change', () => {{
            if (fileInput.files.length) {{
                filePreview.innerHTML = "✅ Photo Attached"; filePreview.style.display = 'block';
                dropZone.classList.add('active');
            }}
        }});
    </script>
</body>
</html>
"""

# RESULT PAGE WITH "SHARE IMAGE" LOGIC
HTML_RESULT = f"""
<!DOCTYPE html>
<html>
<head><title>Sealed</title><meta name="viewport" content="width=device-width, initial-scale=1">{STYLE}</head>
<body>
    <div class="container">
        <h1>Sealed</h1>
        <div class="card">
            <h3 class="success" style="margin-top:0;">✨ Secret Secured</h3>
            <p style="font-size:0.9rem; color:#aaa; margin-bottom:10px;">Share this:</p>
            <input type="text" value="{{{{ share_link }}}}" readonly onclick="this.select()" style="margin-bottom:20px; text-align:center;">
            
            <div style="background:white; padding:15px; border-radius:15px; display:inline-block; animation: popIn 0.5s;">
                <img id="qrImage" src="data:image/png;base64,{{{{ qr_b64 }}}}" style="width:180px; margin:0; display:block;">
            </div>
            
            <button onclick="shareQR()" class="btn" style="background:#25D366; color:#fff; margin-top:20px;">
                Share QR () 📤
            </button>
            
            <br><br>
            <a href="/">Create Another</a>
        </div>
    </div>

    <script>
        async function shareQR() {{
            const img = document.getElementById('qrImage');
            const base64Response = await fetch(img.src);
            const blob = await base64Response.blob();
            const file = new File([blob], "secret_qr.png", {{ type: "image/png" }});

            if (navigator.share && navigator.canShare({{ files: [file] }})) {{
                navigator.share({{
                    files: [file],
                    title: 'Cupid Secret',
                    text: 'Scan this to see my secret message! 🤫'
                }}).catch(console.error);
            }} else {{
                const link = document.createElement('a');
                link.href = img.src;
                link.download = "secret_qr.png";
                link.click();
                alert("QR Saved! You can now send it on WhatsApp.");
            }}
        }}
    </script>
</body>
</html>
"""

# REPLY RESULT PAGE WITH "SHARE IMAGE" LOGIC
HTML_REPLY_RESULT = f"""
<!DOCTYPE html>
<html>
<head><title>Reply Sealed</title><meta name="viewport" content="width=device-width, initial-scale=1">{STYLE}</head>
<body>
    <div class="container">
        <h1>Reply Sealed</h1>
        <div class="card">
            <h3 class="success" style="margin-top:0;">✨ Reply Ready</h3>
            <p style="font-size:0.9rem; color:#aaa; margin-bottom:15px;">
                Send this back to them:
            </p>
            
            <input type="text" value="{{{{ share_link }}}}" readonly onclick="this.select()" style="margin-bottom:20px; text-align:center; border:1px solid #51cf66;">
            
            <div style="background:white; padding:15px; border-radius:15px; display:inline-block;">
                <img id="qrImage" src="data:image/png;base64,{{{{ qr_b64 }}}}" style="width:150px; margin:0; display:block;">
            </div>

            <button onclick="shareQR()" class="btn" style="background:#25D366; color:#fff; margin-top:20px;">
                Share QR (WhatsApp) 📤
            </button>
            
            <br><br>
            <a href="/" style="font-size:0.8rem;">Start New Chat</a>
        </div>
    </div>

    <script>
        async function shareQR() {{
            const img = document.getElementById('qrImage');
            const base64Response = await fetch(img.src);
            const blob = await base64Response.blob();
            const file = new File([blob], "reply_qr.png", {{ type: "image/png" }});

            if (navigator.share && navigator.canShare({{ files: [file] }})) {{
                navigator.share({{
                    files: [file],
                    title: 'Reply',
                    text: 'Here is my reply! 🤫'
                }}).catch(console.error);
            }} else {{
                const link = document.createElement('a');
                link.href = img.src;
                link.download = "reply_qr.png";
                link.click();
                alert("QR Saved! You can now send it on WhatsApp.");
            }}
        }}
    </script>
</body>
</html>
"""

HTML_REVEAL = f"""
<!DOCTYPE html>
<html>
<head><title>Secret Awaits</title><meta name="viewport" content="width=device-width, initial-scale=1">{STYLE}</head>
<body>
    <div class="container">
        <div class="envelope-icon">✉️</div>
        <div class="card">
            <h2 style="margin-top:0;">A Secret Awaits</h2>
            <p style="font-size:1.1rem; line-height:1.5;">{{{{ warning_text }}}}</p>
            <br>
            <form action="/reveal/{{{{ link_id }}}}" method="POST">
                <button type="submit" class="btn">Break the Seal</button>
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
                <img src="data:image/jpeg;base64,{{{{ image_data }}}}" alt="Secret Image" class="reveal-image">
            {{% endif %}}
            
            {{% if message %}}
                <div class="protected-text">“{{{{ message }}}}”</div>
            {{% endif %}}
            
            <p style="margin-top:20px; color:#888; font-size:0.9rem; font-style:italic;">{{{{ footer_text }}}}</p>
            
            <button onclick="showReply()" class="btn" style="background:transparent; border:1px solid #fff; color:#fff; margin-top:20px;">
                ↩️ Reply to Anonymous
            </button>

            <div id="replyBox" class="reply-section">
                <h3 style="margin-top:0; font-size:1.2rem;">Write a Reply</h3>
                <form action="/reply_create" method="POST">
                    <textarea name="message" rows="3" placeholder="Type your reply..." required></textarea>
                    <button type="submit" class="btn" style="background:#fff; color:#000;">Seal & Get Link 📤</button>
                </form>
            </div>

        </div>
    </div>
    <script>
        function showReply() {{
            document.getElementById('replyBox').style.display = 'block';
            window.scrollTo(0, document.body.scrollHeight);
        }}
    </script>
</body>
</html>
"""

HTML_ERROR = f"""
<!DOCTYPE html>
<html>
<head><title>Error</title><meta name="viewport" content="width=device-width, initial-scale=1">{STYLE}</head>
<body>
    <div class="container">
        <h1 style="font-size:4rem; animation: popIn 0.5s;">{{{{ icon }}}}</h1>
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

# --- 4. LOGIC ---
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
             return render_template_string(HTML_ERROR, icon="⚠️", title="Too Big", text="Photo too large.")
    
    if not img_b64 and len(msg.strip()) < 1:
        return render_template_string(HTML_ERROR, icon="⚠️", title="Empty", text="Add message or photo.")

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

@app.route("/reply_create", methods=["POST"])
def reply_create():
    msg = request.form.get("message", "")
    link_id = secrets.token_urlsafe(8)
    expiry = int((datetime.now() + timedelta(minutes=15)).timestamp())
    
    doc = {
        "message": msg,
        "image_data": None,
        "created_at": int(time.time()),
        "expiry": expiry,
        "opened": False,
        "one_time": True 
    }
    db.collection("links").document(link_id).set(doc)
    
    base = request.host_url.rstrip("/")
    share_link = f"{base}/secret/{link_id}"
    qr = qrcode.make(share_link)
    buf = io.BytesIO()
    qr.save(buf, format="PNG")
    qr_b64 = base64.b64encode(buf.getvalue()).decode()
    
    return render_template_string(HTML_REPLY_RESULT, share_link=share_link, qr_b64=qr_b64)

@app.route("/secret/<link_id>", methods=["GET"])
def view_secret(link_id):
    doc_ref = db.collection("links").document(link_id)
    doc = doc_ref.get()
    if not doc.exists: return render_template_string(HTML_ERROR, icon="💨", title="Invalid", text="Link not found.")
    data = doc.to_dict()
    if int(time.time()) > data['expiry']: return render_template_string(HTML_ERROR, icon="⏳", title="Expired", text="Secret expired.")
    if data['one_time'] and data['opened']: return render_template_string(HTML_ERROR, icon="💔", title="Gone", text="Already viewed.")
    warn = "⚠️ Vanishes after 1 view." if data['one_time'] else "✨ Available until expiry."
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
    app.run(debug=False)
