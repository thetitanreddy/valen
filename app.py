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
# We check if Firebase is already initialized to prevent errors on Streamlit re-runs
if not firebase_admin._apps:
    # Try loading from Streamlit Cloud Secrets first (Best for deployment)
    if "firebase" in st.secrets:
        key_dict = dict(st.secrets["firebase"])
        cred = credentials.Certificate(key_dict)
        firebase_admin.initialize_app(cred)
    
    # Fallback to local file (Best for local testing)
    else:
        try:
            cred = credentials.Certificate("firebase_key.json")
            firebase_admin.initialize_app(cred)
        except Exception as e:
            st.error(f"🔥 Firebase setup failed: {e}")
            st.info("Make sure 'firebase_key.json' is in the folder OR secrets are set in Streamlit Cloud.")
            st.stop()

db = firestore.client()

# ---------------- 3. THEME & UI FIXES ----------------
# We store the toggle state in session_state so it doesn't reset on every click
if "theme_toggle" not in st.session_state:
    st.session_state.theme_toggle = False

def apply_theme():
    # Toggle button
    is_dark = st.toggle("🌗 Dark Mode", value=st.session_state.theme_toggle)
    st.session_state.theme_toggle = is_dark

    # Define Colors
    if is_dark:
        bg_color = "#0e1117"
        card_color = "#161b22"
        text_color = "#f0f6fc"
        border_color = "#30363d"
    else:
        bg_color = "#ffe6e6"  # Light pink background
        card_color = "#ffffff" # White card
        text_color = "#000000" # Black text
        border_color = "#e1e4e8"

    # CSS Injection with !important to force visibility
    st.markdown(f"""
    <style>
    .stApp {{
        background-color: {bg_color};
    }}
    div.card {{
        background-color: {card_color};
        padding: 30px;
        border-radius: 20px;
        text-align: center;
        color: {text_color} !important;
        box-shadow: 0px 10px 30px rgba(0,0,0,0.2);
        border: 1px solid {border_color};
    }}
    /* Force headers and text inside the card to inherit the correct color */
    div.card h1, div.card h2, div.card h3, div.card p, div.card span {{
        color: {text_color} !important;
    }}
    </style>
    """, unsafe_allow_html=True)

apply_theme()

# ---------------- 4. HELPER FUNCTIONS ----------------
def get_public_base_url():
    headers = st.context.headers
    host = headers.get("host")
    proto = headers.get("x-forwarded-proto", "https")
    
    # Fallback for localhost testing
    if not host:
        return "http://localhost:8501"
        
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
    
    # Fetch document from Firebase
    doc_ref = db.collection("links").document(link_id)
    doc = doc_ref.get()

    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("💖 You received a secret message")

    if not doc.exists:
        st.error("❌ Invalid or missing link ID.")
    else:
        data = doc.to_dict()
        now_ts = int(time.time())

        # 1. Check if already opened
        if data.get("opened", False):
            st.error("💔 This surprise has already been opened.")
            st.caption("This message was set to self-destruct after one view.")
        
        # 2. Check if expired
        elif now_ts > data.get("expiry", 0):
            st.error("⏳ This surprise has expired.")
            st.caption("You were too late!")
            
        # 3. Valid! Show Message
        else:
            # Mark as opened IMMEDIATELY in database
            doc_ref.update({"opened": True})
            
            # Show the content
            st.balloons()
            st.success(f"💌 {data['message']}")
            st.caption("Someone secretly likes you 😉")
            
            st.divider()
            
            # Show expiry info safely (No loops)
            expiry_date = datetime.fromtimestamp(data["expiry"])
            st.caption(f"🔒 Link auto-expires at: {expiry_date.strftime('%H:%M:%S')}")
            st.warning("⚠️ You can only see this ONCE. If you refresh, it will be gone.")

    st.markdown("</div>", unsafe_allow_html=True)
    
    # Button to go back to home
    if st.button("Create your own surprise?"):
        st.query_params.clear() 
        st.rerun()

    st.stop()


# === CREATOR VIEW (Creating a Message) ===
st.title("💘 Cupid's Surprise")
st.caption("Anonymous • One-time • Expiring Confessions")

with st.form("create_form"):
    message = st.text_area(
        "💌 Write your message",
        placeholder="Someone secretly likes you...",
        max_chars=300
    )

    expiry_minutes = st.selectbox(
        "⏱ Link expiry time",
        [5, 10, 30, 60, 1440],
        format_func=lambda x: f"{x} minutes" if x < 60 else f"{x//60} hour(s)"
    )
    
    submitted = st.form_submit_button("💘 Generate Surprise")

if submitted:
    if not message.strip():
        st.warning("Please write a message first!")
        st.stop()

    # Create data payload
    link_id = secrets.token_urlsafe(8)
    expiry_ts = int((datetime.now() + timedelta(minutes=expiry_minutes)).timestamp())
    
    doc_data = {
        "message": message,
        "created_at": int(time.time()),
        "expiry": expiry_ts,
        "opened": False
    }

    # Save to Firebase
    try:
        db.collection("links").document(link_id).set(doc_data)
        
        # Generate Link
        base_url = get_public_base_url()
        share_link = f"{base_url}/?id={link_id}"

        st.success("🎉 Your surprise link is ready!")
        st.code(share_link)

        # QR Code
        col1, col2 = st.columns([1, 2])
        with col1:
            qr = generate_qr(share_link)
            st.image(qr, caption="Scan to open", width=150)
        with col2:
            st.info("""
            **How it works:**
            1. Share the link or QR code.
            2. The recipient can view it **once**.
            3. After that, it locks forever.
            """)

    except Exception as e:
        st.error(f"Error saving to database: {e}")
