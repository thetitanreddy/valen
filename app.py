from flask import Flask, request, render_template_string, redirect, url_for
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
# This looks for the 'FIREBASE_KEY_JSON' environment variable first (for Vercel).
# If not found, it tries to load 'firebase_key.json' locally.
if not firebase_admin._apps:
    if os.environ.get("FIREBASE_KEY_JSON"):
        # Load from Environment Variable (Vercel/Render)
        cred_dict = json.loads(os.environ.get("FIREBASE_KEY_JSON"))
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
    else:
        # Load from Local File (Computer)
        try:
            cred = credentials.Certificate("firebase_key.json")
            firebase_admin.initialize_app(cred)
        except Exception as e:
            print(f"🔥 Firebase setup failed: {e}")

db = firestore.client()

# --- 2. HTML STYLES & TEMPLATES ---

STYLE = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Cinzel+Decorative:wght@700&family=Lato:wght@300;400&display=swap');
body {
    background-color: #121212;
    color: #e0e0e0;
    font-family: 'Lato', sans-serif;
    margin: 0;
    padding: 0;
    display: flex;
    justify-content: center;
    align-items: center;
    min-height: 100vh;
}
.container {
    width: 90%;
    max-width: 500px;
    text-align: center;
    padding: 20px;
}
h1 {
    font-family: 'Cinzel Decorative', cursive;
    color: #ffffff;
    font-size: 2.5rem;
    margin-bottom: 30px;
}
.card {
    background-color: rgba(255, 255, 255, 0.05);
    padding: 30px;
    border-radius: 15px;
    border: 1px solid #333;
    backdrop-filter: blur(10px);
}
textarea, input[type="text"], input[type="number"], select {
    width: 100%;
    background-color: #2b2b2b;
    border: 1px solid #444;
    color: white;
    padding: 12px;
    border-radius: 8px;
    margin-bottom: 15px;
    font-family: 'Lato', sans-serif;
    box-sizing: border-box;
    font-size: 1rem;
}
.btn {
    background: linear-gradient(180deg, #4b4b4b, #1e1e1e);
    color: #fff;
    border: 1px solid #666;
    padding: 15px 30px;
    border-radius: 30px;
    cursor: pointer;
    font-family: 'Cinzel Decorative', cursive;
    font-size: 1.1rem;
    width: 100%;
    margin-top: 10px;
    transition: 0.3s;
    text-transform: uppercase;
    letter-spacing: 1px;
}
.btn:hover { transform: scale(1.02); border-color: #fff; }

/* ANTI-COPY PROTECTION */
.protected-text {
    -webkit-user-select: none; /* Safari */
    -ms-user-select: none; /* IE */
    user-select: none; /* Standard */
    cursor: default;
}

img { max-width: 100%; border-radius: 8px; margin-bottom: 20px; }
.error { color: #ff6b6b; }
.success { color: #51cf66; }
.qr-box { background: white; padding: 10px; display: inline-block; border-radius: 8px; margin-top: 20px;}
a { color: #aaa; text-decoration: none; font-size: 0.9rem; }
a:hover { color: #fff; }
</style>
"""

# PAGE: CREATE SECRET
HTML_CREATE = f"""
<!DOCTYPE html>
<html>
<head><title>Cupid's Secret</title><meta name="viewport" content="width=device-width, initial-scale=1">{STYLE}</head>
<body>
    <div class="container">
        <h1>Cupid's Secret</h1>
        <div class="card">
            <h3 style="margin-top:0;">Compose a timeless message</h3>
            <form action="/create" method="POST" enctype="multipart/form-data">
                <textarea name="message" rows="4" placeholder="Write your secret here..." maxlength="300"></textarea>
                
                <p style="text-align:left; font-size:0.9rem; margin-bottom:5px; color:#ccc;">Attach Photo (Optional)</p>
                <input type="file" name="file" accept="image/*" style="background:#2b2b2b; padding:10px;">
                
                <div style="display:flex; gap:10px;">
                    <input type="number" name="duration_val" value="15" min="1" style="width:50%;">
                    <select name="duration_unit" style="width:50%;">
                        <option value="Minutes">Minutes</option>
                        <option value="Hours">Hours</option>
                        <option value="Days">Days</option>
                    </select>
                </div>

                <label style="display:flex; align-items:center; gap:10px; font-size:0.9rem; margin-bottom:20px; cursor:pointer;">
                    <input type="checkbox" name="one_time" checked style="width:auto; margin:0;">
                    Vanish after one view?
                </label>

                <button type="submit" class="btn">Seal & Generate Link 📜</button>
            </form>
        </div>
    </div>
</body>
</html>
"""

# PAGE: RESULT (LINK & QR)
HTML_RESULT = f"""
<!DOCTYPE html>
<html>
<head><title>Sealed</title><meta name="viewport" content="width=device-width, initial-scale=1">{STYLE}</head>
<body>
    <div class="container">
        <h1>Sealed</h1>
        <div class="card">
            <h3 class="success">✨ Message Secured</h3>
            <p style="font-size:0.9rem; color:#aaa;">Share this link:</p>
            <input type="text" value="{{{{ share_link }}}}" readonly onclick="this.select()">
            
            <div class="qr-box">
                <img src="data:image/png;base64,{{{{ qr_b64 }}}}" style="width:150px; margin:0;">
            </div>
            <br><br>
            <a href="/">Compose Another</a>
        </div>
    </div>
</body>
</html>
"""

# PAGE: ENVELOPE (LOCKED)
HTML_ENVELOPE = f"""
<!DOCTYPE html>
<html>
<head><title>A Secret Awaits</title><meta name="viewport" content="width=device-width, initial-scale=1">{STYLE}</head>
<body>
    <div class="container">
        <h1>✉️</h1>
        <div class="card">
            <h2>A Secret Awaits</h2>
            <p>{{{{ warning_text }}}}</p>
            <br>
            <form action="/reveal/{{{{ link_id }}}}" method="POST">
                <button type="submit" class="btn">Break the Seal</button>
            </form>
        </div>
    </div>
</body>
</html>
"""

# PAGE: REVEALED MESSAGE
HTML_MESSAGE = f"""
<!DOCTYPE html>
<html>
<head><title>Revealed</title><meta name="viewport" content="width=device-width, initial-scale=1">{STYLE}</head>
<body>
    <div class="container">
        <h1>💖</h1>
        <div class="card">
            {{% if image_data %}}
                <img src="data:image/jpeg;base64,{{{{ image_data }}}}" alt="Secret Image">
            {{% endif %}}
            
            <div class="protected-text" style="font-family: 'Cinzel Decorative', cursive; font-size: 1.8rem; margin: 30px 0; line-height: 1.4;">
                “{{{{ message }}}}”
            </div>
            
            <p style="opacity:0.6; font-style: italic;">— Anonymous</p>
            <hr style="border-color:#333; margin: 20px 0;">
            <p class="success" style="font-size:0.8rem;">{{{{ footer_text }}}}</p>
            
            <br>
            <a href="/">Send your own</a>
        </div>
    </div>
</body>
</html>
"""

# PAGE: ERROR
HTML_ERROR = f"""
<!DOCTYPE html>
<html>
<head><title>Gone</title><meta name="viewport" content="width=device-width, initial-scale=1">{STYLE}</head>
<body>
    <div class="container">
        <h1>{{{{ icon }}}}</h1>
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

# --- 3. HELPER FUNCTIONS ---
def process_image(file):
    """Compresses image to fit in DB (~1MB limit)"""
    try:
        img = Image.open(file)
        if img.mode in ("RGBA", "P"): img = img.convert("RGB")
        
        # Resize if too big
        max_dim = 800
        if max(img.size) > max_dim:
            img.thumbnail((max_dim, max_dim))
            
        buf = io.BytesIO()
        img.save(buf, format='JPEG', quality=70, optimize=True)
        b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
        
        # Firestore limit is 1MB (1,048,576 bytes). 
        # Base64 increases size by ~33%, so we aim for < 750KB raw.
        if len(b64) > 1000000: 
            return None 
        return b64
    except: 
        return None

# --- 4. FLASK ROUTES ---

@app.route("/", methods=["GET"])
def home():
    return render_template_string(HTML_CREATE)

@app.route("/create", methods=["POST"])
def create():
    msg = request.form.get("message", "")
    f = request.files.get("file")
    
    # Image Logic
    img_b64 = None
    if f and f.filename != '':
        img_b64 = process_image(f)
        if not img_b64 and len(msg) < 1:
             return render_template_string(HTML_ERROR, icon="⚠️", title="Too Large", text="Image is too big or message is empty.")

    # Timer Logic
    try:
        val = int(request.form.get("duration_val", 15))
    except:
        val = 15
        
    unit = request.form.get("duration_unit", "Minutes")
    mult = 1
    if unit == "Hours": mult = 60
    elif unit == "Days": mult = 1440
    minutes = val * mult
    
    # Save to Firestore
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
    
    # Create Links
    base = request.host_url.rstrip("/")
    share_link = f"{base}/secret/{link_id}"
    
    # QR Code
    qr = qrcode.make(share_link)
    buf = io.BytesIO()
    qr.save(buf, format="PNG")
    qr_b64 = base64.b64encode(buf.getvalue()).decode()
    
    return render_template_string(HTML_RESULT, share_link=share_link, qr_b64=qr_b64)

@app.route("/secret/<link_id>", methods=["GET"])
def view_secret(link_id):
    doc_ref = db.collection("links").document(link_id)
    doc = doc_ref.get()
    
    # 1. Check Existence
    if not doc.exists:
        return render_template_string(HTML_ERROR, icon="💨", title="Invalid Link", text="The wind has blown this away.")
    
    data = doc.to_dict()
    
    # 2. Check Expiry
    if int(time.time()) > data['expiry']:
        return render_template_string(HTML_ERROR, icon="⏳", title="Expired", text="This message is lost to time.")
    
    # 3. Check if One-Time & Opened
    if data['one_time'] and data['opened']:
         return render_template_string(HTML_ERROR, icon="💔", title="Already Seen", text="This secret has vanished forever.")
         
    # 4. Show Envelope
    warn = "⚠️ Warning: Vanishes forever after reading." if data['one_time'] else "✨ Available until expiry."
    return render_template_string(HTML_ENVELOPE, warning_text=warn, link_id=link_id)

@app.route("/reveal/<link_id>", methods=["POST"])
def reveal(link_id):
    doc_ref = db.collection("links").document(link_id)
    doc = doc_ref.get()
    
    if not doc.exists: 
        return render_template_string(HTML_ERROR, icon="❌", title="Error", text="Not found.")
        
    data = doc.to_dict()
    
    # Security Checks Again
    if int(time.time()) > data['expiry']:
        return render_template_string(HTML_ERROR, icon="⏳", title="Expired", text="Too late.")
    if data['one_time'] and data['opened']:
        return render_template_string(HTML_ERROR, icon="💔", title="Already Seen", text="Already vanished.")

    # Mark as Opened
    doc_ref.update({"opened": True})
    
    footer = "This secret is now locked in the past." if data['one_time'] else "You can return to this memory until it expires."
    
    return render_template_string(HTML_MESSAGE, 
                                  message=data['message'], 
                                  image_data=data['image_data'],
                                  footer_text=footer)

if __name__ == "__main__":
    app.run(debug=True)
