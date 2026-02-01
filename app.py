import streamlit as st
import qrcode
import io
import secrets
import time
import base64
from datetime import datetime, timedelta
from PIL import Image
import firebase_admin
from firebase_admin import credentials, firestore

# ---------------- 1. PAGE CONFIG ----------------
st.set_page_config(
    page_title="Cupid's Secret",
    page_icon="🐎",
    layout="centered"
)

# ---------------- 2. FIREBASE SETUP ----------------
if not firebase_admin._apps:
    if "firebase" in st.secrets:
        key_dict = dict(st.secrets["firebase"])
        cred = credentials.Certificate(key_dict)
        firebase_admin.initialize_app(cred)
    else:
        try:
            cred = credentials.Certificate("firebase_key.json")
            firebase_admin.initialize_app(cred)
        except:
            st.error("🔥 Firebase setup failed. Check secrets or key file.")
            st.stop()

db = firestore.client()

# ---------------- 3. CLEAN MATTE BLACK STYLING ----------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cinzel+Decorative:wght@700&family=Lato:wght@300;400&display=swap');

.stApp {
    background-color: #121212 !important;
    background-image: none !important;
}

h1 {
    font-family: 'Cinzel Decorative', cursive;
    color: #ffffff !important;
    font-size: 3.5rem !important;
    text-align: center;
    font-weight: 700 !important;
    margin-bottom: 30px !important;
}

h2, h3, p, label, .stMarkdown, .stCheckbox, .stCaption {
    font-family: 'Lato', sans-serif;
    color: #e0e0e0 !important;
}

.message-content {
    font-family: 'Cinzel Decorative', cursive;
    font-size: 32px;
    color: #ffffff;
    text-align: center;
    margin: 40px 0;
}

