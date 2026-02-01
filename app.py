import streamlit as st
import qrcode
import io
import secrets
import time
from datetime import datetime, timedelta
import firebase_admin
from firebase_admin import credentials, firestore

# ---------------- 1. PAGE CONFIG ----------------
st.set_page_config(
    page_title="Cupid's Secret",
    page_icon="🐎",
    layout="centered"
)

# ---------------- 2. FIREBASE SETUP ----------------
# Checks for existing app to prevent connection errors on reload
if not firebase_admin._apps:
    # Try loading from Streamlit Cloud Secrets (Deployment)
    if "firebase" in st.secrets:
        key_dict = dict(st.secrets["firebase"])
        cred = credentials.Certificate(key_dict)
        firebase_admin.initialize_app(cred)
    
    # Fallback to local file (Local Testing)
    else:
        try:
            cred = credentials.Certificate("firebase_key.json")
            firebase_admin.initialize_app(cred)
        except:
            st.error("🔥 Firebase setup failed. Check secrets or key file.")
            st.stop()

db = firestore.client()

# ---------------- 3. CLASSICAL B&W STYLING ----------------
st.markdown("""
<style>
/* 1. Import Classical Fonts (Cinzel for titles, Lato for text) */
@import url('https://fonts.googleapis.com/css2?family=Cinzel+Decorative:wght@700&family=Lato:wght@300;400&display=swap');

/* 2. THE BACKGROUND (Running Horses in B&W) */
.stApp {
    background-image: url('https://images.unsplash.com/photo-1506504287829-9c5952c4aa37?q=80&w=2070&auto=format&fit=crop');
    background-size: cover;
    background-attachment: fixed;
    background-position: center center;
}

/* 3. GLASSMORPHISM CARD (Transparent Dark Glass) */
div.card {
    background-color: rgba(0, 0, 0, 0.65); /* Dark see-through */
    backdrop-filter: blur(12px); /* Blur effect */
    -webkit-backdrop-filter: blur(12px);
    padding: 40px;
    border-radius: 15px;
    text-align: center;
    box-shadow: 0px 10px 40px rgba(0, 0, 0, 0.8);
    border: 1px solid rgba(255, 255, 255, 0.15); /* Subtle border */
    margin-top: 20px;
    margin-bottom: 20px;
    color: #ffffff !important;
}

/* 4. TYPOGRAPHY */
h1 {
    font-family: 'Cinzel Decorative', cursive;
    color: #ffffff !important;
    text-shadow: 0px 4px 10px rgba(0,0,0,0.9);
    font-size: 3.5rem !important;
    text-align: center;
    font-weight: 700 !important;
}

h2, h3, p, label, .stMarkdown, .stCheckbox {
    font-family: 'Lato', sans-serif;
    color: #ffffff !important;
    text-shadow: 0px 2px 4px rgba(0,0,0,0.8);
}

/* 5. INPUT FIELDS (Transparent) */
.stTextArea textarea, .stSelectbox > div > div, .stTextInput > div > div {
    background-color: rgba(20, 20, 20, 0.6) !important;
    border-radius: 8px !important;
    border: 1px solid rgba(255, 255, 255, 0.3) !important;
    color: #ffffff !important;
    font-family: 'Lato', sans-serif !important;
}
/* Dropdown menu items */
ul[data-testid="stSelectboxVirtualDropdown"] {
    background-color: #2b2b2b !important;
}

/* Placeholder Color */
::placeholder { 
  color: rgba(255, 255, 255, 0.6) !important;
}

/* 6. BUTTON STYLING (Classical Metallic) */
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
}
div.stButton > button:hover {
    transform: scale(1.02);
    background: linear-gradient(180deg, #5e5e5e, #333333);
    border-color: #ffffff;
    color: #ffffff;
    box-shadow: 0px 0px 20px rgba(255, 255, 255, 0.2);
}

/* Hide Streamlit Header/Footer */
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

# ---------------- 5. APP LOGIC ----------------
query = st.query_params

# === RECEIVER VIEW (Reading a Message) ===
if "id" in query:
    link_id = query["id"]
    
    if "revealed" not in st.session_state:
        st.session_state.revealed = False

    doc_ref = db.collection("links").document(link_id)
    doc = doc_ref.get()

    # Glass Card Wrapper for Receiver
    st.markdown("<div class='card'>", unsafe_allow_html=True)

    if not doc.exists:
        st.error("❌ The wind has blown this message away. (Invalid Link)")
    else:
        data = doc.to_dict()
        now_ts = int(time.time())
        is_one_time = data.get("one_time", True)

        # 1. Check Expiry
        if now_ts > data.get("expiry", 0):
            st.title("⏳")
            st.subheader("Lost to Time")
            st.warning("This message has expired.")

        # 2. Check Opened (If One-Time is active)
        elif is_one_time and data.get("opened", False) and not st.session_state.revealed:
            st.title("💔")
            st.subheader("Already Revealed")
            st.warning("This secret has vanished after being seen.")

        # 3. Ready to Reveal
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

        # 4. Show Message
        else:
            st.balloons()
            # We use HTML directly for better font control
            st.markdown(f"<h2 style='font-family: Cinzel Decorative; font-size: 32px; color: white;'>“{data['message']}”</h2>", unsafe_allow_html=True)
            st.markdown("<p style='opacity: 0.8;'>— Anonymous</p>", unsafe_allow_html=True)
            
            st.divider()
            
            if is_one_time:
                st.success("This secret is now locked in the past.")
            else:
                st.success("You can return to this memory until it expires.")

    st.markdown("</div>", unsafe_allow_html=True)
    
    if st.button("Compose Your Own"):
        st.query_params.clear()
        st.rerun()

    st.stop()


# === CREATOR VIEW (Creating a Message) ===
st.title("Cupid's Secret")
st.markdown("<h3 style='text-align: center; color: rgba(255,255,255,0.8); font-size: 1.2rem;'>Compose a timeless message</h3>", unsafe_allow_html=True)

# NO CARD WRAPPER HERE - Inputs sit directly on background (styled transparently via CSS)
with st.container():
    
    st.markdown("<br>", unsafe_allow_html=True)
    message = st.text_area("Your Confession", placeholder="Write your secret here...", max_chars=300)
    
    col1, col2 = st.columns(2)
    with col1:
        expiry_minutes = st.selectbox("Duration", [15, 30, 60, 1440], format_func=lambda x: f"{x} Minutes" if x < 60 else "24 Hours")
    with col2:
        st.write("") 
        st.write("")
        # Checkbox for Vanishing Mode
        is_one_time = st.checkbox("Vanish after one view?", value=True)

    st.markdown("<br>", unsafe_allow_html=True)

    if st.button("Seal & Generate Link 📜"):
        if not message.strip():
            st.error("The parchment cannot be empty.")
        else:
            link_id = secrets.token_urlsafe(8)
            expiry_ts = int((datetime.now() + timedelta(minutes=expiry_minutes)).timestamp())
            
            doc_data = {
                "message": message,
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
                
                # Show Result in a Glass Card for contrast
                st.markdown("<div class='card'>", unsafe_allow_html=True)
                st.success("✨ Your message has been sealed.")
                st.code(share_link)
                
                qr_img = generate_qr(share_link)
                st.image(qr_img, width=200, caption="Scan to Reveal")
                st.markdown("</div>", unsafe_allow_html=True)
                
            except Exception as e:
                st.error(f"Error: {e}")
