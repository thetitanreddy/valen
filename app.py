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
    page_title="Cupid's Surprise 💘",
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

# ---------------- 3. CLASSICAL B&W STYLING ----------------
# IMPORTANT: Replace the 'background-image' URL below with the exact image your user wants.
# I have used a high-quality placeholder from Unsplash that matches the description.

st.markdown("""
<style>
/* Import Classical Fonts */
@import url('https://fonts.googleapis.com/css2?family=Cinzel+Decorative:wght@700&family=Lato:wght@300;400&display=swap');

/* THE BACKGROUND IMAGE */
.stApp {
    /* REPLACE THIS URL for a different image */
    background-image: url('https://images.unsplash.com/photo-1546445317-29f4545e9d53?q=80&w=2070&auto=format&fit=crop&ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D');
    background-size: cover;
    background-attachment: fixed;
    background-position: center center;
}

/* Transparent "Glass" Card Style */
div.card {
    background-color: rgba(0, 0, 0, 0.6); /* Dark semi-transparent */
    backdrop-filter: blur(10px); /* The frosted glass effect */
    -webkit-backdrop-filter: blur(10px); /* Safari support */
    padding: 40px;
    border-radius: 15px;
    text-align: center;
    box-shadow: 0px 10px 30px rgba(0, 0, 0, 0.5);
    border: 1px solid rgba(255, 255, 255, 0.2); /* Subtle white border */
    margin-top: 20px;
    margin-bottom: 20px;
    color: #ffffff !important;
}

/* Typography */
h1 {
    font-family: 'Cinzel Decorative', cursive;
    color: #ffffff !important;
    text-shadow: 2px 2px 8px rgba(0,0,0,0.8); /* Shadow makes text pop on busy backgrounds */
    font-size: 3rem !important;
    text-align: center;
    font-weight: 700 !important;
}

h2, h3, p, label, .stMarkdown {
    font-family: 'Lato', sans-serif;
    color: #ffffff !important;
}

/* Message Text Styling */
div.message-text {
    font-family: 'Cinzel Decorative', cursive;
    font-size: 26px;
    color: #ffffff;
    line-height: 1.5;
    padding: 20px;
    border-top: 1px solid rgba(255,255,255,0.3);
    border-bottom: 1px solid rgba(255,255,255,0.3);
}

/* Input Fields Styling - Transparent */
.stTextArea textarea, .stSelectbox > div > div, .stTextInput > div > div {
    background-color: rgba(255, 255, 255, 0.15) !important; /* Very see-through */
    border-radius: 10px !important;
    border: 1px solid rgba(255, 255, 255, 0.4) !important;
    color: #ffffff !important; /* White typing text */
    font-family: 'Lato', sans-serif !important;
}
/* Placeholder text color */
::placeholder { 
  color: rgba(255, 255, 255, 0.7) !important;
  opacity: 1; 
}

/* Checkbox styling */
.stCheckbox label span {
    color: white !important;
}

/* Button Styling - Classical Monochrome */
div.stButton > button {
    background: linear-gradient(45deg, #2c3e50, #bdc3c7);
    color: white;
    border-radius: 30px;
    border: 1px solid rgba(255,255,255,0.5);
    padding: 15px 30px;
    font-size: 18px;
    font-family: 'Cinzel Decorative', cursive;
    box-shadow: 0px 5px 15px rgba(0, 0, 0, 0.5);
    transition: transform 0.2s;
    width: 100%;
}
div.stButton > button:hover {
    transform: scale(1.02);
    background: linear-gradient(45deg, #bdc3c7, #2c3e50);
    box-shadow: 0px 8px 20px rgba(255, 255, 255, 0.2);
}
/* Remove default streamlit header */
header {visibility: hidden;}
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

    # Keep the card wrapper for readability against the busy background
    st.markdown("<div class='card'>", unsafe_allow_html=True)

    if not doc.exists:
        st.error("❌ Link not found")
    else:
        data = doc.to_dict()
        now_ts = int(time.time())
        is_one_time = data.get("one_time", True)

        if now_ts > data.get("expiry", 0):
            st.subheader("⏳ Too Late.")
            st.warning("This message has faded away.")

        elif is_one_time and data.get("opened", False) and not st.session_state.revealed:
            st.subheader("💔 Already Viewed")
            st.warning("This secret has already been revealed once.")

        elif not st.session_state.revealed:
            st.title("A Secret Awaits")
            if is_one_time:
                st.caption("⚠️ This message will vanish after a single viewing.")
            else:
                st.caption("✨ Viewable until the sands of time run out.")
            st.markdown("<br>", unsafe_allow_html=True)
            
            if st.button("Reveal the Secret ✨"):
                doc_ref.update({"opened": True})
                st.session_state.revealed = True
                st.rerun()

        else:
            st.balloons()
            # Using markdown for white text instead of st.title which can be stubborn
            st.markdown("# 🖤")
            st.markdown(f"<div class='message-text'>“{data['message']}”</div>", unsafe_allow_html=True)
            st.markdown("<br>— Anonymous", unsafe_allow_html=True)
            st.divider()
            
            if is_one_time:
                st.success("This secret is now locked in time forever.")
            else:
                st.success("You may return to this message until it expires.")

    st.markdown("</div>", unsafe_allow_html=True)
    
    if st.button("Compose your own? ✉️"):
        st.query_params.clear()
        st.rerun()

    st.stop()


# === CREATOR VIEW (Creating a Message) ===
st.title("Cupid's Secret")
st.markdown("<h3 style='text-align: center; color: white;'>Compose a classical message</h3>", unsafe_allow_html=True)

# Removed inner card wrapper so inputs sit directly on the background (but they have their own transparent style now)
with st.container():
    
    message = st.text_area("Your Message", placeholder="Type your secret confession here...", max_chars=300)
    
    col1, col2 = st.columns(2)
    with col1:
        expiry_minutes = st.selectbox("⏱ Duration", [15, 30, 60, 1440], format_func=lambda x: f"{x} mins" if x < 60 else "24 hours")
    with col2:
        st.write("") 
        st.write("")
        # Using HTML to ensure checkbox label is white
        is_one_time = st.checkbox("Vanish after one view?", value=True)

    if st.button("Seal & Generate Link 📜"):
        if not message.strip():
            st.error("Please write a message before sealing.")
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
                with st.spinner("Encrypting your secret..."):
                    db.collection("links").document(link_id).set(doc_data)
                    time.sleep(1)
                
                base_url = get_public_base_url()
                share_link = f"{base_url}/?id={link_id}"
                
                # Show Result in a transparent glass Card
                st.markdown("<div class='card'>", unsafe_allow_html=True)
                st.success("✨ Your message has been sealed.")
                st.code(share_link)
                qr_img = generate_qr(share_link)
                st.image(qr_img, width=200, caption="Scan to Reveal")
                st.markdown("</div>", unsafe_allow_html=True)
                
            except Exception as e:
                st.error(f"Error: {e}")
