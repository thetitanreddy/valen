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

/* DRAG & DROP ZONE STYLES */
.drop-zone {
    width: 100%;
    padding: 25px;
    border: 2px dashed #444;
    border-radius: 10px;
    background-color: #1e1e1e;
    color: #aaa;
    text-align: center;
    cursor: pointer;
    transition: 0.3s;
    box-sizing: border-box;
    margin-bottom: 15px;
}
.drop-zone:hover, .drop-zone.dragover {
    background-color: #2a2a2a;
    border-color: #777;
    color: #fff;
}
.drop-zone p { margin: 0; pointer-events: none; }

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
    text-decoration: none;
    display: inline-block;
    box-sizing: border-box;
}
.btn:hover { transform: scale(1.02); border-color: #fff; color: #fff; }

.btn-download {
    background: linear-gradient(180deg, #2c3e50, #000000);
    border-color: #3498db;
    margin-bottom: 20px;
}

/* ANTI-COPY PROTECTION */
.protected-text {
    -webkit-user-select: none;
    -ms-user-select: none;
    user-select: none;
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
            <form action="/create" method="POST" enctype="multipart/form-data" id="secretForm">
                <textarea name="message" rows="4" placeholder="Write your secret here..." maxlength="300"></textarea>
                
                <div class="drop-zone" id="dropZone">
                    <p>📂 Drag & Drop File<br><span style="font-size:0.8rem; opacity:0.6;">(PDF, Doc, Image - Max 750KB)</span></p>
                    <input type="file" name="file" id="fileInput" hidden>
                </div>
                <div id="filePreview" style="color: #51cf66; font-size: 0.9rem; margin-bottom: 15px; display: none;"></div>
                
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

    <script>
        const dropZone = document.getElementById('dropZone');
        const fileInput = document.getElementById('fileInput');
        const filePreview = document.getElementById('filePreview');

        dropZone.addEventListener('click', () => fileInput.click());

        fileInput.addEventListener('change', () => {{
            if (fileInput.files.length) {{
                filePreview.innerText = "✅ " + fileInput.files[0].name;
                filePreview.style.display = 'block';
                dropZone.style.borderColor = '#51cf66';
            }}
        }});

        dropZone.addEventListener('dragover', (e) => {{
            e.preventDefault();
            dropZone.classList.add('dragover');
        }});

        dropZone.addEventListener('dragleave', () => {{
            dropZone.classList.remove('dragover');
        }});

        dropZone.addEventListener('drop', (e) => {{
            e.preventDefault();
            dropZone.classList.remove('dragover');
            if (e.dataTransfer.files.length) {{
                fileInput.files = e.dataTransfer.files;
                filePreview.innerText = "✅ " + e.dataTransfer.files[0].name;
                filePreview.style.display = 'block';
                dropZone.style.borderColor = '#51cf66';
            }}
        }});
    </script>
</body>
</html>
"""

# PAGE: RESULT
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

# PAGE: ENVELOPE
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
            
            {{% if file_data %}}
                {{% if 'image' in file_type %}}
                    <img src="data:{{{{ file_type }}}};base64,{{{{ file_data }}}}" alt="Secret Image">
                {{% else %}}
                    <a href="data:{{{{ file_type }}}};base64,{{{{ file_data }}}}" download="{{{{ file_name }}}}" class="btn btn-download">
                        📥 Download {{{{ file_name }}}}
                    </a>
                {{% endif %}}
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
def process_file(file):
    """
    Handles ANY file type.
    - If Image: Resize & Compress to save space.
    - If Other: Read raw bytes (Check size limit).
    """
    try:
        # Check size (Seek to end, get position, seek back)
        file.seek(0, os.SEEK_END)
        size = file.tell()
        file.seek(0)
        
        # 750KB limit (approx) to be safe for Firestore 1MB limit
        if size > 750000:
            return None, "File too large. Max 750KB."

        filename = file.filename
        mime_type = file.content_type
        b64_data = ""

        # Optimization for Images
        if mime_type.startswith('image/'):
            try:
                img = Image.open(file)
                if img.mode in ("RGBA", "P"): img = img.convert("RGB")
                max_dim = 800
                if max(img.size) > max_dim:
                    img.thumbnail((max_dim, max_dim))
                
                buf = io.BytesIO()
                img.save(buf, format='JPEG', quality=70, optimize=True)
                b64_data = base64.b64encode(buf.getvalue()).decode('utf-8')
                # If we compressed it, update type/name to jpg
                mime_type = 'image/jpeg' 
            except:
                # Fallback if PIL fails (treat as normal file)
                file.seek(0)
                data = file.read()
                b64_data = base64.b64encode(data).decode('utf-8')
        else:
            # Generic File (PDF, Doc, etc.)
            data = file.read()
            b64_data = base64.b64encode(data).decode('utf-8')

        # Final DB Safety Check
        if len(b64_data) > 1048000:
             return None, "Encoded file too large for database."

        return {
            "data": b64_data,
            "name": filename,
            "type": mime_type
        }, None

    except Exception as e:
        print(f"File Error: {e}")
        return None, "Error processing file."

# --- 4. FLASK ROUTES ---
@app.route("/", methods=["GET"])
def home():
    return render_template_string(HTML_CREATE)

@app.route("/create", methods=["POST"])
def create():
    msg = request.form.get("message", "")
    f = request.files.get("file")
    
    file_info = None
    if f and f.filename != '':
        result, error = process_file(f)
        if error:
             return render_template_string(HTML_ERROR, icon="⚠️", title="Upload Failed", text=error)
        file_info = result

    if not file_info and len(msg) < 1:
         return render_template_string(HTML_ERROR, icon="⚠️", title="Empty", text="Write a message or attach a file.")

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
        "created_at": int(time.time()),
        "expiry": expiry,
        "opened": False,
        "one_time": one_time,
        # Save file details if they exist
        "file_data": file_info['data'] if file_info else None,
        "file_name": file_info['name'] if file_info else None,
        "file_type": file_info['type'] if file_info else None
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
    if not doc.exists: return render_template_string(HTML_ERROR, icon="💨", title="Invalid Link", text="The wind has blown this away.")
    data = doc.to_dict()
    if int(time.time()) > data['expiry']: return render_template_string(HTML_ERROR, icon="⏳", title="Expired", text="This message is lost to time.")
    if data['one_time'] and data['opened']: return render_template_string(HTML_ERROR, icon="💔", title="Already Seen", text="This secret has vanished forever.")
    warn = "⚠️ Warning: Vanishes forever after reading." if data['one_time'] else "✨ Available until expiry."
    return render_template_string(HTML_ENVELOPE, warning_text=warn, link_id=link_id)

@app.route("/reveal/<link_id>", methods=["POST"])
def reveal(link_id):
    doc_ref = db.collection("links").document(link_id)
    doc = doc_ref.get()
    if not doc.exists: return render_template_string(HTML_ERROR, icon="❌", title="Error", text="Not found.")
    data = doc.to_dict()
    if int(time.time()) > data['expiry']: return render_template_string(HTML_ERROR, icon="⏳", title="Expired", text="Too late.")
    if data['one_time'] and data['opened']: return render_template_string(HTML_ERROR, icon="💔", title="Already Seen", text="Already vanished.")
    
    doc_ref.update({"opened": True})
    
    footer = "This secret is now locked in the past." if data['one_time'] else "You can return to this memory until it expires."
    
    # Pass all file data to the template
    return render_template_string(HTML_MESSAGE, 
                                  message=data.get('message', ''), 
                                  file_data=data.get('file_data'),
                                  file_name=data.get('file_name'),
                                  file_type=data.get('file_type', ''),
                                  footer_text=footer)

if __name__ == "__main__":
    app.run(debug=True)
