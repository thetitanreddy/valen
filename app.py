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
    page_icon="💌",
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

# ---------------- 3. DELUXE STYLING ----------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Pacifico&family=Quicksand:wght@400;600&display=swap');

.stApp {
    background: linear-gradient(135deg, #ff9a9e 0%, #fecfef 99%, #fecfef 100%);
    background-attachment: fixed;
}

div.card {
    background-color: rgba(255, 255, 255, 0.95);
    padding: 40px;
    border-radius: 25px;
    text-align: center;
    box-shadow: 0px 15px 35px rgba(255, 65, 108, 0.2);
    border: 2px solid #fff;
    margin-top: 20px;
    margin-bottom: 20px;
}

h1 {
    font-family: 'Pacifico', cursive;
    color: #ff4757 !important;
    text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
    font-size: 3.5rem !important;
    text-align: center;
}

div.card h2 {
    font-family: 'Quicksand', sans-serif;
    color: #2f3542 !important;
    font-weight: 600;
}

div.message-text {
    font-family: 'Pacifico', cursive;
    font-size: 28px;
    color: #ff4757;
    line-height: 1.6;
    padding: 20px;
}

div.expiry-text {
    font-family: 'Quicksand', sans-serif;
    color: #a4b0be;
    font-size: 14px;
    margin-top: 20px;
}

/* Button Styling */
div.stButton > button {
    background: linear-gradient(45deg, #ff6b6b, #ff4757);
    color: white;
    border-radius: 30px;
    border: none;
    padding: 15px 30px;
    font-size: 18px;
    font-weight: bold;
    box-shadow: 0px 5px 15px rgba(255, 71, 87, 0.4);
    transition: transform 0.2s;
    width: 100%;
}
div.stButton > button:hover {
    transform: scale(1.05);
    box-shadow: 0px 8px 20px rgba(255, 71, 87, 0.6);
}
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

    st.markdown("<div class='card'>", unsafe_allow_html=True)

    if not doc.exists:
        st.error("❌ Link not found")
    else:
        data = doc.to_dict()
        now_ts = int(time.time())
        
        # Get settings (default to True for old links for safety)
        is_one_time = data.get("one_time", True)

        # 1. EXPIRED CHECK (Always applies)
        if now_ts > data.get("expiry", 0):
            st.title("⏳")
            st.subheader("Too Late!")
            st.warning("This message has expired.")

        # 2. ALREADY OPENED CHECK (Only if one-time view is enabled)
        elif is_one_time and data.get("opened", False) and not st.session_state.revealed:
            st.title("💔")
            st.subheader("Already Opened")
            st.warning("This secret message has self-destructed.")

        # 3. READY TO OPEN (The Envelope State)
        elif not st.session_state.revealed:
            st.title("💌")
            st.subheader("You have a secret message!")
            
            if is_one_time:
                st.caption("⚠️ Warning: You can only view this ONCE.")
            else:
                st.caption("✨ You can view this until the timer expires.")
                
            st.markdown("<br>", unsafe_allow_html=True)
            
            if st.button("Tap to Open Envelope ✨"):
                # Always mark as opened in DB so we know it was seen
                doc_ref.update({"opened": True})
                st.session_state.revealed = True
                st.rerun()

        # 4. REVEALED MESSAGE
        else:
            st.balloons()
            st.title("💖")
            st.markdown(f"<div class='message-text'>“{data['message']}”</div>", unsafe_allow_html=True)
            st.caption("— Anonymous")
            
            st.divider()
            expiry_date = datetime.fromtimestamp(data["expiry"])
            st.markdown(f"<div class='expiry-text'>🔒 Valid until: {expiry_date.strftime('%H:%M')}</div>", unsafe_allow_html=True)
            
            if is_one_time:
                st.success("This link is now locked forever.")
            else:
                st.success("You can refresh and read this again until time runs out.")

    st.markdown("</div>", unsafe_allow_html=True)
    
    if st.button("Send your own? 💘"):
        st.query_params.clear()
        st.rerun()

    st.stop()


# === CREATOR VIEW (Creating a Message) ===
st.title("Cupid's Surprise")
st.markdown("### Create a Secret Message")

with st.container():
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    
    message = st.text_area("💌 Your Secret Message", placeholder="I've had a crush on you for a while...", max_chars=300)
    
    col1, col2 = st.columns(2)
    with col1:
        expiry_minutes = st.selectbox("⏱ Expires in", [15, 30, 60, 1440], format_func=lambda x: f"{x} mins" if x < 60 else "24 hours")
    with col2:
        st.write("") 
        st.write("")
        # New Checkbox for One-Time View
        is_one_time = st.checkbox("💣 Self-destruct after viewing?", value=True)

    if st.button("Generate Link 💘"):
        if not message.strip():
            st.error("Please write a message!")
        else:
            link_id = secrets.token_urlsafe(8)
            expiry_ts = int((datetime.now() + timedelta(minutes=expiry_minutes)).timestamp())
            
            doc_data = {
                "message": message,
                "created_at": int(time.time()),
                "expiry": expiry_ts,
                "opened": False,
                "one_time": is_one_time  # Save the preference
            }
            
            try:
                with st.spinner("Encrypting your secret..."):
                    db.collection("links").document(link_id).set(doc_data)
                    time.sleep(1)
                
                base_url = get_public_base_url()
                share_link = f"{base_url}/?id={link_id}"
                
                st.success("✨ Secret Link Created!")
                st.code(share_link)
                
                qr_img = generate_qr(share_link)
                st.image(qr_img, width=200, caption="Scan to Open")
                
            except Exception as e:
                st.error(f"Error: {e}")

    st.markdown("</div>", unsafe_allow_html=True)