.stTextArea textarea, .stSelectbox > div > div, .stTextInput > div > div, .stNumberInput > div > div > input {
    background-color: #2b2b2b !important;
    border-radius: 8px !important;
    border: 1px solid #404040 !important;
    color: #ffffff !important;
    font-family: 'Lato', sans-serif !important;
}
ul[data-testid="stSelectboxVirtualDropdown"] {
    background-color: #2b2b2b !important;
    color: white !important;
}
::placeholder { color: #888888 !important; }

/* File Uploader Style */
div[data-testid="stFileUploader"] {
    background-color: #2b2b2b;
    border-radius: 10px;
    padding: 20px;
    border: 1px dashed #404040;
}

div.stButton > button {
    background: linear-gradient(180deg, #4b4b4b, #1e1e1e);
    color: #e0e0e0;
    border-radius: 30px;
    border: 1px solid rgba(255,255,255,0.2);
    padding: 15px 30px;
    font-size: 18px;
    font-family: 'Cinzel Decorative', cursive;
    box-shadow: 0px 5px 15px rgba(0, 0, 0, 0.5);
    transition: all 0.3s ease;
    width: 100%;
    text-transform: uppercase;
    letter-spacing: 2px;
    margin-top: 20px;
}
div.stButton > button:hover {
    transform: scale(1.02);
    background: linear-gradient(180deg, #5e5e5e, #333333);
    border-color: #ffffff;
    color: #ffffff;
    box-shadow: 0px 0px 20px rgba(255, 255, 255, 0.2);
}

header {visibility: hidden;}
footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ---------------- 4. HELPER FUNCTIONS ----------------
def get_public_base_url():
    headers = st.context.headers
    host = headers.get("host")
    proto = headers.get("x-forwarded-proto", "https")
    if not host: return "http://localhost:8501"
    return f"{proto}://{host}"

def generate_qr(data):
    qr = qrcode.make(data)
    buf = io.BytesIO()
    qr.save(buf, format="PNG")
    return buf.getvalue()

def process_image(uploaded_file):
    """Compresses image and converts to Base64 string"""
    try:
        image = Image.open(uploaded_file)
        if image.mode in ("RGBA", "P"):
            image = image.convert("RGB")
        
        max_width = 800
        if image.width > max_width:
            ratio = max_width / float(image.width)
            new_height = int((float(image.height) * float(ratio)))
            image = image.resize((max_width, new_height), Image.Resampling.LANCZOS)
        
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='JPEG', quality=70, optimize=True)
        img_byte_arr = img_byte_arr.getvalue()
        
        if len(img_byte_arr) > 950000:
            return None
            
        return base64.b64encode(img_byte_arr).decode('utf-8')
    except Exception as e:
        print(f"Error processing image: {e}")
        return None

# ---------------- 5. APP LOGIC ----------------
query = st.query_params

# === RECEIVER VIEW (Reading a Message) ===
if "id" in query:
    link_id = query["id"]
    
    if "revealed" not in st.session_state:
        st.session_state.revealed = False

    doc_ref = db.collection("links").document(link_id)
    doc = doc_ref.get()

    if not doc.exists:
        st.error("❌ The wind has blown this message away. (Invalid Link)")
    else:
        data = doc.to_dict()
        now_ts = int(time.time())
        is_one_time = data.get("one_time", True)

        if now_ts > data.get("expiry", 0):
            st.title("⏳")
            st.subheader("Lost to Time")
            st.warning("This message has expired.")

        elif is_one_time and data.get("opened", False) and not st.session_state.revealed:
            st.title("💔")
            st.subheader("Already Revealed")
            st.warning("This secret has vanished after being seen.")

        elif not st.session_state.revealed:
            st.title("✉️")
            st.subheader("A Secret Awaits You")
            
            if is_one_time:
                st.caption("⚠️ Warning: This message will vanish forever after you read it.")
            else:
                st.caption("✨ You may view this message until the time expires.")
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            if st.button("Break the Seal"):
                doc_ref.update({"opened": True})
                st.session_state.revealed = True
                st.rerun()

        else:
            st.balloons()
            
            if data.get("image_data"):
                try:
                    image_bytes = base64.b64decode(data["image_data"])
                    st.image(image_bytes, use_container_width=True)
                except:
                    st.error("Image corrupted.")

            st.markdown(f"<div class='message-content'>“{data['message']}”</div>", unsafe_allow_html=True)
            st.markdown("<p style='text-align: center; opacity: 0.8;'>— Anonymous</p>", unsafe_allow_html=True)
            
            st.divider()
            
            if is_one_time:
                st.success("This secret is now locked in the past.")
            else:
                st.success("You can return to this memory until it expires.")
    
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("Compose Your Own"):
        st.query_params.clear()
        st.rerun()

    st.stop()


# === CREATOR VIEW (Creating a Message) ===
st.title("Cupid's Secret")
st.markdown("<h3 style='text-align: center; color: rgba(255,255,255,0.8); font-size: 1.2rem;'>Compose a timeless message</h3>", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)
message = st.text_area("Your Confession", placeholder="Write your secret here...", max_chars=300)

# --- IMAGE UPLOADER IS HERE ---
uploaded_file = st.file_uploader("Attach a Photo (Optional)", type=['png', 'jpg', 'jpeg'])
# ------------------------------

col1, col2 = st.columns(2)
with col1:
    duration_options = ["15 Mins", "30 Mins", "1 Hr", "24 Hr", "Custom"]
    duration_choice = st.selectbox("Duration", duration_options)
    
    expiry_minutes = 15
    if duration_choice == "Custom":
        c_val, c_unit = st.columns([1, 1])
        with c_val:
            custom_val_str = st.text_input("Value", value="1", label_visibility="collapsed")
            if custom_val_str.isdigit(): custom_val = int(custom_val_str)
            else: custom_val = 1
        with c_unit:
            custom_unit = st.selectbox("Unit", ["Minutes", "Hours", "Days", "Months"], label_visibility="collapsed")
        if custom_unit == "Minutes": expiry_minutes = custom_val
        elif custom_unit == "Hours": expiry_minutes = custom_val * 60
        elif custom_unit == "Days": expiry_minutes = custom_val * 1440
        elif custom_unit == "Months": expiry_minutes = custom_val * 43200 
    elif duration_choice == "15 Mins": expiry_minutes = 15
    elif duration_choice == "30 Mins": expiry_minutes = 30
    elif duration_choice == "1 Hr": expiry_minutes = 60
    elif duration_choice == "24 Hr": expiry_minutes = 1440

with col2:
    st.write("") 
    st.write("")
    if duration_choice == "Custom": st.write("")
    is_one_time = st.checkbox("Vanish after one view?", value=True)

st.markdown("<br>", unsafe_allow_html=True)

if st.button("Seal & Generate Link 📜"):
    if not message.strip() and not uploaded_file:
        st.error("The parchment cannot be empty (add text or image).")
    else:
        # PROCESSING
        image_str = None
        if uploaded_file:
            with st.spinner("Compressing & Sealing Image..."):
                image_str = process_image(uploaded_file)
                if image_str is None:
                    st.error("Image is too large! Please try a smaller photo.")
                    st.stop()

        link_id = secrets.token_urlsafe(8)
        expiry_ts = int((datetime.now() + timedelta(minutes=expiry_minutes)).timestamp())
        
        doc_data = {
            "message": message,
            "image_data": image_str,
            "created_at": int(time.time()),
            "expiry": expiry_ts,
            "opened": False,
            "one_time": is_one_time
        }
        
        try:
            with st.spinner("Sealing your secret..."):
                db.collection("links").document(link_id).set(doc_data)
                time.sleep(0.5)
            
            base_url = get_public_base_url()
            share_link = f"{base_url}/?id={link_id}"
            
            st.success("✨ Your message has been sealed.")
            st.code(share_link)
            
            qr_img = generate_qr(share_link)
            col_l, col_c, col_r = st.columns([1,2,1])
            with col_c:
                 st.image(qr_img, width=200, caption="Scan to Reveal")
            
        except Exception as e:
            st.error(f"Error: {e}")
